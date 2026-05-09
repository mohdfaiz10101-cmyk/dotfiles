---
name: browser-sense-engine
description: "浏览器CDP感知引擎：行为学习+智能内容提取+Letta记忆+浏览画像"
user-invocable: false
version: "1.0.0"
category: agi
tags: [browser, cdp, letta, cerebras, behavior-learning]
effort: medium
auto-generated: true
created: 2026-04-18
---

# Browser Sense Engine

## 场景
## 场景
Floorp/Chrome CDP接入，自动学习用户浏览行为，智能提取有价值内容。

## 核心文件
- ~/agi/browser_sense.py — 主引擎
- ~/agi/browser_memory.db — SQLite行为数据库

## 权重评分系统
停留>30s=+3, 滚动=+2, 高价值域名=+2, 重复访问≥3/天=+3, 收藏=+5
总分≥5 → 提取内容 → Cerebras摘要 → Letta归档

## 启动方式
1. 浏览器需 --remote-debugging-port=9222
2. python3 ~/agi/browser_sense.py（后台守护）
3. --test 测试CDP连接, --profile 查看浏览画像

## 踩坑
- Floorp/Firefox CDP需启动参数，不能热开启
- BrowserOS AppImage 有NixOS兼容性问题，不推荐
- 摘要模型用cerebras-llama-8b（极速免费）

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
