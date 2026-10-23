#!/usr/bin/env python3
"""网络巡检与修复工作流 — Hermes integration layer。

整合现有监控系统（network-scenario-monitor、network-resilience-guard、
mihomo-guardian、uptime-kuma）的输出，统一告警与 Kanban 任务。

用法:
  network-workflow.py inspect          # 只巡检，输出报告
  network-workflow.py check            # 巡检 + 自动修复
  network-workflow.py report           # 巡检 + 修复 + 告警 + 任务
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path(os.environ.get("HOME", "/var/home/charlie"))
HERMES_BIN = HOME / ".local/bin/hermes"
STATE = HOME / ".local/state/network-workflow"
REPORT_JSON = STATE / "latest.json"
REPORT_MD = STATE / "latest.md"
HISTORY = STATE / "events.jsonl"

NETWORK_SCENARIO_JSON = HOME / ".local/state/network-scenario-monitor/latest.json"
NETWORK_RESILIENCE_JSON = HOME / ".local/state/network-resilience/latest.json"
KUMA_DB = HOME / ".local/share/uptime-kuma/kuma.db"
NTFY_SEND = HOME / ".local/bin/ntfy-send"
NTFY_TOPIC = "charlie-network"
NETWORK_DASHBOARD = "http://100.120.189.27:19979"

CRITICAL_PORTS = {
    "mihomo_api": 9091,
    "mihomo_proxy": 7890,
    "hub": 9800,
    "opencode": 18910,
    "uptime_kuma": 3002,
    "network_dashboard": 19979,
    "ntfy": 2586,
    "sub2api": 19090,
    "phone_mcp": 8080,
}

CRITICAL_SERVICES = [
    "frpc.service",
    "container-ntfy.service",
    "network-scenario-monitor.timer",
    "network-resilience-guard.timer",
    "uptime-kuma.service",
    "hermes-web-ui.service",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], timeout: int = 20, env: dict | None = None) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()[:500],
            "ms": round((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "rc": 124, "stdout": "", "stderr": "timeout", "ms": round((time.monotonic() - started) * 1000)}
    except FileNotFoundError:
        return {"ok": False, "rc": 127, "stdout": "", "stderr": "not found", "ms": 0}


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def service_active(name: str) -> bool:
    return run(["systemctl", "--user", "is-active", "--quiet", name])["ok"]


def tcp_probe(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    import socket

    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "latency_ms": round((time.monotonic() - started) * 1000)}
    except OSError as exc:
        return {"ok": False, "latency_ms": None, "error": str(exc)[:160]}


def inspect_netbird() -> dict[str, Any]:
    """检查 NetBird 接口和手机连通性。"""
    result: dict[str, Any] = {"iface": None, "phone_ping": None, "management": None}
    ip_out = run(["ip", "-br", "link", "show", "wt0"])
    if ip_out["ok"] and "UP" in ip_out["stdout"]:
        result["iface"] = "up"
    elif ip_out["ok"]:
        result["iface"] = "down"
    else:
        result["iface"] = "missing"

    ping_out = run(["ping", "-c", "2", "-W", "2", "100.87.37.3"])
    result["phone_ping"] = "ok" if ping_out["ok"] else "fail"

    mgmt = tcp_probe("api.netbird.io", 443)
    result["management"] = "ok" if mgmt["ok"] else "fail"
    result["management_latency_ms"] = mgmt.get("latency_ms")

    result["ok"] = result["iface"] == "up" and result["management"] == "ok"
    return result


def inspect_kuma() -> dict[str, Any]:
    """检查 Uptime Kuma 容器状态和监控项。"""
    result: dict[str, Any] = {"service": None, "port": None, "monitors": []}
    result["service"] = "active" if service_active("uptime-kuma.service") else "inactive"
    result["port"] = "open" if tcp_probe("127.0.0.1", 3002)["ok"] else "closed"
    try:
        import sqlite3
        con = sqlite3.connect(str(KUMA_DB))
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT id, name, type, hostname, port, active FROM monitor ORDER BY id")
        for row in cur.fetchall():
            monitor = dict(row)
            cur.execute(
                "SELECT status, msg, time FROM heartbeat WHERE monitor_id=? ORDER BY id DESC LIMIT 1",
                (monitor["id"],),
            )
            hb = cur.fetchone()
            if hb:
                monitor["last_status"] = hb["status"]
                monitor["last_msg"] = hb["msg"][:200] if hb["msg"] else ""
                monitor["last_time"] = hb["time"]
            result["monitors"].append(monitor)
        con.close()
    except Exception as exc:
        result["error"] = str(exc)[:200]

    down_monitors = [m for m in result["monitors"] if m.get("last_status") == 0 and m.get("active")]
    result["down_count"] = len(down_monitors)
    result["ok"] = result["service"] == "active" and result["port"] == "open" and result["down_count"] == 0
    return result


def inspect_mihomo() -> dict[str, Any]:
    """检查 Mihomo 代理健康。"""
    result: dict[str, Any] = {"service": None, "api": None, "proxy_port": None, "check_output": ""}
    # 用户级 mihomo 可能不叫 mihomo.service，不强依赖 systemd
    result["service"] = "active" if service_active("mihomo.service") else "unknown"
    result["api"] = "ok" if tcp_probe("127.0.0.1", 9091)["ok"] else "fail"
    result["proxy_port"] = "ok" if tcp_probe("127.0.0.1", 7890)["ok"] else "fail"

    # 运行 mihomo-guardian --check
    guardian = run([str(HOME / ".local/bin/mihomo-guardian"), "--check"], timeout=120)
    result["check_output"] = guardian.get("stdout", "") + "\n" + guardian.get("stderr", "")
    result["check_rc"] = guardian["rc"]
    result["ok"] = result["service"] in ("active", "unknown") and result["proxy_port"] == "ok"
    return result


def inspect_5g_portable() -> dict[str, Any]:
    """检查 5G/随身 WiFi / USB 网卡状态。"""
    result: dict[str, Any] = {"wifi_devices": [], "cellular": False, "nmcli_available": False}
    nmcli = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"])
    if nmcli["ok"]:
        result["nmcli_available"] = True
        for line in nmcli["stdout"].splitlines():
            parts = line.split(":")
            if len(parts) >= 3:
                device, dtype, state = parts[0], parts[1], parts[2]
                entry = {"device": device, "type": dtype, "state": state}
                if dtype == "wifi":
                    entry["signal"] = None
                    sig = run(["nmcli", "-t", "-f", "DEVICE,SIGNAL", "device", "wifi", "list", "ifname", device])
                    if sig["ok"]:
                        signals = []
                        for row in sig["stdout"].splitlines():
                            ss = row.split(":")
                            if len(ss) >= 2 and ss[0]:
                                try:
                                    signals.append(int(ss[1]))
                                except ValueError:
                                    pass
                        if signals:
                            entry["signal"] = max(signals)
                    result["wifi_devices"].append(entry)
                elif dtype in ("gsm", "cdma", "nfc"):
                    result["cellular"] = True
                    entry["signal"] = None
                    result.setdefault("cellular_details", []).append(entry)
    else:
        result["nmcli_error"] = nmcli.get("stderr", "")

    result["ok"] = any(d.get("state") == "connected" for d in result.get("wifi_devices", [])) or not result["wifi_devices"]
    return result


def inspect_adb() -> dict[str, Any]:
    """检查 ADB 连通性：本地 FRP 隧道 + NetBird 直连。"""
    result: dict[str, Any] = {"local": None, "netbird": None}
    result["local"] = "ok" if tcp_probe("127.0.0.1", 15555)["ok"] else "fail"
    netbird = tcp_probe("100.87.37.3", 15555)
    result["netbird"] = "ok" if netbird["ok"] else "fail"
    result["netbird_latency_ms"] = netbird.get("latency_ms")
    result["ok"] = result["local"] == "ok" or result["netbird"] == "ok"
    return result


def inspect_phone_mcp() -> dict[str, Any]:
    """检查手机 MCP 服务 (agent-comms) 连通性。"""
    result: dict[str, Any] = {"tcp": None, "http": None, "body": ""}
    tcp = tcp_probe("100.87.37.3", 8080)
    result["tcp"] = "ok" if tcp["ok"] else "fail"
    result["tcp_latency_ms"] = tcp.get("latency_ms")

    token = os.environ.get("PHONE_MCP_TOKEN", "5c53af5e-082a-47f7-b4cb-473090106a82")
    curl = run(
        [
            "curl", "-k", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
            "--max-time", "10",
            "-H", f"Authorization: Bearer {token}",
            "https://100.87.37.3:8080/mcp",
        ],
        timeout=15,
    )
    result["http"] = str(curl.get("stdout", ""))
    result["curl_rc"] = curl["rc"]
    result["ok"] = result["tcp"] == "ok" and result["http"] in ("200", "401", "403")
    return result


def inspect_app_connectivity() -> dict[str, Any]:
    """检查 App/服务网络连接稳定性。"""
    result: dict[str, Any] = {"ports": {}, "services": {}}
    for name, port in CRITICAL_PORTS.items():
        result["ports"][name] = tcp_probe("127.0.0.1", port)
    for svc in CRITICAL_SERVICES:
        result["services"][svc] = service_active(svc)
    failed_ports = [k for k, v in result["ports"].items() if not v.get("ok")]
    failed_services = [k for k, v in result["services"].items() if not v]
    result["ok"] = not failed_ports and not failed_services
    result["failed_ports"] = failed_ports
    result["failed_services"] = failed_services
    return result


def build_report() -> dict[str, Any]:
    """汇总所有检查结果。"""
    report: dict[str, Any] = {
        "ts": now_iso(),
        "sources": {},
        "issues": [],
        "suggested_repairs": [],
    }

    # 1. network-scenario-monitor
    scenario = read_json(NETWORK_SCENARIO_JSON)
    if scenario:
        report["sources"]["network_scenario"] = {
            "classification": scenario.get("classification", {}).get("level"),
            "failures": scenario.get("classification", {}).get("failures", []),
            "desktop_scenario": scenario.get("desktop", {}).get("scenario"),
        }
        for issue in scenario.get("classification", {}).get("failures", []):
            report["issues"].append(f"scenario:{issue}")

    # 2. network-resilience-guard
    resilience = read_json(NETWORK_RESILIENCE_JSON)
    if resilience:
        report["sources"]["network_resilience"] = {
            "layer": resilience.get("layer"),
            "wifi_gateway": resilience.get("wifi_gateway"),
            "router": resilience.get("router"),
            "direct_https": resilience.get("direct_https"),
            "mihomo_https": resilience.get("mihomo_https"),
        }
        layer = resilience.get("layer")
        if layer and layer != "healthy":
            report["issues"].append(f"resilience:layer={layer}")

    # 3. NetBird
    netbird = inspect_netbird()
    report["sources"]["netbird"] = netbird
    if not netbird.get("ok"):
        report["issues"].append("netbird:unhealthy")

    # 4. Mihomo
    mihomo = inspect_mihomo()
    report["sources"]["mihomo"] = mihomo
    if not mihomo.get("ok"):
        report["issues"].append("mihomo:unhealthy")

    # 5. 5G/Portable WiFi
    portable = inspect_5g_portable()
    report["sources"]["5g_portable"] = portable
    if not portable.get("ok"):
        report["issues"].append("5g_portable:wifi_or_cellular_down")

    # 6. 手机 MCP 服务（依赖 NetBird 连通）
    mcp = inspect_phone_mcp()
    report["sources"]["phone_mcp"] = mcp
    if not mcp.get("ok"):
        report["issues"].append("phone_mcp:unreachable")

    # 8. App 连通性
    app = inspect_app_connectivity()
    report["sources"]["app"] = app
    for port in app.get("failed_ports", []):
        report["issues"].append(f"app_port:{port}")
    for svc in app.get("failed_services", []):
        report["issues"].append(f"app_service:{svc}")

    # 7. Kuma
    kuma = inspect_kuma()
    report["sources"]["kuma"] = kuma
    if not kuma.get("ok"):
        report["issues"].append("kuma:unhealthy")

    # 去重
    report["issues"] = sorted(set(report["issues"]))
    report["ok"] = not report["issues"]
    return report


def auto_repair(report: dict[str, Any]) -> list[str[str]]:
    """根据问题自动修复，返回已执行的修复列表。"""
    repairs: list[str] = []
    issues = report.get("issues", [])

    # Kuma 问题 -> 重启 Kuma
    if any("kuma" in issue for issue in issues):
        proc = run(["systemctl", "--user", "restart", "uptime-kuma.service"], timeout=45)
        repairs.append(f"restart uptime-kuma rc={proc['rc']}")

    # Mihomo 问题 -> mihomo-guardian --check
    if any("mihomo" in issue or "proxy" in issue for issue in issues):
        proc = run([str(HOME / ".local/bin/mihomo-guardian"), "--check"], timeout=180)
        repairs.append(f"mihomo-guardian --check rc={proc['rc']}")
        if proc["ok"]:
            pass  # 已自动修复

    # 网络层问题 -> network-resilience-maintenance
    if any("resilience" in issue or "wan" in issue or "router" in issue for issue in issues):
        proc = run([str(HOME / ".local/bin/network-resilience-maintenance")], timeout=180)
        repairs.append(f"network-resilience-maintenance rc={proc['rc']}")

    # FRP 问题 -> 重启 frpc
    if any("frpc" in issue or "frp" in issue for issue in issues):
        proc = run(["systemctl", "--user", "restart", "frpc.service"], timeout=30)
        repairs.append(f"restart frpc rc={proc['rc']}")

    # 手机 MCP 问题 -> 记录故障，暂不自动重启（依赖手机侧）
    if any("phone_mcp" in issue for issue in issues):
        repairs.append("phone_mcp_unreachable_check_phone")

    # WiFi 断连 -> network-guard
    if any("wifi" in issue.lower() for issue in issues):
        proc = run(["bash", str(HOME / "dotfiles/bin/network-guard.sh")], timeout=120)
        repairs.append(f"network-guard rc={proc['rc']}")

    return repairs


def ensure_kuma_monitors() -> None:
    """确保 Kuma 中存在关键网络监控项（幂等）。"""
    desired = [
        {"name": "Mihomo · API", "type": "http", "hostname": "127.0.0.1", "port": 9091, "path": "/", "interval": 120},
        {"name": "Mihomo · Proxy", "type": "port", "hostname": "127.0.0.1", "port": 7890, "interval": 120},
        {"name": "Hub · 9800", "type": "http", "hostname": "127.0.0.1", "port": 9800, "path": "/", "interval": 120},
        {"name": "OpenCode · 18910", "type": "port", "hostname": "127.0.0.1", "port": 18910, "interval": 120},
        {"name": "DuckDNS · 2225", "type": "port", "hostname": "charlie1990.duckdns.org", "port": 2225, "interval": 120},
        {"name": "NetBird · Management", "type": "ping", "hostname": "api.netbird.io", "interval": 120},
        {"name": "Sub2API · 19090", "type": "http", "hostname": "127.0.0.1", "port": 19090, "path": "/v1/models", "interval": 300},
        {"name": "Phone · MCP", "type": "port", "hostname": "100.87.37.3", "port": 8080, "interval": 120},
    ]
    try:
        import urllib.request

        existing = []
        try:
            with urllib.request.urlopen("http://127.0.0.1:3002/api/monitors", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
                if isinstance(data, list):
                    existing = [m.get("name") for m in data if isinstance(m, dict)]
                elif isinstance(data, dict):
                    existing = [m.get("name") for m in data.get("monitors", []) if isinstance(m, dict)]
        except Exception as exc:
            print(f"[WARN] kuma list monitors failed: {exc}", file=sys.stderr)

        added = 0
        for mon in desired:
            if mon["name"] in existing:
                continue
            payload = json.dumps(mon, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:3002/api/add-monitor",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    resp.read()
                added += 1
            except Exception as exc:
                print(f"[WARN] kuma add monitor {mon['name']} failed: {exc}", file=sys.stderr)
        if added:
            print(f"[OK] kuma added {added} monitors")
    except Exception as exc:
        print(f"[WARN] kuma monitor setup failed: {exc}", file=sys.stderr)


def create_kanban(report: dict[str, Any]) -> None:
    """在 network-maintenance 看板创建故障任务。"""
    issues = report.get("issues", [])
    if not issues:
        return

    title = f"网络巡检异常: {', '.join(issues[:3])}"
    body = json.dumps(report, ensure_ascii=False, indent=2)
    env = os.environ.copy()
    env["HERMES_KANBAN_BOARD"] = "network-maintenance"
    proc = run(
        [str(HERMES_BIN), "kanban", "create", "--priority", "2", "--body", body, "--json", title],
        timeout=30,
        env=env,
    )
    if not proc["ok"]:
        print(f"[WARN] kanban create failed: {proc['stderr']}", file=sys.stderr)


def notify_network(title: str, message: str) -> None:
    """发送 ntfy 通知到 charlie-network。"""
    env = os.environ.copy()
    env.update({
        "NTFY_CLICK": NETWORK_DASHBOARD,
        "NTFY_PRIORITY": "high" if "异常" in title or "unhealthy" in message else "default",
    })
    proc = run([str(NTFY_SEND), NTFY_TOPIC, title, message], timeout=15, env=env)
    if not proc["ok"]:
        print(f"[WARN] ntfy send failed: {proc['stderr']}", file=sys.stderr)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# 网络巡检报告",
        f"",
        f"- 时间: `{report['ts']}`",
        f"- 状态: `{' healthy ' if report['ok'] else ' degraded '}`",
        f"- 问题数: `{len(report.get('issues', []))}`",
        "",
        "## 数据源",
    ]
    for name, data in report.get("sources", {}).items():
        lines.append(f"- **{name}**: `{json.dumps(data, ensure_ascii=False)[:500]}`")

    if report.get("issues"):
        lines += ["", "## 问题"]
        lines += [f"- `{issue}`" for issue in report["issues"]]

    repairs = report.get("repairs", [])
    if repairs:
        lines += ["", "## 已执行修复"]
        lines += [f"- `{r}`" for r in repairs]

    return "\n".join(lines) + "\n"


def cmd_inspect() -> dict[str, Any]:
    report = build_report()
    STATE.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return report


def cmd_check() -> dict[str, Any]:
    report = cmd_inspect()
    if not report.get("ok"):
        repairs = auto_repair(report)
        report["repairs"] = repairs
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
        print("\n".join([f"[REPAIR] {r}" for r in repairs]))
    return report


def cmd_report() -> dict[str, Any]:
    report = cmd_check()
    if not report.get("ok"):
        title = f"网络巡检异常: {', '.join(report.get('issues', [])[:3])}"
        message = render_markdown(report)
        notify_network(title, message)
        create_kanban(report)
        print(f"[OK] notified + kanban created")
    else:
        print("[OK] all healthy")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Network workflow")
    parser.add_argument("command", choices=["inspect", "check", "report"], nargs="?", default="report")
    args = parser.parse_args()

    if args.command == "inspect":
        cmd_inspect()
    elif args.command == "check":
        cmd_check()
    elif args.command == "report":
        cmd_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
