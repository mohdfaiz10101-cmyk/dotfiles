# Workspace app entries / Waybar (2026-10-24)

## User design rules (superseded by the single-bar consolidation below)

- Keep exactly the existing top and bottom Waybars. A permanent third app row was explicitly rejected as unattractive.
- Workspace 1 must be the leftmost top-bar target. `分区管理` belongs in the lower-left system/layout area, away from workspace tabs.
- Upper-right global shortcuts: WeChat, Obsidian, Notion, Terminal, with stable labels and window state. A dot means a running window, NOT an unread message count. Urgency uses amber without flashing.
- Lower-center shortcuts follow the focused workspace. Left click launches/focuses; right click opens window/shortcut management; middle click requests a new window where the app supports it.
- Quickshell is a temporary lower-center popover only; it reserves zero extra rows and dismisses on close/leave/timeout.

## Components

- `~/.config/waybar/config`, `~/.config/waybar/style.css`
- `~/.config/quickshell/workspace-panel/apps.json`: app registry and editable workspace favorites; preserve user edits.
- `~/.config/quickshell/workspace-panel/shell.qml`: temporary window menu, add/remove actions, real app icons.
- `~/.local/bin/workspace-panel`: app actions, real Sway IPC subscription, cached bar status.
- `workspace-panel.service`: `/usr/bin/quickshell -c workspace-panel`; `waybar.service` remains the bar owner.
- Runtime state: `/run/user/1000/workspace-panel/state.json` and bounded `bar-*.json` / `global-*.json` streams.
- Existing workspace labels and rules remain in `~/.config/sway/workspaces.json` and `workspace-policy.json`. Obsidian/Notion remain on WS8/9.

## Operational lessons

- `~/.local/bin/quickshell` was an obsolete ELF missing `libcpptrace.so.1` while `/usr/bin/quickshell` 0.2.1 worked. It now links to the system binary. Do not install libraries for the obsolete shadow binary. Old binary is in the recorded backup.
- Use the REAL `/run/user/1000/sway-ipc.*.sock` for actions and UI automation. The Waybar IPC proxy is not a reliable general command endpoint.
- Send `exec <shell-quoted argv>` over raw Sway IPC; `exec -- <argv>` did not launch applications in the verified environment.
- Ignore terminal window-title events, debounce structural events, and publish changed bar state from one watcher. Do not start per-button Python/Sway polling loops.
- Waybar tails small state streams, capped at 64 KiB each, rather than querying Sway repeatedly. Initial files appear when the watcher starts; tail retries are quiet.
- Explicit icon file paths resolve Papirus/system icons reliably when Quickshell has no icon theme in its service environment.
- `ExclusionMode.Normal` with `exclusiveZone: 0` respects Waybar while allowing the temporary popover to overlay windows.
- Kitty running `top` can ask for close confirmation. Smoke tests terminated ONLY the PID of their own newly-created monitor window.
- The old `~/.local/bin/code` points to a missing Nix path; do not offer it as a verified launcher. Current development favorites use installed Cursor and Thunar.

## Verification and reload

```bash
python3 -m py_compile ~/.local/bin/workspace-panel
~/.local/bin/workspace-panel state
systemctl --user restart workspace-panel.service
systemctl --user restart waybar.service
systemctl --user is-active workspace-panel.service waybar.service
~/.local/bin/workspace-panel popup terminal
```

Verified: workspace-dependent entries on WS1–9; actual terminal creation/routing/close; two monitor launch/focus/close/reopen cycles; no duplicate on second activation; real screenshots of the two-bar desktop and popover. A bounded 3-second sample used about 0.004 CPU seconds in each service; this is a spot check, not a long-term benchmark.

Backup pointer: `~/.local/share/workspace-panel/last-backup`. The directory contains original Waybar `config`, `style.css`, and the obsolete `quickshell.old`. For rollback, disable `workspace-panel.service`, restore only the two Waybar files from that directory, then restart `waybar.service`. Preserve the working system Quickshell link.

## Further desktop candidates (evaluated, not installed)

- Vicinae: https://docs.vicinae.com/ — app/window/file search, clipboard, script commands, extensions. Highest-priority candidate to evaluate as a unified command palette; local Sway/IME and startup measurements still needed.
- Walker/Elephant: https://github.com/abenz1267/walker — GTK4/Rust frontend plus provider backend; evaluate as an alternative to Vicinae, not as an additional permanent launcher.
- Noctalia: https://docs.noctalia.dev/noctalia/compositor-settings/sway-scroll/ — integrated desktop alternative supporting Sway. This is a broader shell migration; do not install alongside the existing bar/notification stack casually.
- Sway scratchpad: https://github.com/swaywm/sway/blob/master/config.in — useful for temporary terminal/file/calculator tools without consuming a permanent workspace.

## Vicinae installed and verified (2026-10-24)

Vicinae v0.29.2 was installed with the official installer using user prefix `~/.local`; no rpm-ostree layering or root changes were needed. The earlier candidate-only status above is superseded for Vicinae. Noctalia remains uninstalled.

