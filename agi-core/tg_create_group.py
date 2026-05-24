#!/usr/bin/env python3
"""用 Telethon 用户客户端创建 Telegram 独立群组，启用讨论模式"""

import asyncio, json, os, sys
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest
from telethon.tl.functions.channels import ToggleForumRequest

CONFIG = Path.home() / ".config/tg-user-client.json"
SESSION = Path.home() / ".local/share/tg-user-client/session"
BOT_USERNAME = "openagi_bot"

async def main():
    if not CONFIG.exists():
        print("[!] 需要配置 ~/.config/tg-user-client.json")
        print("    { \"api_id\": 你的api_id, \"api_hash\": \"你的hash\", \"phone\": \"+86手机号\" }")
        return False

    cfg = json.loads(CONFIG.read_text())
    client = TelegramClient(str(SESSION), cfg["api_id"], cfg["api_hash"],
                            proxy=("http", "127.0.0.1", 7890))

    await client.start(phone=cfg.get("phone"))

    # 1. 创建超级群
    result = await client(CreateChatRequest(
        users=[BOT_USERNAME],
        title="🧠 记忆系统监控·讨论组"
    ))

    chat_id = result.chats[0].id
    print(f"[ok] 群组创建: id={chat_id}")

    # 2. 设为 forum
    await client(ToggleForumRequest(channel=chat_id, enabled=True))
    print(f"[ok] 讨论模式已开启 (forum/topics)")

    # 3. 创建一个初始 topic
    from telethon.tl.functions.channels import CreateForumTopicRequest
    topic = await client(CreateForumTopicRequest(
        channel=chat_id,
        title="系统报告",
        icon_color=0x6FB9F0
    ))
    print(f"[ok] Topic: id={topic.updates[0].id}")

    # 4. 发欢迎消息
    await client.send_message(chat_id, "记忆系统监控讨论组已就绪。\n\n三层架构: ChromaDB → Letta → grep\n看门狗: 每15分钟巡检 + 自动修复")
    print(f"[ok] 欢迎消息已发送")

    # 5. 保存配置
    info_path = Path.home() / ".local/state/memory-monitor-group.json"
    info_path.write_text(json.dumps({
        "group_id": chat_id,
        "group_name": "🧠 记忆系统监控·讨论组",
        "bot": BOT_USERNAME,
        "created": __import__('datetime').datetime.now().isoformat(),
    }, indent=2))
    print(f"[ok] 配置已保存: {info_path}")

    await client.disconnect()
    return chat_id

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print(f"\n群组ID: {result}  —  机器人 @{BOT_USERNAME} 已加入")
    except Exception as e:
        print(f"[fail] {e}")