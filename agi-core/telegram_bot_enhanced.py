"""
telegram_bot_enhanced.py — AGI Brain Telegram Bot (L2 对话运维增强版)
Why: 让用户通过 Telegram 与 AGI Brain 对话，查询状态和派发任务
What: polling 模式，支持自然语言对话 + /start /status /tasks 命令 + 图片多模态理解
      + L2-L5: /check /restart /logs /top /diag /heal 运维命令
      + 内联按钮回调: 处理通知中的操作按钮
      + Topic 感知: 群话题中回复到同一话题
Test: 发送 /start 验证收到欢迎消息；发送"系统状态"验证返回状态摘要；发送图片验证返回中文描述
踩坑：httpx timeout 必须 >=40s；Python 3.13 用 asyncio.run()；避免调 logOut API；vision 模型超时设 60s
"""

import asyncio
import base64
import json
import logging
import os
import sys
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
    CallbackQueryHandler,
)
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

# L2-L5 运维引擎（GLM 驱动）
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "dotfiles/agi-core"))
    from tg_pilot import (
        recognize_command, execute_command, CommandResult,
        analyze_notification, NotificationAnalysis,
        scan_and_heal, format_heal_results,
        format_command_result, format_notification_with_analysis,
    )
    _PILOT_LOADED = True
except ImportError:
    _PILOT_LOADED = False

# Forum 群组（通知中心），master 在群中可免授权操作
FORUM_GROUP_ID = int(os.environ.get("TG_FORUM_GROUP", "-1003988580955"))
FINANCE_GROUP_ID = int(os.environ.get("TG_FINANCE_GROUP", "-1003943958531"))
GMAIL_GROUP_ID = int(os.environ.get("TG_GMAIL_GROUP", "-1003754366054"))
MEMORY_TOPIC_ID = 52  # 🧠 记忆系统监控 topic，供 CC/OP 讨论


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


