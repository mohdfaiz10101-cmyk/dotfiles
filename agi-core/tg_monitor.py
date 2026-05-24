#!/usr/bin/env python3
"""
tg_monitor.py — Telegram 监控通知模块
向"🧠 记忆系统监控" topic 发送状态更新，支持讨论模式。

用法:
  python3 tg_monitor.py watchdog "<消息>"
  python3 tg_monitor.py decay "<消息>"
  python3 tg_monitor.py sync "<消息>"
  python3 tg_monitor.py alert "<消息>"    # 高优先级告警
"""

import json
import os
import sys
import urllib.request

# Proxy for Telegram API access
PROXY = "http://127.0.0.1:7890"

BOT_TOKEN = "8797063873:AAGvApEP9frmA74b6nmxODHshzo1TwJR5ks"
FORUM_ID = -1003835605605  # 🧠 记忆系统监控·讨论组
MEMORY_TOPIC_ID = 15       # 📊 系统报告 topic
DISCUSSION_TOPIC_ID = 16   # 💬 CC·OP 讨论 topic

EMOJI = {
    "watchdog": "🐕",
    "decay": "🧹",
    "sync": "🔄",
    "alert": "🚨",
    "ok": "✅",
    "fail": "❌",
    "autoheal": "🔧",
}


def send_message(module: str, msg: str, silent: bool = False) -> str:
    """发送消息到记忆监控 topic"""
    icon = EMOJI.get(module, "📊")
    text = f"{icon} <b>[{module.upper()}]</b>\n{msg}"

    body = json.dumps({
        "chat_id": FORUM_ID,
        "message_thread_id": MEMORY_TOPIC_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": silent,
    }).encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("ok"):
            msg_id = data["result"]["message_id"]
            return f"ok:{msg_id}"
        return f"fail:{data.get('description','unknown')}"
    except Exception as e:
        return f"fail:{e}"


def send_channel_summary(lines: list[str]) -> str:
    """发送多条状态汇总"""
    text = (
        f"📊 <b>记忆系统健康报告</b> <code>{__import__('datetime').datetime.now().strftime('%H:%M')}</code>\n\n"
        + "\n".join(lines)
    )
    body = json.dumps({
        "chat_id": FORUM_ID,
        "message_thread_id": MEMORY_TOPIC_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": True,  # 常规报告静默
    }).encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=body, headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return "ok" if data.get("ok") else f"fail:{data}"
    except Exception as e:
        return f"fail:{e}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: tg_monitor.py <module> <message>")
        sys.exit(1)

    module, msg = sys.argv[1], " ".join(sys.argv[2:])
    silent = module not in ("alert",)
    result = send_message(module, msg, silent=silent)
    print(result)