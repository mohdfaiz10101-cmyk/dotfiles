#!/usr/bin/env bash
# link.sh — 将 dotfiles 目录 symlink 到系统实际路径
# 用法: ./link.sh          # 创建所有 symlink
#       ./link.sh --force  # 覆盖已存在的文件/目录
set -euo pipefail

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
FORCE="${1:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

# link <dotfiles_subdir> <target_path>
# 如果目标是 symlink → 更新
# 如果目标不存在 → 创建 symlink
# 如果目标是真实目录/文件 → --force 时备份+替换，否则跳过
do_link() {
    local src="$DOTFILES/$1"
    local dest="$2"

    if [ ! -e "$src" ]; then
        skip "$dest (源不存在: $src)"
        return
    fi

    # 已经指向正确位置
    if [ -L "$dest" ]; then
        local current
        current="$(readlink -f "$dest")"
        if [ "$current" = "$(readlink -f "$src")" ]; then
            ok "$dest (已链接)"
            return
        fi
    fi

    # 目标不存在 → 直接创建
    if [ ! -e "$dest" ]; then
        ln -s "$src" "$dest"
        ok "$dest → $src"
        return
    fi

    # 目标已存在且是真实文件/目录
    if [ "$FORCE" = "--force" ]; then
        local backup="${dest}.bak.$(date +%s)"
        mv "$dest" "$backup"
        ln -s "$src" "$dest"
        ok "$dest → $src (备份到 ${backup})"
    else
        fail "$dest (已存在，用 --force 覆盖)"
    fi
}

echo "=== Dotfiles Symlink 工具 ==="
echo "源目录: $DOTFILES"
echo ""

# 确保父目录存在
mkdir -p ~/.claude/skills
mkdir -p ~/.claude/projects/-home-charlie/memory
mkdir -p ~/.bin 2>/dev/null || true
mkdir -p ~/.config/systemd/user
mkdir -p ~/.config/opencode/agents

# === Symlink 映射表 ===

# CLAUDE.md
do_link "claude/CLAUDE.md" "$HOME/CLAUDE.md"

# Skills (目录级 symlink)
do_link "claude/skills" "$HOME/.claude/skills"

# Memory
do_link "claude/memory" "$HOME/.claude/projects/-home-charlie/memory"

# 用户脚本
if [ -d "$DOTFILES/bin" ] && [ "$(ls -A "$DOTFILES/bin" 2>/dev/null)" ]; then
    # bin 用目录级 symlink
    do_link "bin" "$HOME/bin"
fi

# Launcher 脚本
do_link "launcher" "$HOME/launcher"

# Systemd user services
do_link "systemd" "$HOME/.config/systemd/user"

# OpenCode 配置
do_link "opencode/opencode.json" "$HOME/.config/opencode/opencode.json" 2>/dev/null || true
do_link "opencode/AGENTS.md" "$HOME/.config/opencode/AGENTS.md" 2>/dev/null || true
do_link "opencode/oh-my-openagent.jsonc" "$HOME/.config/opencode/oh-my-openagent.jsonc" 2>/dev/null || true
do_link "opencode/agents" "$HOME/.config/opencode/agents" 2>/dev/null || true

# NixOS 配置（需要 sudo）
if [ -d /etc/nixos ] && [ -d "$DOTFILES/nixos" ]; then
    echo ""
    echo "--- NixOS 配置 (需要 sudo) ---"
    if [ "$(id -u)" -eq 0 ] || [ "$FORCE" = "--force" ]; then
        # 只有明确 --force 才动 NixOS 配置
        sudo ln -sf "$DOTFILES/nixos" /etc/nixos 2>/dev/null && ok "/etc/nixos" || skip "/etc/nixos (需要 sudo)"
    else
        skip "/etc/nixos (restore.sh 中处理，或手动 sudo ./link.sh --force)"
    fi
fi

echo ""
echo "=== 完成 ==="
echo "验证: ls -la ~/bin ~/launcher ~/.claude/skills"