- `Super+Space`: `~/.local/bin/vicinae-launch`, starts/checks the service then toggles search.
- `Super+Shift+Space`: original Wofi fallback remains.
- Right-click lower-bar `应用 ▴`: global search; left click retains workspace application management.
- `~/.config/sway/config.d/vicinae.conf` imports actual Sway environment and prewarms `vicinae.service`. This Sway session does NOT activate `graphical-session.target`; merely enabling that target's service is insufficient for login startup.
- Settings: `~/.config/vicinae/settings.json`. Theme: `~/.local/share/vicinae/themes/codex-dark.toml` (canonical colors from `~/.config/codex-theme/palette.md`). Putting a theme only under `~/.config/vicinae/themes` does not make it available; a restart picked up the correct data-directory theme.
- Unit from official installer: `~/.local/share/systemd/user/vicinae.service`; session/PATH/Wayland/idle I/O overrides in `~/.config/systemd/user/vicinae.service.d/desktop.conf`.
- File index roots are actual XDG Documents (`/var/mnt/ai/xdg/文档`), Downloads (`/var/mnt/ai/xdg/下载`), and `~/.ai-context/runbooks`. Do not expand to the entire home or large generated trees by default.
- File provider preferences in this version use camelCase: `autoIndexing`, `indexingPaths`, `excludedIndexingPaths`, under `providers.files.preferences`.
- `vicinae cmd launch wm:switch-windows`, `vicinae cmd launch files:search`, and `vicinae cmd launch clipboard:history` open dedicated commands.
- The v0.29.2 wlroots foreign-toplevel backend works on this Sway setup even though the documentation's window-support table omits Sway. Verified listing AND actual focus to existing con_id 794. Do not infer compatibility solely from older docs.
- Verified actual Fcitx Pinyin composition to `测试`, application creation via `vicinae app launch --new foot.desktop` and WS1 routing, indexed manual lookup, clipboard capture of an isolated test string, and real UI screenshots. Test terminal closed without touching existing sessions. Warm IPC timings are request round trips, not measured rendering latency.
- Input helper can write the already-permitted `/dev/uinput`, but cannot read several physical `/dev/input/event*` devices. Clipboard history works; automatic snippet expansion was not validated. Do not grant broad capabilities just to suppress these logs.
- Existing config backups and installation evidence: `~/.local/state/vicinae-setup/`. Never print existing clipboard history or provider databases for diagnosis.

## Two desktop setups: coexistence boundary

User wants the current desktop retained while considering Noctalia. The verified current setup is Sway + two Waybars + Vicinae. Noctalia supports Sway according to its official compositor guide, but it has NOT been installed, and no second login entry exists yet.

Recommended implementation for a future Noctalia setup: separate Sway config/session entry, separate Noctalia settings, and session-scoped ownership of bar, notifications, wallpaper, idle/lock and launcher shortcuts. Existing `waybar.service`, `workspace-panel.service` and notifications must not start in that alternate session. Current Waybar is enabled under `default.target`, so adding only a second .desktop entry would not isolate it. Keep GDM; no reason to replace the login manager. Do not log out or stop the user's current Sway session to demonstrate coexistence.

Sources: https://docs.vicinae.com/install/linux ; https://docs.vicinae.com/config ; https://docs.noctalia.dev/noctalia/compositor-settings/sway-scroll/ ; https://docs.noctalia.dev/noctalia/getting-started/installation/ .

## Desktop consolidation and visible layout switching (2026-10-24)

The user rejected the accumulated visual clutter and explicitly asked for real optimization/integration, not more tool buttons. The default is now ONE top Waybar. This supersedes the earlier two-bar default above. Existing windows, sessions and app workspace routing were preserved.

Visual hierarchy:
- Left: workspace tabs only; no leading workspace-menu misclick target. WS8 and WS9 now have `笔记` and `协作` labels in the existing single source of truth.
- Center: current-workspace launch/focus actions and `＋` for window/favorite management.
- Right: `常用`, `简洁 ▾` layout selector, compact health/network/volume/clock, and a collapsed `⋯` tray drawer. CPU/memory/SSID detail lives in tooltips. Four global app labels and duplicated tray items are no longer permanently displayed.
- Window title/spinner is removed from the global bar; Sway's application tab strip remains for actual terminal navigation.
- The temporary Quickshell window menu anchors below the top bar in compact mode and above the lower bar in complete mode.

`~/.local/bin/desktop-controls` owns the actions:
```bash
desktop-controls menu
desktop-controls favorites
desktop-controls apply compact
desktop-controls apply complete
desktop-controls status
```

Actual layout sources: `~/.config/waybar/layouts/compact.json` and `complete.json`. Current selection: `~/.config/desktop-controls/settings.json`. Applying a layout atomically writes `~/.config/waybar/config`, restarts only Waybar and its temporary-menu service, and rolls back files if a restart command fails. Edit the layout source as well when changing a layout; otherwise the next selection would replace edits made only to the generated active config. CSS is shared in `~/.config/waybar/style.css` and was rewritten cleanly instead of appending another override layer.

Important switching lesson: a Waybar child must NOT restart Waybar directly because stopping its parent cgroup can kill the switch. The menu launches `desktop-controls apply ...` in its own collected transient `desktop-layout-switch.service` with `systemd-run --user`. UI selection is exact-key mapped; do not prefix inactive rows with whitespace because `.strip()` removes it and breaks lookup.

Verified: real mouse click on the new `简洁 ▾` button, actual Wofi selection of `完整`, transient-unit switch, return to compact, exactly one active bar, context app changes on WS2/4/8/9/1, top-anchored popup screenshot, all three desktop services active, valid Python and both layout JSONs. `Noctalia` is explicitly labeled uninstalled/unavailable in the selector; this button switches layouts within Sway and does not pretend to switch to an uninstalled shell.

Backup pointer for the consolidation: `~/.local/state/desktop-controls/last-backup`. Do not reinstall or log out to restore the complete layout; the selector and the command above already do it.
