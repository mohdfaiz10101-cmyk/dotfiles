"""
self_heal.py — 自愈巡检工作流
LangGraph StateGraph: Sense → Classify → 并行(DiskFix|ServiceFix|ProxyFix) → Verify → Report
复用 brain.py sense()，所有 bash 执行走 safe_tools.bash_safe_call

Usage:
    cd ~/agi && python3 -m flows.self_heal
"""

import json
import re
from datetime import datetime
from typing import Annotated, Any
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flows.safe_tools import bash_safe_call
from brain import sense

FLOW_NAME = "self_heal"
MAX_RETRIES = 2


class HealState(TypedDict):
    """自愈工作流状态（有状态图）。"""

    sense_data: dict
    issues: list[str]
    severity: str                          # "P0"/"P1"/"P2" — 问题严重度
    disk_result: str
    service_result: str
    proxy_result: str
    verify_data: dict
    report: str
    retry_count: int
    success: bool
    human_approved: bool                   # 人工审批结果
    learn_outcome: str                     # 学习节点记录
    fix_history: list[dict]                # 修复历史（用于 learn）


# ── Sense ──────────────────────────────────────────────────────────────────


def node_sense(state: HealState) -> dict:
    """采集系统感知数据，复用 brain.sense()。"""
    data = sense()
    return {"sense_data": data, "retry_count": 0, "success": False}


# ── Classify ────────────────────────────────────────────────────────────────


def _parse_disk_pct(raw: str) -> int:
    """解析磁盘使用百分比字符串。"""
    m = re.search(r"(\d+)%", raw or "")
    return int(m.group(1)) if m else 0


def node_classify(state: HealState) -> dict:
    """根据 sense 数据分类问题类型。"""
    sd = state.get("sense_data", {})
    issues = []

    # 磁盘检查
    disk_pct = _parse_disk_pct(sd.get("disk_ai", ""))
    if disk_pct > 85:
        issues.append(f"disk:{disk_pct}%")

    # 服务检查
    services = sd.get("services", {})
    for svc_name, svc_status in services.items():
        if svc_status != "active":
            issues.append(f"service:{svc_name}={svc_status}")

    # 代理检查（通过 curl 测试）
    if not issues:
        # 只在有磁盘/服务问题时并行检测代理，否则跳过
        proxy_check = bash_safe_call(
            "curl -s --connect-timeout 5 -x http://127.0.0.1:7890 https://www.google.com -o /dev/null -w '%{http_code}'",
            timeout=10,
            flow=FLOW_NAME,
            node="Classify",
        )
        if proxy_check not in ("200", "301", "302"):
            issues.append("proxy:down")

    return {"issues": issues}


# ── 并行修复节点 ────────────────────────────────────────────────────────────


def node_disk_fix(state: HealState) -> dict:
    """磁盘修复：>85% 清理缓存。"""
    issues = state.get("issues", [])
    disk_issues = [i for i in issues if i.startswith("disk:")]

    if not disk_issues:
        return {"disk_result": "[SKIP] 无磁盘问题"}

    result_parts = []
    for issue in disk_issues:
        pct = issue.split(":")[1]
        result_parts.append(f"磁盘使用率 {pct}，尝试清理...")

        # 清理 apt 缓存
        r1 = bash_safe_call(
            "sudo apt-get clean 2>/dev/null || true",
            timeout=30,
            flow=FLOW_NAME,
            node="DiskFix",
        )
        result_parts.append(f"apt clean: {r1}")

        # 清理 pip 缓存
        r2 = bash_safe_call(
            "pip cache purge 2>/dev/null || true",
            timeout=30,
            flow=FLOW_NAME,
            node="DiskFix",
        )
        result_parts.append(f"pip cache: {r2}")

        # 清理 journal 日志
        r3 = bash_safe_call(
            "sudo journalctl --vacuum-time=3d 2>/dev/null | tail -1",
            timeout=15,
            flow=FLOW_NAME,
            node="DiskFix",
        )
        result_parts.append(f"journal: {r3}")

    return {"disk_result": "\n".join(result_parts)}


