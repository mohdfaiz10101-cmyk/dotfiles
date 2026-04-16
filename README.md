# Charlie's Dotfiles

一键备份和恢复所有 NixOS 配置、脚本、skills、记忆。

## 快速开始

### 新机器恢复
```bash
curl -sSL https://raw.githubusercontent.com/charlie-nixos/dotfiles/main/restore.sh | bash
```

### 推送更新
```bash
~/dotfiles/push-to-cloud.sh
```

## 目录结构

```
dotfiles/
├── nixos/           → /etc/nixos/        (NixOS 系统配置)
├── claude/skills/   → ~/.claude/skills/  (87个 skills)
├── claude/memory/   → memory/            (记忆文件)
├── claude/CLAUDE.md → ~/CLAUDE.md        (核心规则)
├── bin/             → ~/bin/             (用户脚本)
├── launcher/        → ~/launcher/        (launcher 脚本)
├── systemd/         → ~/.config/systemd/user/ (用户服务)
├── opencode/        → ~/.config/opencode/     (OpenCode 配置)
├── push-to-cloud.sh  一键推送
├── restore.sh        一键恢复
└── link.sh           创建 symlink
```
