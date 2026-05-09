#!/usr/bin/env python3
"""Telethon 用户级 Telegram 客户端
- 用真实用户账号（非 bot）读取所有消息、群组、频道
- 消息记录到 ~/agi/data/tg-inbox.jsonl（与 tg_logger.py 共享格式）
- 需要先执行 python3 tg_user_client.py --auth 完成手机验证

获取 api_id / api_hash:
  1. 访问 https://my.telegram.org
  2. 登录 → API development tools
  3. 创建应用，获取 api_id 和 api_hash
  4. 写入 ~/.config/tg-user-client.json
"""
import asyncio, json, os, sys, logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("tg-user")

CONFIG_FILE = Path.home() / ".config/tg-user-client.json"
SESSION_FILE = Path.home() / ".local/share/tg-user-client/session"
INBOX_FILE   = Path.home() / "agi/data/tg-inbox.jsonl"

SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"""
[tg-user-client] 配置文件不存在: {CONFIG_FILE}

请先：
1. 访问 https://my.telegram.org → API development tools
2. 创建应用，获取 api_id（数字）和 api_hash（字符串）
3. 创建配置文件：

   mkdir -p ~/.config
   cat > {CONFIG_FILE} << 'EOF'
   {{
     "api_id": 12345678,
     "api_hash": "your_api_hash_here",
     "phone": "+8613800138000"
   }}
   EOF

4. 再运行：python3 {__file__} --auth
""")
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text())


def append_inbox(record: dict):
    with INBOX_FILE.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def run_listener(client):
    from telethon import events

    @client.on(events.NewMessage)
    async def handler(event):
        msg = event.message
        if not msg or not msg.text:
            return

        sender = await event.get_sender()
        chat   = await event.get_chat()

        sender_name = ""
        if sender:
            sender_name = getattr(sender, "first_name", "") or ""
            last = getattr(sender, "last_name", "") or ""
            if last:
                sender_name += f" {last}"
            username = getattr(sender, "username", "") or ""
            if not sender_name and username:
                sender_name = f"@{username}"

        chat_name = ""
        if chat:
            chat_name = getattr(chat, "title", "") or getattr(chat, "first_name", "") or ""

        record = {
            "ts":      datetime.fromtimestamp(msg.date.timestamp()).strftime("%Y-%m-%d %H:%M"),
            "date":    datetime.fromtimestamp(msg.date.timestamp()).strftime("%Y-%m-%d"),
            "from":    sender_name or "Unknown",
            "from_id": getattr(sender, "id", 0) if sender else 0,
            "chat":    chat_name or "私聊",
            "chat_id": getattr(chat, "id", 0) if chat else 0,
            "text":    msg.text[:500],
            "source":  "user-client",
        }
        append_inbox(record)
        log.info(f"[新消息] {record['from']} @ {record['chat']}: {msg.text[:50]}")

    log.info("Telethon 用户客户端已启动，监听所有消息...")
    await client.run_until_disconnected()


async def auth_flow(cfg: dict):
    from telethon import TelegramClient
    client = TelegramClient(str(SESSION_FILE), cfg["api_id"], cfg["api_hash"],
                            proxy=("socks5", "127.0.0.1", 7890))
    await client.start(phone=cfg.get("phone"))
    me = await client.get_me()
    log.info(f"授权成功: {me.first_name} (@{me.username}) id={me.id}")
    await client.disconnect()
    print("[OK] 会话已保存，下次启动无需重新验证")


async def main(mode: str):
    try:
        from telethon import TelegramClient
    except ImportError:
        print("请先安装: pip install telethon")
        sys.exit(1)

    cfg = load_config()

    if mode == "auth":
        await auth_flow(cfg)
        return

    client = TelegramClient(str(SESSION_FILE), cfg["api_id"], cfg["api_hash"],
                            proxy=("socks5", "127.0.0.1", 7890))
    await client.start(phone=cfg.get("phone"))
    await run_listener(client)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "listen"
    asyncio.run(main(mode.lstrip("-")))
