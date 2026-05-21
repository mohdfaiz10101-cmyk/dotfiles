# 基础设施参考（按需加载）

> 从 CLAUDE.md L1 拆出，减少每次会话注入的 token。
> 需要时通过 `macg_context_probe("基础设施")` 或直接读此文件获取。

## 模型路由决策表

| 任务类型 | 执行方式 |
|---------|---------|
| 简单问答、格式化 | `glm "<prompt>"` 或直接处理 |
| 中文对话、翻译 | `glm "<prompt>"` |
| Bug修复、功能实现 | 直接处理 |
| 代码生成（长上下文） | `glm` 或 LiteLLM `glm-4-flash` |
| 架构设计、方案对比 | `glm` 完整版 |

**外部模型**：GLM=`glm "<prompt>"` | DeepSeek=LiteLLM `localhost:4000` key `sk-litellm-charlie-2026` model `silicon/deepseek-v3.2`

**Deep 路由自动升级**：Router `Route: deep | Confidence: 80%+` 且当前为 Turbo → `glm` 委派
**失败升级链**：连续2次失败 → 传递原始任务+失败原因，格式 `[ESCALATION] 从X升级到Y`

## 基础设施清单

| 组件 | 地址/路径 |
|------|---------|
| AGI Brain | `~/agi/macg.py` + systemd |
| Letta 记忆 | `localhost:8283` |
| LiteLLM 网关 | `localhost:4000` |
| FastAPI Gateway | `localhost:9900` |
| Hub API | `localhost:9800` |
| OP 任务系统 | `op-tasks.md` + systemd timers |
| ChromaDB | `localhost:8000` |
| Paperclip | `localhost:3100` |
| mihomo 代理 | `localhost:7890` |
| 3000 控制台 | `localhost:3000` — Next.js dev模式（HMR） |
| memory/ | `~/.claude/projects/-home-charlie/memory/` |
| changelog | `memory/changelog.jsonl`（事件溯源） |
| L2/L3规则 | `memory/rules-secondary.md` |

## 系统状态 MCP (sys-info)

| 工具 | 用途 |
|------|------|
| `sys_info_service(name)` | 实时 systemctl 状态 |
| `sys_info_port(port)` | 端口占用查询 |
| `sys_info_disk()` | 各挂载点用量 |
| `sys_info_proxy()` | 代理链路状态 |

端口: `localhost:18094`