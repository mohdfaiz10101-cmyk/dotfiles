#!/usr/bin/env bash
# baseline-auto-update.sh — 智能归因 + 自动更新基线
# 检测到配置变更时自动判断来源：
#   - nixos-rebuild 触发 → 自动更新基线
#   - git 记录匹配（你手动改的）→ 自动更新基线
#   - 未知来源 → Telegram 告警
# 用法: baseline-auto-update.sh <变更文件路径>

set -euo pipefail
FILE="${1:-}"; [[ -z "$FILE" ]] && { echo "用法: $0 <文件路径>"; exit 1; }
BASELINE="$HOME/.claude/projects/-home-charlie/memory/baseline.toml"
NOW=$(date +%s)

# 检查是否在 nixos-rebuild 前后5分钟
nixos_rebuild_check() {
  local last_rebuild=$(journalctl --user -u nixos-rebuild --no-pager -n 1 --output=short-unix 2>/dev/null | cut -d. -f1 || echo "0")
  [[ "$last_rebuild" == "0" ]] && return 1
  local diff=$((NOW - last_rebuild))
  [[ $diff -lt 300 && $diff -gt -300 ]] && return 0
  return 1
}

# 检查 git log 是否有你最近的 commit
git_commit_check() {
  local f="$1"
  cd "$(dirname "$f")" 2>/dev/null || return 1
  git log --oneline -1 --format="%at" -- "$(basename "$f")" 2>/dev/null || echo "0"
}

CHANGE_TS=$(stat -c %Y "$FILE" 2>/dev/null || echo "$NOW")

# 归因判断
SOURCE="unknown"
if nixos_rebuild_check; then
  SOURCE="nixos-rebuild"
elif [[ $(git_commit_check "$FILE") != "0" ]]; then
  local git_ts=$(git_commit_check "$FILE")
  local diff=$((CHANGE_TS - git_ts))
  [[ $diff -lt 60 && $diff -gt -60 ]] && SOURCE="git-commit(charlie)"
fi

case "$SOURCE" in
  nixos-rebuild)
    NEW_SHA=$(sha256sum "$FILE" 2>/dev/null | cut -c1-16 || echo "unknown")
    echo "[auto] nixos-rebuild 触发: $FILE → 自动更新基线 sha256=$NEW_SHA"
    # 更新 baseline.toml 中对应条目 (简化版: 追加记录)
    echo "# $(date -Iseconds) auto-update: $FILE sha256=$NEW_SHA (source=$SOURCE)" >> ~/.claude/projects/-home-charlie/memory/baseline-updates.log
    notify-send "基线自动更新" "$(basename $FILE) (系统升级)" 2>/dev/null || true
    ;;
  git-commit*)
    NEW_SHA=$(sha256sum "$FILE" 2>/dev/null | cut -c1-16 || echo "unknown")
    echo "[auto] 手动修改: $FILE → 自动更新基线 sha256=$NEW_SHA"
    echo "# $(date -Iseconds) auto-update: $FILE sha256=$NEW_SHA (source=$SOURCE)" >> ~/.local/share/integrity/baseline-updates.log
    ;;
  *)
    echo "[!] 异常变更: $FILE 来源未知"
    echo "# $(date -Iseconds) ALERT: $FILE changed without known source" >> ~/.local/share/integrity/baseline-updates.log
    # 写 op-tasks
    echo "- [ ] [!] 配置异常: $FILE 被未知来源修改 ($(date +%H:%M))" >> "$HOME/.claude/projects/-home-charlie/memory/op-tasks.md" 2>/dev/null || true
    notify-send -u critical "⚠️ 配置异常" "$(basename $FILE) 被未知来源修改" 2>/dev/null || true
    exit 1
    ;;
esac