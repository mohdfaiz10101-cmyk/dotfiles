"""
discord_bot_enhanced.py — AGI Brain Discord Bot
Why: 让用户通过 Discord 与 AGI Brain 交互，支持频道消息和私聊
What: on_message 事件处理，支持 !agi 前缀命令 + 自然语言对话
Test: 发送 !agi status 验证收到状态摘要；发送 !agi guide 验证帮助信息
踩坑：help 命令与 discord.py 内置命令冲突，改名为 agiguide
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from conversation import chat

BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
STATUS_FILE = os.environ.get("STATUS_FILE", "/tmp/agi-brain-status.json")
OP_TASKS_FILE = os.environ.get(
    "OP_TASKS_FILE", "/home/charlie/.claude/projects/-home-charlie/memory/op-tasks.md"
)

# 前缀命令配置
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!agi ", intents=intents, proxy="http://127.0.0.1:7890"
)
# 移除内置 help 命令，防止与 agiguide 冲突
bot.remove_command("help")


@bot.event
async def on_ready() -> None:
    """Bot 就绪事件。

    Why: 确认 Bot 成功连接 Discord
    What: 打印就绪日志
    Test: 启动 Bot 验证终端输出就绪消息
    """
    print(
        f"[DISCORD] {bot.user} 已连接 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


@bot.command(name="status")
async def cmd_status(ctx: commands.Context) -> None:
    """显示系统状态（!agi status）。

    Why: 快速查看 AGI Brain 当前运行状态
    What: 读取状态文件，格式化后发送到 Discord
    Test: 输入 !agi status 验证收到包含摘要的消息
    """
    status_path = Path(STATUS_FILE)
    if not status_path.exists():
        await ctx.send("⚠️ AGI Brain 状态文件不存在，Brain 可能未运行")
        return
    try:
        status = json.loads(status_path.read_text())
        updated = status.get("updated_at", "未知")[:19].replace("T", " ")
        summary = status.get("summary", "无摘要")
        alerts = status.get("alerts", [])
        sense = status.get("sense", {})

        msg = (
            f"**📊 系统状态（{updated}）**\n"
            f"摘要：{summary}\n"
            f"CPU：{sense.get('cpu_usage', 'N/A')} | "
            f"内存：{sense.get('memory_usage', 'N/A')} | "
            f"AI盘：{sense.get('disk_ai', 'N/A')}"
        )
        if alerts:
            msg += "\n\n⚠️ **告警：**\n" + "\n".join(f"• {a}" for a in alerts)

        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"读取状态失败：{e}")


@bot.command(name="tasks")
async def cmd_tasks(ctx: commands.Context) -> None:
    """显示 OP 待执行任务（!agi tasks）。

    Why: 查看 AGI Brain 派发的任务队列
    What: 读取 op-tasks.md，过滤未完成任务发送
    Test: 输入 !agi tasks 验证收到任务列表或"暂无"提示
    """
    op_tasks_path = Path(OP_TASKS_FILE)
    if not op_tasks_path.exists():
        await ctx.send("📋 暂无 OP 任务（文件不存在）")
        return
    content = op_tasks_path.read_text(encoding="utf-8")
    pending = [line for line in content.splitlines() if "- [ ]" in line]
    if not pending:
        await ctx.send("✅ 暂无待执行的 OP 任务")
        return
    tasks_text = "\n".join(pending[-10:])
    await ctx.send(f"**📋 待执行任务（最近10条）：**\n```\n{tasks_text}\n```")


@bot.command(name="agiguide")
async def cmd_agiguide(ctx: commands.Context) -> None:
    """显示帮助（!agi agiguide）。

    Why: 提供功能说明，避免与 discord.py 内置 help 命令冲突（改名为 agiguide）
    What: 发送使用说明消息
    Test: 输入 !agi agiguide 验证收到功能列表
    """
    await ctx.send(
        "**🧠 AGI Brain Discord Bot**\n\n"
        "**前缀命令（!agi）：**\n"
        "  `!agi status` — 系统状态\n"
        "  `!agi tasks` — OP 待执行任务\n"
        "  `!agi agiguide` — 本帮助\n\n"
        "**自然语言（@Bot 后发消息）：**\n"
        "  询问系统状态、派发 OP 任务、日常对话"
    )


@bot.event
async def on_message(message: discord.Message) -> None:
    """处理所有消息事件，支持 @mention 触发对话。

    Why: 让用户通过 @AGI Brain 进行自然语言交互
    What: 过滤机器人自身消息 → 检查 @mention → 调用 conversation.chat()
    Test: @Bot 发送消息验证收到中文回复
    """
    # 忽略自身消息
    if message.author == bot.user:
        return

    # 处理前缀命令
    await bot.process_commands(message)

    # 检查是否 @mention 了 Bot
    if bot.user not in message.mentions:
        return

    # 提取消息内容（去除 @mention 部分）
    content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not content:
        await message.channel.send(
            "你好！有什么可以帮你的？（发送 `!agi agiguide` 查看功能）"
        )
        return

    session_id = f"discord_{message.author.id}"
    async with message.channel.typing():
        try:
            reply = await chat(content, session_id=session_id)
        except Exception as e:
            reply = f"处理消息时出错：{e}"

    # Discord 消息长度限制 2000 字符
    if len(reply) > 1900:
        reply = reply[:1900] + "...(已截断)"

    await message.channel.send(reply)


def main() -> None:
    """启动 Discord Bot。

    Why: 持续监听 Discord 消息，响应用户交互
    What: 调用 bot.run() 启动事件循环
    Test: 启动后在 Discord 发送 !agi status 验证收到回复
    """
    if not BOT_TOKEN:
        print("[DISCORD] 错误：DISCORD_BOT_TOKEN 未配置")
        return

    print(f"[DISCORD] Bot 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
