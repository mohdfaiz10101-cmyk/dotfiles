#!/usr/bin/env python3
"""Sensor: High CPU process detection (>50%)."""

import subprocess, json


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""


def collect() -> dict:
    hogs = []
    raw = _run(
        "ps -eo pid,comm,%cpu --sort=-%cpu | awk 'NR>1 && $3+0>50{print $1,$2,$3}' | head -3"
    )
    for line in (raw or "").strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            hogs.append({"pid": parts[0], "name": parts[1], "cpu": parts[2]})
    return {"cpu_hogs": hogs}


if __name__ == "__main__":
    print(json.dumps(collect()))
