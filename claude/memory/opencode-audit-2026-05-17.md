---
name: OpenCode 配置审计 2026-05-17
description: OpenCode 全面评估结果：P0/P1/P2 问题 + 社区 Bug 匹配 + agent 设计方案
type: project
---

## 审计日期：2026-05-17

### P0 问题（立即修复）
1. **StepFun API Key 明文** — opencode.json:119，80字符裸 key
2. **wechat MCP 路径不存在** — `/mnt/ai/apps/wechat-agent/mcp-server/` 不存在
3. **macg MCP venv 不存在** — `/mnt/ai/home-offload/agi/.venv/` 不存在
4. **playwright MCP 未安装** — `mcp-server-playwright` 未安装

**3/7 MCP 启动必失败**，每次冷启动浪费时间等超时。

### P1 问题
5. bash permission 过松（`*` 全局 allow）
6. instructions 路径不一致（OpenCode 读 ~/Documents/memory/，CC 读 ~/.claude/projects/memory/）
7. model output limit 偏低（deepseek-v4-pro 应 16384，step-3.5-flash 应 16384）
8. lessons.md 61KB 过大，每次会话注入消耗大量 token

### P2 问题
9. `continue_loop_on_deny: true` — deny 后仍循环
10. plugin 列表不完整（cost-guard/mem/mystatus 已装未启用）
11. 21 个 agent 文件，多数实验性
12. stepfun provider 冗余（应统一走 LiteLLM）

### 社区 Bug 匹配（已命中/高危）
- **#11112** "Preparing write..." 死循环 — 可能是"按继续不执行"的根因
- **#21032** oh-my-openagent 版本兼容性断裂（1.3.14 失效）
- **#2940** tmux 下随机挂起 — 高概率命中（sisyphus 跑 tmux）
- **#6708** GLM 4.7 tool call 放进 thinking tag — 影响 small_model
- **#14** opencode-scheduler NixOS 不兼容 — 已命中
- **#16331** 权限 glob 匹配 bug

### 插件风险
- **opencode-pty**: NixOS 不兼容（硬编码路径）
- **opencode-scheduler**: NixOS 完全不工作（硬编码 perl）
- **opencode-vibeguard**: 社区报告不工作
- **oh-my-openagent**: 版本兼容性频繁断裂

### Config-Auditor Agent 方案
- 职责：MCP 路径检查、API Key 安全扫描、Instructions 一致性、Permission 覆盖度、Token 消耗趋势
- 频率：每周（OP Timer 触发）
- 前提：先修 P0 问题再启用

**Why:** 首次全面审计发现 4 个 P0 + 4 个 P1 问题，需要持续监控防止退化
**How to apply:** 修完 P0 后创建 config-auditor agent，接入 OP Timer 做周度自动审计
