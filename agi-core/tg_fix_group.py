#!/usr/bin/env python3
"""补充设置v3：用正确的entity方式拉bot + 开forum"""

import asyncio, json
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import ToggleForumRequest, InviteToChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

CONFIG = Path.home() / ".config/tg-user-client.json"
STRING_SESSION = Path.home() / ".local/share/telegram/userbot-session.txt"
GROUP_TITLE = "🧠 记忆系统监控·讨论组"

async def main():
    cfg = json.loads(CONFIG.read_text())
    ss = STRING_SESSION.read_text().strip()
    client = TelegramClient(StringSession(ss), cfg["api_id"], cfg["api_hash"],
                            proxy=("http", "127.0.0.1", 7890))
    await client.connect()
    if not await client.is_user_authorized():
        print("[!] 会话过期")
        return

    # 找到刚创建的群组
    dialogs = await client.get_dialogs()
    target = None
    for d in dialogs:
        if d.title == GROUP_TITLE:
            target = d
            break

    if not target:
        print("[!] 找不到群组，可能还没出现在对话列表")
        return

    chat_id = target.id
    entity = target.entity
    print(f"[ok] 找到群组: id={chat_id}, title={target.title}")

    # 1. 开 forum
    await client(ToggleForumRequest(channel=entity, enabled=True, tabs=False))
    print("[ok] 讨论模式已开")

    # 2. 拉 bot
    bot = await client.get_input_entity("openagi_bot")
    await client(InviteToChannelRequest(channel=entity, users=[bot]))
    print("[ok] @openagi_bot 已加入")

    await client.disconnect()

asyncio.run(main())