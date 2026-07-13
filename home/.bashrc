# 加载集中式 API Keys 配置
[ -f ~/.config/api-keys/env ] && source ~/.config/api-keys/env

# 用户本地 bin
export PATH="$HOME/.local/bin:$PATH"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

source ~/.config/ai-shared/aliases.sh 2>/dev/null

# Claude Code tmux wrapper — claude-with-router + 防丢会话
cct() {
  local session="cc-$(date +%m%d)"
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux attach -t "$session"
  else
    tmux new-session -s "$session" "claude-with-router"
  fi
}

# 真正的 Claude Opus 升级（清除 GLM 环境变量）
ccop() {
  env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN \
      -u ANTHROPIC_DEFAULT_HAIKU_MODEL -u ANTHROPIC_DEFAULT_SONNET_MODEL \
      -u ANTHROPIC_DEFAULT_OPUS_MODEL -u ANTHROPIC_SMALL_FAST_MODEL \
      /run/current-system/sw/bin/claude --model opus "$@"
}
export LD_LIBRARY_PATH="/nix/store/nn129jwsznqv7k888wb05m5whpyndqrf-pipewire-1.6.2/lib64:/nix/store/nn129jwsznqv7k888wb05m5whpyndqrf-pipewire-1.6.2/lib:$LD_LIBRARY_PATH"
. "$HOME/.cargo/env"

#THIS MUST BE AT THE END OF THE FILE FOR SDKMAN TO WORK!!!
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"
