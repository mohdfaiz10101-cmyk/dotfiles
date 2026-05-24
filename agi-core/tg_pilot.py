#!/usr/bin/env python3
"""
tg_pilot.py — GLM 驱动的智能运维引擎 (L2-L5)
替代 Claude Code (CC)，用 GLM 模型实现：
  L2 对话运维: 自然语言命令 → 系统操作 → 结果回复
  L3 AI分诊:   通知分析 → 严重度判定 → 操作按钮
  L4 自主修复: 故障检测 → GLM诊断 → 自动修复(3轮) → 升级
  L5 预判感知: 指标趋势 → 异常检测 → 提前预警

模型: GLM-5.1(分析/诊断), GLM-4.7(快速分类), 均走 LiteLLM localhost:4000
"""

import asyncio
import json
import os
import subprocess
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import httpx

# ── 配置 ──────────────────────────────────────────────────────────────

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://localhost:4000/v1")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "sk-litellm-charlie-2026")
PROXY = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")

# 模型分配
MODEL_ANALYZE = "glm-5.1"       # L3 分析、L4 诊断
MODEL_FAST = "glm-4.7"           # L2 命令识别、L5 异常检测

STATE_DIR = Path.home() / ".local/state/tg-pilot"
METRICS_DB = STATE_DIR / "metrics.db"
STATE_DIR.mkdir(parents=True, exist_ok=True)


# ── L3: 通知分析 ─────────────────────────────────────────────────────

@dataclass
class NotificationAnalysis:
    severity: str       # critical/high/medium/low
    diagnosis: str      # 根因猜测（一句话）
    suggestion: str     # 建议操作
    actions: list       # [(label, callback_data), ...]
    category: str       # 分类修正
    needs_attention: bool

NOTIFICATION_PROMPT = """你是运维AI。分析以下系统通知，用JSON格式输出（严格单行JSON，不要markdown包裹）：

{
  "severity": "critical|high|medium|low",
  "diagnosis": "根因猜测（≤30字）",
  "suggestion": "建议操作（≤30字）",
  "actions": [{"label": "按钮文字", "code": "action_code"}],
  "category": "system|service|security|wechat|patrol|proxy|task|info",
  "needs_attention": true/false
}

可用的 action_code:
- restart:<服务名>  重启服务
- logs:<服务名>     查看日志
- check:<服务名>     检查状态
- diag              完整诊断
- top               资源概览
- ignore            忽略

通知内容: """


