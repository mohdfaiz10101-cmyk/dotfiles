---
name: wechat-merge-plan
description: 微信聊天记录合并方案（Windows+Linux双端数据库合并）
type: project
---

**目标**：合并 Windows + Linux 两端微信数据库

**现状**：
- Linux 端：16 个加密 DB，密钥已提取（~/.cache/wechat-finance/keys.json）
- Windows 端：79 个加密 DB（/mnt/data/WeChat Files/），密钥未知
- 工具：~/.local/bin/wechat-finance（1003 行 Python）
- 旧方案：~/launcher.bak.1776340007/windows-wechat-sync/

**卡点**：Windows 端需运行 pywxdump 提取密钥。
**用户选择**：CLI + Web UI + PostgreSQL + 连接 OpenCode。
