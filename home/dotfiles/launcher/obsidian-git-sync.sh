#!/bin/bash
# obsidian-git-sync.sh — Obsidian Vault git 自动同步
set -euo pipefail

VAULT="/home/charlie/Obsidian Vault"
cd "$VAULT" || exit 1

# 检查是否是 git repo
if [ ! -d ".git" ]; then
  echo "[obsidian-sync] Not a git repo, initializing..."
  git init
  git remote add origin "https://github.com/$(git config user.name 2>/dev/null || echo 'local')/obsidian-vault.git" 2>/dev/null || true
fi

# Stage all changes
git add -A

# Commit if there are changes
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "sync: $(date '+%Y-%m-%d %H:%M')" --author="auto-sync <auto@local>" 2>/dev/null || true
  # Push (silent fail if no remote)
  git push 2>/dev/null || true
  echo "[obsidian-sync] Committed and pushed $(date '+%H:%M')"
else
  echo "[obsidian-sync] No changes to sync"
fi
