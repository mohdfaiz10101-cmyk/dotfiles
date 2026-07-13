#!/usr/bin/env python3
"""Chronos Bio-feedback — 屏幕时间监控 + KDE 自适应调节"""

import json
import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

STATE_DIR = Path(Path.home() / ".local/state/chronos")
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "biofeedback_state.json"

TICK_INTERVAL = 10  # seconds

# Protection thresholds (minutes)
LEVEL_CAUTION = 45
LEVEL_WARNING = 60
LEVEL_CRITICAL = 120

# Keyboard device paths for activity detection
KBD_GLOB = "/dev/input/by-path/*-event-kbd"


class IdleDetector:
    """Detect user idle via loginctl."""

    @staticmethod
    def is_idle() -> bool:
        try:
            r = subprocess.run(
                ["loginctl", "show-session", "2", "-p", "IdleHint"],
                capture_output=True, text=True, timeout=5,
            )
            return "IdleHint=yes" in r.stdout
        except Exception:
            return False


class ActivityMeter:
    """Keyboard activity rate via /dev/input mtime changes."""

    def __init__(self):
        self.history = []  # list of (timestamp, total_mtime)
        self.window = 300  # 5-minute sliding window

    def _get_total_mtime(self) -> float:
        import glob
        total = 0.0
        for p in glob.glob(KBD_GLOB):
            try:
                total += os.stat(p).st_mtime
            except OSError:
                pass
        return total

    def get_rate(self) -> float:
        now = time.time()
        mtime_sum = self._get_total_mtime()
        self.history.append((now, mtime_sum))

        cutoff = now - self.window
        self.history = [(t, v) for t, v in self.history if t > cutoff]

        if len(self.history) < 2:
            return 0.0

        dt = self.history[-1][0] - self.history[0][0]
        dv = self.history[-1][1] - self.history[0][1]
        if dt <= 0:
            return 0.0

        # mtime changes per second across all keyboards
        rate = dv / dt
        # Normalize: ~5 changes/sec = high activity
        return min(1.0, rate / 5.0)


class KDEController:
    """KDE Plasma brightness / Night Color / contrast control."""

    def __init__(self):
        self.qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
        self.kde_available = bool(self.qdbus)
        self.original_brightness = self._get_brightness()
        self.night_active = False
        self.contrast_changed = False

    def _get_brightness(self) -> int:
        if not self.kde_available:
            return 10000
        try:
            r = subprocess.run(
                [self.qdbus, "org.kde.ScreenBrightness",
                 "/org/kde/ScreenBrightness/display0",
                 "org.kde.ScreenBrightness.Display.Brightness"],
                capture_output=True, text=True, timeout=5,
            )
            return int(r.stdout.strip())
        except (ValueError, subprocess.TimeoutExpired, FileNotFoundError):
            return 10000

    def _set_brightness(self, value: int):
        if not self.kde_available:
            return
        subprocess.run(
            [self.qdbus, "org.kde.ScreenBrightness",
             "/org/kde/ScreenBrightness/display0",
             "org.kde.ScreenBrightness.Display.SetBrightness",
             str(value), "0"],
            timeout=5, check=False,
        )

    def _enable_night_color(self):
        if self.night_active or not self.kde_available:
            return
        self.night_active = True
        subprocess.run(
            ["kwriteconfig6", "--file", "kwinrc",
             "--group", "NightColor", "--key", "Active", "true",
             "--group", "NightColor", "--key", "Mode", "Constant",
             "--group", "NightColor", "--key", "NightTemperature", "4500"],
            timeout=5, check=False,
        )
        subprocess.run(
            [self.qdbus, "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
            timeout=5, check=False,
        )

    def _disable_night_color(self):
        if not self.night_active or not self.kde_available:
            return
        self.night_active = False
        subprocess.run(
            ["kwriteconfig6", "--file", "kwinrc",
             "--group", "NightColor", "--key", "Active", "false"],
            timeout=5, check=False,
        )
        subprocess.run(
            [self.qdbus, "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
            timeout=5, check=False,
        )

    def _lower_contrast(self):
        if self.contrast_changed or not self.kde_available:
            return
        self.contrast_changed = True
        globals_path = os.path.expanduser("~/.config/kdeglobals")
        subprocess.run(
            ["kwriteconfig6", "--file", globals_path,
             "--group", "ColorEffects:Disabled",
             "--key", "ContrastEffect", "2",
             "--key", "ContrastAmount", "0.3"],
            timeout=5, check=False,
        )

    def _restore_contrast(self):
        if not self.contrast_changed or not self.kde_available:
            return
        self.contrast_changed = False
        globals_path = os.path.expanduser("~/.config/kdeglobals")
        subprocess.run(
            ["kwriteconfig6", "--file", globals_path,
             "--group", "ColorEffects:Disabled",
             "--key", "ContrastEffect", "0",
             "--key", "ContrastAmount", "0"],
            timeout=5, check=False,
        )

    def apply_level(self, level: str, screen_min: float):
        if level == "normal":
            self._restore()
        elif level == "caution":
            new_b = max(2000, int(self.original_brightness * 0.8))
            self._set_brightness(new_b)
            self._enable_night_color()
            self._lower_contrast()
        elif level == "warning":
            new_b = max(1500, int(self.original_brightness * 0.6))
            self._set_brightness(new_b)
            subprocess.run(
                ["notify-send", "-u", "normal", "-t", "10000",
                 "Chronos Bio-feedback",
                 f"已连续使用 {int(screen_min)} 分钟，建议短暂休息"],
                timeout=5, check=False,
            )
        elif level == "critical":
            self._set_brightness(800)
            subprocess.run(
                ["notify-send", "-u", "critical", "-t", "30000",
                 "Chronos: 强制休息",
                 "连续使用超过 2 小时，请立即离开屏幕休息"],
                timeout=5, check=False,
            )

    def _restore(self):
        self._set_brightness(self.original_brightness)
        self._disable_night_color()
        self._restore_contrast()


class BiofeedbackEngine:
    def __init__(self):
        self.idle = IdleDetector()
        self.meter = ActivityMeter()
        self.kde = KDEController()
        self.active_since = None
        self.current_level = "normal"

    def _compute_level(self, minutes: float) -> str:
        if minutes >= LEVEL_CRITICAL:
            return "critical"
        elif minutes >= LEVEL_WARNING:
            return "warning"
        elif minutes >= LEVEL_CAUTION:
            return "caution"
        return "normal"

    def run(self):
        signal.signal(signal.SIGTERM, lambda *_: self._shutdown())

        print("[OK] Chronos Bio-feedback started", file=sys.stderr)
        if not self.kde.kde_available:
            print("[WARN] qdbus/qdbus6 不可用，KDE 调节功能降级为仅记录与通知", file=sys.stderr)

        while True:
            is_idle = self.idle.is_idle()
            activity = self.meter.get_rate()

            if is_idle:
                # User idle — reset active timer
                self.active_since = None
                if self.current_level != "normal":
                    self.kde.apply_level("normal", 0)
                    self.current_level = "normal"
            else:
                if self.active_since is None:
                    self.active_since = time.time()
                screen_min = (time.time() - self.active_since) / 60
                new_level = self._compute_level(screen_min)

                if new_level != self.current_level:
                    print(f"[{new_level.upper()}] screen={screen_min:.0f}min activity={activity:.2f}",
                          file=sys.stderr)
                    self.kde.apply_level(new_level, screen_min)
                    self.current_level = new_level

            # Write state
            screen_min = 0.0
            if self.active_since and not is_idle:
                screen_min = (time.time() - self.active_since) / 60

            state = {
                "screen_minutes": round(screen_min, 1),
                "activity_rate": round(activity, 3),
                "protection_level": self.current_level,
                "idle": is_idle,
                "timestamp": time.time(),
            }
            STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

            time.sleep(TICK_INTERVAL)

    def _shutdown(self):
        print("[OK] Restoring KDE settings...", file=sys.stderr)
        self.kde.apply_level("normal", 0)
        sys.exit(0)


if __name__ == "__main__":
    BiofeedbackEngine().run()
