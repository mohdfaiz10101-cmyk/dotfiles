#!/usr/bin/env bash
# AI 配置同步 ← GitHub（2026-05-12）
# 触发：GitHub Webhook / systemd timer 15min

set -e

SYNC_DIR="$HOME/ai-config-sync"
LOG_FILE="$HOME/.local/log/ai-config-sync.log"
CONFLICT_DIR="$HOME/ai-config-sync/conflicts"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

cd "$SYNC_DIR"

# 拉取
if git pull origin main 2>&1 | tee -a "$LOG_FILE"; then
    log "pull ok"
else
    # 冲突处理
    if git status | grep -q "both modified"; then
        log "CONFLICT detected, backing up"
        mkdir -p "$CONFLICT_DIR"
        git diff > "$CONFLICT_DIR/conflict-$(date '+%Y%m%d-%H%M%S').patch"
        git checkout --theirs .
        git add -A
        git commit -m "conflict-resolve: auto-merge $(date '+%Y-%m-%d %H:%M')" || true
        # 通知 A2A
        echo "CONFLICT: $(date '+%Y-%m-%d %H:%M') — config sync conflict, auto-resolved with theirs" >> "$HOME/.claude/projects/-home-charlie/memory/conflict-log.md"
    fi
fi

# 推送 agents 到 OpenCode（只推送 agents 目录，不影响运行中的配置）
AGENTS_SRC="$SYNC_DIR/openclaw-config/agents"
AGENTS_DST="$HOME/.config/opencode/agents"
if [ -d "$AGENTS_SRC" ] && [ -d "$AGENTS_DST" ]; then
    rsync -av --ignore-existing "$AGENTS_SRC/" "$AGENTS_DST/" 2>/dev/null || true
    log "agents synced to local opencode"
fi

log "pull complete"
