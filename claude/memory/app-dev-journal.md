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

## AGI Brain — 个人智能自主循环系统
- **日期**：2026-04-17
- **技术栈**：Python 3.13 / httpx / python-telegram-bot 22 / discord.py 2 / SQLite / LiteLLM
- **架构决策**：Sense→Think→Act 三环主循环，60s 间隔；LLM 用 glm-4.7（LiteLLM 网关）
- **踩坑记录**：
  - `cloud/glm-4-flash` 模型名不存在 → 改用 `glm-4.7`（LiteLLM 实际注册的名称）
  - brain.py 导入 dotenv 必须在其他模块前（环境变量加载顺序）
  - Python 3.13 venv 需要先 mkdir 父目录（~/agi 是软链接到 /mnt/ai/home-offload/agi）
  - home-offload 目录不存在需 sudo 创建
- **可复用 pattern**：`sense()` 用 subprocess 读 /proc，`_write_status()` 写 /tmp/，Bot 鉴权用 chat_id 白名单
- **部署方式**：用户空间，手动 python3 brain.py 启动，后续可封装 systemd service
- **文件路径**：`~/agi/`（软链接 → `/mnt/ai/home-offload/agi/`）

## macg (LangGraph Multi-Agent CLI) — CC+OP融合对话入口
- **日期**：2026-04-18
- **技术栈**：Python / LangGraph / langchain-anthropic / langchain-openai / SQLite checkpointer
- **架构决策**：Supervisor(GLM免费) 路由到 glm_agent 或 claude_agent，共享 MessagesState
- **踩坑**：langgraph.checkpoint.sqlite 需单独安装 langgraph-checkpoint-sqlite
- **可复用 pattern**：op_delegate 工具写入 op-tasks.md → OP 定时器捡起执行
- **文件**：~/agi/macg.py + ~/.local/bin/macg
- **部署**：~/agi/.venv 虚拟环境，pip install langgraph langgraph-checkpoint-sqlite langchain-anthropic langchain-openai

## [AGI Android APK] — CopilotKit 手机控制台
- **日期**：2026-04-18
- **技术栈**：Capacitor 6 + 原生 HTML/JS（无需 React Native）→ Android APK
- **架构决策**：复用已有 AGI Gateway (9900) SSE/REST，不新建后端；Capacitor 包装单页 HTML，避免 Next.js 完整编译
- **连接方式**：Tailscale IP → NixOS 主机 → port 9900
- **任务链**：APK-A0（环境）→ APK-A1（初始化）→ APK-A2（UI）→ APK-A3（构建）
- **输出**：~/Desktop/文档/agi-console-YYYYMMDD.apk
- **状态**：已写入 op-tasks.md，等待 OP 执行
