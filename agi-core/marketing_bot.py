"""
marketing_bot.py — 营销 AI Bot（复用主 bot token，仅在营销群响应）
Why: 为 Charlie 营销中心群提供 AI 文案生成、营销规划、市场分析能力
What: polling 模式，过滤营销群 chat_id，调用 LiteLLM 处理营销需求
Test: 在营销群发 /copy 测试文案生成；在其他群发消息验证不响应（chat_id 过滤）
踩坑：复用主 bot token 时需严格 chat_id 过滤，避免与主 bot 冲突；
      python-telegram-bot 22.x 用 ApplicationBuilder().token().build()
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("marketing_bot")

# ─── 配置 ───────────────────────────────────────────────
BOT_TOKEN = "8797063873:AAGvApEP9frmA74b6nmxODHshzo1TwJR5ks"
LITELLM_BASE = "http://localhost:4000/v1"
LITELLM_KEY = "sk-litellm-charlie-2026"
MODEL = "step-3.5-flash-2603"
PROXY_URL = "http://127.0.0.1:7890"

# 仅在营销群响应（由 create_new_groups.py 输出）
MARKETING_CHAT_ID = -1003941857965  # Charlie 营销中心

SYSTEM_PROMPT = """你是 Charlie 的专业营销 AI 助手，擅长：
- 撰写吸引人的营销文案（短视频脚本、广告词、朋友圈文案）
- 制定营销方案（竞品分析、用户画像、投放策略）
- 分析市场定位和差异化卖点
- 提供外贸业务的 B2B 营销建议

回答简洁专业，中文为主，适当使用数字和结构化格式。"""


# ─── LiteLLM 调用 ────────────────────────────────────────
async def call_litellm(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """调用 LiteLLM API 获取 AI 回答。

    Why: 统一通过本地 LiteLLM 代理访问大模型，避免直接暴露 API key
    What: POST /v1/chat/completions，返回模型文本回答
    Test: 传入 "写一句广告语"，断言返回非空字符串且长度 > 10
    """
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{LITELLM_BASE}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except httpx.TimeoutException:
        return "⏱ AI 响应超时，请稍后重试。"
    except httpx.HTTPStatusError as e:
        logger.error("LiteLLM HTTP 错误: %s", e)
        return f"❌ AI 服务错误: HTTP {e.response.status_code}"
    except Exception as e:
        logger.exception("LiteLLM 调用失败")
        return f"❌ AI 调用失败: {e}"


# ─── 权限检查 ─────────────────────────────────────────────
def is_marketing_chat(update: Update) -> bool:
    """检查消息是否来自营销群。

    Why: 复用主 bot token 时必须过滤 chat_id，防止干扰其他群的主 bot 逻辑
    What: 对比 update.effective_chat.id 与 MARKETING_CHAT_ID
    Test: 传入 chat_id=-1003941857965 的 mock update 应返回 True
    """
    if update.effective_chat is None:
        return False
    return update.effective_chat.id == MARKETING_CHAT_ID


# ─── 命令处理器 ──────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Why: 引导用户了解 bot 功能; What: 发送功能说明; Test: /start → 收到欢迎消息"""
    if not is_marketing_chat(update):
        return

    await update.message.reply_text(
        "🎯 *Charlie 营销 AI 助手* 已就位！\n\n"
        "**可用命令：**\n"
        "/copy `<需求>` — 生成营销文案\n"
        "/plan `<产品/服务>` — 制定营销方案\n"
        "/analyze `<内容>` — 分析市场定位\n\n"
        "或直接发送文字，我来当你的营销顾问 💡",
        parse_mode="Markdown",
    )


async def cmd_copy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/copy <需求> → 生成营销文案。

    Why: 快速生成文案是营销最高频需求
    What: 提取命令参数，构造文案生成 prompt，调用 LiteLLM 返回结果
    Test: /copy 推广新款蓝牙耳机 → 返回 3 条以上不同风格文案
    """
    if not is_marketing_chat(update):
        return

    if not context.args:
        await update.message.reply_text("用法：`/copy <营销需求>`\n示例：`/copy 推广夏季新款防晒霜`", parse_mode="Markdown")
        return

    requirement = " ".join(context.args)
    thinking_msg = await update.message.reply_text("✍️ 正在生成文案...")

    prompt = f"""请为以下需求生成3种不同风格的营销文案（每种20-50字）：

