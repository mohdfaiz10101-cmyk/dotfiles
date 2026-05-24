#!/usr/bin/env python3
"""
telegram-khoj-bridge.py — Khoj Telegram 话题群桥接
监听群消息 → Khoj API 搜索 → LLM 总结 → 回复
"""
import asyncio, json, os, logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("khoj-bridge")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
KHOJ_URL = "http://127.0.0.1:42110"
LITELLM_URL = "http://127.0.0.1:4000/v1/chat/completions"
LITELLM_KEY = "sk-litellm-charlie-2026"

# 允许的群组 chat_id
ALLOWED_CHATS = set()


async def search_khoj(query: str) -> list[dict]:
    """搜索 Khoj 知识库"""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{KHOJ_URL}/api/search", params={"q": query}, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # SSE 格式解析
                    results = []
                    for line in text.strip().split("\n"):
                        if line.startswith("data:"):
                            try:
                                data = json.loads(line[5:].strip())
                                if isinstance(data, list):
                                    results.extend(data)
                                elif isinstance(data, dict):
                                    results.append(data)
                            except json.JSONDecodeError:
                                continue
                    return results
    except Exception as e:
        log.error(f"Khoj search failed: {e}")
    return []


async def ask_llm(query: str, context: str = "") -> str:
    """用 LLM 回答问题"""
    import aiohttp
    messages = []
    if context:
        messages.append({"role": "system", "content": f"你是 Khoj 知识库助手。根据以下上下文回答用户问题。\n\n上下文：\n{context}"})
    messages.append({"role": "user", "content": query})
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LITELLM_URL,
                json={
                    "model": "glm-4-flash",
                    "messages": messages,
                    "max_tokens": 2000,
                    "temperature": 0.3,
                },
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    text = await resp.text()
                    return f"LLM 调用失败 ({resp.status}): {text[:200]}"
    except Exception as e:
        return f"LLM 调用异常: {e}"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理群消息"""
    chat_id = update.effective_chat.id
    text = update.message.text or ""
    
    # 记录群
    ALLOWED_CHATS.add(chat_id)
    
    # 只响应提及 bot 的消息
    if not text or "@charlie_1688_bot" not in text:
        return
    
    query = text.replace("@charlie_1688_bot", "").strip()
    if not query:
        await update.message.reply_text("请发送问题，例如：@charlie_1688_bot 什么是 Khoj？")
        return
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # 搜索 Khoj
    khoj_results = await search_khoj(query)
    if khoj_results:
        context_str = "\n".join([
            r.get("entry", r.get("title", str(r)[:200]))
            for r in khoj_results[:5]
        ])
        answer = await ask_llm(query, context_str)
    else:
        answer = await ask_llm(query)
    
    # 回复
    preview = answer[:800]
    if len(answer) > 800:
        preview += "\n\n…(已截断)"
    
    await update.message.reply_text(preview, reply_to_message_id=update.message.message_id)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Khoj 知识库助手已就绪\n"
        "在群里 @charlie_1688_bot 加问题即可搜索\n"
        "索引范围：文档 / 笔记 / 图片 / 代码"
    )


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("khoj", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    log.info("Khoj Telegram Bridge 启动中...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())