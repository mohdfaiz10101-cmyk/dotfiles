---
name: ai-cluster-architecture
description: AI 三套系统架构详情（CC/Aider/Paperclip）+ 服务端口 + Letta 记忆体系
type: reference
---

## AI 工具链全景（2026-04-06 更新，三套系统并存）

### 系统 A — Claude Code 智能路由（实时交互）

**入口**：`cc`（= `claude --model sonnet --plugin-dir ~/claude-router-plugin`）
**场景**：即时编码、调试、探索、配置修改

```
用户 prompt → classify-prompt.py（$0）
  ↓
┌─ standard(60-70%) → Sonnet 直接处理（$3/M）
├─ fast(20%)        → Task(model:"haiku")（$0.01/M）
├─ deep(10%)        → Task(model:"opus")（$15/M）
├─ deepseek         → curl LiteLLM silicon/deepseek-v3.2（$0.27/M）
└─ glm              → Bash: glm "<prompt>"（免费）
```

**别名**：`cc`=智能路由 / `cco`=直接Opus / `cg`=GLM
**关键文件**：`~/CLAUDE.md` / `~/claude-router-plugin/` / `~/.local/bin/claude-with-router`

### 系统 B — Aider + LiteLLM（Git-aware 代码编辑）

**入口**：Hub → `/agent/aider/` 或 `aider` CLI
**配置**：`~/.aider.conf.yml` / LiteLLM: `/mnt/ai/ai-cluster/litellm/config.yaml`
**模型**：glm-smart 主模型 → 降级链 glm-4-flash → glm-4 → groq-llama-70b → 本地 qwen3-8b
**预算上限**：$10/月（LiteLLM 全局）

### 系统 C — Paperclip（异步 Agent 调度）

**入口**：Hub → `http://localhost:3100` Web UI
**代码**：`/mnt/ai/ai-cluster/paperclip/` / **数据**：`/mnt/pool/offload/paperclip/`
**Dispatcher**：`~/.local/bin/paperclip-dispatcher`（每15分钟扫描）
**Agent 分配**：GLM Coder(免费) / DeepSeek Coder / GLM Long Context(1M) / Sonnet / Opus

### 三套系统关系
- A 做即时交互，B 做批量代码修改，C 做异步项目管理
- B 和 C 共享 LiteLLM，A 独立走 Anthropic API

## 服务端口清单

| 服务 | 端口 | 说明 |
|------|------|------|
| Charlie Hub (Caddy) | 9800 | 总控 UI + 反向代理 |
| Charlie Hub API | 9801 | FastAPI 后端 |
| ttyd-claude/gemini/opencode/aider | 7690-7693 | AI 终端 |
| HyperChat CRM | 9098 | WeChat + CRM + Hermetic Ledger |
| Paperclip | 3100 | 任务管理 |
| LiteLLM | 4000 | 模型路由代理（43端点） |
| Letta API/Proxy/MCP | 8283/8284/8788 | 记忆系统 |
| ChromaDB | 8000 | 向量数据库 |
| Ollama | 11434 | 本地模型 |
| LangChain Hub | 8899 | 知识检索 |
| Whisper | 8178 | 语音识别 |

## Letta 记忆体系

**容器**：letta + letta-proxy + letta-db（Docker）
**Agents**：code-assistant / nixos-sysadmin / plain-speech
**MCP 工具**：letta_recall / letta_search / letta_store / letta_update_core / letta_ask / letta_agents
**Systemd**：letta-mcp.service + 5 个 timers
**炼化**：letta-distill.timer 每日 03:00

## Paperclip Agent 升级（2026-04-06）

- GLM Long Context agent: cloud/glm-4-long (1M 上下文)
- DeepSeek Coder: silicon/deepseek-v3.2 via LiteLLM
- 配置通过嵌入式 PostgreSQL (端口 54329)

## HyperChat / Hermetic Ledger

- Hermetic Ledger：CustomerHeartbeat + 页面生成器 + Marketing
- API：`/api/ledger/heartbeat/*`, `/api/ledger/page/*`, `/api/ledger/marketing/*`
- 数据源：`wechat_clean.db`（SQLite WAL），CRM `crm.db`
- 静态导出：`generate_static.py --ledger` → Vercel