需求：{requirement}

格式：
**风格1（情感共鸣）：** [文案]
**风格2（功能卖点）：** [文案]
**风格3（场景代入）：** [文案]"""

    result = await call_litellm(prompt)
    await thinking_msg.edit_text(f"📝 **文案生成结果：**\n\n{result}", parse_mode="Markdown")


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/plan <产品> → 生成营销方案。

    Why: 结构化营销方案节省规划时间
    What: 调用 LiteLLM 输出目标用户/渠道/策略/KPI 四维方案
    Test: /plan B2B 工业零件外贸 → 返回包含渠道策略的完整方案
    """
    if not is_marketing_chat(update):
        return

    if not context.args:
        await update.message.reply_text("用法：`/plan <产品或服务>`\n示例：`/plan SaaS 项目管理工具`", parse_mode="Markdown")
        return

    product = " ".join(context.args)
    thinking_msg = await update.message.reply_text("📊 正在制定营销方案...")

    prompt = f"""为以下产品制定一份简洁营销方案：

产品/服务：{product}

请输出：
1. **目标用户画像**（3句话）
2. **核心卖点**（3-5个）
3. **推荐渠道**（带优先级）
4. **内容策略**（短期1个月行动）
5. **关键指标 KPI**（2-3个可量化目标）"""

    result = await call_litellm(prompt)
    await thinking_msg.edit_text(f"🗺 **营销方案：**\n\n{result}", parse_mode="Markdown")


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/analyze <内容> → 分析市场定位。

    Why: 帮助用户找到产品差异化定位和竞争优势
    What: 分析给定内容的用户痛点、竞品对比、定位建议
    Test: /analyze 国内某中小SaaS工具 → 返回 SWOT 或定位分析
    """
    if not is_marketing_chat(update):
        return

    if not context.args:
        await update.message.reply_text("用法：`/analyze <产品描述或市场信息>`", parse_mode="Markdown")
        return

    content = " ".join(context.args)
    thinking_msg = await update.message.reply_text("🔍 正在分析...")

    prompt = f"""分析以下内容的市场定位：

内容：{content}

请输出：
1. **目标市场细分**
2. **用户核心痛点**
3. **竞争优势/差异化**
4. **定位建议**（一句话品牌主张）
5. **风险提示**（1-2个需注意的点）"""

    result = await call_litellm(prompt)
    await thinking_msg.edit_text(f"📈 **市场分析：**\n\n{result}", parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """普通文字消息 → 作为营销咨询处理。

    Why: 降低使用门槛，自然语言直接咨询，无需记住命令
    What: 过滤 bot 命令后，将文本作为营销问题发送给 LiteLLM
    Test: 发送"如何提升短视频转化率" → 返回可操作建议
    """
    if not is_marketing_chat(update):
        return

    if update.message is None or update.message.text is None:
        return

    # 跳过命令消息（以 / 开头）
    if update.message.text.startswith("/"):
        return

    user_text = update.message.text.strip()
    if len(user_text) < 2:
        return

    thinking_msg = await update.message.reply_text("💭 思考中...")

    prompt = f"营销咨询：{user_text}\n\n请给出专业、简洁、可落地的建议。"
    result = await call_litellm(prompt)
    await thinking_msg.edit_text(result)


# ─── 错误处理 ─────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Why: 避免未捕获异常导致 bot 崩溃; What: 记录错误日志"""
    logger.error("Bot 错误: %s", context.error, exc_info=context.error)


# ─── 主入口 ──────────────────────────────────────────────
def main() -> None:
    """启动 marketing_bot polling。

    Why: polling 模式无需公网 webhook，适合内网部署
    What: 注册命令和消息处理器，启动 Telegram Bot polling
    Test: 运行后在营销群发 /start 验证欢迎消息
    """
    logger.info("营销 Bot 启动中，监听群: %d", MARKETING_CHAT_ID)

    # HTTPXRequest 走本地代理（避免直连 api.telegram.org 被墙）
    request = HTTPXRequest(
        proxy=PROXY_URL,
        connect_timeout=15.0,
        read_timeout=30.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    # 注册命令处理器
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("copy", cmd_copy))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("analyze", cmd_analyze))

    # 文字消息处理器（放在命令之后）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # 错误处理
    app.add_error_handler(error_handler)

    logger.info("[OK] marketing_bot 已就绪，开始 polling...")
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
