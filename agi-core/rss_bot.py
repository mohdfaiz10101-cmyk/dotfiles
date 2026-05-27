"""
rss_bot.py — FreshRSS Telegram Bot (@charlie_rss_bot)
Why: 通过 Telegram 管理 FreshRSS 订阅，推送摘要，免开浏览器
What: polling 模式，支持订阅/列表/未读/推送/标记已读
Test: /list 验证返回订阅列表；/unread 3 验证返回3条带摘要的未读
"""

import asyncio
import logging
import os
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = "8741460176:AAEfqHpKo-bmu7bF4d7jMgGkn4gG9QPCzXQ"
ALLOWED_CHATS = {-1003725372254, -1003676314922, 5036541266}

FRESHRSS_BASE = "http://localhost:8420/api/greader.php"
FRESHRSS_USER = "admin"
FRESHRSS_PASS = "admin"

LITELLM_BASE = "http://localhost:4000/v1"
LITELLM_KEY = "sk-litellm-charlie-2026"
TEXT_MODEL = "glm-4.7"
PROXY = "http://127.0.0.1:7890"

# token 缓存
_auth_token: str = ""
_auth_expires: float = 0.0


def _check_auth(update: Update) -> bool:
    """验证消息来自授权聊天。
    Why: 防止未授权用户操控 RSS bot
    What: 检查 chat id 是否在白名单
    Test: 白名单 id 返回 True，其他返回 False
    """
    cid = update.effective_chat.id if update.effective_chat else 0
    return cid in ALLOWED_CHATS


async def _get_freshrss_token() -> str:
    """获取 FreshRSS GReader API auth token（55分钟缓存）。
    Why: GReader API 每次请求需要 token，缓存避免重复登录
    What: POST ClientLogin → 解析 Auth= 行 → 缓存55分钟
    Test: 连续两次调用，第二次不发 HTTP 请求（时间戳相同）
    """
    global _auth_token, _auth_expires
    if _auth_token and time.time() < _auth_expires:
        return _auth_token
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{FRESHRSS_BASE}/accounts/ClientLogin",
            data={"Email": FRESHRSS_USER, "Passwd": FRESHRSS_PASS},
        )
        resp.raise_for_status()
        for line in resp.text.splitlines():
            if line.startswith("Auth="):
                _auth_token = line[5:].strip()
                _auth_expires = time.time() + 55 * 60
                return _auth_token
    raise RuntimeError("FreshRSS 登录失败，未找到 Auth token")


async def _freshrss_get(path: str, params: dict | None = None) -> dict:
    """发送已认证的 GReader API GET 请求。
    Why: 封装认证头，避免每处重复
    What: 自动获取 token → 带 Authorization 发 GET
    Test: 调用 /reader/api/0/subscription/list 验证返回 subscriptions 列表
    """
    token = await _get_freshrss_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{FRESHRSS_BASE}/reader/api/0{path}",
            params={**(params or {}), "output": "json"},
            headers={"Authorization": f"GoogleLogin auth={token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def _freshrss_post(path: str, data: dict) -> httpx.Response:
    """发送已认证的 GReader API POST 请求。
    Why: 写操作（标记已读/添加订阅）需要 POST
    What: 获取 token → 带 Authorization 发 POST
    Test: 标记已读后再 /unread 验证数量减少
    """
    token = await _get_freshrss_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{FRESHRSS_BASE}/reader/api/0{path}",
            data=data,
            headers={"Authorization": f"GoogleLogin auth={token}"},
        )
        return resp


async def _llm_summarize(text: str) -> str:
    """用 glm-4.7 生成50字摘要。
    Why: 未读条目内容过长，摘要方便快速浏览
    What: POST LiteLLM → 返回50字以内摘要
    Test: 传入长文本，返回字符串长度 ≤ 150
    """
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{LITELLM_BASE}/chat/completions",
                json={
                    "model": TEXT_MODEL,
                    "messages": [
                        {"role": "system", "content": "请用50字以内中文摘要以下文章，直接输出摘要，不要前缀。"},
                        {"role": "user", "content": text[:1500]},
                    ],
                    "max_tokens": 120,
                },
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            )
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"（摘要失败: {e}）"


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """显示订阅列表（最多20条）。
    Why: 快速查看当前 RSS 订阅源
    What: 调用 /subscription/list → 格式化输出标题+URL
    Test: /list 验证返回包含订阅数量的消息
    """
    if not _check_auth(update):
        return
    try:
        data = await _freshrss_get("/subscription/list")
        subs = data.get("subscriptions", [])[:20]
        if not subs:
            await update.message.reply_text("暂无订阅源")
            return
        lines = [f"📰 订阅列表（{len(subs)} 条）："]
        for i, s in enumerate(subs, 1):
            lines.append(f"{i}. {s.get('title', '无标题')}")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"获取订阅列表失败: {e}")


