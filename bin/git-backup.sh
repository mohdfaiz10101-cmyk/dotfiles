#!/usr/bin/env bash
# git-backup.sh — 全系统 Git 备份
# 覆盖所有 ~/ 下的 git 仓库，自动 commit + push
# 路径: ~/bin/git-backup.sh (git tracked by dotfiles)

set -euo pipefail
LOG="/tmp/git-backup-$(date +%Y%m%d).log"
DATE=$(date '+%Y-%m-%d %H:%M')
OK=0; FAIL=0; SKIP=0

log() { echo "$*" | tee -a "$LOG"; }

backup_repo() {
    local path="$1" desc="$2"
    local name=$(basename "$path")

    if [ ! -d "$path/.git" ]; then
        log "[SKIP] $desc — 非 git 仓库"; ((SKIP++)); return
    fi

    cd "$path" || { log "[FAIL] $desc — 无法进入目录"; ((FAIL++)); return; }

    local changes
    changes=$(git status --porcelain 2>/dev/null || true)
    if [ -z "$changes" ]; then
        log "[SKIP] $desc — 无变更"; ((SKIP++)); return
    fi

    local count=$(echo "$changes" | wc -l)
    git add -A 2>/dev/null
    git commit -m "${DATE} 自动备份（${count} 个文件变更）" 2>/dev/null || true

    # 获取当前分支
    local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

    if git push origin "$branch" 2>/dev/null; then
        log "[OK] $desc → $branch (${count}文件)"; ((OK++))
    else
        log "[FAIL] $desc → $branch push失败"; ((FAIL++))
    fi
}

log "=== Git 备份开始 $DATE ==="

# 核心配置
backup_repo ~/dotfiles                "dotfiles(核心配置)"
backup_repo /etc/nixos                "NixOS系统配置"

# 开发项目
backup_repo ~/agi                     "AGI Brain"
backup_repo ~/hub                     "Hub API"
backup_repo ~/launcher                "Launcher"
backup_repo ~/crewai-project          "CrewAI"
backup_repo ~/nixos-dev               "NixOS开发"
backup_repo ~/claude-router-plugin    "Claude路由插件"

# 文档/知识
backup_repo ~/Documents/Obsidian      "Obsidian笔记"
backup_repo ~/Desktop                 "桌面文件"
backup_repo ~/cline-workspace         "Cline工作区"
backup_repo ~/.openclaw/workspace     "OpenClaw工作区"

# 工具
backup_repo ~/ccm-cli                 "CCM CLI"
backup_repo ~/balance-trigger         "余额触发器"
backup_repo ~/docker/deepwiki-open    "DeepWiki Docker"
backup_repo ~/free-claude-api-pool    "Free Claude API"
backup_repo ~/pets/playground         "宠物项目"

log "=== 完成: OK=$OK SKIP=$SKIP FAIL=$FAIL ==="

# 复制到桌面
mkdir -p ~/Desktop/日志/操作记录/
cp "$LOG" ~/Desktop/日志/操作记录/git-backup-$(date +%Y%m%d).log 2>/dev/null || true