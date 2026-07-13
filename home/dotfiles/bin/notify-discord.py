#!/home/charlie/bin/.notify-venv/bin/python3
"""Discord 通知网关 — Bot API 直发（无需 Webhook 权限）
用法: echo "内容" | python3 ~/bin/notify-discord.py P1 "标题" "#频道名"
级别: P0(立即) P1(15min内) P2(每日摘要) P3(仅存档)
频道: 默认 #alerts，可指定 #marketing/#tech/#ops/#brain/#daily-digest

首次使用需运行: python3 ~/bin/notify-discord.py --setup
  创建 Discord 频道 → 保存频道 ID 到 ~/.config/ai/discord-channels.json
"""

import asyncio, hashlib, json, sys, os
from datetime import datetime
from pathlib import Path

BOT_TOKEN = os.environ.get(
    "DISCORD_BOT_TOKEN",
    "MTQ5MDY0MTY3ODEzNzAzMjg0NA.G7dnjb.8XnDoykFr9O8SRsQH1nnCXiV0Ge2LEOGTI47f8",
)
GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", "1490683033919950941"))
STATE_FILE = Path(os.environ.get("NOTIFY_STATE_FILE", Path.home() / ".local/state/notify-state.json"))
CHANNEL_FILE = Path.home() / ".config" / "ai" / "discord-channels.json"

# 角色定义：频道名 → { 显示名, 主题色 }
PERSONAS = {
    "alerts": {"name": "🛡️ 哨兵", "color": 0xE74C3C},
    "marketing": {"name": "📊 营销总监", "color": 0x9B59B6},
    "tech": {"name": "🔧 架构师", "color": 0x2ECC71},
    "ops": {"name": "⚡ 调度员", "color": 0xF39C12},
    "brain": {"name": "🧠 Charlie", "color": 0x3498DB},
    "daily-digest": {"name": "📋 每日摘要", "color": 0x1ABC9C},
}

CHANNELS = list(PERSONAS.keys())

COOLDOWN_SEC = {"P0": 60, "P1": 300, "P2": 1800, "P3": 86400}
COLOR_MAP = {"P0": 0xFF0000, "P1": 0xFFA500, "P2": 0x3498DB, "P3": 0x95A5A6}
EMOJI = {"P0": "🔴", "P1": "⚠️", "P2": "📋", "P3": "📝"}


# ── State & Config ──────────────────────────────────────────


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


def load_channels():
    if CHANNEL_FILE.exists():
        try:
            return json.loads(CHANNEL_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_channels(channels):
    CHANNEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHANNEL_FILE.write_text(json.dumps(channels, indent=2))


def should_notify(level, content_hash, state):
    now = datetime.now()
    key = f"dc:{level}:{content_hash}"
    last = state.get(key, {}).get("time")
    if last:
        try:
            elapsed = (now - datetime.fromisoformat(last)).total_seconds()
            if elapsed < COOLDOWN_SEC.get(level, 300):
                return False, int(elapsed)
        except (ValueError, TypeError):
            pass
    return True, 0


# ── Discord REST API ────────────────────────────────────────


async def api(method, path, json_data=None):
    """Discord REST API helper with proxy support."""
    import aiohttp

    proxy = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    url = f"https://discord.com/api/v10{path}"
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method,
            url,
            headers=headers,
            json=json_data,
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            data = await resp.json()
            if resp.status >= 400:
                print(f"[FAIL] API {resp.status}: {data}", file=sys.stderr)
                return None
            return data


# ── Setup ───────────────────────────────────────────────────


async def setup_channels():
    """创建 Discord 频道（纯 REST，不走 Gateway）"""
    channels = load_channels()

    existing_list = await api("GET", f"/guilds/{GUILD_ID}/channels")
    if existing_list is None:
        return

    existing = {ch["name"]: ch for ch in existing_list if ch["type"] == 0}
    categories = {ch["id"]: ch for ch in existing_list if ch["type"] == 4}
    print(f"Guild: {GUILD_ID} ({len(existing)} text channels)")

    # Find or create "AI Agents" category
    cat_id = None
    for cid, cat in categories.items():
        if cat["name"] == "AI Agents":
            cat_id = cid
            print(f"  [SKIP] Category 'AI Agents' exists")
            break

    if not cat_id:
        result = await api(
            "POST",
            f"/guilds/{GUILD_ID}/channels",
            {
                "name": "AI Agents",
                "type": 4,
            },
        )
        if result:
            cat_id = result["id"]
            print(f"  [NEW] Category: AI Agents")
        else:
            print("[FAIL] Cannot create category", file=sys.stderr)
            return

    for ch_name in CHANNELS:
        if ch_name in existing:
            channel = existing[ch_name]
            channels[ch_name] = channel["id"]
            print(f"  [SKIP] #{ch_name} exists (id={channel['id']})")
        else:
            result = await api(
                "POST",
                f"/guilds/{GUILD_ID}/channels",
                {
                    "name": ch_name,
                    "type": 0,
                    "parent_id": cat_id,
                },
            )
            if result:
                channels[ch_name] = result["id"]
                print(f"  [NEW] #{ch_name}")
            else:
                print(f"  [FAIL] Cannot create #{ch_name}", file=sys.stderr)

    save_channels(channels)
    print(f"\n[OK] Setup complete. Channels saved to {CHANNEL_FILE}")


# ── Send Message ────────────────────────────────────────────


async def send_message(content, title, level, channel_name="alerts"):
    """通过 Bot API 直接发送 Discord 消息（embed 区分角色）"""
    import aiohttp

    channels = load_channels()

    if channel_name not in channels:
        print(
            f"[FAIL] No channel ID for #{channel_name}. Run --setup first.",
            file=sys.stderr,
        )
        return False

    channel_id = channels[channel_name]
    persona = PERSONAS.get(channel_name, {"name": channel_name, "color": 0x95A5A6})

    ts = datetime.now().strftime("%m-%d %H:%M")
    emoji = EMOJI.get(level, "📋")
    embed = {
        "title": f"{emoji} [{level}] {ts}" + (f" — {title}" if title else ""),
        "description": content[:4096],
        "color": persona["color"],
        "footer": {"text": persona["name"]},
    }

    payload = {"embeds": [embed]}

    proxy = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status < 400:
                        return True
                    elif resp.status == 429:
                        data = await resp.json()
                        await asyncio.sleep(data.get("retry_after", 5))
                    else:
                        body = await resp.text()
                        print(
                            f"[FAIL] API {resp.status}: {body[:200]}", file=sys.stderr
                        )
                        return False
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                else:
                    print(f"[FAIL] Send error: {e}", file=sys.stderr)
                    return False
    return False


# ── Main ────────────────────────────────────────────────────


async def main():
    if "--setup" in sys.argv:
        await setup_channels()
        return

    level = "P2"
    title = ""
    channel_name = "alerts"

    for arg in sys.argv[1:]:
        if arg in COOLDOWN_SEC:
            level = arg
        elif arg.startswith("#"):
            channel_name = arg.lstrip("#")
        elif not title:
            title = arg

    content = sys.stdin.read().strip()
    if not content:
        return

    content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
    state = load_state()

    ok, elapsed = should_notify(level, content_hash, state)
    if not ok:
        print(f"[SKIP] cooldown {elapsed}s/{COOLDOWN_SEC[level]}s")
        return

    if await send_message(content, title, level, channel_name):
        key = f"dc:{level}:{content_hash}"
        state[key] = {
            "time": datetime.now().isoformat(),
            "title": title,
            "channel": channel_name,
        }
        save_state(state)
        print(f"[OK] Sent [{level}] to Discord #{channel_name}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
