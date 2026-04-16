#!/usr/bin/env bash
# restore.sh — 新机器一键恢复 dotfiles
# 用法: curl -sSL <raw-url>/restore.sh | bash
#   或: ./restore.sh
set -euo pipefail

REPO_URL="https://github.com/charlie-nixos/dotfiles.git"
DOTFILES="$HOME/dotfiles"
BRANCH="${DOTFILES_BRANCH:-main}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

echo "╔══════════════════════════════════════╗"
echo "║  Charlie Dotfiles 一键恢复           ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Step 1: 检查依赖 ──
echo "--- Step 1: 检查依赖 ---"

check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "$1 已安装"
        return 0
    else
        fail "$1 未安装"
        return 1
    fi
}

MISSING=0
check_cmd git || MISSING=1
check_cmd rsync || MISSING=1

if [ "$MISSING" -eq 1 ]; then
    fail "缺少必要依赖，请先安装: git rsync"
    exit 1
fi

# ── Step 2: 克隆 dotfiles ──
echo ""
echo "--- Step 2: 克隆 dotfiles ---"

if [ -d "$DOTFILES/.git" ]; then
    ok "$DOTFILES 已存在，拉取最新..."
    cd "$DOTFILES"
    git pull origin "$BRANCH" 2>&1 || fail "拉取失败，继续使用本地版本"
else
    info "克隆 $REPO_URL ..."
    git clone -b "$BRANCH" "$REPO_URL" "$DOTFILES" 2>&1 || {
        fail "克隆失败。检查:"
        fail "  1. 仓库是否存在且为 private？"
        fail "  2. SSH key 是否已添加到 GitHub？"
        fail "  3. 网络/代理是否正常？"
        exit 1
    }
    ok "克隆完成"
fi

cd "$DOTFILES"

# ── Step 3: 创建 symlink ──
echo ""
echo "--- Step 3: 创建 symlink ---"

# 内联 link.sh 逻辑（因为 curl|bash 时没有 link.sh）
mkdir -p ~/.claude/skills 2>/dev/null || true
mkdir -p ~/.claude/projects/-home-charlie/memory 2>/dev/null || true
mkdir -p ~/.config/systemd/user
mkdir -p ~/.config/opencode/agents

do_link() {
    local src="$DOTFILES/$1"
    local dest="$2"

    [ ! -e "$src" ] && return

    # 已指向正确位置
    [ -L "$dest" ] && [ "$(readlink -f "$dest")" = "$(readlink -f "$src")" ] && {
        ok "$dest (已链接)"
        return
    }

    # 目标不存在
    if [ ! -e "$dest" ]; then
        ln -s "$src" "$dest" 2>/dev/null && ok "$dest → $src" || fail "$dest"
        return
    fi

    # 目标已存在 → 备份
    local backup="${dest}.bak.$(date +%s)"
    mv "$dest" "$backup" 2>/dev/null
    ln -s "$src" "$dest" 2>/dev/null && ok "$dest → $src (旧文件备份到 .bak)" || fail "$dest"
}

# CLAUDE.md
do_link "claude/CLAUDE.md" "$HOME/CLAUDE.md"

# Skills
do_link "claude/skills" "$HOME/.claude/skills"

# Memory
do_link "claude/memory" "$HOME/.claude/projects/-home-charlie/memory"

# 脚本
do_link "bin" "$HOME/bin"
do_link "launcher" "$HOME/launcher"

# Systemd
do_link "systemd" "$HOME/.config/systemd/user"

# OpenCode
do_link "opencode/opencode.json" "$HOME/.config/opencode/opencode.json" 2>/dev/null || true
do_link "opencode/AGENTS.md" "$HOME/.config/opencode/AGENTS.md" 2>/dev/null || true
do_link "opencode/agents" "$HOME/.config/opencode/agents" 2>/dev/null || true

# ── Step 4: 验证 ──
echo ""
echo "--- Step 4: 验证 ---"

ERRORS=0

verify() {
    if [ -L "$1" ] || [ -f "$1" ]; then
        ok "$1"
    else
        fail "$1 (缺失)"
        ERRORS=$((ERRORS + 1))
    fi
}

verify "$HOME/CLAUDE.md"
verify "$HOME/.claude/skills"
verify "$HOME/bin"
verify "$HOME/launcher"
verify "$HOME/.config/systemd/user"

# ── 完成 ──
echo ""
echo "╔══════════════════════════════════════╗"
if [ "$ERRORS" -eq 0 ]; then
    echo "║  ✅ 恢复完成！所有配置已就位         ║"
else
    echo "║  ⚠️  恢复完成，有 $ERRORS 个警告          ║"
fi
echo "╚══════════════════════════════════════╝"
echo ""
echo "后续步骤:"
echo "  1. 重启 systemd 用户服务: systemctl --user daemon-reload"
echo "  2. NixOS 配置需手动: sudo ln -sf $DOTFILES/nixos /etc/nixos"
echo "  3. 日常更新: ~/dotfiles/push-to-cloud.sh"
