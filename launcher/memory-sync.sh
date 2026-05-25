#!/bin/bash
# memory-sync.sh — Memory 增量优化：归档、去重、统计
set -euo pipefail

MEMORY_DIR="$HOME/.claude/projects/-home-charlie/memory"
ARCHIVE_DIR="$MEMORY_DIR/archive"
STATS_FILE="$HOME/.local/state/chronos/memory_stats.json"
DAYS_THRESHOLD=30

mkdir -p "$ARCHIVE_DIR"
mkdir -p "$(dirname "$STATS_FILE")"

# 1. 归档 lessons-learned.md 中超过 30 天的条目
if [ -f "$MEMORY_DIR/lessons-learned.md" ]; then
  CUTOFF=$(date -d "-${DAYS_THRESHOLD} days" '+%Y-%m-%d' 2>/dev/null || date -v-${DAYS_THRESHOLD}d '+%Y-%m-%d')
  ARCHIVE_FILE="$ARCHIVE_DIR/lessons-$(date '+%Y-%m').md"

  # 提取过期条目（日期格式 [YYYY-MM-DD]）
  if [ -s "$MEMORY_DIR/lessons-learned.md" ]; then
    awk -v cutoff="$CUTOFF" '
    BEGIN { old = "" }
    /^- \[[0-9]{4}-[0-9]{2}-[0-9]{2}\]/ {
      match($0, /\[([0-9]{4}-[0-9]{2}-[0-9]{2})\]/, arr)
      if (arr[1] < cutoff) { old = old $0 "\n"; next }
    }
    { print }
    END {
      if (old != "") {
        printf "%s", old >> "'"$ARCHIVE_FILE"'"
      }
    }
    ' "$MEMORY_DIR/lessons-learned.md" > "$MEMORY_DIR/lessons-learned.md.tmp" && \
    mv "$MEMORY_DIR/lessons-learned.md.tmp" "$MEMORY_DIR/lessons-learned.md"
  fi
fi

# 2. 检测重复条目（连续相同内容行）
for f in "$MEMORY_DIR"/*.md; do
  [ -f "$f" ] || continue
  uniq "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done

# 3. 更新统计信息
TOTAL_LINES=0
TOTAL_SIZE=0
FILE_COUNT=0
for f in "$MEMORY_DIR"/*.md; do
  [ -f "$f" ] || continue
  lines=$(wc -l < "$f")
  size=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
  TOTAL_LINES=$((TOTAL_LINES + lines))
  TOTAL_SIZE=$((TOTAL_SIZE + size))
  FILE_COUNT=$((FILE_COUNT + 1))
done

cat > "$STATS_FILE" <<EOF
{
  "total_files": $FILE_COUNT,
  "total_lines": $TOTAL_LINES,
  "total_bytes": $TOTAL_SIZE,
  "last_sync": "$(date -Iseconds)"
}
EOF

echo "[memory-sync] $FILE_COUNT files, $TOTAL_LINES lines, $((TOTAL_SIZE / 1024))KB"
