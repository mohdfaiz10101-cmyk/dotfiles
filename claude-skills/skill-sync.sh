#!/bin/bash
# Skill 自动同步脚本 — Git commit + Letta 索引
# 用途：自动提交 skills 变更到 Git，并将更新索引到 Letta MCP

set -e

SKILLS_DIR="$HOME/.claude/skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SKILLS_DIR}/.sync.log"
LETTA_INDEX_SCRIPT="${SCRIPT_DIR}/skill-to-letta.py"

# 初始化日志
{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===== Skill Sync Started ====="
} >> "$LOG_FILE"

cd "$SKILLS_DIR" || {
    echo "[ERROR] Cannot cd to $SKILLS_DIR" >&2
    exit 1
}

# ===== Step 1: Git Sync =====
echo "[INFO] Step 1: Syncing to Git..."

if [[ -n $(git status --porcelain) ]]; then
    git add -A
    commit_msg="chore(skills): auto-sync @ $(date '+%Y-%m-%d %H:%M:%S')"
    git commit -m "$commit_msg"
    echo "[OK] Skills committed to Git with message: $commit_msg"
    {
        echo "[OK] Git commit: $commit_msg"
    } >> "$LOG_FILE"
else
    echo "[SKIP] No changes to commit"
    {
        echo "[SKIP] No changes in git status"
    } >> "$LOG_FILE"
fi

# ===== Step 2: Letta Index =====
echo "[INFO] Step 2: Indexing to Letta..."

if [[ -f "$LETTA_INDEX_SCRIPT" ]]; then
    if python3 "$LETTA_INDEX_SCRIPT" >> "$LOG_FILE" 2>&1; then
        echo "[OK] Letta indexing completed"
    else
        echo "[WARN] Letta indexing encountered issues (see log)"
    fi
else
    echo "[WARN] skill-to-letta.py not found at $LETTA_INDEX_SCRIPT"
    {
        echo "[WARN] skill-to-letta.py not found - skipping Letta index"
    } >> "$LOG_FILE"
fi

# ===== Summary =====
{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===== Skill Sync Completed ====="
    echo ""
} >> "$LOG_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Skill Sync Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Git Status: $(git status --short | wc -l) changes"
echo "Total Skills: $(find "$SKILLS_DIR" -maxdepth 1 -type d | wc -l)"
echo "Log: $LOG_FILE"
echo ""
