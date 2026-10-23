#!/usr/bin/env python3
"""全量 systemd user 健康巡检 + 报告。"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPORT = Path.home() / ".local/state/systemd-audit/latest.json"
STATE = Path.home() / ".local/state/systemd-audit"


def run(cmd: list[str], timeout: int = 20) -> dict:
    import time
    started = time.monotonic()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": p.returncode == 0,
            "rc": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr.strip()[:300],
            "ms": round((time.monotonic() - started) * 1000),
        }
    except Exception as exc:
        return {"ok": False, "rc": 1, "stdout": "", "stderr": str(exc)[:160], "ms": 0}


def parse_show() -> list[dict]:
    p = run(["systemctl", "--user", "show", "-p", "Id", "-p", "LoadState", "-p", "ActiveState", "-p", "SubState", "-p", "Description", "--type=service", "--type=timer"])
    units: list[dict] = []
    if not p["ok"]:
        return units
    current: dict = {}
    for line in p["stdout"].splitlines():
        line = line.strip()
        if not line:
            if current:
                units.append(current)
                current = {}
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            current[key] = val
    if current:
        units.append(current)
    return units


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    units = parse_show()
    failed = [u for u in units if u.get("ActiveState") == "failed"]
    not_found = [u for u in units if u.get("LoadState") == "not-found"]
    unknown = [u for u in units if u.get("ActiveState") == "failed" or u.get("LoadState") == "not-found"]
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    summary = {
        "ts": now,
        "total": len(units),
        "failed_count": len(failed),
        "not_found_count": len(not_found),
        "unknown_count": len(unknown),
        "failed": failed,
        "not_found": not_found,
        "unknown": unknown,
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
