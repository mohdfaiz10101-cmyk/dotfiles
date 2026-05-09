---
name: kanban-agent-review
description: CC/op 互评集成到看板 — git diff 分析 + LLM 评审 + 状态自动更新
user-invocable: false
version: "1.0.0"
category: workflow
tags: [kanban, review, cc-op, git, automation]
effort: medium
---
# Kanban Agent Review

## 场景
任务完成后需要 CC 评审 op 工作（或反之），并自动更新看板状态。

## 架构
- `POST /api/review` → `launcher-server.py:_run_review()`
- git diff main..<branch> → qwen3 分析 → verdict: pass/fail/warn
- pass+doing → 自动移 done；fail+doing → 退回 todo
- 结果写入 `memory/op-review-report.md`

## 路由规则
| diff 行数 | 模型 | 成本 |
|----------|------|------|
| ≤10行, 无配置 | 自动通过（$0） | 免费 |
| 其余 | local/qwen3-8b | 免费 |

## 触发
kanban.html 每张卡片的「📝 互评」按钮 → `reviewCard()`

## 注意
- git 分支需存在 main/op/cc
- op-review-report.md append-only，不要手动清空
