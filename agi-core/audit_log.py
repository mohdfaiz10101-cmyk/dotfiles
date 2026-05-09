"""
audit_log.py — AGI Brain 审计日志
Why: 记录每次自动处理的任务结果，供报告生成使用
What: JSONL 格式 append-only 日志，支持按日期查询
"""

import json
import os
from datetime import datetime, date
from pathlib import Path

AUDIT_LOG = Path(os.environ.get(
    "AGI_AUDIT_LOG",
    "/home/charlie/.claude/projects/-home-charlie/memory/agi-audit-log.jsonl"
))


def log_tasks_queued(actions: list[dict]) -> None:
    """记录派发给 OP 的任务"""
    op_actions = [a for a in actions if a.get("assign_to") == "op"]
    if not op_actions:
        return
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        for a in op_actions:
            f.write(json.dumps({
                "ts": ts,
                "type": "task_queued",
                "task": a.get("task", ""),
                "priority": a.get("priority", "medium"),
                "source": "AGI→OP",
                "status": "queued",
                "impact": "pending",
            }, ensure_ascii=False) + "\n")


def log_task_result(task: str, status: str, evidence: str = "", impact: str = "") -> None:
    """记录任务执行结果（由 OP 回写或 brain 推断）"""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 推断 impact
    if not impact:
        if status in ("success", "完成", "ok"):
            impact = "positive"
        elif status in ("skip", "skipped", "已存在", "无需操作"):
            impact = "neutral"
        elif status in ("fail", "failed", "error", "失败"):
            impact = "negative"
        else:
            impact = "neutral"
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": ts,
            "type": "task_result",
            "task": task,
            "status": status,
            "impact": impact,
            "evidence": evidence[:200],
        }, ensure_ascii=False) + "\n")


def log_brain_cycle(summary: str, alerts: list, skipped_llm: bool = False) -> None:
    """记录每轮 brain 主循环摘要"""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": ts,
            "type": "cycle",
            "summary": summary,
            "alert_count": len(alerts),
            "skipped_llm": skipped_llm,
        }, ensure_ascii=False) + "\n")


def read_today_entries() -> list[dict]:
    """读取今日所有审计条目"""
    if not AUDIT_LOG.exists():
        return []
    today = date.today().isoformat()
    entries = []
    with AUDIT_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("ts", "").startswith(today):
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries


def read_entries_since(days: int = 1) -> list[dict]:
    """读取最近 N 天的条目"""
    if not AUDIT_LOG.exists():
        return []
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    entries = []
    with AUDIT_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("ts", "") >= cutoff:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries
