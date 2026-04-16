#!/home/charlie/bin/.notify-venv/bin/python3
"""Telegram 通知网关 — 带 cooldown/dedup/分级
用法: echo "内容" | python3 ~/bin/notify-telegram.py P1 "标题"
级别: P0(立即) P1(15min内) P2(每日摘要) P3(仅存档)
"""

import asyncio, hashlib, json, sys, os
from datetime import datetime, timedelta
from pathlib import Path

BOT_TOKEN = os.environ.get(
    "TG_BOT_TOKEN", "8797063873:AAGvApEP9frmA74b6nmxODHshzo1TwJR5ks"
)
CHAT_ID = os.environ.get("TG_CHAT_ID", "5036541266")
PROXY = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
STATE_FILE = Path(os.environ.get("NOTIFY_STATE_FILE", "/tmp/notify-state.json"))

COOLDOWN_SEC = {"P0": 60, "P1": 300, "P2": 1800, "P3": 86400}
EMOJI = {"P0": "🔴", "P1": "⚠️", "P2": "📋", "P3": "📝"}


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except OSError:
        pass


def should_notify(level, content_hash, state):
    now = datetime.now()
    key = f"{level}:{content_hash}"
    last = state.get(key, {}).get("time")
    if last:
        try:
            elapsed = (now - datetime.fromisoformat(last)).total_seconds()
            if elapsed < COOLDOWN_SEC.get(level, 300):
                return False, int(elapsed)
        except (ValueError, TypeError):
            pass
    return True, 0


async def send_telegram(text):
    import aiohttp

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text[:4000], "parse_mode": "HTML"}

    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.post(
                    url,
                    json=payload,
                    proxy=PROXY,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 429:
                        data = await resp.json()
                        retry = data.get("parameters", {}).get("retry_after", 5)
                        await asyncio.sleep(retry)
                    elif resp.status < 400:
                        return True
                    else:
                        body = await resp.text()
                        print(
                            f"[FAIL] TG API {resp.status}: {body[:200]}",
                            file=sys.stderr,
                        )
                        return False
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                else:
                    print(f"[FAIL] TG send error: {e}", file=sys.stderr)
                    return False
    return False


async def main():
    level = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in COOLDOWN_SEC else "P2"
    title = sys.argv[2] if len(sys.argv) > 2 else ""

    content = sys.stdin.read().strip()
    if not content:
        return

    content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
    state = load_state()

    ok, elapsed = should_notify(level, content_hash, state)
    if not ok:
        print(f"[SKIP] cooldown {elapsed}s/{COOLDOWN_SEC[level]}s")
        return

    ts = datetime.now().strftime("%m-%d %H:%M")
    emoji = EMOJI.get(level, "📋")
    header = f"{emoji} [{level}] {ts}"
    if title:
        header += f" — {title}"

    msg = f"<b>{header}</b>\n\n{content[:3900]}"

    if await send_telegram(msg):
        state[f"{level}:{content_hash}"] = {
            "time": datetime.now().isoformat(),
            "title": title,
        }
        save_state(state)
        print(f"[OK] Sent [{level}] to Telegram")
    else:
        print(f"[FAIL] Could not send", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
