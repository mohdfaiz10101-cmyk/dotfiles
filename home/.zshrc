# 基础 zshrc - 紧急恢复版
# 如果找到完整备份请替换

# 历史设置
HISTFILE=~/.zsh_history
SAVEHIST=5000
HISTSIZE=5000
setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS

# 基本别名
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'


# SSH 连接自动进入 tmux
if [[ -z "$TMUX" ]] && [[ -n "$SSH_CONNECTION" ]]; then
    exec tmux new-session -A -s main
fi
export TMUX_TMPDIR=/tmp
export PATH="$HOME/.local/bin:$PATH"
alias sm='~/.local/bin/sm'
codex() {
  case "$1" in
    1|codex1) shift; ~/.local/bin/codex1 "$@" ;;
    2|codex2) shift; ~/.local/bin/haven-entry-codex2 "$@" ;;
    3|codex3) shift; ~/.local/bin/codex3 "$@" ;;
    raw|cli|original) shift; command codex "$@" ;;
    *) command codex "$@" ;;
  esac
}
alias cdx1='~/.local/bin/codex1'
alias cdx2='~/.local/bin/codex2'
alias cdx3='~/.local/bin/codex3'
alias dash='~/.local/bin/open-dashboard-workspace.sh'
alias opx='~/.local/bin/opencode-task'
alias opreflect='~/.local/bin/opencode-reflect'
alias hqinfo='~/.local/bin/hqssh-hosts-info'
alias hqtmux='~/.local/bin/hqssh-tmux attach'
alias hqtails='~/.local/bin/hqssh sessions -H tailscale'
alias hqpub='~/.local/bin/hqssh sessions -H public-frp'
alias oc51='~/.local/bin/opencode-glm51'
export PATH=$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.cargo/bin:/run/wrappers/bin:/usr/bin:/bin:$HOME/.local/share/flatpak/exports/bin:/var/lib/flatpak/exports/bin
source ~/.config/zsh/completion.zsh

# zsh-autosuggestions
if [ -f /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]; then
  source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

# Hermes tmux attach for SSH sessions — DISABLED (.hermes/ not migrated to Silverblue)
# if [[ -n "$SSH_TTY" ]] && [[ "$HERMES_AUTO" != "no" ]]; then
#   if [ -n "$TMUX" ]; then
#     exec tmux switch-client -t hermes
#   elif tmux has-session -t hermes 2>/dev/null; then
#     exec tmux attach-session -t hermes
#   else
#     exec tmux new-session -s hermes "$HOME/.local/bin/hermes chat"
#   fi
# fi

# === 包管理器路径 → /mnt/ai (2026-06-01 OP) ===
export PYTHONUSERBASE=/mnt/ai/python-user
export GOPATH=/mnt/ai/go
export BUN_INSTALL=/mnt/ai/cache/node-modules
export PATH="$PYTHONUSERBASE/bin:$GOPATH/bin:$BUN_INSTALL/bin:$PATH"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
export http_proxy=http://127.0.0.1:7890
# === Migrated from old NixOS config ===
alias ai-ps='docker ps --format table'
alias dps='docker ps'
alias dc='docker compose'
alias proxy-restart='sudo systemctl restart mihomo'
alias proxy-log='journalctl -u mihomo -f'
alias proxy-ui='echo http://127.0.0.1:9090/ui'
alias proxy-on='export http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890'
alias proxy-off='unset http_proxy https_proxy'
alias ports='ss -tlnp'
alias ll='eza -l --icons --group-directories-first 2>/dev/null || ls -la'
alias la='eza -la --icons 2>/dev/null || ls -la'
alias lt='eza --tree --level=2 2>/dev/null || ls'
alias cat='bat --style=plain 2>/dev/null || cat'

# ===== MIGRATED FROM NIXOS - ALL ALIASES =====
# NixOS management (adapted)
alias ns='echo "Use rpm-ostree or dnf on Fedora"'
alias nixos-test='echo "Use rpm-ostree test on Fedora"'
alias nix-clean='sudo dnf autoremove -y; flatpak uninstall --unused -y'
alias pin-stable='sudo ostree admin pin 0'

# AI services
alias ai-log='journalctl -u ai-liteLLM -f'
alias ai-up='cd /mnt/ai/ai-cluster && for d in litellm letta langfuse jellyfin; do (cd $d 2>/dev/null && docker compose up -d 2>/dev/null); done; echo "AI cluster started"'
alias ai-ps='docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"'
alias ai-down='cd /mnt/ai/ai-cluster && for d in litellm letta langfuse jellyfin; do (cd $d 2>/dev/null && docker compose down 2>/dev/null); done; echo "AI cluster stopped"'

# Tmux / opencode

# Proxy
alias proxy-status='curl -s http://127.0.0.1:9091/configs 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get("mode","?"))" 2>/dev/null || echo "?"'
alias proxy-restart='sudo systemctl restart mihomo && echo restarted'
alias proxy-log='journalctl -u mihomo -f'
alias proxy-ui='echo http://127.0.0.1:9090/ui'
alias proxy-on='export http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890'
alias proxy-off='unset http_proxy https_proxy'

# Docker aliases
alias dps='docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"'
alias dc='docker compose'

# Claude
alias q="claude 2>/dev/null || echo not-found"
alias q-lite="ANTHROPIC_BASE_URL=http://127.0.0.1:4002 claude 2>/dev/null || echo not-found"

# System
alias ports='ss -tlnp'
alias ipinfo='curl -s ipinfo.io | python3 -m json.tool'
alias ..='cd ..'
alias ...='cd ../..'
alias c='clear'
alias ll='ls -la --color=auto'
alias la='ls -la --color=auto'
alias cat='bat --style=plain 2>/dev/null || cat'

# Disk / Backup
alias dashboard='echo http://127.0.0.1:7681'

# Memory / Obsidian
alias obsidian='flatpak run md.obsidian.Obsidian 2>/dev/null || echo "obsidian not installed yet"'
alias opencode='$HOME/.local/bin/opencode-enforced'
# === Sway 终端2 智能检测 ===
# ocw → 自动迁到 WS2 (终端2 / Windows)
ocw() {
    if [[ -n "$SWAYSOCK" ]]; then
        swaymsg 'move container to workspace 2, workspace 2' 2>/dev/null
    fi
    ssh -t G@192.168.123.136 opencode "$@"
}

# preexec hook: 检测 Windows 相关命令，自动迁终端到 WS2
autoload -Uz add-zsh-hook 2>/dev/null
_sway_win_detect() {
    local cmd="$1"
    [[ "$cmd" =~ ^ocw ]] && return  # ocw 函数已处理
    if [[ "$cmd" =~ "ssh.*192\.168\.123\.136" ]]; then
        if [[ -n "$SWAYSOCK" ]]; then
            swaymsg 'move container to workspace 2, workspace 2' 2>/dev/null
        fi
    fi
}
if command -v swaymsg &>/dev/null && [[ -n "${SWAYSOCK:-}" ]]; then
    add-zsh-hook preexec _sway_win_detect 2>/dev/null
fi

alias oc='$HOME/.local/bin/oc'
alias overcode='opencode'

# === Fedora Migration Tools (2026-06-14) ===
# Starship prompt
if command -v starship &>/dev/null; then
    eval "$(starship init zsh)"
fi
# Zoxide
if command -v zoxide &>/dev/null; then
    eval "$(zoxide init zsh)"
fi
# FZF
if command -v fzf &>/dev/null; then
    source /usr/share/fzf/shell/key-bindings.zsh 2>/dev/null || true
fi
# Atuin
if command -v atuin &>/dev/null; then
    eval "$(atuin init zsh)"
fi

# API Keys (from NixOS)
[ -f ~/.config/api-keys/systemd.env ] && while IFS= read -r line; do
  [[ "$line" =~ ^[A-Z].*= ]] && export "$line"
done < ~/.config/api-keys/systemd.env


# Locale for UTF-8 support
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# opencode
export PATH=/var/home/charlie/.opencode/bin:$PATH

#THIS MUST BE AT THE END OF THE FILE FOR SDKMAN TO WORK!!!
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"

# zsh-syntax-highlighting (must be last)
if [ -f /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]; then
  source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi
