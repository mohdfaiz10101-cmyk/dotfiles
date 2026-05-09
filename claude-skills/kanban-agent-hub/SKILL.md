---
name: kanban-agent-hub
description: "看板内嵌 CC⇄OP 三层 Agent 架构：任务对话/架构讨论/Orchestrator调度/终端接入"
user-invocable: false
version: "1.0.0"
category: ai
tags: [kanban, multi-agent, cc-op, orchestrator, litellm, deepseek]
effort: medium
auto-generated: true
created: 2026-04-17
---

# Kanban Agent Hub

## 场景
在 launcher-server.py 后端添加 /api/cc-op-speak (DeepSeek生成对话)、/api/cc-op-discuss (GLM-4.7架构讨论)、/api/orchestrate (综合决策+自动派发任务到CC/OP队列)、/api/cc-op-dialog|discuss-history|orchestrate-history GET端点。kanban.html 新增 Agent Hub 第5列（5个标签：👁监控/💬对话/🧠讨论/⚡调度/⌨终端），含ttyd内嵌iframe。踩坑：GLM-4.7是推理模型会'分析角色'而非直接输出，改用DeepSeek-V3.2+system_msg约束；LiteLLM中模型名是deepseek-v3.2无前缀；call_glm需system_msg+user_msg双参数。数据文件：cc-op-dialog.jsonl/cc-op-discuss.jsonl/cc-op-orchestrate.jsonl。Orchestrator自动提取决策中CC职责和OP职责写入各自任务队列。

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
