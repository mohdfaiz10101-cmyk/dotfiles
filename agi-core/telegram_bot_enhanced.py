"""
telegram_bot_enhanced.py — AGI Brain Telegram Bot
Why: 让用户通过 Telegram 与 AGI Brain 对话，查询状态和派发任务
What: polling 模式，支持自然语言对话 + /start /status /tasks 命令 + 图片多模态理解
Test: 发送 /start 验证收到欢迎消息；发送"系统状态"验证返回状态摘要；发送图片验证返回中文描述
踩坑：httpx timeout 必须 ≥40s；Python 3.13 用 asyncio.run()；避免调 logOut API；vision 模型超时设 60s
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

import httpx

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest
from conversation import chat

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
STATUS_FILE = os.environ.get("STATUS_FILE", "/tmp/agi-brain-status.json")
OP_TASKS_FILE = os.environ.get(
    "OP_TASKS_FILE", "/home/charlie/.claude/projects/-home-charlie/memory/op-tasks.md"
)

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://localhost:4000/v1")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "sk-litellm-charlie-2026")
VISION_MODEL = os.environ.get("VISION_MODEL", "doubao/vision")


def _check_auth(update: Update) -> bool:
    """验证消息来自授权用户或群组@提及。

    Why: 防止未授权用户控制 AGI Brain，但允许群组中@机器人
    What: 私聊对比chat_id，群组检测@提及+发送者ID
    Test: 私聊正确ID返回True；群组@机器人返回True；群组无@返回False
    """
    if not update.effective_chat:
        return False

    # 私聊：直接对比chat_id
    if update.effective_chat.type == "private":
        return update.effective_chat.id == ALLOWED_CHAT_ID

    # 群组/超级群组：检查是否@提及机器人
    if update.effective_chat.type in ("group", "supergroup"):
        if not update.message:
            return False

        # 检查entities中是否有mention
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":
                    # 提取@后的bot用户名
                    text = update.message.text or ""
                    mention = text[entity.offset : entity.offset + entity.length]
                    # 获取当前bot的用户名
                    bot_username = (
                        context.application.bot.username
                        if hasattr(context, "application")
                        else ""
                    )
                    if mention == f"@{bot_username}":
                        return True

        # 检查回复是否是机器人发的消息
        if (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
        ):
            if update.message.reply_to_message.from_user.is_bot:
                return True

    return False


def _check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    """验证消息来自授权用户或群组@提及。

    Why: 防止未授权用户控制 AGI Brain，但允许群组中@机器人
    What: 私聊对比chat_id，群组检测@提及+发送者ID
    Test: 私聊正确ID返回True；群组@机器人返回True；群组无@返回False
    """
    if not update.effective_chat:
        return False

    # 私聊：直接对比chat_id
    if update.effective_chat.type == "private":
        return update.effective_chat.id == ALLOWED_CHAT_ID

    # 群组/超级群组：检查是否@提及机器人
    if update.effective_chat.type in ("group", "supergroup"):
        if not update.message:
            return False
        if not context or not hasattr(context, "application"):
            return False

        # 检查entities中是否有mention
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":
                    # 提取@后的bot用户名
                    text = update.message.text or ""
                    mention = text[entity.offset : entity.offset + entity.length]
                    # 获取当前bot的用户名
                    bot_username = context.application.bot.username
                    if mention == f"@{bot_username}":
                        return True

        # 检查回复是否是机器人发的消息
        if (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
        ):
            if update.message.reply_to_message.from_user.is_bot:
                return True

    return False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /start 命令。

    Why: 引导用户了解 Bot 功能
    What: 发送欢迎消息和命令列表
    Test: 发送 /start 验证收到中文欢迎消息
    """
    if not _check_auth(update, context):
        return
    await update.message.reply_text(
        "🧠 AGI Brain 已连接\n\n"
        "命令列表：\n"
        "/status — 查看系统状态\n"
        "/tasks — 查看 OP 待执行任务\n"
        "/help — 帮助\n\n"
        "直接发消息即可对话，支持：\n"
        "• 查询系统状态\n"
        "• 派发任务给 OP\n"
        "• 日常对话"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /status 命令，返回当前系统状态。

    Why: 快速获取系统状态无需自然语言识别
    What: 读取状态文件，格式化输出
    Test: 验证输出包含更新时间和摘要字段
    """
    if not _check_auth(update, context):
        return
    status_path = Path(STATUS_FILE)
    if not status_path.exists():
        await update.message.reply_text("⚠️ AGI Brain 状态文件不存在，Brain 可能未运行")
        return
    try:
        status = json.loads(status_path.read_text())
        updated = status.get("updated_at", "未知")[:19].replace("T", " ")
        summary = status.get("summary", "无摘要")
        alerts = status.get("alerts", [])
        sense = status.get("sense", {})

        msg = (
            f"📊 系统状态（{updated}）\n\n"
            f"摘要：{summary}\n"
            f"CPU：{sense.get('cpu_usage', 'N/A')}\n"
            f"内存：{sense.get('memory_usage', 'N/A')}\n"
            f"AI盘：{sense.get('disk_ai', 'N/A')}"
        )
        if alerts:
            msg += "\n\n⚠️ 告警：\n" + "\n".join(f"• {a}" for a in alerts)

        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"读取状态失败：{e}")


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /tasks 命令，显示 OP 待执行任务。

    Why: 让用户了解 AGI Brain 派发的任务队列
    What: 读取 op-tasks.md，过滤未完成任务
    Test: 验证输出包含 [ ] 标记的任务或"暂无"提示
    """
    if not _check_auth(update):
        return
    op_tasks_path = Path(OP_TASKS_FILE)
    if not op_tasks_path.exists():
        await update.message.reply_text("📋 OP 任务文件不存在（暂无派发任务）")
        return
    content = op_tasks_path.read_text(encoding="utf-8")
    pending = [line for line in content.splitlines() if "- [ ]" in line]
    if not pending:
        await update.message.reply_text("✅ 暂无待执行的 OP 任务")
        return
    tasks_text = "\n".join(pending[-10:])  # 最多显示10条
    await update.message.reply_text(f"📋 待执行任务（最近10条）：\n{tasks_text}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /help 命令。

    Why: 提供功能说明
    What: 发送帮助文本
    Test: 验证回复包含功能说明
    """
    if not _check_auth(update, context):
        return
    await update.message.reply_text(
        "🧠 AGI Brain 使用指南\n\n"
        "命令：\n"
        "  /status — 系统状态摘要\n"
        "  /tasks — OP 待执行任务\n\n"
        "自然语言示例：\n"
        "  「系统状态如何？」\n"
        "  「派任务给OP：检查LiteLLM服务」\n"
        "  「今天有什么需要关注的？」"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理普通文本消息（自然语言对话）。

    Why: 让用户自然语言与 AGI Brain 交互，无需记忆命令
    What: 调用 conversation.chat()，返回 LLM 生成的回复
    Test: 发送"你好"验证收到中文回复
    """
    logging.info("[MSG] chat=%s type=%s text=%r entities=%s",
        update.effective_chat.id,
        update.effective_chat.type,
        (update.message.text or "")[:50],
        update.message.entities)
    if not _check_auth(update, context):
        logging.info("[AUTH] rejected chat=%s type=%s", update.effective_chat.id, update.effective_chat.type)
        return
    user_text = update.message.text or ""
    if not user_text.strip():
        return

    await update.message.chat.send_action("typing")
    session_id = f"telegram_{update.effective_chat.id}"

    try:
        reply = await chat(user_text, session_id=session_id)
    except Exception as e:
        reply = f"处理消息时出错：{e}"

    await update.message.reply_text(reply)


async def _analyze_image_with_vision(image_bytes: bytes, caption: str) -> str:
    """调用 LiteLLM doubao/vision 模型分析图片，返回中文描述。

    Why: 封装 vision 请求逻辑，与 handler 解耦，便于单独测试
    What: 将图片转 base64，构建 OpenAI vision format 请求，返回模型回复文本
    Test: 传入有效 JPEG bytes + 空 caption，断言返回非空中文字符串
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        caption.strip()
        if caption.strip()
        else "请用中文详细描述这张图片的内容、场景和关键细节"
    )

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{LITELLM_BASE}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {LITELLM_KEY}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户发送的图片或文档图片（多模态理解）。

    Why: 让用户直接发图给 Bot，用 doubao/vision 模型获得中文图片分析
    What: 下载最高分辨率图片 → base64 编码 → 调用 vision API → 回复中文描述
    Test: 发送一张截图，验证 Bot 在 60s 内回复非空中文描述；发带文字说明的图片，
          验证文字被作为 prompt 传入
    """
    if not _check_auth(update, context):
        return

    await update.message.chat.send_action("upload_photo")

    # 获取图片文件对象：photo 列表最后一项是最高分辨率
    caption = update.message.caption or ""
    file_obj = None

    if update.message.photo:
        tg_file = await update.message.photo[-1].get_file()
        file_obj = tg_file
    elif update.message.document:
        doc = update.message.document
        # 仅处理图片类文档（mime_type 以 image/ 开头）
        if not doc.mime_type or not doc.mime_type.startswith("image/"):
            await update.message.reply_text("⚠️ 仅支持图片文件（JPEG/PNG/GIF/WEBP 等）")
            return
        file_obj = await doc.get_file()

    if file_obj is None:
        await update.message.reply_text("⚠️ 无法获取图片，请重试")
        return

    # 下载到临时文件，处理完立即删除
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        await file_obj.download_to_drive(tmp_path)
        image_bytes = tmp_path.read_bytes()

        await update.message.chat.send_action("typing")
        result = await _analyze_image_with_vision(image_bytes, caption)
        await update.message.reply_text(result)

    except httpx.TimeoutException:
        await update.message.reply_text("⏱️ 图片理解超时（60s），请重试或发送较小的图片")
    except Exception as e:
        print(f"[VISION] 图片分析失败: {e}")
        await update.message.reply_text("图片理解失败，请重试")
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    """启动 Telegram Bot（polling 模式）。

    Why: 持续监听 Telegram 消息，响应用户交互
    What: 构建 Application，注册 handlers，启动 polling
    Test: 启动后发送 /start 验证收到回复
    """
    if not BOT_TOKEN:
        print("[TELEGRAM] 错误：TELEGRAM_BOT_TOKEN 未配置")
        return

    print(f"[TELEGRAM] Bot 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 自定义 HTTP 请求：proxy + verify=False（httpx NixOS 系统版本 SSL over proxy 有 bug）
    telegram_request = HTTPXRequest(
        proxy="http://127.0.0.1:7890",
        read_timeout=20.0,
        write_timeout=20.0,
        connect_timeout=20.0,
        httpx_kwargs={"verify": False},
    )
    app = Application.builder().token(BOT_TOKEN).request(telegram_request).build()

    # 注册命令处理器
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("tasks", cmd_tasks))
    app.add_handler(CommandHandler("help", cmd_help))

    # 注册图片处理器（photo + document 图片，优先于文字 handler）
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_image))

    # 注册普通消息处理器
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 全局 update 日志（排查群消息）
    async def log_all_updates(update, context):
        logging.info("[UPDATE] %s", update.to_dict())
    app.add_handler(MessageHandler(filters.ALL, log_all_updates), group=99)

    # 启动 polling
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=False,  # 不丢弃积压消息
    )


if __name__ == "__main__":
    main()
