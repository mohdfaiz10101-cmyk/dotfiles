---
name: ai-rules-three-layer-sync
description: "AI三层规则同步：ai-shared-rules.md → CLAUDE.md + AGENTS.md + macg.py，inotify实时触发"
user-invocable: false
version: "1.0.0"
category: system
tags: [ai, sync, rules, macg, inotify]
effort: medium
auto-generated: true
created: 2026-04-18
---

# Ai Rules Three Layer Sync

## 场景
## 场景
用户在 ~/dotfiles/ai-shared-rules.md 修改共享规则后，需自动同步到三层：
1. CLAUDE.md（CC规则）2. AGENTS.md（OP规则）3. macg.py（AGI Brain运行时读取）

## 架构
- 单一事实源: ~/dotfiles/ai-shared-rules.md
- 同步脚本: ~/.local/bin/ai-rules-sync.sh
- 监听服务: ai-rules-sync.service（inotifywait close_write）
- macg.py 用 _load_shared_rules() 运行时读取，不做文件内容替换（避免 Python 语法破坏）

## 关键文件
- ~/dotfiles/ai-shared-rules.md — 编辑此文件触发同步
- ~/.local/bin/ai-rules-watch.sh — inotifywait 循环监听
- ~/.local/bin/ai-rules-sync.sh — 实际同步逻辑
- ~/.config/systemd/user/ai-rules-sync.service — systemd 守护

## 踩坑
- systemd ExecStart 不能用单引号包 bash -c，需独立脚本
- macg.py 内 INFRA_CONTEXT 在 build_graph() 函数内有缩进，regex 替换易破坏语法 → 改为运行时读文件
- inotifywait 路径必须用 /run/current-system/sw/bin/inotifywait（NixOS）

## 验证
systemctl --user is-active ai-rules-sync.service
touch ~/dotfiles/ai-shared-rules.md && sleep 3 && tail -3 /tmp/ai-rules-sync.log

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
