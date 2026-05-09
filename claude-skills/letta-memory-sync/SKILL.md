---
name: letta-memory-sync
description: "memory/*.md → Letta archival 增量同步，hash去重，垃圾清洗，sleep-time开启"
user-invocable: false
version: "1.0.0"
category: memory
tags: [letta, memory, sync, distill, archival]
effort: medium
auto-generated: true
created: 2026-04-19
---

# Letta Memory Sync

## 场景
## 场景
memory/*.md 积累了大量知识但未同步到 Letta 向量库，导致 letta_search 无法召回。

## 步骤
1. 清洗垃圾: curl GET archival-memory → 分类 spam（会话dump/健康检查）→ DELETE
2. 批量注入: lessons-learned → nixos-sysadmin; codebase-map/app-dev-journal → code-assistant
3. 开启 sleep-time: PATCH /v1/agents/{id} {enable_sleeptime:true}
4. 创建增量同步脚本: ~/agi/letta-sync.py（hash去重，每条md→archival）
5. 创建每日 timer: letta-sync.timer OnCalendar=04:00

## 关键命令
python3 ~/agi/letta-sync.py  # 手动增量同步
systemctl --user status letta-sync.timer  # 检查定时器

## 踩坑
- Letta API 307 redirect: 需用 curl -sL 跟随
- agent ID 不稳定: 每次先 GET /v1/agents/ 获取真实ID
- glm-5-turbo 返回空 content: 改用 glm-5.1
- archival 只存原子知识点(200-500字符)，不存完整对话

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
