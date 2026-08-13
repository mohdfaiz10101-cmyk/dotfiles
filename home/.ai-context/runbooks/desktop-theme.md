# Runbook: Codex Desktop Theme

## Design source

- Canonical palette: `~/.config/codex-theme/palette.md`
- Visual direction: near-black neutral surfaces, restrained borders, OpenAI
  green for focus/success, semantic blue/yellow/red only for status.

## Components

- Sway: `~/.config/sway/config`
- Main Waybar: `~/.config/waybar/style.override.css`
- Layout toolbar: `~/.config/waybar/toolbar.css`
- Kitty: `~/.config/kitty/kitty.conf`
- Foot: `~/.config/foot/foot.ini`
- Rofi/Wofi: `~/.config/rofi/launcher.rasi`,
  `~/.config/wofi/style.css`
- OpenCode: `~/.config/opencode/themes/codex.json`,
  `~/.config/opencode/tui.json`
- Notifications/lock: `~/.config/mako/config`,
  `~/.config/swaylock/config`
- GTK: `~/.config/gtk-3.0/settings.ini`,
  `~/.config/gtk-4.0/settings.ini`
- tmux: `~/.tmux.conf`

## Reload

```bash
swaymsg reload
systemctl --user restart waybar.service waybar-toolbar.service
makoctl reload
tmux -S /run/user/1000/tmux/opencode.sock source-file ~/.tmux.conf
```

OpenCode reads its TUI theme when a new attach process starts. Existing GTK
applications may need to be reopened.

## Terminal Tabs

- Workspace `1` is the Foot terminal workspace and uses Sway's `tabbed`
  layout. Foot windows are routed there and forced tiled.
- `Super+Tab` / `Super+Shift+Tab` select the next / previous tab.
- `Super+Ctrl+Left` / `Super+Ctrl+Right` reorder the focused tab.
- `sway-workspace-controller.service` requires `SWAYSOCK` in the user-manager
  environment. The Sway config imports it before restarting the controller;
  verify with `systemctl --user show-environment | rg '^SWAYSOCK='`.

## Rules

- Do not introduce a second palette directly into component files.
- Preserve green for focus/success; do not use it as decorative body text.
- Keep toolbars neutral and use colored backgrounds only for warnings/errors.
- Validate both Waybar configurations before restart.
