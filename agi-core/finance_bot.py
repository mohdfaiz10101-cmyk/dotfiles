"""
finance_bot.py — 财务 Telegram Bot (@charlie_finbot)
Why: 随手记账，通过自然语言或命令管理个人支出
What: SQLite 存储，支持手动记账+LLM 解析自然语言记账
Test: /add 30 餐饮 午餐 → 记录成功；/today → 显示今日汇总
"""

import asyncio
import json
import logging
import re
import sqlite3
from datetime import datetime, date
from pathlib import Path

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = "8814876417:AAHiy9KPgZ3SkX2eSnqsIXUkKragruNsmNk"
ALLOWED_CHATS = {-1003738258294, 5036541266}
PROXY = "http://127.0.0.1:7890"

DB_PATH = Path("/home/charlie/agi/finance.db")
LITELLM_BASE = "http://localhost:4000/v1"
LITELLM_KEY = "sk-litellm-charlie-2026"
TEXT_MODEL = "glm-4.7"


def _get_db() -> sqlite3.Connection:
    """获取 SQLite 连接并确保表已建立。
    Why: 懒建表，首次连接自动初始化
    What: 建立 expenses 表（id/amount/category/note/created_at）
    Test: 删除 DB 文件后调用，验证表被自动创建
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL DEFAULT '其他',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _check_auth(update: Update) -> bool:
    """验证授权聊天。
    Why: 财务数据敏感，只允许指定聊天访问
    What: 检查 chat id 白名单
    Test: 白名单 id 返回 True
    """
    cid = update.effective_chat.id if update.effective_chat else 0
    return cid in ALLOWED_CHATS


def _add_expense(amount: float, category: str, note: str) -> int:
    """插入一条支出记录，返回 id。
    Why: 封装数据库写入，便于测试和复用
    What: INSERT → commit → 返回 lastrowid
    Test: 调用后 SELECT 验证记录存在
    """
    conn = _get_db()
    cur = conn.execute(
        "INSERT INTO expenses (amount, category, note, created_at) VALUES (?, ?, ?, ?)",
        (amount, category, note, datetime.now().isoformat()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """手动记账：/add <金额> <类别> [备注]。
    Why: 快速精确记录支出
    What: 解析参数 → INSERT → 回复确认
    Test: /add 50.5 餐饮 晚饭 → 验证回复包含金额
    """
    if not _check_auth(update):
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text("用法：/add <金额> <类别> [备注]\n例：/add 30 餐饮 午餐")
        return
    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("金额格式不正确，请输入数字")
        return
    category = args[1]
    note = " ".join(args[2:]) if len(args) > 2 else ""
    row_id = _add_expense(amount, category, note)
    await update.message.reply_text(f"✅ 已记录 #{row_id}：{category} ¥{amount:.2f} {note}")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """今日支出汇总。
    Why: 快速了解今天花了多少
    What: 查询今日记录 → 按类别汇总
    Test: /today → 验证包含总金额
    """
    if not _check_auth(update):
        return
    today = date.today().isoformat()
    conn = _get_db()
    rows = conn.execute(
        "SELECT amount, category, note, created_at FROM expenses WHERE created_at LIKE ? ORDER BY created_at DESC",
        (f"{today}%",),
    ).fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text(f"📅 {today} 暂无支出记录")
        return
    total = sum(r[0] for r in rows)
    lines = [f"📅 今日支出（{today}）共 ¥{total:.2f}："]
    for amount, cat, note, ts in rows:
        time_str = ts[11:16]
        lines.append(f"  {time_str} {cat} ¥{amount:.2f} {note}")
    await update.message.reply_text("\n".join(lines))


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """本月按类别汇总。
    Why: 了解月度消费结构
    What: 查询本月记录 → 按类别 GROUP BY
    Test: /month → 验证包含类别和金额
    """
    if not _check_auth(update):
        return
    month = date.today().strftime("%Y-%m")
    conn = _get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount), COUNT(*) FROM expenses WHERE created_at LIKE ? GROUP BY category ORDER BY SUM(amount) DESC",
        (f"{month}%",),
    ).fetchall()
    total_row = conn.execute(
        "SELECT SUM(amount) FROM expenses WHERE created_at LIKE ?",
        (f"{month}%",),
    ).fetchone()
    conn.close()
    if not rows:
        await update.message.reply_text(f"📊 {month} 暂无支出记录")
        return
    total = total_row[0] or 0
    lines = [f"📊 {month} 月度汇总（共 ¥{total:.2f}）："]
    for cat, amt, cnt in rows:
        lines.append(f"  {cat}：¥{amt:.2f}（{cnt} 笔）")
    await update.message.reply_text("\n".join(lines))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update):
        return
    await update.message.reply_text(
        "💰 财务 Bot 使用指南\n\n"
        "/add <金额> <类别> [备注] — 记账\n"
        "/today — 今日汇总\n"
        "/month — 本月按类别汇总\n"
        "/help — 帮助\n\n"
        "自然语言示例：\n"
        "  「今天买菜花了30元」\n"
        "  「打车50块」"
    )


async def _parse_expense_with_llm(text: str) -> dict | None:
    """用 LLM 从自然语言提取记账信息。
    Why: 让用户用自然语言记账，LLM 结构化解析
    What: 构造 JSON 提取 prompt → 解析返回 {amount, category, note}
    Test: 传入"买菜30元" → 返回 {"amount": 30, "category": "餐饮", "note": "买菜"}
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LITELLM_BASE}/chat/completions",
                json={
                    "model": TEXT_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "从用户消息中提取记账信息，返回 JSON 格式：\n"
                                '{"amount": 数字, "category": "类别", "note": "备注"}\n'
                                "类别参考：餐饮/交通/购物/娱乐/医疗/其他\n"
                                "如果无法提取，返回 null"
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 100,
                    "temperature": 0,
                },
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            )
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # 提取 JSON 块
            match = re.search(r"\{[^}]+\}", content)
            if match:
                return json.loads(match.group())
    except Exception:
        pass
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """自然语言记账：LLM 解析消息并自动记录。
    Why: 降低记账门槛，自然语言直接触发
    What: 调用 LLM 解析 → 提取金额类别 → INSERT → 回复确认
    Test: 发送"午饭花了25块" → 验证记录到数据库
    """
    if not _check_auth(update):
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    # 快速过滤：不像记账消息的跳过
    if not any(c in text for c in ["元", "块", "￥", "¥", "RMB", "花", "买", "付", "消费"]):
        await update.message.reply_text("请用 /help 查看命令，或直接描述支出（如「买菜30元」）")
        return
    await update.message.chat.send_action("typing")
    parsed = await _parse_expense_with_llm(text)
    if not parsed or not parsed.get("amount"):
        await update.message.reply_text("未能解析记账信息，请用 /add <金额> <类别> 手动记录")
        return
    amount = float(parsed["amount"])
    category = parsed.get("category", "其他")
    note = parsed.get("note", text[:30])
    row_id = _add_expense(amount, category, note)
    await update.message.reply_text(f"✅ 已自动记录 #{row_id}：{category} ¥{amount:.2f} {note}")


def main() -> None:
    print(f"[FINANCE-BOT] 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # 确保 DB 存在
    _get_db().close()
    req = HTTPXRequest(proxy=PROXY, read_timeout=20.0, connect_timeout=15.0, httpx_kwargs={"verify": False})
    app = Application.builder().token(BOT_TOKEN).request(req).build()
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("month", cmd_month))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=["message"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
