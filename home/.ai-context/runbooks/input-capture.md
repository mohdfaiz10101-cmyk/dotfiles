# Runbook: Mouse/Input Capture

## Symptoms
- ttyd/OpenClaw page appears to capture mouse clicks or scroll.
- Terminal emits mouse escape fragments such as `35;7;33M`.
- Text typed into the OpenCode input box does not appear, often because a stale ttyd browser tab/WebSocket still owns the only client slot or has desynced the tmux attach.
- Sway desktop/workspaces flicker, windows appear to drift between workspaces,
  or focus jumps while Sunshine is running and Sway inputs include
  `48879:57005:*_passthrough`.
- Foot/Codex windows appear briefly every few seconds, making workspaces flash
  or move, when `codex-foot-tab-sort.timer` is active with the old
  `OnUnitActiveSec=5s` cadence or when the launcher inherits `TMUX`.

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

## Sway Desktop Flicker / Window Drift

First stop remote-input and auto-window churn:

```bash
systemctl --user stop sunshine.service
systemctl --user stop codex-foot-tab-sort.service
systemctl --user restart sway-workspace-controller.service
swaymsg -t get_inputs | jq -r '.[] | [.identifier,.name,.type] | @tsv'
```

Durable local fixes:

- `~/.local/bin/adb-phone-keepalive.sh` must not auto-start Sunshine by
  default. It only starts Sunshine when
  `ADB_PHONE_KEEPALIVE_START_SUNSHINE=1` is explicitly set.
- `~/.local/bin/codex-foot-console-maintain` should repair missing discovered
  Foot/Codex tabs only when `CODEX_FOOT_REPAIR_MISSING=1` is explicitly set.
  The timer path must only sort existing `foot-codex<N>` windows; otherwise
  closed/old local tabs are recreated every few minutes and make workspaces
  flicker.
- `~/.local/bin/codex-foot-tab-sort` must exit before calling
  `127.0.0.1:19000/quota.json` when no `foot-codex<N>` windows exist. This
  avoids repeated timer curl timeouts and background churn after the user has
  closed local Codex tabs.
- `~/.local/bin/codex-foot-tabs` must `unset TMUX TMUX_PANE` before launching
  Foot. Otherwise tmux-originated environments can make the local Foot tmux
  attach exit immediately.
- `codex-foot-tab-sort.timer` should run at a slow cadence such as
  `OnUnitActiveSec=2min`, not every 5 seconds.
- `~/.config/sway/workspace-policy.json` must exclude `foot(-codex[0-9]+)?`
  from generic title rules such as `codex|opencode`, so Foot Codex terminals
  cannot be moved to workspace 5 by title.

Verify stabilization:

```bash
systemctl --user is-active sunshine.service codex-foot-tab-sort.timer codex-foot-tab-sort.service sway-workspace-controller.service
swaymsg -t get_tree | jq -r '.. | objects | select((.type? == "workspace") and (.name? == "1")) | [ .name, ([.. | objects | select((.type? == "con" or .type? == "floating_con") and (.app_id? | test("^foot-codex[0-9]+$"))) | .app_id] | sort | join(",")) ] | @tsv'
before=$(stat -c %s ~/.local/state/sway-workspace-controller.log); sleep 7; after=$(stat -c %s ~/.local/state/sway-workspace-controller.log); echo "$((after-before))"
```

## Mobile AI Browser Tab Cleanup

- Workbench-controlled Chromium uses CDP on `127.0.0.1:9224` and profile
  `~/.config/mobile-ai-chromium`.
- Regular cleanup is `mobile-ai-browser-cleanup.timer` →
  `~/.local/bin/mobile-ai-browser-cleanup` every 10 minutes.
- The cleaner is conservative: it closes extension changelog/update pages,
  stale blank pages, and duplicate Workbench home/browser tabs; it does not
  close arbitrary user web pages.
- Workbench `/browser` also exposes `关当前` and `清旧页`; API endpoints:
  `POST /api/browser/close` and `POST /api/browser/cleanup`.
- The Sway workspace controller pins the Workbench-controlled Chromium window
  to workspace 4 by detecting `--user-data-dir=~/.config/mobile-ai-chromium`,
  so title changes such as `Codex WebTTY` do not bounce that browser window
  between workspace 4 and 5.
- Sway-level visible window cleanup is `sway-tab-cleanup.timer` →
  `~/.local/bin/sway-tab-cleanup` every 10 minutes. It only closes unfocused
  stale Chromium windows with titles like `Device Match`, `Codex <N> WebTTY`,
  `ttyd-codex...entry`, `New Tab`, or `无标题`; it skips the
  Workbench-controlled Chromium profile and ordinary web pages.

