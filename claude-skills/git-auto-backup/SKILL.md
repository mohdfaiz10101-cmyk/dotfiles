---
name: git-auto-backup
description: "多仓库自动git备份：定时commit+push，systemd timer + OpenCode agent双兜底"
user-invocable: false
version: "1.0.0"
category: devops
tags: [git, backup, systemd, automation]
effort: medium
auto-generated: true
created: 2026-04-18
---

# Git Auto Backup

## 场景
## 场景
多个 git 仓库需要定期自动备份到 GitHub，不想手动操作。

## 实现
- 脚本: ~/.local/bin/git-backup.sh（backup_repo函数，检查变更→commit→push）
- Timer: git-backup.timer（每日 03:00）
- OP Agent: ~/.config/opencode/agents/git-backup.md（OpenCode定期job）

## 仓库配置（~/dotfiles/opencode/git-backup-daily.json）
dotfiles→op分支 / claude-router-plugin→main / skills→main

## 踩坑
- remote 指向别人仓库：git remote -v 确认，set-url 修正
- skills 初始无 git：git init → git add -A → git commit → 再 remote add
- push 前确认 branch 名（main vs master vs op）：git branch 查看

## 验证
bash ~/.local/bin/git-backup.sh && cat /tmp/git-backup-$(date +%Y%m%d).log

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
