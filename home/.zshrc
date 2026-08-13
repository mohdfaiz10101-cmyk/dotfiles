export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PATH="$HOME/.local/bin:$PATH"
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
    if ! tmux -S "$sock" has-session -t "${session}:" 2>/dev/null; then
        tmux -S "$sock" new-session -d -s "$session" -c /var/home/charlie \
            -e "HOME=/var/home/charlie" \
            -e "CODEX_HOME=/var/home/charlie/.codex" \
            -e "XDG_RUNTIME_DIR=/run/user/1000" \
            -e "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus" \
            -e "PATH=/var/home/charlie/.nvm/versions/node/current/bin:/var/home/charlie/.local/bin:/usr/bin:/bin" \
            -e "HTTP_PROXY=http://127.0.0.1:7892" \
            -e "HTTPS_PROXY=http://127.0.0.1:7890" "OPENAI_API_KEY=4GY0L5jyGZlZUrTO8JZlQ5TYHTW5HVettJ9ls7ymImw3nalmM1rGO6CFV0DwayuiC" "OPENAI_BASE_URL=https://api.stepfun.com/step_plan/v1" \
            -e "ALL_PROXY=http://127.0.0.1:7890" \
            -e "NO_PROXY=localhost,127.0.0.1,0.0.0.0,::1,192.168.123.0/24,100.64.0.0/10,.ts.net" \
            -e "CODEX_TOKEN_SAFE_RUN=/var/home/charlie/.local/bin/codex-token-safe-run" \
            -e "BASH_ENV=/var/home/charlie/.config/codex-shell-env/env.sh" \
            -e "ENV=/var/home/charlie/.config/codex-shell-env/env.sh" \
            -e "ZDOTDIR=/var/home/charlie/.config/codex-shell-env" \
            /var/home/charlie/.local/bin/codex-resume-or-new
        tmux -S "$sock" set-option -g history-limit 50000
        tmux -S "$sock" set-option -g mouse off
        tmux -S "$sock" set-option -t "${session}:${window}" remain-on-exit off
        tmux -S "$sock" set-option -t "${session}:${window}" allow-passthrough off 2>/dev/null || true
        tmux -S "$sock" set-option -t "${session}:${window}" extended-keys off 2>/dev/null || true
        sleep 1
    fi
    if [[ "$#" -eq 0 ]]; then
        exec tmux -S "$sock" attach-session -t "${session}:${window}"
    else
        tmux -S "$sock" send-keys -t "${session}:${window}" "$*" Enter
    fi
}
alias wifi='nmtui'