def _is_in_forum(update: Update) -> bool:
    """检查消息是否来自 Forum 群组"""
    return (update.effective_chat
            and update.effective_chat.id == FORUM_GROUP_ID)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /help 命令。
    """
    if not _check_auth(update, context) and not _is_in_forum(update):
        return
    await update.message.reply_text(
        "🧠 AGI Brain 使用指南\n\n"
        "📊 <b>查看</b>\n"
        "  /status — 系统状态摘要\n"
        "  /tasks — OP 待执行任务\n"
        "  /top — 资源概览\n\n"
        "🔧 <b>运维</b>\n"
        "  /check &lt;服务&gt; — 检查服务状态\n"
        "  /logs &lt;服务&gt; — 查看服务日志\n"
        "  /restart &lt;服务&gt; — 重启服务\n"
        "  /diag — 完整系统诊断\n"
        "  /heal — 扫描+自动修复\n\n"
        "💬 自然语言直接对话",
        parse_mode="HTML"
    )


# ── L2: 运维命令处理器 ──────────────────────────────────────────────

async def _reply_in_topic(update: Update, text: str, parse_mode: str = "HTML"):
    """在话题中回复（如果消息来自 Forum 话题）"""
    kwargs = {"text": text[:4000], "parse_mode": parse_mode}
    if (update.effective_message
            and update.effective_message.message_thread_id
            and update.effective_chat
            and update.effective_chat.type == "supergroup"):
        kwargs["message_thread_id"] = update.effective_message.message_thread_id
    await update.message.reply_text(**kwargs)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update, context) and not _is_in_forum(update):
        return
    target = " ".join(context.args) if context.args else ""
    if not target:
        await _reply_in_topic(update, "用法: /check &lt;服务名&gt;")
        return

    await update.message.chat.send_action("typing")
    if _PILOT_LOADED:
        result = await execute_command("check", target)
        await _reply_in_topic(update, format_command_result(result))
    else:
        import subprocess
        p = subprocess.run(
            ["systemctl", "--user", "status", target, "--no-pager", "-l", "-n", "20"],
            capture_output=True, text=True, timeout=10
        )
        await _reply_in_topic(update, f"<pre>{p.stdout[:1500]}</pre>")


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update, context) and not _is_in_forum(update):
        return
    target = " ".join(context.args) if context.args else ""
    if not target:
        await _reply_in_topic(update, "用法: /restart &lt;服务名&gt;")
        return

    await update.message.chat.send_action("typing")
    if _PILOT_LOADED:
        result = await execute_command("restart", target)
        await _reply_in_topic(update, format_command_result(result))
    else:
        import subprocess
        p = subprocess.run(
            ["systemctl", "--user", "restart", target],
            capture_output=True, text=True, timeout=15
        )
        if p.returncode == 0:
            await _reply_in_topic(update, f"✅ 已重启 {target}")
        else:
            await _reply_in_topic(update, f"❌ 重启失败: {p.stderr[:300]}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update, context) and not _is_in_forum(update):
        return
    target = " ".join(context.args) if context.args else ""
    if not target:
        await _reply_in_topic(update, "用法: /logs &lt;服务名&gt;")
        return

    await update.message.chat.send_action("typing")
    if _PILOT_LOADED:
        result = await execute_command("logs", target)
        await _reply_in_topic(update, format_command_result(result))
    else:
        import subprocess
        p = subprocess.run(
            ["journalctl", "--user", "-u", target, "--no-pager", "-n", "20"],
            capture_output=True, text=True, timeout=10
        )
        await _reply_in_topic(update, f"<pre>{p.stdout[:1500]}</pre>")


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update, context) and not _is_in_forum(update):
        return
    await update.message.chat.send_action("typing")
    if _PILOT_LOADED:
        result = await execute_command("top", "")
        await _reply_in_topic(update, format_command_result(result))
    else:
        import subprocess
        cpu = subprocess.check_output("top -bn1 | head -3", shell=True, timeout=5).decode()
        mem = subprocess.check_output("free -h", shell=True, timeout=5).decode()
        disk = subprocess.check_output("df -h / /mnt/ai /mnt/data 2>/dev/null", shell=True, timeout=5).decode()
        await _reply_in_topic(update, f"<b>📊 资源概览</b>\n\n<pre>CPU:\n{cpu}\nMEM:\n{mem}\nDISK:\n{disk}</pre>")


async def cmd_diag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update, context) and not _is_in_forum(update):
        return
    await update.message.chat.send_action("typing")

    import subprocess
    results = []

    # systemd 失败服务
    p = subprocess.run(
        ["systemctl", "--user", "list-units", "--type=service", "--state=failed", "--no-legend"],
        capture_output=True, text=True, timeout=10
    )
    failed = p.stdout.strip()
    results.append(f"<b>🩺 系统诊断</b>\n")
    results.append(f"❌ 失败服务: {'无' if not failed else len(failed.split(chr(10))) - 1}个" if failed else "❌ 失败服务: 0")

    # Docker 容器
    p = subprocess.run(
        "docker ps -a --format '{{.Names}} {{.Status}}'", shell=True, capture_output=True, text=True, timeout=10
    )
    unhealthy = [l for l in p.stdout.split("\n") if "unhealthy" in l.lower() or "exited" in l.lower()]
    results.append(f"🐳 异常容器: {'无' if not unhealthy else len(unhealthy)}个")

    # 端口检查
    ports = {3000: "控制台", 4000: "LiteLLM", 9801: "Hub-API", 9875: "Launcher", 8283: "Letta"}
    for port, name in ports.items():
        try:
            import socket
            s = socket.socket()
            s.settimeout(2)
            s.connect(("127.0.0.1", port))
            s.close()
        except Exception:
            results.append(f"🔌 {name}({port}): ❌ 不可达")

    await _reply_in_topic(update, "\n".join(results[:10]))


async def cmd_heal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update, context) and not _is_in_forum(update):
        return
    await update.message.chat.send_action("typing")

    if _PILOT_LOADED:
        results = await scan_and_heal()
        report = format_heal_results(results)
        await _reply_in_topic(update, report)
    else:
        await _reply_in_topic(update, "⚠️ 自愈引擎未加载")


async def cmd_exec_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """执行原始命令（需授权）"""
    if not _check_auth(update, context):
        await _reply_in_topic(update, "⛔ 需私聊授权")
        return
    cmd = " ".join(context.args) if context.args else ""
    if not cmd:
        await _reply_in_topic(update, "用法: /exec &lt;命令&gt;")
        return

    dangerous = ["reboot", "shutdown", "rm -rf", "nixos-rebuild", "format", "dd if=", "mkfs"]
    if any(d in cmd.lower() for d in dangerous):
        await _reply_in_topic(update, f"⛔ 危险命令已拦截: {cmd}")
        return

    await update.message.chat.send_action("typing")
    if _PILOT_LOADED:
        result = await execute_command("exec", cmd)
        await _reply_in_topic(update, format_command_result(result))
    else:
        import subprocess
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (p.stdout or p.stderr)[:1500]
        await _reply_in_topic(update, f"<pre>{out}</pre>")


# ── 内联按钮回调处理器 (L3: 通知操作按钮 + /cmd 命令按钮) ──────────

async def handle_pilot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理通知中的操作按钮和 /cmd 命令按键"""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("pilot:"):
        return

    action_code = data[6:]  # 去掉 "pilot:" 前缀
    user_text = f"执行: {action_code}"

    await query.message.reply_text(f"⚙️ 执行中...")

    if _PILOT_LOADED:
        if action_code == "diag":
            import subprocess
            p = subprocess.run(
                ["systemctl", "--user", "list-units", "--type=service", "--state=failed", "--no-legend"],
                capture_output=True, text=True, timeout=10
            )
            failed = p.stdout.strip()
            await query.message.reply_text(
                f"🩺 快速诊断:\n❌ 失败服务: {'无' if not failed else len(failed.split(chr(10)))}个"
            )
        elif action_code == "top":
            result = await execute_command("top", "")
            await query.message.reply_text(format_command_result(result))
        elif action_code == "ignore":
            await query.message.reply_text("✅ 已忽略")
        elif action_code.startswith("restart:"):
            svc = action_code[8:]
            result = await execute_command("restart", svc)
            await query.message.reply_text(format_command_result(result))
        elif action_code.startswith("logs:"):
            svc = action_code[5:]
            result = await execute_command("logs", svc)
            await query.message.reply_text(format_command_result(result))
        elif action_code.startswith("check:"):
            svc = action_code[6:]
            result = await execute_command("check", svc)
            await query.message.reply_text(format_command_result(result))
        else:
            await query.message.reply_text(f"未知操作: {action_code}")
    else:
        await query.message.reply_text("⚠️ 运维引擎未加载")


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

    app = Application.builder().token(BOT_TOKEN).build()

    # 注册命令处理器
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("tasks", cmd_tasks))
    app.add_handler(CommandHandler("help", cmd_help))
    
    # L2 运维命令
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("diag", cmd_diag))
    app.add_handler(CommandHandler("heal", cmd_heal))
    app.add_handler(CommandHandler("exec", cmd_exec_cmd))
    
    # 获取群组 chat_id（在群里发 /gid）
    async def cmd_gid(update: Update, context: ContextTypes.DEFAULT_TYPE):
        cid = update.effective_chat.id
        ctype = update.effective_chat.type
        title = update.effective_chat.title or ''
        await update.message.reply_text(f"chat_id={cid}\ntype={ctype}\ntitle={title}")
        # 同时更新 gmail-bridge 环境变量
        env_file = Path.home() / ".local/state/gmail-bridge/gmail.env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        old = env_file.read_text() if env_file.exists() else "TG_CHAT_ID=5036541266\n"
        new = ""
        for line in old.split("\n"):
            if line.startswith("GMAIL_TG_CHAT="):
                new += f"GMAIL_TG_CHAT={cid}\n"
            elif line.startswith("# GMAIL_TG_CHAT="):
                new += f"GMAIL_TG_CHAT={cid}\n"
            else:
                new += line + "\n"
        if "GMAIL_TG_CHAT=" not in new:
            new += f"GMAIL_TG_CHAT={cid}\n"
        env_file.write_text(new.strip() + "\n")
        # 重启 watch timer 使新环境变量生效
        import subprocess
        subprocess.run(["systemctl", "--user", "restart", "gmail-watch.timer"], timeout=5)
    app.add_handler(CommandHandler("gid", cmd_gid))

    # 注册图片处理器（photo + document 图片，优先于文字 handler）
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_image))

    # 注册 Gmail 回复命令（优先于对话 handler）
    async def handle_gmail_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
        import subprocess, re
        text = update.message.text.strip()
        m = re.match(r'回\s*#(\S+)\s+(.+)', text)
        if not m:
            return  # 不是回复命令，继续传递
        uid = m.group(1)
        reply_text = m.group(2).strip()
        use_uid = not uid.isdigit() or len(uid) > 10
        args = ["reply-uid", uid, reply_text] if use_uid else ["reply", uid, reply_text]
        result = subprocess.run(
            ["python3", "/mnt/ai/apps/gmail-bridge/gmail-bridge.py"] + args,
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            await update.message.reply_text(f"✅ 已回复 #{uid}")
        else:
            await update.message.reply_text(f"❌ 回复失败: {result.stderr[:200]}")

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gmail_reply), group=0)

    # 注册财务中心处理器（群消息→finance API）
    async def handle_finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        import urllib.request
        if not update.effective_chat or update.effective_chat.id != FINANCE_GROUP_ID:
            return  # 不是财务群，继续传递
        text = update.message.text.strip()
        tid = update.message.message_thread_id if hasattr(update.message, 'message_thread_id') else 0

        # 简单意图路由
        if any(kw in text for kw in ["查卡","卡","银行卡","卡片"]):
            try:
                resp = urllib.request.urlopen("http://localhost:9811/cards", timeout=5).read()
                cards = json.loads(resp)
                if not cards:
                    await update.message.reply_text("📭 暂无银行卡", message_thread_id=tid)
                else:
                    lines = ["*💳 我的银行卡*\n"]
                    for c in cards:
                        t = "信用卡" if c.get("card_type") == "credit" else "储蓄卡"
                        lines.append(f"• {c['bank_name']} *{c['card_last4']}* ({t})")
                        if c.get("billing_date"):
                            lines.append(f"  账单日:{c['billing_date']}日 还款日:{c['due_date']}日")
                    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", message_thread_id=tid)
            except Exception as e:
                await update.message.reply_text(f"❌ 查询失败: {e}", message_thread_id=tid)

        elif any(kw in text for kw in ["还款","账单","到期"]):
            try:
                resp = urllib.request.urlopen("http://localhost:9811/reminders", timeout=5).read()
                reminders = json.loads(resp)
                if not reminders:
                    await update.message.reply_text("✅ 近7天无到期还款", message_thread_id=tid)
                else:
                    lines = ["*🔔 还款提醒*\n"]
                    for r in reminders:
                        d = r.get("days_until", 0)
                        icon = "🔴" if d <= 3 else ("🟡" if d <= 7 else "🟢")
                        await update.message.reply_text(
                            f"{icon} {r['bank_name']} *{r['card_last4']}* — {r.get('next_due','?')} ({d}天)",
                            parse_mode="Markdown", message_thread_id=tid
                        )
            except Exception as e:
                await update.message.reply_text(f"❌ 查询失败: {e}", message_thread_id=tid)

        elif any(kw in text for kw in ["帮助","help"]):
            await update.message.reply_text(
                "*🏦 财务助手*\n• `查卡` — 查看银行卡\n• `还款` — 查看还款提醒\n• `记账 银行 金额 商户` — 记录消费\n• `帮助` — 本消息",
                parse_mode="Markdown", message_thread_id=tid
            )

        elif text.startswith("记账"):
            await update.message.reply_text("💡 格式：`银行名 金额 商户`\n如：`浦发 6400 刷卡机`", parse_mode="Markdown", message_thread_id=tid)

        else:
            # 尝试自动记账解析
            parts = text.split(None, 2)
            if len(parts) >= 2 and parts[1].replace("¥","").replace(",","").replace("元","").replace(".","").isdigit():
                await update.message.reply_text("💡 记账格式：`银行名 金额 商户`\n如：`浦发 6400 刷卡机`", parse_mode="Markdown", message_thread_id=tid)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_finance), group=0)
    
    # 注册普通消息处理器（对话，group=1 确保回复命令先匹配）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message), group=1)

    # 注册 Gmail inline 键盘回调处理器（group=0，pilot回调优先）
    async def handle_gmail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        import subprocess
        query = update.callback_query
        await query.answer()
        data = query.data
        if not data or not data.startswith("mail:"):
            return
        
        parts = data.split(":", 2)
        if len(parts) < 3:
            return
        
        action = parts[1]
        uid = parts[2]
        
        if action == "reply":
            await query.message.reply_text(
                f"请输入回复内容:\n<code>回 #{uid} 你的回复</code>",
                parse_mode="HTML"
            )
        elif action == "read":
            subprocess.run(["python3", "/mnt/ai/apps/gmail-bridge/gmail-bridge.py", "mark-read", uid], timeout=10)
            await query.answer("✓ 已标记已读")
        elif action == "attach":
            subprocess.run(["python3", "/mnt/ai/apps/gmail-bridge/gmail-bridge.py", "attachments", uid], timeout=30)
            await query.answer("📎 附件处理完成")
        elif action == "forward":
            await query.message.reply_text(
                f"请输入转发目标:\n<code>转发 #{uid} 目标@email.com</code>",
                parse_mode="HTML"
            )
        elif action == "block":
            result = subprocess.run(["python3", "/mnt/ai/apps/gmail-bridge/gmail-bridge.py", "block", uid], capture_output=True, text=True, timeout=10)
            await query.answer("🚫 已拉黑" if result.returncode == 0 else f"失败: {result.stderr[:50]}")
        elif action == "unsub":
            result = subprocess.run(["python3", "/mnt/ai/apps/gmail-bridge/gmail-bridge.py", "unsub", uid], capture_output=True, text=True, timeout=30)
            await query.answer("✕ 退订处理中" if result.returncode == 0 else f"失败: {result.stderr[:50]}")
    
    app.add_handler(CallbackQueryHandler(handle_pilot_callback, pattern=r"^pilot:"))
    app.add_handler(CallbackQueryHandler(handle_gmail_callback))

    # 全局 update 日志（排查群消息）
    async def log_all_updates(update, context):
        logging.info("[UPDATE] %s", update.to_dict())
    app.add_handler(MessageHandler(filters.ALL, log_all_updates), group=99)

    # 启动 polling
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
