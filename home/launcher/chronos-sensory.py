#!/usr/bin/env python3
"""Chronos Sensory — System load ambient sound generator."""

import json
import math
import os
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

STATE_DIR = Path(Path.home() / ".local/state/chronos")
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "sensory_state.json"

SAMPLE_RATE = 22050
FFPLAY = "/run/current-system/sw/bin/ffplay"

# Intense threshold duration for bio-feedback cross-module trigger
INTENSE_SUSTAINED_FILE = STATE_DIR / "sensory_intense_sustained"


class SystemMetrics:
    def __init__(self):
        self.prev_idle = 0
        self.prev_total = 0
        self.first_sample = True

    def get_cpu_pct(self) -> float:
        try:
            with open("/proc/stat") as f:
                line = f.readline()
            parts = line.split()[1:]
            vals = [int(x) for x in parts]
            idle = vals[3]
            total = sum(vals)

            if self.first_sample:
                self.prev_idle = idle
                self.prev_total = total
                self.first_sample = False
                return 0.0

            diff_idle = idle - self.prev_idle
            diff_total = total - self.prev_total
            self.prev_idle = idle
            self.prev_total = total

            if diff_total == 0:
                return 0.0
            return (1.0 - diff_idle / diff_total) * 100.0
        except Exception:
            return 0.0

    def get_gpu_pct(self) -> float:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            return float(r.stdout.strip())
        except Exception:
            return 0.0

    @staticmethod
    def combined(cpu: float, gpu: float) -> float:
        return cpu * 0.6 + gpu * 0.4


PROFILES = {
    "calm": {
        "freqs": [174, 285],
        "amps": [0.3, 0.15],
        "duration": 8.0,
        "fade": 2.0,
    },
    "active": {
        "freqs": [396, 528],
        "amps": [0.25, 0.2],
        "duration": 6.0,
        "fade": 1.0,
    },
    "intense": {
        "freqs": [60, 120, 240],
        "amps": [0.35, 0.2, 0.1],
        "duration": 3.0,
        "fade": 0.3,
        "pulse_hz": 2.0,
    },
}


def _select_profile(load: float) -> str:
    if load < 30:
        return "calm"
    elif load < 70:
        return "active"
    return "intense"


def _make_wav_numpy(profile: dict) -> bytes:
    dur = profile["duration"]
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    wave = np.zeros(n, dtype=np.float64)

    for freq, amp in zip(profile["freqs"], profile["amps"]):
        wave += amp * np.sin(2 * math.pi * freq * t)

    # Pulse modulation for intense mode
    if "pulse_hz" in profile:
        pulse = 0.5 * (1 + np.sign(np.sin(2 * math.pi * profile["pulse_hz"] * t)))
        wave *= pulse

    # Envelope: fade in/out
    fade_samples = int(SAMPLE_RATE * profile["fade"])
    if fade_samples > 0 and fade_samples < n // 2:
        envelope = np.ones(n)
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        wave *= envelope

    # Normalize
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak * 0.85
    samples = (wave * 32767).astype(np.int16)

    return _wrap_wav(samples.tobytes())


def _make_wav_stdlib(profile: dict) -> bytes:
    dur = profile["duration"]
    n = int(SAMPLE_RATE * dur)
    fade_samples = int(SAMPLE_RATE * profile["fade"])
    data = bytearray()

    for i in range(n):
        t = i / SAMPLE_RATE
        val = 0.0
        for freq, amp in zip(profile["freqs"], profile["amps"]):
            val += amp * math.sin(2 * math.pi * freq * t)

        # Pulse modulation
        if "pulse_hz" in profile:
            pulse = 0.5 * (1 + math.copysign(1, math.sin(2 * math.pi * profile["pulse_hz"] * t)))
            val *= pulse

        # Envelope
        if i < fade_samples:
            val *= i / fade_samples
        elif i > n - fade_samples:
            val *= (n - i) / fade_samples

        clamped = max(-32767, min(32767, int(val * 32767 * 0.85)))
        data += struct.pack("<h", clamped)

    return _wrap_wav(bytes(data))


