"""
report_generator.py — AGI Brain 每日审计报告
Why: 让用户不看细节，只看结论：今天自动处理了什么、正面/负面各多少
What: 读取审计日志 → 统计分类 → 生成可读报告 → 推送 Telegram/Discord + 写桌面文件
"""

import asyncio
import json
import os
from datetime import datetime, date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from audit_log import read_today_entries, read_entries_since

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_ALERTS_CHANNEL_ID = os.environ.get("DISCORD_ALERTS_CHANNEL_ID", "")
LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-charlie-2026")
REPORT_MODEL = os.environ.get("REPORT_MODEL", "glm-4-flash")

DESKTOP_REPORT_DIR = Path.home() / "Desktop" / "巡检报告" / "AGI审计"
OBSIDIAN_REPORT_DIR = Path.home() / "Documents" / "Obsidian" / "System-Status" / "AGI审计"


def build_stats(entries: list[dict]) -> dict:
    """统计今日执行数据"""
    cycles = [e for e in entries if e["type"] == "cycle"]
    queued = [e for e in entries if e["type"] == "task_queued"]
    results = [e for e in entries if e["type"] == "task_result"]

    # op-task-results.json 里的结果也纳入统计
    op_results = _read_op_results()

    positive = [r for r in results if r.get("impact") == "positive"]
    negative = [r for r in results if r.get("impact") == "negative"]
    neutral  = [r for r in results if r.get("impact") == "neutral"]
    pending  = [q for q in queued if not any(q["task"][:20] in r.get("task","") for r in results)]

    total_alerts = sum(c.get("alert_count", 0) for c in cycles)
    llm_calls = sum(1 for c in cycles if not c.get("skipped_llm"))
    skipped = sum(1 for c in cycles if c.get("skipped_llm"))

    return {
        "date": date.today().isoformat(),
        "cycles": len(cycles),
        "llm_calls": llm_calls,
        "llm_skipped": skipped,
        "total_queued": len(queued),
        "total_results": len(results) + len(op_results),
        "positive": len(positive),
        "negative": len(negative),
        "neutral": len(neutral),
        "pending": len(pending),
        "total_alerts": total_alerts,
        "op_results": op_results,
        "negative_tasks": [r.get("task","") for r in negative],
        "positive_tasks": [r.get("task","") for r in positive[:5]],
    }


def _read_op_results() -> list[dict]:
    """从 op-task-results.json 读取结果"""
    p = Path(Path.home() / ".local/state/op-task-results.json")
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def format_report(stats: dict, detail_level: str = "summary") -> str:
    """生成人类可读的报告文本"""
    d = stats["date"]
    pos = stats["positive"]
    neg = stats["negative"]
    neu = stats["neutral"]
    total = stats["total_results"]
    queued = stats["total_queued"]
    pending = stats["pending"]
    alerts = stats["total_alerts"]
    cycles = stats["cycles"]
    llm = stats["llm_calls"]
    skip = stats["llm_skipped"]

    neg_emoji = "🔴" if neg > 0 else "✅"
    health = "⚠️ 需关注" if neg > 0 else ("🟡 平稳" if alerts > 0 else "🟢 健康")

    lines = [
        f"📊 AGI Brain 日报 — {d}",
        f"系统状态：{health}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🔄 主循环：{cycles} 轮  |  LLM调用：{llm} 次  |  空跑跳过：{skip} 次",
        f"📋 派发任务：{queued} 条  |  已执行反馈：{total} 条  |  待处理：{pending} 条",
        f"",
        f"执行影响评级：",
        f"  ✅ 正面：{pos} 条",
        f"  {neg_emoji} 负面：{neg} 条",
        f"  ➖ 中性：{neu} 条",
        f"  ⚠️ 今日告警：{alerts} 次",
    ]

    if neg > 0 and stats["negative_tasks"]:
        lines.append("")
        lines.append("❌ 需关注（负面执行）：")
        for t in stats["negative_tasks"][:3]:
            lines.append(f"  • {t[:60]}")

    if detail_level == "detail" and stats["positive_tasks"]:
        lines.append("")
        lines.append("✅ 正面处理（代表）：")
        for t in stats["positive_tasks"]:
            lines.append(f"  • {t[:60]}")

    op_results = stats.get("op_results", [])
    if op_results:
        lines.append("")
        lines.append(f"🤖 OP 执行反馈（{len(op_results)} 条）：")
        for r in op_results[-3:]:
            status = r.get("status", "?")
            task = r.get("task", "")[:50]
            lines.append(f"  [{status}] {task}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"查看详细：cat ~/Desktop/巡检报告/AGI审计/{d}.md")

    return "\n".join(lines)


async def _send_report(text: str) -> None:
    """通过统一通知中心推送报告"""
    from notify import get_notifier, Channel, Message, Priority
    n = get_notifier()
    await n.send(Message(
        text=text,
        priority=Priority.LOW,
        channels=[Channel.TELEGRAM, Channel.DISCORD],
    ))


def save_desktop_report(stats: dict, report_text: str) -> Path:
    """保存到桌面报告目录，并同步到 Obsidian"""
    DESKTOP_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fname = DESKTOP_REPORT_DIR / f"{stats['date']}.md"
    # Markdown 格式详细报告
    md = f"# AGI Brain 审计报告 {stats['date']}\n\n"
    md += f"```\n{report_text}\n```\n\n"
    md += "## 原始统计\n\n```json\n"
    md += json.dumps(stats, ensure_ascii=False, indent=2)
    md += "\n```\n"
    fname.write_text(md, encoding="utf-8")

    # 同步到 Obsidian
    try:
        OBSIDIAN_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        obs_fname = OBSIDIAN_REPORT_DIR / f"{stats['date']}.md"
        obs_md = f"# AGI Brain 审计报告 {stats['date']}\n\n"
        obs_md += f"tags: #agi #daily-report #auto\n\n"
        obs_md += f"```\n{report_text}\n```\n\n"
        obs_md += "## 原始统计\n\n```json\n"
        obs_md += json.dumps(stats, ensure_ascii=False, indent=2)
        obs_md += "\n```\n"
        obs_fname.write_text(obs_md, encoding="utf-8")
        print(f"[REPORT] 已同步 Obsidian → {obs_fname}")
    except Exception as e:
        print(f"[REPORT] Obsidian 同步失败：{e}")

    return fname


async def generate_and_send(detail_level: str = "summary") -> str:
    """生成今日报告并推送，返回报告文本"""
    entries = read_today_entries()
    stats = build_stats(entries)
    report_text = format_report(stats, detail_level)

    # 保存桌面
    fpath = save_desktop_report(stats, report_text)
    print(f"[REPORT] 已写入 {fpath}")

    # 推送
    await _send_report(report_text)

    return report_text


if __name__ == "__main__":
    import sys
    detail = "detail" if "--detail" in sys.argv else "summary"
    report = asyncio.run(generate_and_send(detail))
    print(report)
