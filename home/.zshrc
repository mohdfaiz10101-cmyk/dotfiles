export LANG=C.UTF-8
export LC_ALL=C.UTF-8
HISTFILE=~/.zsh_history
SAVEHIST=5000
HISTSIZE=5000
setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS

if [[ -z "$TMUX" ]] && [[ -n "$SSH_CONNECTION" ]]; then
    exec tmux new-session -A -s main
fi
export TMUX_TMPDIR=/tmp
. "/var/home/charlie/.acme.sh/acme.sh.env"

codex() {
    local sock=/run/user/1000/tmux/codex.sock
    local session=codex-main
    local window=0
    # TUI 需要真终端: TERM=dumb/unset 时 codex 0.163.0 只输出 ~114 字节就废掉
    # (实测: 正常 4467 字节, TERM=dumb 114 字节), 表现为"能启动但无法交互输入"。
    if [ -z "${TERM:-}" ] || [ "$TERM" = "dumb" ]; then
        export TERM=xterm-256color
    fi
    if [ -z "${COLORTERM:-}" ]; then
        export COLORTERM=truecolor
    fi
    # attach 失败时(server 挂了/session 刚死)不要直接 exit, 走重建分支
    if ! tmux -S "$sock" has-session -t "${session}:" 2>/dev/null; then
        tmux -S "$sock" new-session -d -s "$session" -c /var/home/charlie \
            -e "HOME=/var/home/charlie" \
            -e "CODEX_HOME=/var/home/charlie/.codex" \
            -e "XDG_RUNTIME_DIR=/run/user/1000" \
            -e "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus" \
            -e "PATH=/var/home/charlie/.local/bin:/var/home/charlie/.npm-global/bin:/var/home/charlie/.nvm/versions/node/current/bin:/usr/bin:/bin" \
            -e "HTTP_PROXY=http://127.0.0.1:7892" \
            -e "HTTPS_PROXY=http://127.0.0.1:7890" \
            -e "ALL_PROXY=http://127.0.0.1:7890" \
            -e "NO_PROXY=localhost,127.0.0.1,0.0.0.0,::1,192.168.123.0/24,100.64.0.0/10,.ts.net" \
            -e "CODEX_TOKEN_SAFE_RUN=/var/home/charlie/.local/bin/codex-token-safe-run" \
            -e "BASH_ENV=/var/home/charlie/.config/codex-shell-env/env.sh" \
            -e "ENV=/var/home/charlie/.config/codex-shell-env/env.sh" \
            -e "ZDOTDIR=/var/home/charlie/.config/codex-shell-env" \
            /var/home/charlie/.local/bin/codex-resume-or-new
        tmux -S "$sock" set-option -g history-limit 50000
        tmux -S "$sock" set-option -g mouse off
        # 关键: codex 退出后保留 pane, 否则 session 立即消失, attach 瞬间返回 = "闪退"
        tmux -S "$sock" set-option -t "${session}:${window}" remain-on-exit on
        tmux -S "$sock" set-option -t "${session}:${window}" allow-passthrough off 2>/dev/null || true
        tmux -S "$sock" set-option -t "${session}:${window}" extended-keys off 2>/dev/null || true
        # 尺寸必须跟随 attach 的客户端, 不能 manual 固定。
        # manual + 固定大尺寸会把 codex 输入框裁到视口外 = "能启动但无法输入"。
        tmux -S "$sock" set-option -t "${session}:${window}" window-size latest 2>/dev/null || true
        tmux -S "$sock" set-window-option -t "${session}:${window}" aggressive-resize on 2>/dev/null || true
        sleep 2
    fi
    if [[ "$#" -eq 0 ]]; then
        exec tmux -S "$sock" attach-session -t "${session}:${window}"
    else
        tmux -S "$sock" send-keys -t "${session}:${window}" "$*" Enter
    fi
}
alias wifi='nmtui 2>/dev/null || nmcli device wifi list'
alias wifi-list='nmcli device wifi list'
alias wifi-connect='nmtui-connect 2>/dev/null || nmcli device wifi list'
alias wifi-editor='nmtui-edit 2>/dev/null || nmcli connection show'
alias wifi-scan='nmcli device wifi rescan; nmcli device wifi list'
alias wifi-status='nmcli -p device'
export ANDROID_SERIAL=100.87.37.3:5555  # PKR110 NetBird primary

# ─── Windows 远程执行（win-s2d8gp89fu1 / Tailscale MagicDNS） ───
# 入口脚本 ~/.local/bin/win，连接由 win-ssh-keepalive.timer 每 20min 预热
alias win='/var/home/charlie/.local/bin/win'
alias win-check='/var/home/charlie/.local/bin/win --check'
alias win-warm='/var/home/charlie/.local/bin/win --warm'
alias win-bat='/var/home/charlie/.local/bin/win --bat'
alias win-ps='/var/home/charlie/.local/bin/win --ps'
alias win-mount='/var/home/charlie/.local/bin/win --mount'
# Windows 桌面部署目录（Linux 侧视角），方便 scp/rsync
alias win-desktop='cd /var/mnt/winpc-c/Users/G/Desktop'