def node_service_fix(state: HealState) -> dict:
    """服务修复：down 则 restart。只做 restart/start，禁止 stop/disable。"""
    issues = state.get("issues", [])
    svc_issues = [i for i in issues if i.startswith("service:")]

    if not svc_issues:
        return {"service_result": "[SKIP] 无服务问题"}

    result_parts = []
    for issue in svc_issues:
        svc_info = issue.replace("service:", "")
        svc_name = svc_info.split("=")[0] if "=" in svc_info else svc_info
        result_parts.append(f"服务 {svc_name} 异常，尝试重启...")
        r = bash_safe_call(
            f"systemctl restart {svc_name}",
            timeout=30,
            flow=FLOW_NAME,
            node="ServiceFix",
        )
        result_parts.append(f"restart {svc_name}: {r}")

    return {"service_result": "\n".join(result_parts)}


def node_proxy_fix(state: HealState) -> dict:
    """代理修复：检测代理可用性。"""
    issues = state.get("issues", [])
    proxy_issues = [i for i in issues if i.startswith("proxy:")]

    if not proxy_issues:
        return {"proxy_result": "[SKIP] 无代理问题"}

    result_parts = ["代理异常，尝试修复..."]

    # 重启 mihomo
    r1 = bash_safe_call(
        "systemctl restart mihomo", timeout=30, flow=FLOW_NAME, node="ProxyFix"
    )
    result_parts.append(f"restart mihomo: {r1}")

    # 等待后重新测试
    import time

    time.sleep(3)
    r2 = bash_safe_call(
        "curl -s --connect-timeout 5 -x http://127.0.0.1:7890 https://www.google.com -o /dev/null -w '%{http_code}'",
        timeout=10,
        flow=FLOW_NAME,
        node="ProxyFix",
    )
    result_parts.append(f"代理测试: {r2}")

    return {"proxy_result": "\n".join(result_parts)}


# ── Verify ──────────────────────────────────────────────────────────────────


def node_verify(state: HealState) -> dict:
    """重新 sense() 验证修复结果。"""
    data = sense()
    sd = data

    # 检查修复是否成功
    remaining = []
    disk_pct = _parse_disk_pct(sd.get("disk_ai", ""))
    if disk_pct > 85:
        remaining.append(f"disk:{disk_pct}%")

    services = sd.get("services", {})
    for svc_name, svc_status in services.items():
        if svc_status != "active":
            remaining.append(f"service:{svc_name}={svc_status}")

    success = len(remaining) == 0
    return {"verify_data": data, "success": success, "issues": remaining}


def should_retry(state: HealState) -> str:
    """判断是否需要重试。"""
    if state.get("success", False):
        return "report"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "report"
    return "classify"


# ── Report ──────────────────────────────────────────────────────────────────


def node_report(state: HealState) -> dict:
    """生成修复报告。"""
    success = state.get("success", False)
    retries = state.get("retry_count", 0)
    issues = state.get("issues", [])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if success:
        report = (
            f"[自愈报告] {ts}\n"
            f"状态: 修复成功（重试 {retries} 次）\n"
            f"磁盘: {state.get('disk_result', 'N/A')[:200]}\n"
            f"服务: {state.get('service_result', 'N/A')[:200]}\n"
            f"代理: {state.get('proxy_result', 'N/A')[:200]}"
        )
    else:
        report = (
            f"[自愈报告] {ts}\n"
            f"状态: 修复失败（已重试 {retries} 次）\n"
            f"残留问题: {', '.join(issues)}\n"
            f"磁盘: {state.get('disk_result', 'N/A')[:200]}\n"
            f"服务: {state.get('service_result', 'N/A')[:200]}\n"
            f"代理: {state.get('proxy_result', 'N/A')[:200]}\n"
            f"需要人工介入"
        )

    # 尝试发送 Telegram 通知
    try:
        import asyncio
        from brain import _send_telegram

        asyncio.run(_send_telegram(report))
    except Exception:
        pass

    return {"report": report}


# ── Retry 包装 ─────────────────────────────────────────────────────────────


def node_retry_classify(state: HealState) -> dict:
    """重试分类节点，递增计数。"""
    new_count = state.get("retry_count", 0) + 1
    return {"retry_count": new_count}


# ── Severity 分类 ─────────────────────────────────────────────────────────────


