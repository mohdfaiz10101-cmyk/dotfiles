#!/usr/bin/env bash
# push-to-cloud.sh — 一键推送 dotfiles 到 GitHub
# 用法: ./push-to-cloud.sh "commit message"
set -euo pipefail

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
cd "$DOTFILES"

MSG="${1:-auto backup $(date '+%Y-%m-%d %H:%M')}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

echo "=== 同步本地变更到 dotfiles ==="

# 1. 从系统实际路径同步最新内容到 dotfiles（双向同步源头）
echo "[1/4] 同步 skills..."
rsync -a --delete --exclude='node_modules' ~/.claude/skills/ "$DOTFILES/claude/skills/"

echo "[2/4] 同步 memory..."
rsync -a --delete ~/.claude/projects/-home-charlie/memory/ "$DOTFILES/claude/memory/"

echo "[3/4] 同步脚本和服务..."
rsync -a --delete ~/bin/ "$DOTFILES/bin/"
rsync -a --delete ~/launcher/ "$DOTFILES/launcher/"
rsync -a --delete ~/.config/systemd/user/ "$DOTFILES/systemd/"

echo "[4/4] 同步配置文件..."
cp -f ~/CLAUDE.md "$DOTFILES/claude/CLAUDE.md"

# OpenCode 配置（排除重文件）
# 注意：opencode.json 和 AGENTS.md 是软链接指向 dotfiles，不能 rsync 回来（会创建循环链接）
# 只同步 oh-my-openagent.jsonc（不是软链接）
rsync -a --exclude='node_modules' --exclude='plugins' --exclude='.env' \
    ~/.config/opencode/oh-my-openagent.jsonc \
    "$DOTFILES/opencode/" 2>/dev/null || true

rsync -a --delete ~/.config/opencode/agents/ "$DOTFILES/opencode/agents/" 2>/dev/null || true

echo ""
echo "=== Git 推送 ==="

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    ok "无变更，跳过推送"
    exit 0
fi

git add -A
git commit -m "$MSG"
git push origin main 2>&1 || {
    fail "推送失败，检查网络或 SSH key"
    exit 1
}

ok "已推送到 GitHub: $MSG"

# 显示统计
echo ""
echo "=== 备份统计 ==="
echo "文件数: $(find "$DOTFILES" -not -path '*/\.git/*' -type f | wc -l)"
echo "总大小: $(du -sh "$DOTFILES" --exclude='.git' 2>/dev/null | cut -f1)"
