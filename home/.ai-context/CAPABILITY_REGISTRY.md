# Capability Registry

> Generated automatically from live OpenCode config, systemd, rules, and CodeGraph.
> Updated: 2026-07-13T13:19:15

## MCP

| Name | Kind | Policy | Enabled | Agent | Transport | Entry |
|---|---|---|---:|---|---|---|
| `baidu-netdisk` | data | on_demand | false | `tech-researcher` | local | `` |
| `claude-knowledge` | general | on_demand | false | `sisyphus` | local | `` |
| `codegraph` | code-intelligence | core | true | `sisyphus` | local | `` |
| `context7` | research-ui | core | true | `tech-researcher` | http | `https://mcp.context7.com/mcp` |
| `fetch` | research-ui | core | true | `tech-researcher` | local | `` |
| `firecrawl` | research-ui | on_demand | false | `tech-researcher` | local | `` |
| `grep_app` | general | on_demand | false | `sisyphus` | http | `https://mcp.grep.app/mcp` |
| `haven` | device | on_demand | false | `ops-dispatcher` | local | `` |
| `hermes` | general | on_demand | false | `sisyphus` | local | `` |
| `ios-connect` | device | on_demand | false | `ops-dispatcher` | local | `` |
| `khoj` | memory | on_demand | false | `sisyphus` | local | `` |
| `letta` | memory | core | true | `sisyphus` | local | `` |
| `memory-engine` | memory | core | true | `sisyphus` | local | `` |
| `ntfy` | messaging | on_demand | false | `ops-dispatcher` | local | `` |
| `phone-connect` | device | core | true | `ops-dispatcher` | local | `` |
| `playwright` | research-ui | on_demand | false | `tech-researcher` | local | `` |
| `server-memory` | memory | on_demand | false | `sisyphus` | local | `` |
| `sqlite` | data | on_demand | false | `tech-researcher` | local | `` |
| `sys-info` | general | core | true | `sisyphus` | local | `` |
| `tablet` | device | on_demand | false | `ops-dispatcher` | local | `` |
| `vision` | research-ui | on_demand | false | `tech-researcher` | local | `` |
| `wechat` | messaging | on_demand | false | `ops-dispatcher` | local | `` |
| `win` | device | core | true | `ops-dispatcher` | local | `` |

## Agents

| Agent | Model | Purpose |
|---|---|---|
| `arch` | `openai-compatible/step-router-v1` | 架构师 — 系统设计、技术选型、方案评审 |
| `build` | `openai-compatible/step-3.5-flash-2603` | 代码构建器 — 代码生成、功能实现、测试编写 |
| `chat` | `zai/glm-5-turbo` | 对话模式 — 日常问答、知识查询、翻译总结 |
| `compaction` | `openai-compatible/step-3.5-flash-plan` |  |
| `explore` | `openai-compatible/step-3.5-flash-2603` | 代码搜索员 — 定位文件、函数、实现模式 |
| `marketing-auditor` | `openai-compatible/step-3.5-flash-2603` | 营销审计员 — 独立检查营销结论、证据与风险 |
| `marketing-coordinator` | `openai-compatible/step-router-v1` | 营销协调器 — 统筹营销调研、内容与浏览器验证 |
| `ops-dispatcher` | `openai-compatible/step-3.5-flash-2603` | 设备与外部操作调度器 — 手机、平板、Windows、消息与网盘 |
| `plan` | `openai-compatible/step-3.5-flash-2603-plan` | 规划器 — 分析需求、生成可执行计划（Plan Mode） |
| `refactor` | `openai-compatible/step-3.5-flash-2603` | 重构器 — 代码优化、架构改进、模式重构 |
| `router-auditor` | `openai-compatible/step-router-v1` | Router 审计员 — 失败后第二意见、改道建议和 DeepSeek/Step 交叉判断 |
| `sisyphus` | `openai-compatible/step-router-v1` | Sisyphus — 主力编排 Agent，自动分解委派验证 |
| `tech-architect` | `openai-compatible/step-router-v1` | 技术架构师 — 复杂跨组件设计与架构评审 |
| `tech-researcher` | `openai-compatible/step-router-v1` | 技术研究员 — Web、文档、UI 和外部证据调查 |
| `telegram-operator` | `openai-compatible/step-3.5-flash-2603` | Telegram 专用操作 Agent — 出站通知、群信息查询与经授权的消息操作 |

## CodeGraph repositories

- `charlie` → `/var/home/charlie`
- `workspace` → `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace`

## Adaptation issues

- [RULE BLOAT] `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/AGENTS.md` has 212 lines
