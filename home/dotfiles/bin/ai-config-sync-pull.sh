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
    # 冲突处理 — 永不自动覆盖，仅备份+通知
    if git status | grep -q "both modified"; then
        log "CONFLICT detected — 本地有手动修改，放弃自动合并"
        mkdir -p "$CONFLICT_DIR"
        git diff > "$CONFLICT_DIR/conflict-$(date '+%Y%m%d-%H%M%S').patch"
        git merge --abort 2>/dev/null || git checkout --ours . 2>/dev/null || true
        log "conflict aborted, local changes preserved"
        # 通知
        echo "CONFLICT: $(date '+%Y-%m-%d %H:%M') — 检测到冲突，保留本地修改未自动合并" >> "$HOME/.claude/projects/-home-charlie/memory/conflict-log.md"
        notify-send "⚠️ ai-config-sync 冲突" "检测到冲突，本地修改已保留，需人工审查" 2>/dev/null || true
    else
        log "pull failed (non-conflict), check manually"
    fi
fi

# agents 同步已禁用 — rsync --ignore-existing 会恢复已删除的 agent，改为手动管理
# AGENTS_SRC="$SYNC_DIR/openclaw-config/agents"
# AGENTS_DST="$HOME/.config/opencode/agents"

log "pull complete"
