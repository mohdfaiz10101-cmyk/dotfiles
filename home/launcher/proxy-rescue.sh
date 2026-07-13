#!/usr/bin/env bash
set -euo pipefail

# Why: Provide a proxy-independent AI assistant + diagnostics when proxy is down.
# What: Creates a tmux "rescue" session with GLM (no proxy), diag templates, and clean shell.
# Test: Run the script, verify 3 tmux windows exist, GLM responds without proxy.

SESSION="rescue"

show_help() {
    cat <<'HELP'
proxy-rescue.sh — 代理故障应急环境

启动 tmux session "rescue"，包含 3 个窗口：
  窗口 0 [glm]   : 代理隔离的 GLM 交互模式（国内 API，无需代理）
  窗口 1 [diag]  : 代理诊断命令模板（复制粘贴使用）
  窗口 2 [shell] : 代理隔离的普通 shell

用法：
  proxy-rescue.sh          启动或 attach 到 rescue session
  proxy-rescue.sh --help   显示此帮助
HELP
    exit 0
}

[[ "${1:-}" == "--help" || "${1:-}" == "-h" ]] && show_help

# Attach if session already exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
    exec tmux attach-session -t "$SESSION"
fi

DIAG_TEXT='=== 代理诊断 ===
systemctl status xray
systemctl --user status mihomo
ss -tlnp | grep -E '\''7890|7891|9090'\''
journalctl -u xray -n 20 --no-pager
curl -x http://127.0.0.1:7890 -sI https://www.gstatic.com/generate_204
curl -sI https://api.anthropic.com/v1/messages

=== 常见修复 ===
# Xray DNS 失败 → 重启
sudo systemctl restart xray

# 切换到 mihomo
sudo systemctl stop xray && systemctl --user start mihomo

# 测试 Claude 连通性
curl -x http://127.0.0.1:7890 -sI https://api.anthropic.com/v1/messages

=== 完全断网应急 ===
# GLM 不需要代理（国内 API），可在窗口 0 使用
# 向 GLM 描述故障现象，获取修复建议'

UNSET_PROXY="unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY"

# Window 0: glm (proxy-isolated)
tmux new-session -d -s "$SESSION" -n "glm"
tmux send-keys -t "$SESSION:glm" "$UNSET_PROXY && clear && echo '=== GLM 交互模式（代理已隔离）===' && glm" Enter

# Window 1: diag (diagnostic templates)
tmux new-window -t "$SESSION" -n "diag"
tmux send-keys -t "$SESSION:diag" "cat <<'EOF'
${DIAG_TEXT}
EOF" Enter

# Window 2: shell (proxy-isolated)
tmux new-window -t "$SESSION" -n "shell"
tmux send-keys -t "$SESSION:shell" "$UNSET_PROXY && clear && echo '=== 应急 Shell（代理已隔离）==='" Enter

# Focus window 0
tmux select-window -t "$SESSION:glm"

exec tmux attach-session -t "$SESSION"
