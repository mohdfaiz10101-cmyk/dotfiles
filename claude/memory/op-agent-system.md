---
name: op-agent-system
description: OpenCode Agent 巡查体系 + Skill→Agent 路由映射 + Letta Agents ID
type: reference
---

## Skill→Agent 智能路由映射（2026-04-16）

**nixos-sysadmin**（系统运维）：
`nixos-safety-check` `system-health-check` `proxy-diagnose` `security-audit` `docker-cleanup` `docker-network-troubleshooting` `timer-schedule-manager` `taskboard` `age-key-backup` `merge-sub`

**code-assistant**（代码开发）：
`api-design-principles` `architecture-patterns` `async-python-patterns` `python-testing-patterns` `typescript-advanced-types` `python-packaging` `git-advanced-workflows` `github-actions-templates` `k8s-manifest-generator` `gitops-workflow` `deployment-pipeline-design` `terraform-module-library` `tool-calling-patterns` `skill-create`

**PM/编排层**（主 agent 自用）：
`mpm*` `paperclip*` `memory-maintenance` `proactive-maintenance-planner` `claude-rules-audit`

## Letta Agents

- `agent-02380eae...` → code-assistant
- `agent-8651643c...` → nixos-sysadmin
- `agent-4cc72483...` → plain-speech

## OpenCode Agent 巡查体系（2026-04-16）

**6 个 agent 配置**（~/.config/opencode/agents/）：
- security-watchdog — SSH/端口/密钥安全（每30分钟）
- proxy-guardian — mihomo/xray 代理链路（每30分钟）
- service-nurse — Docker/LiteLLM/Letta/磁盘（每15分钟）
- discord-butler — Discord Bot 状态（每15分钟）
- cost-accountant — AI 成本日报（22:00）
- memory-curator — 记忆维护（03:00）

**已知问题**：OnCalendar 格式和 perl 路径需 sed 修复。
