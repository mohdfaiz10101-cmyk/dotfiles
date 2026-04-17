---
name: app-dev-journal
description: App/软件开发经验日志 — 技术栈选型、架构决策、踩坑记录、可复用 pattern
type: project
---

# App/软件开发经验日志

<!-- 每次开发 App 或软件项目时自动记录，格式见 CLAUDE.md APP_DEV_JOURNAL 规则 -->

## Kanban Agent Hub — CC⇄OP 三层架构
- **日期**：2026-04-17
- **技术栈**：Python HTTP + GLM-4.7(默认) + DeepSeek-V3.2(对话生成) + ttyd iframes
- **架构决策**：
  - CC Agent（Claude Code）：战略层，任务分配
  - OP Agent（OpenCode timers）：运维层，巡检执行
  - Orchestrator：综合层，读取讨论 → 决策 → 自动分派任务到双方队列
- **关键文件**：`~/launcher/launcher-server.py` (后端), `~/launcher/kanban.html` (前端)
- **数据文件**：`memory/cc-op-dialog.jsonl`, `memory/cc-op-discuss.jsonl`, `memory/cc-op-orchestrate.jsonl`
- **踩坑记录**：
  - GLM-4.7 为推理模型，会"分析角色"而非直接输出 → 改用 DeepSeek-V3.2 做对话生成
  - DeepSeek 在 LiteLLM 中的 model_name 是 `deepseek-v3.2`（无前缀，非 silicon/xxx）
  - call_glm 需要 system_msg + user_msg 双参数才能约束输出格式
- **可复用 pattern**：completion-style prompt（提供前缀 "CC指令："）+ system message 强约束
