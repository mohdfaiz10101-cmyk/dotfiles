#!/usr/bin/env python3
"""Sensor: Service health checks (systemd + HTTP)."""

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
    status = {}
    # User systemd services
    for svc in ["hub-api", "agi-brain"]:
        out = _run(f"systemctl --user is-active {svc} 2>/dev/null || echo inactive")
        status[svc] = out if out else "unknown"
    # Docker/HTTP services
    checks = {
        "letta": "http://localhost:8283/v1/health",
        "litellm": "http://localhost:4000/health",
        "chromadb": "http://localhost:8000/api/v2/heartbeat",
    }
    for name, url in checks.items():
        code = _run(
            f"/run/current-system/sw/bin/curl -sL -o /dev/null -w '%{{http_code}}' --max-time 3 '{url}' 2>/dev/null"
        )
        status[name] = (
            "active" if code in ("200", "401", "404") else f"inactive(http={code})"
        )
    return {"services": status}


if __name__ == "__main__":
    print(json.dumps(collect()))
