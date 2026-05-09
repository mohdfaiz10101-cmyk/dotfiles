---
name: opencode-agent-alias-memory
description: "opencode agent 别名/术语 → 同步写入 Letta archival + memory/MEMORY.md，防止跨会话遗忘"
user-invocable: false
version: "1.0.0"
category: memory
tags: [opencode, sisyphus, memory, alias]
effort: medium
auto-generated: true
created: 2026-04-24
---

# Opencode Agent Alias Memory

## 场景
1. 用户提到 agent 别名时立即 letta_store 写入标签 opencode,agent-alias\n2. 同步更新 memory/MEMORY.md 的 OpenCode Agents 部分\n3. 触发条件：用户纠正术语/新agent/新别名出现\n4. 别名速查：sisy=sisyphus=OP运维执行Agent(glm-5.1)；atlas=大师编排；prometheus=规划器；hephaestus=深度执行\n5. 配置路径：~/.config/opencode/oh-my-openagent.jsonc + ~/.config/opencode/agents/

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
