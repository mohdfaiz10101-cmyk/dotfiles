---
name: op-auto-exec-no-confirm
description: "OP禁止询问确认，直接执行op-tasks.md中的[ ]任务并写回[x]结果"
user-invocable: false
version: "1.0.0"
category: workflow
tags: [op, auto-exec, tasks]
effort: medium
auto-generated: true
created: 2026-04-18
---

# Op Auto Exec No Confirm

## 场景
## 场景
OP（OpenCode）读取 op-tasks.md 时默认询问确认，需要改为直接执行。

## 核心配置
~/.config/opencode/agents/ops-dispatcher.md 死规则：
- 禁止输出'是否执行''需要确认'
- [ ] 任务直接执行，完成→[x] ✅ {时间} {摘要}，失败→[!]
- 连续执行不停顿

## 同步位置
- AGENTS.md 末尾 AUTO_EXEC 块
- CLAUDE.md AUTO_EXEC 规则
- ai-shared-rules.md OP自动执行规则段落

## 验证
cat ~/.config/opencode/agents/ops-dispatcher.md | grep '禁止询问确认'

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
