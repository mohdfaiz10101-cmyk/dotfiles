---
name: agi-brain-rebuild
description: "AGI Brain 重建：Sense→Think→Act主循环 + Telegram多模态Bot + doubao/vision集成"
user-invocable: false
version: "1.0.0"
category: 系统运维
tags: [agi, telegram, vision, doubao, multimodal, rebuild]
effort: medium
auto-generated: true
created: 2026-04-17
---

# Agi Brain Rebuild

## 场景
场景：~/agi/ 代码丢失需重建。架构：brain.py(主循环60s) + think.py(MEMORY.md注入) + conversation.py(SQLite对话历史) + proactive.py(30min主动推送) + telegram_bot_enhanced.py(polling+vision)。踩坑：(1)httpx timeout>=40s (2)Python3.13用asyncio.run()不用get_event_loop() (3)状态文件用/tmp/不用~/.cache/ (4)tg-command与agi-telegram-bot共用token冲突→stop旧的 (5)voxtype remote模式不是server (6)doubao/vision模型名：doubao-1-5-vision-pro-32k，api_base：https://ark.cn-beijing.volces.com/api/v3，env变量ARK_API_KEY。LiteLLM config位于/mnt/ai-cluster/litellm/litellm-config.yml，env在同目录.env。重建步骤：python3 -m venv .venv → pip install httpx python-telegram-bot python-dotenv → 写6个py文件 → systemctl enable agi-brain agi-telegram-bot。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
