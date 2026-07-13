# Runbook: Mouse/Input Capture

## Symptoms
- ttyd/OpenClaw page appears to capture mouse clicks or scroll.
- Terminal emits mouse escape fragments such as `35;7;33M`.
- Text typed into the OpenCode input box does not appear, often because a stale ttyd browser tab/WebSocket still owns the only client slot or has desynced the tmux attach.

## Fix
```bash
tmux -S /run/user/1000/tmux/opencode.sock set-option -g mouse off
tmux -S /run/user/1000/tmux/opencode.sock set-option -t openclaw mouse off
systemctl --user disable --now ydotool-bridge.service
systemctl --user restart ttyd-8080.service
```

## Persistent Location
- `~/.local/bin/openclaw-tmux-wrap` must set global and session `mouse off`.
- In `~/.local/bin/openclaw-tmux-wrap`, create the tmux session before running `tmux set-option -g mouse off`; otherwise a cold start with no tmux server exits with `no server running on /run/user/1000/tmux/opencode.sock`.
- `~/.local/bin/openclaw-tmux-wrap` must use `tmux attach-session -d` so a stale ttyd/local client cannot resize or desync the visible terminal.
- `~/.local/bin/ttyd-openclaw-entry` should exec `~/.local/bin/openclaw-tmux-wrap`; do not bypass tmux for 18080 because the user depends on tmux persistence.
- `~/.config/systemd/user/ttyd-8080.service` should use ttyd's native index, no `-m 1`, and `-t "rendererType=dom"` for better browser input/IME behavior. Avoid the old custom `-I ~/.local/share/ttyd-custom/index.html` unless IME/input is verified.
- If both local `oc` and 18080 cannot type, stop debugging FRP/ttyd first: this points to the shared OpenCode TUI/tmux path. Force `TERM=xterm-256color` in both `~/.local/bin/oc` and `~/.local/bin/opencode-openclaw-attach-loop`, then rebuild the `openclaw` tmux session.
- `ydotool-bridge.service` should stay disabled unless KVM remote input is explicitly needed.

## Verify
```bash
tmux -S /run/user/1000/tmux/opencode.sock show-options -g mouse
systemctl --user is-active ydotool-bridge.service
ps -eo comm,args | rg -i 'ydotool|wayvnc|sunshine|scrcpy'
```