Verify:

```bash
systemctl --user is-active mobile-ai-browser-cleanup.timer sway-tab-cleanup.timer mobile-ai-workbench.service sway-workspace-controller.service
~/.local/bin/mobile-ai-browser-cleanup --dry-run --json | jq .
~/.local/bin/sway-tab-cleanup --dry-run --json | jq .
curl -fsS -H 'x-device-code: w19900422' http://127.0.0.1:19888/api/browser/tabs | jq .
```

## Hermes 19910 WebTTY Layout

- `ttyd-hermes.service` serves public `http://charlie1990.duckdns.org:19910/`
  through `~/.local/bin/ttyd-hermes-proxy.js`.
- The upstream page already has a fixed top `#sessionbar`. Do not inject a
  second fixed top toolbar such as `#agent-toolbar-sessionbar`; it overlays the
  session buttons on mobile.
- Extra maintenance actions should stay collapsed in the lower-left
  `#agent-toolbar` behind a single small toggle, with action buttons hidden
  until the toolbar is opened.
- Do not put `pointer-events:none` on the toolbar container. Prefer native
  `<details><summary>...</summary></details>` for collapsed mobile toolbars;
  it is more reliable than custom `pointerup` / `touchend` toggle code inside
  ttyd pages that already capture terminal input.
- After changes, verify the phone-visible DuckDNS path, not only local curl:
  `~/.local/bin/adb-record --tag hermes-19910-layout -- shell curl -I --max-time 8 http://charlie1990.duckdns.org:19910/`.

If Sunshine was recently involved, also check NVIDIA state before blaming
Sway:

```bash
nvidia-smi
journalctl --since '30 min ago' --no-pager | rg -i 'NVRM|nvidia|drm|hdmi|display'
```

## Kasm Cursor GUI

- 手机端 Cursor GUI 入口用 `mobile-ai-workbench` 的 `/kasm`。
- `/kasm` 现在分两排：
  - `Cursor GUI`：启动真实 Cursor 独立窗口
  - `Codex TTY`：叠加打开对应 WebTTY，不影响 GUI
- `/kasm` 必须内嵌真实画面，不要只做按钮跳转。
- KasmVNC 画面默认要带可见光标：
  - `show_dot=true`
  - `prefer_local_cursor=true`
  - `pointer_relative=false`
- 独立账号窗口按 `C1..C8` 启动：
  - `POST /api/kasm/cursor/start`，body `{"account":"1"}` 到 `{"account":"8"}`
  - 默认先起 `C5`
  - 接口把 `already-running` 也算成功，避免按钮误报失败
- Kasm 桌面里也放了 finger-friendly 启动器：
  - `~/Desktop/Cursor-C1.desktop` ... `Cursor-C8.desktop`
  - `~/Desktop/Codex-C1-WebTTY.desktop` ... `Codex-C8-WebTTY.desktop`
- 宿主桌面 `Cursor-C1.desktop` ... `Cursor-C8.desktop` 只是 `cursor-account` 的快捷方式；它们最终也读取同一套 `CODEX_HOME` / `auth.json` / `config.toml`，所以只要先跑 `~/.local/bin/kasm-codex-home-sync`，桌面版 Cursor 就会拿到对应的 sub2 配置。
- 每个账号用独立目录：
  - `/home/kasm-user/.local/share/kasm-cursor-webtop/c1`
  - ...
  - `/home/kasm-user/.local/share/kasm-cursor-webtop/c8`
- 如果 Kasm 页面只有空白或只见背景，先查：
  - `/home/kasm-user/.local/share/kasm-cursor-webtop` 是否可由容器内 `kasm-user` 写入
  - 启动脚本是否因为 `chmod` / 绑定目录权限直接退出
  - `Cursor` 是否停在登录页而不是未启动
  - 如果窗口标题是 `README.md - Cursor` 但内容仍是登录/欢迎页，优先判断为**未登录 Cursor 账号**，不是渲染崩溃；当前主机没有可复用的 `~/.config/Cursor` 登录态
- 验证：
```bash
curl -fsS -H 'x-device-code: w19900422' http://127.0.0.1:19888/api/kasm/status | jq .
curl -fsS -H 'x-device-code: w19900422' -H 'content-type: application/json'   -d '{"account":"1"}' http://127.0.0.1:19888/api/kasm/cursor/start | jq .
podman exec kasm-cursor-webtop bash -lc 'ps -ef | grep -E "/opt/cursor/cursor .*user-data-dir=/home/kasm-user/.local/share/kasm-cursor-webtop/c[1-8]/user-data" | grep -v grep'
```
