#!/usr/bin/env python3
"""Sensor: CPU/Memory/Disk metrics from /proc."""

import subprocess, json

BINDIR = "/run/current-system/sw/bin"

def _run(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""


def collect() -> dict:
    cpu = _run(f"{BINDIR}/top -bn1 | {BINDIR}/grep 'Cpu(s)' | {BINDIR}/awk '{{print $2}}'")
    mem = _run(f"{BINDIR}/free -m | {BINDIR}/awk 'NR==2{{printf \"%s/%s\", $3,$2}}'")
    disk = _run(f"{BINDIR}/df -h /mnt/ai 2>/dev/null | {BINDIR}/tail -1 | {BINDIR}/awk '{{print $5}}'")
    return {"cpu_usage": cpu, "memory_usage": mem, "disk_ai": disk}


if __name__ == "__main__":
    print(json.dumps(collect()))
