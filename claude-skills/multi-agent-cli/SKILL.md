---
name: multi-agent-cli
description: "LangGraph Multi-Agent CLI：GLM免费默认+Claude按需升级，共享上下文持久化，op_delegate委托OP执行"
user-invocable: false
version: "1.0.0"
category: ai-tools
tags: [langgraph, multi-agent, glm, claude, cli]
effort: medium
auto-generated: true
created: 2026-04-18
---

# Multi Agent Cli

## 场景
## 场景\n双模型融合CLI，解决CC+OP上下文共享问题\n\n## 文件位置\n- ~/agi/macg.py — LangGraph版（完整）\n- ~/agi/mac.py — 简化版（手动路由）\n- ~/.local/bin/macg — 启动脚本\n\n## 架构\nSupervisor(GLM) → glm_agent(免费) 或 claude_agent(按需)\n共享MessagesState + SQLite持久化\n\n## 安装\ncd ~/agi && source .venv/bin/activate\npip install langgraph langchain-anthropic langchain-openai langgraph-checkpoint-sqlite\n\n## 工具列表\nbash / read_file / write_file / glob_files / grep_files\nop_delegate / memory_read / memory_write / web_search\n\n## 注意事项\n- GLM通过LiteLLM http://localhost:4000/v1\n- ANTHROPIC_API_KEY需设置\n- op_delegate写入~/.claude/projects/-home-charlie/memory/op-tasks.md

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
