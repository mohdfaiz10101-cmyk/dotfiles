#!/usr/bin/env bash
# post-agent-gate.sh — Agent 完成后自动提取并写回学习
# 集成到 opencode post-agent hook
# 用法: post-agent-gate.sh <agent_name> <session_dir>
# 检测: git diff / changelog 增量 / 新增文件
# 自动提取关键决策写回 lessons-learned.md + Letta

set -euo pipefail
AGENT="${1:-unknown}"
MEMORY_DIR="$HOME/.claude/projects/-home-charlie/memory"
CHANGELOG="$MEMORY_DIR/changelog.jsonl"

# 1. 检测本 session 的文件变更
detect_changes() {
  # 检查最近5分钟 changelog 增量
  local now=$(date +%s)
  local cutoff=$((now - 600))
  tail -100 "$CHANGELOG" 2>/dev/null | while IFS= read -r line; do
    local ts=$(echo "$line" | jq -r '.ts // empty' 2>/dev/null)
    local epoch=$(date -d "$ts" +%s 2>/dev/null || echo "0")
    [[ "$epoch" -gt "$cutoff" ]] && echo "$line"
  done
}

# 2. 提取关键决策
extract_insights() {
  detect_changes | jq -r '
    select(.type != "file-change" or (.scope | test("agents|config|service|system")))
    | "\(.ts | fromdateiso8601? // .ts): \(.desc // .type)"
  ' 2>/dev/null | head -10
}

# 3. 写入 lessons-learned
INSIGHTS=$(extract_insights)
if [[ -n "$INSIGHTS" ]]; then
  {
    echo ""
    echo "# [$(date +%Y-%m-%dT%H:%M)] $AGENT session insights"
    echo "$INSIGHTS" | while IFS= read -r line; do
      [[ -n "$line" ]] && echo "- $line"
    done
  } >> "$MEMORY_DIR/lessons-learned.md"
fi

# 4. 写入 Letta (异步，不阻塞)
letta_store() {
  local text="$1"
  curl -s -X POST "http://localhost:8283/v1/agents/nixos-sysadmin/archival-memory" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"[$AGENT] $text\"}" 2>/dev/null > /dev/null || true
}

echo "[gate] post-agent: $AGENT — 检测到 $(echo "$INSIGHTS" | wc -l) 条洞察"

# 清理临时文件
rm -f /tmp/opencode-gate-*.tmp 2>/dev/null || true