---
name: OpenCode 升级与记忆系统修复 2026-05-17
description: OP 1.4.0→1.15.3 升级 + P0/P1/P2 配置修复 + Letta/PostgreSQL 恢复 + hiai-opencode 安装
type: project
---

## OpenCode 升级
- 版本: 1.4.0 → 1.15.3（GitHub releases 直装，非 nix/npm）
- 二进制位置: /home/charlie/.npm-global/bin/opencode（144MB）
- 自动升级脚本已更新: ~/.local/bin/opencode-autoupgrade（改用 GitHub API + socks5 代理）

## 配置修复
- default_agent: sisyphus → bob（hiai-opencode 编排器接管路由）
- MCP: 7→3（保留 letta, ref, macg；移除 context7/memory 给 hiai-opencode 管理）
- Plugin: 移除已死的 oh-my-openagent/opencode-snip/pty/scheduler/vibeguard
- 新增: opencode-cost-guard, opencode-mem, @hiai-gg/hiai-opencode@latest
- Compaction: threshold=80000, keepRecentTurns=5, autoContinue=true
- Permission: +rm -r/nixos-rebuild/docker/NTFS 限制
- continue_loop_on_deny: false
- StepFun API Key 迁移到 {env:STEPFUN_API_KEY}

## Agent 分层优化
- L1 核心(3): sisyphus, service-nurse, ops-dispatcher
- L2 守护(6): cost-accountant, security-watchdog, proxy-guardian, memory-curator, discord-butler, git-backup
- L3 按需(3): tech-researcher, tech-architect, cc-autonomous
- 归档(9): finance, marketing-*, content-creator, charlie-ego, agi-mentor, planner, reviewer, doc-manager

## 模型分配
- 重型推理(glm-5.1): tech-architect, tech-researcher, cc-autonomous
- 常规运维(glm-5-turbo): 其余 9 个 agent
- sisyphus: glm-5-turbo (未变)

## 记忆系统恢复
- PostgreSQL 16 + pgvector 0.8.2: NixOS 原生安装（非 Docker）
- PGDATA: /mnt/ai/apps/postgresql/data
- systemd: postgresql.service (user) + letta.service (enabled)
- Letta 8283: UP, Letta MCP 8284: UP
- DB 表需手动 create_all（已执行）

## Ghosty 禁用
- opencode-sisyphus-guard.timer: DISABLED（关闭即退出）
- 不再自动续跑 OP session

## hiai-opencode
- 已安装，接管 agent 路由（Bob 编排器）
- 自带 Context7/MemPalace/Sequential-Thinking/grep_app MCP
- oh-my-agent 因网络问题未安装成功（后续重试）

**Why:** 跨 11 版本升级 + 记忆系统全面恢复 + agent 架构优化
**How to apply:** OP 启动时自动使用新配置；Letta 开机自启；waybar 记忆灯显示综合状态
