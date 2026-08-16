# Capability Registry

> Generated automatically from live OpenCode config, systemd, rules, and CodeGraph.
> Updated: 2026-08-16T19:46:16

## MCP

| Name | Kind | Policy | Enabled | Agent | Transport | Entry |
|---|---|---|---:|---|---|---|
| `agent-comms` | general | on_demand | true | `sisyphus` | local | `python3` |
| `baidu-netdisk` | data | on_demand | false | `tech-researcher` | local | `python3` |
| `claude-knowledge` | general | on_demand | false | `sisyphus` | local | `/var/home/charlie/.nvm/versions/node/v22.22.3/bin/node` |
| `codegraph` | code-intelligence | core | true | `sisyphus` | local | `/var/home/charlie/.local/bin/codegraphcontext` |
| `codex-account-manager` | general | on_demand | true | `sisyphus` | local | `python3` |
| `context7` | research-ui | core | true | `tech-researcher` | remote | `https://mcp.context7.com/mcp` |
| `fetch` | research-ui | core | true | `tech-researcher` | local | `/var/home/charlie/.nvm/versions/node/v22.22.3/bin/mcp-fetch-server` |
| `firecrawl` | research-ui | on_demand | false | `tech-researcher` | local | `/var/home/charlie/.local/bin/mcp-firecrawl-wrapper.sh` |
| `ghidra` | general | on_demand | true | `sisyphus` | local | `/var/home/charlie/.local/bin/ghidra-mcp-bridge` |
| `grep_app` | general | on_demand | false | `sisyphus` | remote | `https://mcp.grep.app/mcp` |
| `haven` | device | on_demand | false | `ops-dispatcher` | local | `/var/home/charlie/.local/bin/haven-mcp-wrapper.sh` |
| `hermes` | general | on_demand | false | `sisyphus` | local | `/var/home/charlie/.local/bin/hermes` |
| `ios-connect` | device | on_demand | false | `ops-dispatcher` | local | `python3` |
| `khoj` | memory | on_demand | false | `sisyphus` | local | `/mnt/ai/oa-venv/bin/python3` |
| `letta` | memory | core | true | `sisyphus` | local | `/var/home/charlie/.local/bin/letta-mcp` |
| `memory-engine` | memory | core | true | `sisyphus` | local | `/usr/bin/python3` |
| `mobile-browser-bridge` | research-ui | on_demand | true | `tech-researcher` | local | `python3` |
| `ntfy` | messaging | on_demand | false | `ops-dispatcher` | local | `python3` |
| `phone-connect` | device | core | true | `ops-dispatcher` | local | `python3` |
| `playwright` | research-ui | on_demand | false | `tech-researcher` | local | `/var/home/charlie/.nvm/versions/node/v22.22.3/bin/playwright-mcp` |
| `server-memory` | memory | on_demand | false | `sisyphus` | local | `/var/home/charlie/.nvm/versions/node/v22.22.3/bin/node` |
| `sqlite` | data | on_demand | false | `tech-researcher` | local | `db-mcp` |
| `sys-info` | general | core | true | `sisyphus` | local | `python3` |
| `tablet` | device | on_demand | false | `ops-dispatcher` | local | `python3` |
| `vision` | research-ui | on_demand | false | `tech-researcher` | local | `/var/home/charlie/.local/bin/mcp-vision-wrapper.sh` |
| `wechat` | messaging | on_demand | false | `ops-dispatcher` | local | `/var/home/charlie/.local/bin/wechat-query-mcp` |
| `win` | device | core | true | `ops-dispatcher` | local | `python3` |

## Agents

| Agent | Model | Purpose |
|---|---|---|
| `arch` | `stepfun-plan/step-3.7-flash` | 架构师 — 系统设计、技术选型、方案评审 |
| `build` | `stepfun-plan/step-3.5-flash-2603` | 代码构建器 — 代码生成、功能实现、测试编写 |
| `chat` | `zai/glm-5-turbo` | 对话模式 — 日常问答、知识查询、翻译总结 |
| `compaction` | `stepfun-plan/step-3.5-flash-plan` |  |
| `explore` | `stepfun-plan/step-3.5-flash-2603` | 代码搜索员 — 定位文件、函数、实现模式 |
| `marketing-auditor` | `stepfun-plan/step-3.5-flash-2603` | 营销审计员 — 独立检查营销结论、证据与风险 |
| `marketing-coordinator` | `stepfun-plan/step-3.7-flash` | 营销协调器 — 统筹营销调研、内容与浏览器验证 |
| `ops-dispatcher` | `stepfun-plan/step-3.5-flash-2603` | 设备与外部操作调度器 — 手机、平板、Windows、消息与网盘 |
| `plan` | `stepfun-plan/step-3.5-flash-2603-plan` | 规划器 — 分析需求、生成可执行计划（Plan Mode） |
| `refactor` | `stepfun-plan/step-3.5-flash-2603` | 重构器 — 代码优化、架构改进、模式重构 |
| `router-auditor` | `stepfun-plan/step-router-v1` | Router 审计员 — 失败后第二意见、改道建议和 DeepSeek/Step 交叉判断 |
| `sisyphus` | `stepfun-plan/step-3.5-flash-2603` | Sisyphus — 主力编排 Agent，自动分解委派验证 |
| `tech-architect` | `stepfun-plan/step-3.7-flash` | 技术架构师 — 复杂跨组件设计与架构评审 |
| `tech-researcher` | `stepfun-plan/step-3.7-flash` | 技术研究员 — Web、文档、UI 和外部证据调查 |
| `telegram-operator` | `stepfun-plan/step-3.5-flash-2603` | Telegram 专用操作 Agent — 出站通知、群信息查询与经授权的消息操作 |

## CodeGraph repositories


## Adaptation issues

- [CODEGRAPH UNHEALTHY] no repositories discovered; warm up with `opencode-lifecycle.py codegraph-warmup`
- [MCP OVERLAP] `general` has 4 enabled servers: agent-comms, codex-account-manager, ghidra, sys-info
- [MCP POLICY] `agent-comms` is on-demand but enabled by default
- [MCP POLICY] `codex-account-manager` is on-demand but enabled by default
- [MCP POLICY] `ghidra` is on-demand but enabled by default
- [MCP POLICY] `mobile-browser-bridge` is on-demand but enabled by default
- [RULE BLOAT] `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/AGENTS.md` has 212 lines
