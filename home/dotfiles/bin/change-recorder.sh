#!/usr/bin/env bash
# change-recorder.sh — 变更事件记录器
# 用法:
#   change-recorder.sh <事件类型> <描述> [影响范围] [详情]
#   事件类型: git-commit | file-change | service-change | agent-remove | config-change | task-done
#
# 也可作为 git post-commit hook 使用:
#   .git/hooks/post-commit → change-recorder.sh git-commit "自动记录" "$PWD"
#
# 格式 (JSONL):
# {"ts":"2026-05-19T01:30:00+08:00","type":"git-commit","desc":"xxx","scope":"xxx","detail":"xxx","session":""}

CHANGELOG="$HOME/.claude/projects/-home-charlie/memory/changelog.jsonl"

# 确保文件存在
mkdir -p "$(dirname "$CHANGELOG")"
touch "$CHANGELOG"

TYPE="${1:?用法: change-recorder.sh <type> <desc> [scope] [detail]}"
DESC="${2:?缺少描述}"
SCOPE="${3:-}"
DETAIL="${4:-}"

# 检测当前 session（OP/CC/手动）
SESSION=""
if [[ -n "$OPENCODE_SESSION_ID" ]]; then
    SESSION="opencode"
elif [[ -n "$CLAUDE_SESSION" ]]; then
    SESSION="claude"
fi

TS=$(date -Iseconds)

jq -nc --arg ts "$TS" --arg type "$TYPE" --arg desc "$DESC" --arg scope "$SCOPE" --arg detail "$DETAIL" --arg session "$SESSION" \
    '{ts:$ts, type:$type, desc:$desc, scope:$scope, detail:$detail, session:$session}' \
    >> "$CHANGELOG"

# 文件大小限制（10MB 轮转）
SIZE=$(stat -c%s "$CHANGELOG" 2>/dev/null || echo 0)
if (( SIZE > 10485760 )); then
    ARCHIVE="${CHANGELOG}.$(date +%Y%m).jsonl"
    mv "$CHANGELOG" "$ARCHIVE"
    touch "$CHANGELOG"
    echo "[$TS] changelog 轮转 → $ARCHIVE" >&2
fi
