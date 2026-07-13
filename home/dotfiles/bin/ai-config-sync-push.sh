#!/usr/bin/env bash
# AI 配置同步 → GitHub（2026-05-12）
# 触发：op-tasks.md 变更 / OpenCode config 变更

set -e

SYNC_DIR="$HOME/ai-config-sync"
CONFIG_DIR="$HOME/.config/opencode"
LOG_FILE="$HOME/.local/log/ai-config-sync.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# 检查是否有变更
cd "$SYNC_DIR"
if git diff --quiet && git diff --cached --quiet; then
    log "no changes, skip"
    exit 0
fi

# 拉取最新（避免冲突）
git pull --rebase origin main 2>/dev/null || true

# 提交并推送
git add -A
git commit -m "sync: $(date '+%Y-%m-%d %H:%M') — opencode config / op-tasks update" || true
git push origin main 2>&1 | tee -a "$LOG_FILE"

log "sync complete"