async def analyze_notification(text: str) -> NotificationAnalysis:
    """L3: 用 GLM-5.1 分析通知，返回严重度+诊断+操作建议"""
    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            resp = await client.post(
                f"{LITELLM_BASE}/chat/completions",
                json={
                    "model": MODEL_ANALYZE,
                    "messages": [
                        {"role": "system", "content": "只用JSON回复，不要其他文字。"},
                        {"role": "user", "content": NOTIFICATION_PROMPT + text[:2000]}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.1,
                },
                headers={
                    "Authorization": f"Bearer {LITELLM_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            # 清洗 markdown 包裹
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            data = json.loads(raw)
        except Exception:
            # 降级：规则分类
            data = {
                "severity": "medium",
                "diagnosis": "自动分析暂不可用",
                "suggestion": "手动检查",
                "actions": [{"label": "诊断", "code": "diag"}],
                "category": "info",
                "needs_attention": True,
            }

    return NotificationAnalysis(
        severity=data.get("severity", "medium"),
        diagnosis=data.get("diagnosis", ""),
        suggestion=data.get("suggestion", ""),
        actions=data.get("actions", []),
        category=data.get("category", "info"),
        needs_attention=data.get("needs_attention", True),
    )


# ── L2: 对话运维（命令识别+执行）──────────────────────────────────────

CMD_PROMPT = """你是运维命令识别器。用户输入自然语言运维指令，输出JSON：
{
  "action": "check|restart|logs|status|exec|chat",
  "target": "服务名或命令",
  "is_dangerous": true/false
}

危险操作: reboot, shutdown, rm -rf, nixos-rebuild, format, dd

用户指令: """


@dataclass
class CommandResult:
    success: bool
    action: str
    target: str
    output: str
    error: str = ""


async def recognize_command(user_text: str) -> dict:
    """L2: 自然语言→运维命令识别"""
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(
                f"{LITELLM_BASE}/chat/completions",
                json={
                    "model": MODEL_FAST,
                    "messages": [
                        {"role": "system", "content": "只用JSON回复。"},
                        {"role": "user", "content": CMD_PROMPT + user_text[:500]}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.0,
                },
                headers={
                    "Authorization": f"Bearer {LITELLM_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            return json.loads(raw)
        except Exception:
            return {"action": "chat", "target": "", "is_dangerous": False}


async def execute_command(action: str, target: str) -> CommandResult:
    """L2: 执行运维操作（先试用户级，再试系统级）"""
    cmds = {
        "check": [["systemctl", "--user", "status", target, "--no-pager", "-l"],
                  ["systemctl", "status", target, "--no-pager", "-l"]],
        "restart": [["systemctl", "--user", "restart", target],
                    ["sudo", "systemctl", "restart", target]],
        "logs": [["journalctl", "--user", "-u", target, "--no-pager", "-n", "30"],
                 ["sudo", "journalctl", "-u", target, "--no-pager", "-n", "30"]],
        "docker-logs": [["docker", "logs", "--tail", "30", target]],
        "docker-restart": [["docker", "restart", target]],
        "status": [["systemctl", "--user", "is-active", target],
                   ["systemctl", "is-active", target]],
        "top": [["bash", "-c",
                "echo '=== CPU ===' && top -bn1 | head -5 && echo && "
                "echo '=== MEM ===' && free -h && echo && "
                "echo '=== DISK ===' && df -h / /mnt/ai /mnt/data 2>/dev/null"]],
    }

    if action in cmds:
        for cmd_variant in cmds[action]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd_variant,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=15.0
                )
                if proc.returncode == 0:
                    return CommandResult(
                        success=True,
                        action=action,
                        target=target,
                        output=stdout.decode("utf-8", errors="replace")[:2000],
                    )
                last_error = stderr.decode("utf-8", errors="replace")[:500]
            except asyncio.TimeoutError:
                last_error = "超时"
        return CommandResult(False, action, target, "", last_error or "所有级别均失败")

    elif action == "exec":
        try:
            proc = await asyncio.create_subprocess_shell(
                target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=15.0
            )
            return CommandResult(
                success=proc.returncode == 0,
                action="exec",
                target=target,
                output=stdout.decode("utf-8", errors="replace")[:2000],
                error=stderr.decode("utf-8", errors="replace")[:500],
            )
        except asyncio.TimeoutError:
            return CommandResult(False, "exec", target, "", "超时")

    return CommandResult(False, action, target, "", f"未知操作: {action}")


# ── L4: 自主修复 ─────────────────────────────────────────────────────-

DIAGNOSE_PROMPT = """你是资深运维。分析服务失败原因并给出修复步骤，JSON格式：

{{
  "root_cause": "根因（≤50字）",
  "fix_steps": ["步骤1", "步骤2", "步骤3"],
  "can_auto_fix": true/false,
  "risk": "low|medium|high",
  "escalate_reason": "如果不自动修复此处说明原因"
}}

服务: {service_name}
状态: {status_output}
日志: {logs_output}
"""


async def diagnose_failure(service_name: str) -> dict:
    """L4: GLM 诊断失败服务"""
    # 获取状态和日志
    status = subprocess.run(
        ["systemctl", "--user", "status", service_name, "--no-pager", "-l"],
        capture_output=True, text=True, timeout=10
    )
    logs = subprocess.run(
        ["journalctl", "--user", "-u", service_name, "--no-pager", "-n", "50"],
        capture_output=True, text=True, timeout=10
    )

    prompt = DIAGNOSE_PROMPT.format(
        service_name=service_name,
        status_output=status.stdout[:2000] or status.stderr[:500],
        logs_output=logs.stdout[:2000] or logs.stderr[:500],
    )

    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            resp = await client.post(
                f"{LITELLM_BASE}/chat/completions",
                json={
                    "model": MODEL_ANALYZE,
                    "messages": [
                        {"role": "system", "content": "只用JSON回复，不选markdown。"},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 400,
                    "temperature": 0.1,
                },
                headers={
                    "Authorization": f"Bearer {LITELLM_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            return json.loads(raw)
        except Exception:
            return {
                "root_cause": "诊断超时",
                "fix_steps": ["systemctl --user restart " + service_name],
                "can_auto_fix": True,
                "risk": "low",
                "escalate_reason": "",
            }


FIX_ACTIONS = {
    "restart": lambda svc: subprocess.run(
        ["systemctl", "--user", "restart", svc],
        capture_output=True, text=True, timeout=15
    ),
    "docker_restart": lambda svc: subprocess.run(
        ["docker", "restart", svc],
        capture_output=True, text=True, timeout=15
    ),
    "reset_failed": lambda svc: subprocess.run(
        ["systemctl", "--user", "reset-failed", svc],
        capture_output=True, text=True, timeout=10
    ),
    "docker_cleanup": lambda _: subprocess.run(
        ["docker", "container", "prune", "-f"],
        capture_output=True, text=True, timeout=30
    ),
}


async def heal_service(service_name: str, max_rounds: int = 3) -> dict:
    """L4: 自主修复 — 诊断→修复→验证 循环（最多3轮）"""
    result = {
        "service": service_name,
        "healed": False,
        "rounds": 0,
        "actions_taken": [],
        "final_diagnosis": "",
    }

    for round_num in range(1, max_rounds + 1):
        diagnosis = await diagnose_failure(service_name)
        result["rounds"] = round_num
        result["final_diagnosis"] = diagnosis.get("root_cause", "")

        if not diagnosis.get("can_auto_fix"):
            result["healed"] = False
            break

        for step in diagnosis.get("fix_steps", [])[:2]:  # 每次最多2步
            step_lower = step.lower()

            # 映射到实际操作
            if "restart" in step_lower and "docker" in step_lower:
                proc = FIX_ACTIONS["docker_restart"](service_name)
                result["actions_taken"].append(f"docker restart {service_name}")
            elif "restart" in step_lower or "systemctl" in step_lower:
                proc = FIX_ACTIONS["restart"](service_name)
                result["actions_taken"].append(f"systemctl restart {service_name}")
            elif "reset" in step_lower:
                proc = FIX_ACTIONS["reset_failed"](service_name)
                result["actions_taken"].append(f"systemctl reset-failed {service_name}")
            elif "docker" in step_lower and "clean" in step_lower:
                proc = FIX_ACTIONS["docker_cleanup"](None)
                result["actions_taken"].append("docker container prune -f")
            else:
                continue

            # 等一秒验证
            await asyncio.sleep(1)

        # 验证修复结果
        check = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            capture_output=True, text=True, timeout=10
        )
        if check.stdout.strip() == "active":
            result["healed"] = True
            break

    return result


async def scan_and_heal() -> list[dict]:
    """L4: 扫描所有失败服务并尝试修复"""
    proc = subprocess.run(
        ["systemctl", "--user", "list-units", "--type=service",
         "--state=failed", "--no-legend"],
        capture_output=True, text=True, timeout=10
    )

    results = []
    for line in proc.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if not parts:
            continue
        # systemd 255+ 在 --no-legend 输出中也带 ● 前缀
        if parts[0] == "●" and len(parts) > 1:
            svc_name = parts[1].replace(".service", "")
        else:
            svc_name = parts[0].replace(".service", "")
        result = await heal_service(svc_name)
        results.append(result)

    return results


# ── L5: 预判感知 ─────────────────────────────────────────────────────

def init_metrics_db():
    """初始化指标数据库"""
    conn = sqlite3.connect(str(METRICS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cpu REAL,
            mem REAL,
            disk_root REAL,
            disk_ai REAL,
            load_1m REAL,
            failed_services INTEGER
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts)
    """)
    conn.commit()
    conn.close()


def collect_metrics():
    """采集当前系统指标"""
    cpu = mem = disk_root = disk_ai = load_1m = 0.0
    failed = 0
    my_env = {**os.environ, "LANG": "C"}

    try:
        raw = subprocess.check_output(
            ["top", "-bn1"], timeout=5, env=my_env
        ).decode()
        for line in raw.split("\n"):
            if "Cpu" in line:
                # %Cpu(s): 1.2 us, 0.5 sy, 0.0 ni, 98.0 id, 0.3 wa
                for token in line.split(","):
                    if "id" in token:
                        cpu = 100 - float(token.strip().split()[0])
                        break
                break
    except Exception:
        pass

    try:
        raw = subprocess.check_output(
            ["free"], timeout=5, env=my_env
        ).decode()
        for line in raw.split("\n"):
            if "Mem:" in line:
                parts = line.split()
                used = float(parts[2]) if len(parts) > 2 else 0
                total = float(parts[1]) if len(parts) > 1 else 1
                mem = used / total * 100 if total > 0 else 0
                break
    except Exception:
        pass

    try:
        raw = subprocess.check_output(
            ["df", "/"], timeout=5, env=my_env
        ).decode()
        for line in raw.split("\n"):
            parts = line.split()
            if len(parts) >= 5 and parts[-1] == "/":
                disk_root = int(parts[-2].rstrip("%"))
                break
    except Exception:
        pass

    try:
        raw = subprocess.check_output(
            ["df", "/mnt/ai"], timeout=5, env=my_env
        ).decode()
        for line in raw.split("\n"):
            parts = line.split()
            if len(parts) >= 5 and parts[-1] == "/mnt/ai":
                disk_ai = int(parts[-2].rstrip("%"))
                break
    except Exception:
        pass

    try:
        raw = subprocess.check_output(
            ["uptime"], timeout=5, env=my_env
        ).decode()
        if "load average:" in raw:
            load_1m = float(raw.split("load average:")[1].split(",")[0].strip())
    except Exception:
        pass

    try:
        raw = subprocess.check_output(
            ["systemctl", "--user", "list-units", "--type=service",
             "--state=failed", "--no-legend"],
            timeout=5
        ).decode()
        failed = len(raw.strip().split("\n")) if raw.strip() else 0
    except Exception:
        pass

    conn = sqlite3.connect(str(METRICS_DB))
    conn.execute(
        "INSERT INTO metrics (cpu, mem, disk_root, disk_ai, load_1m, failed_services) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (round(cpu, 1), round(mem, 1), disk_root, disk_ai, round(load_1m, 2), failed)
    )
    conn.commit()
    conn.close()

    return {
        "cpu": cpu, "mem": mem, "disk_root": disk_root,
        "disk_ai": disk_ai, "load_1m": load_1m, "failed": failed
    }


def detect_anomalies() -> list[str]:
    """L5: 检测异常趋势（基于过去24h数据对比1h均值）"""
    conn = sqlite3.connect(str(METRICS_DB))
    alerts = []

    try:
        # 最近1小时均值
        row_1h = conn.execute(
            "SELECT avg(cpu), avg(mem), avg(disk_root), avg(load_1m), avg(failed_services) "
            "FROM metrics WHERE ts > datetime('now', '-1 hour')"
        ).fetchone()

        # 最近24小时均值
        row_24h = conn.execute(
            "SELECT avg(cpu), avg(mem), avg(disk_root), avg(load_1m), avg(failed_services) "
            "FROM metrics WHERE ts > datetime('now', '-24 hours')"
        ).fetchone()

        if row_1h and row_24h and row_1h[0] is not None and row_24h[0] is not None:
            cpu_1h, mem_1h, disk_1h, load_1h, fail_1h = row_1h
            cpu_24h, mem_24h, disk_24h, load_24h, fail_24h = row_24h

            # CPU 异常（高于24h均值1.5x且>50%）
            if cpu_1h > cpu_24h * 1.5 and cpu_1h > 50:
                alerts.append(f"CPU使用率异常: 当前{cpu_1h:.0f}% vs 24h均值{cpu_24h:.0f}%")

            # 内存增长趋势（>80%）
            if mem_1h > 80:
                alerts.append(f"内存使用率高: {mem_1h:.0f}%")

            # 磁盘 >90%
            if disk_1h > 90:
                alerts.append(f"磁盘使用率高: {disk_1h}%")

            # 负载异常
            if load_1h > load_24h * 2 and load_1h > 4:
                alerts.append(f"系统负载异常: {load_1h} vs 24h均值{load_24h:.1f}")

            # 失败服务增多
            if fail_1h > fail_24h and fail_1h > 2:
                alerts.append(f"失败服务增多: {int(fail_1h)}个，24h均值{int(fail_24h)}个")

    except Exception:
        pass
    finally:
        conn.close()

    return alerts


# ── 内联键盘生成 ──────────────────────────────────────────────────────

SEVERITY_EMOJI = {
    "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"
}

ACTION_LABELS = {
    "restart": "🔄 重启",
    "logs": "📋 查看日志",
    "check": "🔍 检查",
    "diag": "🩺 完整诊断",
    "top": "📊 资源概览",
    "ignore": "👌 忽略",
}

ACTION_EMOJI = {
    "restart:": "🔄",
    "logs:": "📋",
    "check:": "🔍",
    "diag": "🩺",
    "top": "📊",
    "ignore": "👌",
}


def format_notification_with_analysis(
    text: str, analysis: NotificationAnalysis
) -> tuple[str, Optional[dict]]:
    """格式化通知消息+内联键盘"""
    sev = SEVERITY_EMOJI.get(analysis.severity, "🟡")
    sev_text = analysis.severity.upper()

    formatted = (
        f"{sev} <b>[{sev_text}]</b> {analysis.diagnosis}\n"
        f"💡 {analysis.suggestion}\n\n"
        f"📝 <i>{text[:500]}</i>"
    )

    if analysis.actions:
        buttons = []
        row = []
        for i, action in enumerate(analysis.actions):
            label = ACTIONS_LABELS.get(action["code"], action["label"])
            row.append({
                "text": label,
                "callback_data": f"pilot:{action['code']}"
            })
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        keyboard = {"inline_keyboard": buttons}
    else:
        keyboard = None

    return formatted, keyboard


def format_command_result(result: CommandResult) -> str:
    """格式化命令执行结果"""
    if result.success:
        icon = "✅"
    else:
        icon = "❌"

    text = f"{icon} <b>{result.action} {result.target}</b>"

    if result.output.strip():
        text += f"\n\n<pre>{result.output[:1500]}</pre>"

    if result.error.strip():
        text += f"\n\n⚠️ <code>{result.error[:300]}</code>"

    return text


def format_heal_results(results: list[dict]) -> str:
    """格式化自愈结果"""
    if not results:
        return "✅ 无失败服务"

    lines = ["🩺 <b>自主修复报告</b>\n"]
    for r in results:
        icon = "✅" if r["healed"] else "❌"
        lines.append(
            f"{icon} <b>{r['service']}</b> — "
            f"{r['final_diagnosis'][:50]}\n"
            f"   操作: {', '.join(r['actions_taken'][-3:])}\n"
            f"   轮数: {r['rounds']}"
        )
    return "\n".join(lines)


# ── 导出 ──────────────────────────────────────────────────────────────

__all__ = [
    "analyze_notification",
    "NotificationAnalysis",
    "recognize_command",
    "execute_command",
    "CommandResult",
    "diagnose_failure",
    "heal_service",
    "scan_and_heal",
    "init_metrics_db",
    "collect_metrics",
    "detect_anomalies",
    "format_notification_with_analysis",
    "format_command_result",
    "format_heal_results",
]