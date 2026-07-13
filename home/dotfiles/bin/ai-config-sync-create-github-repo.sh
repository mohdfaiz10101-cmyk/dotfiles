#!/usr/bin/env bash
# 创建 GitHub 仓库 ai-config-sync
# 用法: 先设置 GITHUB_TOKEN 环境变量，然后运行此脚本

set -e

TOKEN="${GITHUB_TOKEN:?需要设置 GITHUB_TOKEN 环境变量}"
REPO_NAME="${1:-ai-config-sync}"
SYNC_DIR="$HOME/ai-config-sync"

# 检查仓库是否已存在
if curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/$(gh api user -q .login 2>/dev/null || echo $GITHUB_USER)/$REPO_NAME" | grep -q '"name"'; then
    echo "仓库已存在，跳过创建"
    cd "$SYNC_DIR" && git remote add origin "https://$TOKEN@github.com/$(gh api user -q .login 2>/dev/null || echo $GITHUB_USER)/$REPO_NAME.git" 2>/dev/null || true
else
    # 创建仓库
    echo "创建 GitHub 仓库: $REPO_NAME"
    gh repo create "$REPO_NAME" --private --description "OpenCode × StepClaw 配置同步仓库" --source "$SYNC_DIR" --push 2>&1 || {
        # 如果 gh 不可用，用 curl
        echo "gh 不可用，用 curl 创建..."
        curl -s -H "Authorization: token $TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            https://api.github.com/user/repos \
            -d "{\"name\":\"$REPO_NAME\",\"private\":true,\"description\":\"OpenCode × StepClaw 配置同步仓库\"}" | grep -q '"name"' && echo "仓库创建成功" || echo "仓库创建失败"
    }
fi