def node_severity(state: HealState) -> dict:
    """根据问题类型和数量评估严重度。"""
    issues = state.get("issues", [])
    if not issues:
        return {"severity": "P2", "fix_history": []}

    # P0: 服务全挂 / 磁盘 >95%
    for issue in issues:
        if issue.startswith("disk:") and _parse_disk_pct(issue) > 95:
            return {"severity": "P0"}
        if issue.startswith("service:") and len(issues) >= 3:
            return {"severity": "P0"}

    # P1: 单服务异常 / 磁盘 85-95%
    for issue in issues:
        if issue.startswith("disk:") and _parse_disk_pct(issue) > 85:
            return {"severity": "P1"}
        if issue.startswith("service:"):
            return {"severity": "P1"}

    return {"severity": "P2"}


# ── Human-in-the-loop 审批 ────────────────────────────────────────────────────


def node_human_check(state: HealState) -> dict:
    """P0 问题需要人工审批才能修复。"""
    severity = state.get("severity", "P2")
    issues = state.get("issues", [])

    if severity != "P0":
        return {"human_approved": True}

    # P0 问题：写入 op-tasks 等待人工审批
    import asyncio
    try:
        from brain import _write_op_tasks
        task = {
            "task": f"[P0-紧急] 自愈需要人工审批: {', '.join(issues)}",
            "priority": "high",
            "context": f"severity={severity}, issues={issues}",
        }
        asyncio.get_event_loop().run_until_complete(_write_op_tasks([task]))
    except Exception:
        pass

    return {"human_approved": False, "report": f"[P0] 需要人工审批: {', '.join(issues)}"}


def should_human_approve(state: HealState) -> str:
    """判断是否需要人工审批。"""
    if state.get("human_approved", True):
        return "fix"
    return "report"


# ── Learn 节点 ────────────────────────────────────────────────────────────────


def node_learn(state: HealState) -> dict:
    """从修复结果中学习，记录 fix_history + 更新 lessons-learned。"""
    history = state.get("fix_history", [])
    success = state.get("success", False)
    severity = state.get("severity", "P2")
    issues = state.get("issues", [])

    outcome = "success" if success else "failed"
    entry = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "severity": severity,
        "issues": issues,
        "outcome": outcome,
        "retries": state.get("retry_count", 0),
        "disk": state.get("disk_result", "")[:100],
        "service": state.get("service_result", "")[:100],
        "proxy": state.get("proxy_result", "")[:100],
    }
    history.append(entry)

    # 写入 lessons-learned（仅失败时）
    if not success:
        try:
            from datetime import datetime
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            lesson = f"\n- [{ts}] [SELF_HEAL] 修复失败 severity={severity} issues={issues} retries={state.get('retry_count', 0)}\n"
            lessons_path = Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"
            with open(lessons_path, "a") as f:
                f.write(lesson)
        except Exception:
            pass

    return {"learn_outcome": outcome, "fix_history": history}


# ── 构建图 ─────────────────────────────────────────────────────────────────


def build_graph():
    """构建有状态自愈 StateGraph（v2 — conditional branching + learn）。"""
    graph = StateGraph(HealState)

    # 节点
    graph.add_node("sense", node_sense)
    graph.add_node("classify", node_classify)
    graph.add_node("severity", node_severity)
    graph.add_node("human_check", node_human_check)
    graph.add_node("disk_fix", node_disk_fix)
    graph.add_node("service_fix", node_service_fix)
    graph.add_node("proxy_fix", node_proxy_fix)
    graph.add_node("verify", node_verify)
    graph.add_node("learn", node_learn)
    graph.add_node("report", node_report)
    graph.add_node("retry_classify", node_retry_classify)

    # 线性流程: Sense → Classify → Severity → HumanCheck
    graph.add_edge(START, "sense")
    graph.add_edge("sense", "classify")
    graph.add_edge("classify", "severity")
    graph.add_edge("severity", "human_check")

    # HumanCheck → 条件分支: approved → fix_chain / denied → report
    graph.add_conditional_edges(
        "human_check",
        should_human_approve,
        {"fix": "disk_fix", "report": "report"},
    )

    # 修复链: disk → service → proxy → verify（各节点内部 SKIP 无关问题）
    graph.add_edge("disk_fix", "service_fix")
    graph.add_edge("service_fix", "proxy_fix")
    graph.add_edge("proxy_fix", "verify")

    # Verify → Learn → 重试或报告
    graph.add_conditional_edges(
        "verify", should_retry, {"learn": "learn", "retry": "retry_classify", "report": "report"}
    )
    graph.add_edge("learn", "report")
    graph.add_edge("retry_classify", "classify")
    graph.add_edge("report", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({})
    print(result.get("report", "无报告"))
