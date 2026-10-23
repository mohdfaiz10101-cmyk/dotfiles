# Waybar workspace cleanup — 2026-10-23

## Current layout and source
- Live unit: `waybar.service`; wrapper reads `~/.config/waybar/config` and `style.css`.
- One native `sway/workspaces` instance, short numbered labels, persistent slots 1–7.
  Other active workspaces (e.g. Obsidian's 8) remain visible automatically.
- Top-left `分区 ▾`: left = grouped switch, right = move focused window,
  middle = window list (focus/move). No drawer expansion.
- Top-right: WeChat/Obsidian/Notion/terminal text labels with existing state classes/actions.
- Bottom: CPU/memory, existing multi-NIC signal chip, layout; idle/audio/clock/tray.
  No paused status placeholders or duplicate built-in network module.
- `~/.config/sway/workspaces.json`: labels/groups/short names.
- `~/.local/bin/workspace-menu.py`: reads source directly, exact selection-to-ID lookup.
- Existing `rofi-workspace-menu.sh` entry is a compatibility wrapper.
- Generator `apply-workspace-groups.py --waybar` outputs native module JSON;
  `--policy` preserves routing rules. Both print only, never overwrite config.

## Findings
- Multiple sway/workspaces instances each include active workspaces; persistent-workspaces
  is not an exclusive group filter. Group drawers led to duplicate buttons and overflow.
- Avoid global `.hidden { opacity: 0; }` as drawer layout control.
- Default menu is Wofi `--dmenu`, with `single_click=true` and dedicated
  `~/.config/wofi/workspaces.css`. `--show drun` is not a stdin selection menu.
- Rofi fallback uses isolated `workspaces.rasi`, explicit window -> mainbox ->
  inputbar/listview, and `-steal-focus`. Old theme with direct window children
  showed only input. Rofi keyboard selection worked after focus fix, but synthetic
  pointer acceptance remained unreliable; Wofi mouse and keyboard both verified.
- Preserve `waybar.service.d/20-sway-ipc-proxy.conf` and no-transition CSS.
  Restart only waybar.service; never pattern-kill Waybar test processes.

## Verification
- JSON, Python AST, bash action syntax checked.
- Live logs: top 1536x34, bottom 1536x30, one process.
- Native workspace button changed to 3; Wofi mouse/keyboard changed to 6.
  Restored focused workspace 1 after tests.
- Right/middle popups verified; escaped without moving user windows.
- Evidence and initial backup: `~/.local/state/waybar-cleanup/20261023/`.
- Restore initial state if explicitly needed:
  `bash ~/.local/state/waybar-cleanup/20261023/rollback.sh`
