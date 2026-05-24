#!/usr/bin/env python3
"""tg-finance-bot.py — 财务管理 Telegram Bot（forum topic 交互）
监听财务中心群消息，自动处理记账、查卡、还款查询等。

用法: python3 tg-finance-bot.py
systemd: finance-bot.service
"""
import asyncio
import json
import os
import sys
import time
import httpx
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────
TG_TOKEN = Path("/home/charlie/.config/telegram-bot-token").read_text().strip()
FINANCE_API = "http://localhost:9811"
STATE_FILE = Path("/home/charlie/.local/state/finance-bot-offset.json")

TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"

# ── 状态持久化 ──────────────────────────────────────────────────
def load_offset() -> int:
    try:
        return json.loads(STATE_FILE.read_text()).get("offset", 0)
    except Exception:
        return 0

def save_offset(offset: int):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"offset": offset, "updated": time.strftime("%Y-%m-%d %H:%M:%S")}))

# ── API 辅助 ────────────────────────────────────────────────────
async def tg_send(chat_id: int, text: str, thread_id: int = 0, parse_mode: str = "Markdown"):
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if thread_id:
        data["message_thread_id"] = thread_id
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{TG_API}/sendMessage", data=data)

async def finance_api(endpoint: str, method: str = "GET", data: dict = None):
    url = f"{FINANCE_API}/{endpoint}"
    async with httpx.AsyncClient(timeout=10) as c:
        if method == "GET":
            r = await c.get(url)
        else:
            r = await c.post(url, json=data)
        if r.status_code == 200:
            return r.json()
        return None

# ── 命令处理 ────────────────────────────────────────────────────
async def handle_message(chat_id: int, text: str, thread_id: int = 0):
    text = text.strip()
    if not text or text.startswith("/"):
        return

    # 意图识别
    if any(kw in text for kw in ["查卡", "我的卡", "银行卡", "卡片列表"]):
        cards = await finance_api("cards")
        if not cards:
            await tg_send(chat_id, "📭 暂无银行卡", thread_id)
            return
        lines = ["*💳 我的银行卡*", ""]
        for c in cards:
            t = "信用卡" if c["card_type"] == "credit" else "储蓄卡"
            lines.append(f"• {c['bank_name']} *{c['card_last4']} ({t})")
            if c.get("billing_date"):
                lines.append(f"  账单日: {c['billing_date']}日 | 还款日: {c['due_date']}日")
        await tg_send(chat_id, "\n".join(lines), thread_id)

    elif any(kw in text for kw in ["还款", "还款日", "账单", "到期", "reminder"]):
        reminders = await finance_api("reminders")
        if not reminders:
            await tg_send(chat_id, "✅ 近7天无到期还款", thread_id)
            return
        lines = ["*🔔 还款提醒*", ""]
        for r in reminders:
            d = r["days_until"]
            icon = "🔴" if d <= 3 else ("🟡" if d <= 7 else "🟢")
            bal = f'¥{r["current_balance"]:,.0f}' if r.get("current_balance", 0) > 0 else "已还清"
            lines.append(f"{icon} {r['bank_name']} *{r['card_last4']} — {bal} — {r['next_due']} ({d}天)")
        await tg_send(chat_id, "\n".join(lines), thread_id)

    elif any(kw in text for kw in ["记账", "消费", "花了", "买了"]):
        # 简单记账："记账 浦发 6400 刷卡机"
        await tg_send(chat_id, "💡 记账格式：\n`银行名 金额 商户`\n如：`浦发 6400 白色刷卡机`", thread_id)

    elif any(kw in text for kw in ["帮助", "help", "用法"]):
        help_text = """*🏦 财务助手命令*

• `查卡` / `银行卡` — 查看所有卡片
• `还款` / `账单` — 查看近期还款
• `记账 银行 金额 商户` — 记录消费
• `帮助` — 显示本消息

直接发送银行短信可自动解析记账。"""
        await tg_send(chat_id, help_text, thread_id)

    else:
        # 尝试作为记账格式解析：银行名 金额 商户
        parts = text.split(None, 2)
        if len(parts) >= 2:
            bank_hint = parts[0]
            try:
                amount = float(parts[1].replace("¥", "").replace(",", "").replace("元", ""))
            except ValueError:
                return  # 不是记账，忽略
            merchant = parts[2] if len(parts) > 2 else "未知商户"

            # 匹配银行卡
            cards = await finance_api("cards")
            matched = None
            for c in cards:
                if bank_hint in c["bank_name"] or bank_hint == c["card_last4"]:
                    matched = c
                    break

            if matched:
                txn = {
                    "card_id": matched["id"],
                    "date": time.strftime("%Y-%m-%d"),
                    "amount": amount,
                    "merchant": merchant,
                    "transaction_type": "消费",
                    "note": text
                }
                result = await finance_api("transactions", "POST", txn)
                if result:
                    await tg_send(chat_id, f'✅ 已记录: {matched["bank_name"]} ¥{amount:,.0f} @ {merchant}', thread_id)
            else:
                await tg_send(chat_id, f'⚠️ 未找到匹配银行卡: "{bank_hint}"\n请先添加银行卡或使用完整银行名称', thread_id)

# ── 主循环 ──────────────────────────────────────────────────────
async def main():
    print("[finance-bot] 启动...")
    offset = load_offset()

    while True:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {"offset": offset, "timeout": 30, "allowed_updates": ["message"]}
                r = await client.get(f"{TG_API}/getUpdates", params=params)
                if r.status_code != 200:
                    await asyncio.sleep(5)
                    continue
                updates = r.json().get("result", [])

            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")
                thread_id = msg.get("message_thread_id", 0)
                from_user = msg.get("from", {}).get("id", 0)

                # 只处理群消息
                if msg["chat"]["type"] not in ("group", "supergroup"):
                    continue
                # 排除bot自己
                if from_user == 8797063873:
                    continue

                await handle_message(chat_id, text, thread_id)
                save_offset(offset)

        except Exception as e:
            print(f"[finance-bot] 错误: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())