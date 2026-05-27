"""
ops_bot.py — 运维 Telegram Bot (@charlie_op_bot)
Why: 随时随地通过 Telegram 查看系统状态，无需 SSH
What: polling 模式，支持 CPU/内存/磁盘/Docker/日志 查询
Test: /check 验证返回 CPU% 和内存使用；/disk 验证返回关键分区
"""

import asyncio
import logging
import subprocess
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = "8942130653:AAHJ2q1yXHMmF1hFBrOAHm6xCNlp-cA0Ofc"
ALLOWED_CHATS = {-1003843208954, 5036541266}
PROXY = "http://127.0.0.1:7890"

ALLOWED_SERVICES = {
    "agi-brain", "rss-bot", "ops-bot", "finance-bot",
    "litellm", "letta", "freshrss", "telegram-bot",
    "caddy", "frpc",
}


def _check_auth(update: Update) -> bool:
    """验证授权聊天。
    Why: 运维命令只允许指定群/私聊调用
    What: 检查 chat id 白名单
    Test: 白名单 id 返回 True
    """
    cid = update.effective_chat.id if update.effective_chat else 0
    return cid in ALLOWED_CHATS


def _truncate(text: str, limit: int = 2000) -> str:
    """截断输出防止超出 Telegram 消息长度。
    Why: journalctl/docker 输出可能很长
    What: 超出 limit 时截断并附加提示
    Test: 传入 3000 字符字符串，返回长度 ≤ 2050
    """
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…(已截断)"


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """系统快速巡检：CPU/内存/磁盘/Docker 容器数。"""
    if not _check_auth(update):
        return
    try:
        cpu_out = subprocess.run(["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
        mem_out = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5).stdout.strip()
        docker_out = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=5)
        docker_count = len(docker_out.stdout.strip().splitlines()) if docker_out.returncode == 0 else -1
        df_out = subprocess.run(["df", "-h", "/", "/mnt/ai"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception as e:
        await update.message.reply_text(f"巡检失败: {e}")
        return

    lines = [
        f"🖥️ 系统状态 — {datetime.now().strftime('%H:%M:%S')}",
        f"CPU: {cpu_out}%",
        f"内存:\n{mem_out}",
        f"磁盘:\n{df_out}",
    ]
    if docker_count >= 0:
        lines.append(f"Docker 运行中: {docker_count} 个容器")
    await update.message.reply_text("\n".join(lines))


async def cmd_docker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """列出运行中的 Docker 容器。
    Why: 快速查看容器状态，无需 SSH
    What: docker ps --format 格式化输出
    Test: /docker 验证返回表格格式容器列表
    """
    if not _check_auth(update):
        return
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip() or "没有运行中的容器"
        await update.message.reply_text(f"🐳 Docker 容器：\n```\n{_truncate(output)}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"docker ps 失败: {e}")


async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """显示关键分区磁盘使用情况。
    Why: 快速排查磁盘满的问题
    What: df -h 过滤关键挂载点
    Test: /disk 验证包含 /mnt/ai 分区信息
    """
    if not _check_auth(update):
        return
    try:
        result = subprocess.run(
            ["df", "-h", "/", "/mnt/ai", "/mnt/data", "/mnt/pool"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout.strip()
        await update.message.reply_text(f"💾 磁盘使用：\n```\n{_truncate(output)}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"df 失败: {e}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """查看服务日志（白名单服务）。
    Why: 快速排查服务异常，无需 SSH
    What: journalctl --user -u <服务> -n 20，白名单保护
    Test: /logs agi-brain 验证返回最近20行日志
    """
    if not _check_auth(update):
        return
    service = context.args[0] if context.args else ""
    if not service:
        await update.message.reply_text(f"用法：/logs <服务名>\n可用服务：{', '.join(sorted(ALLOWED_SERVICES))}")
        return
    # 去掉 .service 后缀兼容两种写法
    service_name = service.replace(".service", "")
    if service_name not in ALLOWED_SERVICES:
        await update.message.reply_text(f"服务 '{service_name}' 不在白名单中")
        return
    try:
        result = subprocess.run(
            ["journalctl", "--user", "-u", service_name, "-n", "20", "--no-pager"],
            capture_output=True, text=True, timeout=10,
        )
        output = (result.stdout or result.stderr).strip() or "无日志输出"
        await update.message.reply_text(f"📋 {service_name} 日志：\n```\n{_truncate(output)}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"读取日志失败: {e}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_auth(update):
        return
    await update.message.reply_text(
        "🛠️ 运维 Bot 使用指南\n\n"
        "/check — CPU/内存/磁盘/Docker 汇总\n"
        "/docker — Docker 容器列表\n"
        "/disk — 磁盘使用详情\n"
        "/logs <服务> — 服务最近日志\n"
        "/help — 帮助"
    )


def main() -> None:
    print(f"[OPS-BOT] 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    req = HTTPXRequest(proxy=PROXY, read_timeout=20.0, connect_timeout=15.0, httpx_kwargs={"verify": False})
    app = Application.builder().token(BOT_TOKEN).request(req).build()
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("docker", cmd_docker))
    app.add_handler(CommandHandler("disk", cmd_disk))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("help", cmd_help))
    app.run_polling(allowed_updates=["message"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