def _wrap_wav(pcm_data: bytes) -> bytes:
    """Wrap raw PCM data into a WAV file bytes."""
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,           # chunk size
        1,            # PCM
        1,            # mono
        SAMPLE_RATE,
        SAMPLE_RATE * 2,  # byte rate
        2,            # block align
        16,           # bits per sample
        b"data",
        data_size,
    )
    return header + pcm_data


class AudioPlayer:
    def __init__(self):
        self.proc = None

    def play(self, wav_bytes: bytes):
        self.stop()
        try:
            self.proc = subprocess.Popen(
                [FFPLAY, "-autoexit", "-nodisp", "-loglevel", "quiet", "-f", "wav", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.proc.stdin.write(wav_bytes)
            self.proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=3)
        self.proc = None


class SensoryEngine:
    def __init__(self):
        self.metrics = SystemMetrics()
        self.player = AudioPlayer()
        self.current_profile = None
        self.intense_since = None
        self.tick = 5.0

    def run(self):
        signal.signal(signal.SIGTERM, lambda *_: self._shutdown())

        # Check if user is idle (cross-module: if bio-feedback says idle, mute)
        print("[OK] Chronos Sensory started", file=sys.stderr)
        if HAS_NUMPY:
            print("[OK] numpy accelerated", file=sys.stderr)
        else:
            print("[WARN] stdlib fallback (no numpy)", file=sys.stderr)

        # First sample to baseline CPU
        self.metrics.get_cpu_pct()
        time.sleep(1)

        while True:
            is_idle = self._is_system_idle()
            cpu = self.metrics.get_cpu_pct()
            gpu = self.metrics.get_gpu_pct()
            load = self.metrics.combined(cpu, gpu)
            new_profile = _select_profile(load)

            # Cross-module: mute when idle
            if is_idle:
                if self.current_profile is not None:
                    self.player.stop()
                    self.current_profile = None
                self._write_state(load, "muted")
                time.sleep(self.tick)
                continue

            # Track sustained intense
            if new_profile == "intense":
                if self.intense_since is None:
                    self.intense_since = time.time()
                elif time.time() - self.intense_since > 600:  # 10 min
                    INTENSE_SUSTAINED_FILE.write_text(
                        json.dumps({"since": self.intense_since, "load": load})
                    )
            else:
                self.intense_since = None
                INTENSE_SUSTAINED_FILE.unlink(missing_ok=True)

            if new_profile != self.current_profile:
                print(f"[{new_profile.upper()}] load={load:.1f}% cpu={cpu:.1f} gpu={gpu:.1f}",
                      file=sys.stderr)
                profile = PROFILES[new_profile]
                if HAS_NUMPY:
                    wav = _make_wav_numpy(profile)
                else:
                    wav = _make_wav_stdlib(profile)
                self.player.play(wav)
                self.current_profile = new_profile

            self._write_state(load, self.current_profile or "calm")
            time.sleep(self.tick)

    def _is_system_idle(self) -> bool:
        """Check loginctl + bio-feedback state."""
        try:
            r = subprocess.run(
                ["loginctl", "show-session", "2", "-p", "IdleHint"],
                capture_output=True, text=True, timeout=5,
            )
            if "IdleHint=yes" in r.stdout:
                return True
        except Exception:
            pass

        # Cross-module: check bio-feedback state
        bf_file = STATE_DIR / "biofeedback_state.json"
        if bf_file.exists():
            try:
                bf = json.loads(bf_file.read_text())
                if bf.get("idle", False):
                    return True
            except (json.JSONDecodeError, KeyError):
                pass
        return False

    def _write_state(self, load: float, profile: str):
        state = {
            "load": round(load, 1),
            "profile": profile,
            "numpy": HAS_NUMPY,
            "timestamp": time.time(),
        }
        STATE_FILE.write_text(json.dumps(state, indent=2))

    def _shutdown(self):
        self.player.stop()
        INTENSE_SUSTAINED_FILE.unlink(missing_ok=True)
        print("[OK] Sensory stopped", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    SensoryEngine().run()
