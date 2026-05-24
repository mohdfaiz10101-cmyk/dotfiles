#!/usr/bin/env python3
"""用 Telethon 用户客户端创建 Telegram 独立群组，启用讨论模式"""

import asyncio, json, os, sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import CreateChannelRequest, ToggleForumRequest, InviteToChannelRequest
from telethon.tl.types import InputUser

CONFIG = Path.home() / ".config/tg-user-client.json"
STRING_SESSION = Path.home() / ".local/share/telegram/userbot-session.txt"
BOT_USERNAME = "openagi_bot"

async def main():
    if not CONFIG.exists():
        print("[!] 需要配置 ~/.config/tg-user-client.json")
        return False

    cfg = json.loads(CONFIG.read_text())

    ss = STRING_SESSION.read_text().strip()
    client = TelegramClient(StringSession(ss), cfg["api_id"], cfg["api_hash"],
                            proxy=("http", "127.0.0.1", 7890))

    await client.connect()
    if not await client.is_user_authorized():
        print("[!] 会话已过期，需重新验证")
        return False

    # 1. 创建超级群 (megagroup=True)
    result = await client(CreateChannelRequest(
        title="🧠 记忆系统监控·讨论组",
        about="记忆系统三层架构(ChromaDB→Letta→grep)健康监控 + 看门狗自愈 + CC/OP讨论",
        megagroup=True,
    ))
    chat = result.chats[0]
    chat_id = chat.id
    print(f"[ok] 独立群创建: id={chat_id}, title={chat.title}")

    # 2. 设为 forum（讨论模式）
    await client(ToggleForumRequest(channel=chat_id, enabled=True, tabs=False))
    print(f"[ok] 讨论模式已开启 (forum/topics)")

    # 3. 获取 bot 实体并拉入群
    bot_entity = await client.get_input_entity(BOT_USERNAME)
    await client(InviteToChannelRequest(
        channel=chat_id,
        users=[bot_entity],
    ))
    print(f"[ok] @{BOT_USERNAME} 已加入群组")

    # 3. 发欢迎消息
    await client.send_message(chat_id, "🧠 记忆系统监控讨论组已就绪\n\n三层架构: ChromaDB → Letta → grep\n看门狗: 每15分钟巡检 + 自动修复\nbot: @openagi_bot 已加入")

    # 4. 保存配置
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