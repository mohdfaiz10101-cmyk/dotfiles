#!/usr/bin/env python3
"""Telegram bot message logger — polls getUpdates, appends to tg-inbox.jsonl"""
import json, time, os, logging
from pathlib import Path
from datetime import datetime
import urllib.request, urllib.error

BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8797063873:AAGvApEP9frmA74b6nmxODHshzo1TwJR5ks")
PROXY     = os.getenv("https_proxy", os.getenv("HTTPS_PROXY", "http://127.0.0.1:7890"))
INBOX     = Path.home() / "agi/data/tg-inbox.jsonl"
OFFSET_F  = Path("/tmp/tg-logger-offset.txt")
API       = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("tg-logger")

INBOX.parent.mkdir(parents=True, exist_ok=True)

def api_get(path: str, params: dict = {}) -> dict:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{API}/{path}?{qs}"
    proxy = urllib.request.ProxyHandler({"https": PROXY, "http": PROXY})
    opener = urllib.request.build_opener(proxy)
    try:
        resp = opener.open(url, timeout=35)
        return json.loads(resp.read())
    except Exception as e:
        log.warning(f"API error: {e}")
        return {}

def get_offset() -> int:
    try:
        return int(OFFSET_F.read_text().strip())
    except:
        return 0

def save_offset(n: int):
    OFFSET_F.write_text(str(n))

def extract_text(msg: dict) -> str:
    if "text" in msg:
        return msg["text"]
    if "caption" in msg:
        return f"[图片/文件] {msg['caption']}"
    for t in ("photo", "video", "document", "voice", "sticker"):
        if t in msg:
            return f"[{t}]"
    return ""

def main():
    log.info("tg-logger 启动")
    while True:
        offset = get_offset()
        data = api_get("getUpdates", {"offset": offset, "timeout": 30, "limit": 100})
        if not data.get("ok"):
            time.sleep(5)
            continue

        updates = data.get("result", [])
        for upd in updates:
            upd_id = upd["update_id"]
            save_offset(upd_id + 1)

            msg = upd.get("message") or upd.get("channel_post") or upd.get("edited_message")
            if not msg:
                continue

            text = extract_text(msg)
            if not text:
                continue

            sender = msg.get("from", {})
            chat   = msg.get("chat", {})
            record = {
                "ts":      datetime.fromtimestamp(msg["date"]).strftime("%Y-%m-%d %H:%M"),
                "date":    datetime.fromtimestamp(msg["date"]).strftime("%Y-%m-%d"),
                "from":    sender.get("first_name", "") + " " + sender.get("last_name", ""),
                "from_id": sender.get("id", 0),
                "chat":    chat.get("title") or chat.get("first_name", "私聊"),
                "chat_id": chat.get("id", 0),
                "text":    text,
            }
            with INBOX.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.info(f"记录: {record['from']} @ {record['chat']}: {text[:40]}")

        if not updates:
            time.sleep(2)

if __name__ == "__main__":
    main()