async def cmd_unread(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """获取最新未读条目并附带摘要。
    Why: 快速浏览未读，每条自动摘要节省时间
    What: 拉取未读 → 并发 LLM 摘要 → 逐条发送
    Test: /unread 3 验证返回3条带标题和摘要的消息
    """
    if not _check_auth(update):
        return
    n = int(context.args[0]) if context.args and context.args[0].isdigit() else 5
    n = min(n, 10)
    try:
        data = await _freshrss_get("/stream/contents/user/-/state/com.google/reading-list", {
            "xt": "user/-/state/com.google/read",
            "n": str(n),
        })
        items = data.get("items", [])
        if not items:
            await update.message.reply_text("暂无未读条目 ✅")
            return
        await update.message.reply_text(f"📥 获取 {len(items)} 条未读，正在生成摘要…")
        for item in items:
            title = item.get("title", "无标题")
            content = item.get("summary", {}).get("content", "") or item.get("content", {}).get("content", "")
            link = item.get("alternate", [{}])[0].get("href", "")
            summary = await _llm_summarize(content or title)
            msg = f"📌 **{title}**\n{summary}"
            if link:
                msg += f"\n🔗 {link}"
            await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"获取未读失败: {e}")


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """添加 RSS 订阅源。
    Why: 无需打开浏览器即可订阅
    What: POST /subscription/edit 添加 feed URL
    Test: /subscribe https://example.com/rss → 验证订阅成功回复
    """
    if not _check_auth(update):
        return
    url = context.args[0] if context.args else ""
    if not url or not url.startswith("http"):
        await update.message.reply_text("用法：/subscribe <RSS URL>")
        return
    try:
        resp = await _freshrss_post("/subscription/edit", {
            "ac": "subscribe",
            "s": f"feed/{url}",
        })
        if resp.status_code in (200, 204):
            await update.message.reply_text(f"✅ 已添加订阅：{url}")
        else:
            await update.message.reply_text(f"添加失败（{resp.status_code}）：{resp.text[:200]}")
    except Exception as e:
        await update.message.reply_text(f"订阅失败: {e}")


async def cmd_push(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """主动推送5条未读（复用 cmd_unread 逻辑）。
    Why: 快捷推送，不需要指定数量
    What: 设 context.args = ["5"] 后调用 cmd_unread
    Test: /push → 收到5条未读推送
    """
    if not _check_auth(update):
        return
    context.args = ["5"]
    await cmd_unread(update, context)


async def cmd_markread(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """标记全部已读。
    Why: 批量清理未读数量
    What: POST /mark-all-as-read
    Test: /markread 后 /unread 验证返回"暂无未读"
    """
    if not _check_auth(update):
        return
    try:
        ts = int(time.time())
        await _freshrss_post("/mark-all-as-read", {"s": "user/-/state/com.google/reading-list", "ts": str(ts)})
        await update.message.reply_text("✅ 已标记全部已读")
    except Exception as e:
        await update.message.reply_text(f"标记失败: {e}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update):
        return
    await update.message.reply_text(
        "📰 RSS Bot 使用指南\n\n"
        "/list — 订阅列表\n"
        "/unread [n] — 获取n条未读（默认5）\n"
        "/subscribe <url> — 添加订阅源\n"
        "/push — 推送5条未读\n"
        "/markread — 标记全部已读\n\n"
        "直接发 URL 自动订阅"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """自然语言：检测 URL 自动订阅。
    Why: 减少命令记忆负担，直接粘贴 URL 即可订阅
    What: 检测消息含 http → 当 RSS URL 订阅
    Test: 发送 https://example.com/feed.xml → 自动订阅
    """
    if not _check_auth(update):
        return
    text = (update.message.text or "").strip()
    if text.startswith("http"):
        context.args = [text.split()[0]]
        await cmd_subscribe(update, context)
    else:
        await update.message.reply_text("发送 /help 查看命令，或直接发 RSS URL 快速订阅")


def main() -> None:
    if not BOT_TOKEN:
        print("错误：BOT_TOKEN 未配置")
        return
    print(f"[RSS-BOT] 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    req = HTTPXRequest(proxy=PROXY, read_timeout=30.0, connect_timeout=15.0, httpx_kwargs={"verify": False})
    app = Application.builder().token(BOT_TOKEN).request(req).build()
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("unread", cmd_unread))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("push", cmd_push))
    app.add_handler(CommandHandler("markread", cmd_markread))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=["message"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
