# Runbook: Unified Control Plane

One architecture for operating Charlie's local AI/work/project stack.

## Desired State

- `appsmith.service` — Appsmith launcher/catalog on `:8089`; current generated apps are shortcut wrappers, not yet the Hub API control plane
- `hub-api.service` — API gateway, service registry, snapshots, semantic command endpoint, listens on `:9800`
- `n8n.service` — automation/workflow bus, listens on `:5678`
- FastGPT `:3000` — knowledge, plans, reviews
- OpenCode `:4097` / Web `:18910` — execution layer
- Mobile AI Workbench `mobile-ai-workbench.service` on `:19888` — phone-first
  operations shell that embeds the existing Codex WebTTY accounts and exposes
  compact task/quota/network/plugin panels plus the controlled Fedora Chromium
  browser. It is an outer control surface, not a replacement for the existing
  `19899/19900/19902/19903/19904` account gates.
- Mobile AI Browser `mobile-ai-browser.service` — headed Fedora Chromium with
  a dedicated profile `~/.config/mobile-ai-chromium`; CDP is local-only on
  `127.0.0.1:9224` and is controlled through Workbench `/browser` and
  `/api/browser/*`.
- Mobile AI Browsh — text browser beside Chromium. `mobile-ai-browsh-backend.service`
  runs ttyd on local-only `127.0.0.1:19886` with base path `/browsh-tty`;
  `mobile-ai-browsh-gate.service` exposes a device-code local/LAN gate on
  `:19885`; the preferred phone path is Workbench `/browsh`, which proxies
  `/browsh-tty/*` through the already-public `:19888` so no router rule is
  needed for `19885`. Browsh itself must be tmux-backed by session
  `mobile-ai-browsh`; otherwise every iframe/new window starts another Browsh,
  the second process exits, and ttyd shows reconnecting.
- Zulip/Mattermost — discussion and bot feedback
- Plane/Huly — project and workspace systems

## Entry Points

```bash
http://192.168.123.71:19888/?device=w19900422
http://charlie1990.duckdns.org:19888/?device=w19900422
http://100.120.189.27:9800/go/appsmith
http://100.120.189.27:9800/workspace
http://100.120.189.27:9800/projects
http://100.120.189.27:8089/
http://100.120.189.27:5678/
```

Current direct-entry rule:

- `:19888` is the mobile remote AI workbench. It should reuse existing Codex
  account gates as iframes and should not re-implement terminal state,
  quota parsing, or task recovery. Add new phone-facing actions as plugins/API
  panels here before adding more floating controls to each WebTTY page.
- 2026-07-15 `:19888/` is also the first task-management surface. Keep the
  homepage top taskbar with direct links for `/tasks` and `/windows`, a
  `新建当前账号` action that creates a Codex CLI window under the selected
  account, and an async task-state summary. Do not bury multi-window operations
  only under the tool drawer.
- 2026-07-17 phone IME stability rule: Workbench must lazy-load only the active
  account iframe on the home page. Periodic status/task/window refresh must not
  replace active DOM or reload the selected iframe while focus is in an
  iframe, input, textarea, select, or contenteditable element. This prevents
  Android/iOS mobile browsers from flashing the page and dropping the IME while
  the user is composing text.
- 2026-07-15 unified task dispatch: use Workbench **派发任务** (or `/go/hub`)
  as the sole general task entry. It opens Hub `/projects`, where every task is
  reviewed before dispatch. `/tasks` is only the Codex session/status view;
  `OpenCode` is for short exploratory chats and `Crush` for small repair work,
  not the default long-running task queue. The Super Button text command creates
  a Hub `pending_approval` task rather than starting an agent directly.
- Default code policy is **Goose diagnosis -> Aider single writer**. Choose
  `智能代码（Goose -> Aider）`, supply an existing workspace below
  `/var/home/charlie`, then approve it in Hub. Hub starts a bounded transient
  `hub-auto-<task-id>` user unit through `agent-goose-aider-router`; its state
  and tail log are visible on the task card. `仅规划（Goose）` never writes;
  `OpenCode（短会话）` and `Crush（小修复）` remain explicit legacy choices.
  Do not auto-chain a failed/finished task: inspect its log and create a new
  approved task for follow-up work.
- Button vocabulary is intentionally unified: Workbench top bar uses
  **派发任务** and **Codex 会话**; port labels use **Goose 诊断** and **Aider
  执行**. The old broken Hub tool-drawer panel was removed rather than retained
  as a second task surface.
- 2026-07-14 `:19888` also owns phone-friendly port navigation. Use
  `/ports` for the port manager and `/go/<key>` as short URLs so mobile users
  do not type long host:port addresses. Current keys include `wb`, `wins`,
  `c1`, `c2`, `c3`, `c4`, `c5`, `br`, `bw`, `op`, `hub`, `fgpt`, `term`, `n8n`,
  `app`, `tty`, `crush`, `aider`, `goose`, `guise`, and `ntfy`.
  `/go/crush` uses Crush WebTTY public port `17766`; `/go/aider` maps to the
  independent Aider WebTTY `127.0.0.1:7693` path `/tool/aider/`, and
  `/go/goose` plus `/go/guise` map to the independent Goose/Guise WebTTY
  `127.0.0.1:7694` path `/tool/guise/`. Do not point the Codex Aider/Guise
  buttons at Crush. `/go/br` opens `/browser`, the phone remote-control
  page for the real Fedora Chromium. `/go/bw` opens `/browsh`, the Browsh
  text-browser WebTTY panel. The legacy `/browser-tools` path is now an alias
  for `/browser`.
- 2026-07-14 `:19888` also owns phone-facing entry speed monitoring. Use
  `/speed` for the speed panel and `/api/speed` for JSON. The probe compares
  local, current phone-host, and DuckDNS routes and records total/TTFB timing,
  so slow opens can be classified as local service failure, public/DuckDNS/FRP
  path failure, or phone/browser-side rendering latency.
- 2026-07-14 phone island notification: `mobile-ai-speed-island.timer` runs
  `~/.local/bin/mobile-ai-speed-island-notify` every 5 minutes and sends ntfy
  alerts to `charlie-actions` only when `/api/speed` finds slow/down entries.
  `mobile-ai-speed-island-notify test` sends a manual test notification. This
  can appear in the phone dynamic-island/camera capsule only if the phone OS
  maps ntfy/system notifications into that UI; direct overlay integration
  requires ADB/phone-side service access.
- 2026-07-14 OnePlus/ColorOS root check: `~/.local/bin/mobile-ai-phone-island-root-tune test`
  connects to ADB `127.0.0.1:15555`, verifies Magisk root, backs up and enables
  OPlus `fluid_seeding_settings_service_switch_key`, replays ntfy background /
  notification AppOps, sends a test notification, and prints
  `fluid_seeding_notification`. On PKR110 / Android 16, root tuning makes ntfy
  reliable as a high-priority banner but does **not** add `io.heckel.ntfy` to
  `fluid_seeding_notification`; the setting remains limited to system-supported
  packages such as `com.android.incallui`, `com.coloros.oshare`, and alarm clock.
  Do not blindly forge this JSON. Direct camera-capsule integration needs a
  SeedlingSdk/FluidSeeding-supported app, LSPosed hook, or a custom Android app
  that matches ColorOS' private service contract.
- 2026-07-14 simulated island / super floating button path: use Workbench
  `/super` as the stable phone-side capsule UI and Tasker/ST action bus instead
  of trying to force third-party apps into ColorOS FluidSeeding. Generate phone
  URLs with `~/.local/bin/mobile-ai-super-urls`; default panel is
  `http://100.120.189.27:19888/super?device=w19900422`. Tasker/ST can call
  `GET /api/super/run?action=<action>&device=w19900422` directly, without
  cookies or custom headers. Current actions include `open-workbench`,
  `open-speed`, `open-codex1`, `open-codex4`, `open-codex5`, `open-hub`, `open-op`, `open-step-ui`,
  `step-task`, `speed-test`, `notify-test`, and `island-root-tune`.
- 2026-07-14 native Android super floating button APK: source lives in
  `~/.local/share/mobile-ai-super-button`, package
  `com.charlie.mobileaisuperbutton`, and rebuild/reinstall is
  `~/.local/bin/mobile-ai-super-button-build-install`. The signed APK is copied
  to `~/.local/share/phone-agent-web/mobile-ai-super-button.apk` and is
  downloadable from `http://100.120.189.27:9829/mobile-ai-super-button.apk`.
  As of 2026-07-19 the APK `MainActivity.BASE_URL` is
  `http://charlie1990.duckdns.org:19888` because the phone may be on 5G with
  NetBird but without the old Tailnet `100.120.189.27` route; do not regress it
  to a Tailnet-only URL for the floating notice path.
  It runs a foreground service and a `TYPE_APPLICATION_OVERLAY` capsule that
  calls Workbench `/api/super/run` actions. On Android 16 / OnePlus PKR110,
  plain `adb install` can hang over FRP ADB; use push to `/data/local/tmp` plus
  root `pm install --user 0 -r /data/local/tmp/mobile-ai-super-button.apk`.
  Root can grant overlay with `cmd appops set com.charlie.mobileaisuperbutton
  SYSTEM_ALERT_WINDOW allow`. Verification evidence should show
  `OverlayService isForeground=true` and a window with
  `ty=APPLICATION_OVERLAY appop=SYSTEM_ALERT_WINDOW`.
- 2026-07-14 AI Super Button v2 adds a right-side expanded panel with text
  search, AI dispatch, voice dispatch, launcher shortcuts, and old fixed action
  buttons. Keep complex logic in Workbench, not in the APK. The APK calls
  `POST /api/super/dispatch` and opens `open_url` when the backend returns one.
  Voice uses Android `RecognizerIntent`; if the phone has no speech recognizer
  or microphone permission, the text/search buttons remain the fallback.
- 2026-07-15 the native expanded capsule and its main activity both include
  **派发任务**. It calls Workbench `open-hub` and opens Hub `/projects`; it
  never dispatches agents directly. Task text sent through AI/voice dispatch
  still creates a `pending_approval` Hub task first.
- 2026-07-19 AI Super Button shell layout: when a meaningful notice arrives,
  keep the full floating notification capsule visible, with `AI`, notice text,
  dropdown `⌄`, and close `×`. Empty/default standby may use the compact
  `AI + badge + ⌄` button, but active workflow notices from `phone-flow` or
  `phone-shadow` must not shrink to a dot-only state because the user relies on
  the phone desktop strip for n8n/flow progress. The dropdown includes
  `打开面板`, `语音调度`, `超级面板`, `隐藏到下次通知`, `关闭悬浮服务`, and `收起菜单`.
  The strip polls `GET /api/super/notice` every 3s and also shows immediate
  action/dispatch feedback. This is the lightweight "dynamic island" substitute
  when ColorOS FluidSeeding is unavailable.
- 2026-07-19 AI Super Button notice robustness: the APK accepts
  `am start-foreground-service -a com.charlie.mobileaisuperbutton.SET_NOTICE -n
  com.charlie.mobileaisuperbutton/.OverlayService --es notice '<line>'` as an
  immediate update path. The `/api/super/notice` JSON read limit is 8192 chars;
  the old 1024-char limit truncated Workbench metadata, caused `JSONException`,
  and left stale reset text on the capsule.
- 2026-07-15 AI Super Button drag behavior: because the overlay uses
  `Gravity.TOP | Gravity.END`, horizontal `WindowManager.LayoutParams.x` is a
  right-edge offset. Finger moving right must subtract from `x`; finger moving
  left must add to `x`. Always clamp overlay `x/y` back inside display bounds
  after drag and after expand/collapse. The app main screen includes
  "重置悬浮按钮位置", and install helper starts the service with
  `com.charlie.mobileaisuperbutton.RESET_POSITION` so an off-screen capsule is
  recovered on reinstall/restart.
- Workbench v2 super APIs:
  `GET /api/super/launcher?q=<query>` returns quick launcher entries from
  `portLinks` and `superActions`; `GET /api/super/search?q=<query>` searches
  launcher entries, bounded runbook snippets, selected services, and phone app
  activities when ADB `127.0.0.1:15555` is reachable; `POST
  /api/super/dispatch` accepts JSON `{"text":"..."}` and rule-routes opening
  Codex/OpenCode/Workbench, status checks, search, or Step UI point-and-order
  tasks. Payment/order/destructive flows must still stop at confirmation.
  `GET /api/super/notice` returns the compact line rendered in the APK's right
  notification strip.
- 2026-07-15 Super dispatch app-search rule: phone app queries must check local
  app index/known aliases before AI/Step fallback. Known aliases cover common
  Chinese app names such as 微信、支付宝、美团、高德、抖音、小红书、QQ、Tasker,
  MacroDroid, and AidLux. Commands like `查微信` should return
  `kind=local/action=search-phone-apps`; commands like `打开微信` should try
  `monkey -p <package> ...` first when ADB is reachable. Keep Codex/OpenCode/
  Workbench/Step/速度/通知 reserved so they route to Workbench immediately and
  are not delayed by ADB app listing.
- If APK build succeeds but install fails with ADB `device offline`,
  `Connection refused`, or LAN `No route to host`, do not rebuild repeatedly.
  The build artifact is already available at
  `http://100.120.189.27:9829/mobile-ai-super-button.apk`. The deterministic
  install helper is `~/.local/bin/mobile-ai-super-button-install-phone`; it
  tries ADB `127.0.0.1:15555`, LAN ADB `192.168.123.22:5555`, then falls back
  to the AidLux phone-agent/root-helper queue from `phone-agent.md`. For the
  current OnePlus PKR110 NetBird ADB path, set
  `ADB_SERIAL=100.87.37.3:5555 ~/.local/bin/mobile-ai-super-button-build-install`
  so the APK is rebuilt, copied to `phone-agent-web`, overwritten on the phone,
  permissions are restored by root, and `OverlayService` is restarted
  immediately. Verify fallback completion with `phone-status-read | tail -n 80`.
- 2026-07-14 Step UI / GELab-Zero point-and-order path: `open-step-ui` starts
  `gelab-zero.service` and opens the Streamlit panel on `:33503`.
  `step-task` stores the latest natural-language phone task at
  `~/.local/state/mobile-ai-super/latest-step-task.txt` and starts Step UI.
  Use this for cross-app or screen-understanding tasks such as ordering/search
  flows. For exact known coordinates or simple shell actions, prefer
  `phone-connect`/Tasker actions because GELab-Zero costs more tokens and is
  less deterministic. Never let GUI agents pay/order directly; stop on the
  confirmation/payment page and let the user confirm manually.
- `mobile-ai-browser.service` loads extension code from the original Chromium
  profile with `--load-extension=$HOME/.config/chromium/Default/Extensions/...`
  but keeps runtime data in `~/.config/mobile-ai-chromium`. This avoids
  corrupting the user's normal Chromium profile. Extension settings/login state
  may still require one-time setup in the mobile browser profile.
- If `http://charlie1990.duckdns.org:19888/` fails with
  `ERR_EMPTY_RESPONSE` or cannot connect while `127.0.0.1:19888` works, check
  both layers: router runtime NAT must contain `iptables -t nat -S | grep
  19888`, and Fedora firewalld must include `19888/tcp`. On 2026-07-14 the
  router nvram rule existed but Fedora firewalld was missing `19888/tcp`; fixed
  with `sudo firewall-cmd --add-port=19888/tcp` and
  `sudo firewall-cmd --permanent --add-port=19888/tcp`.
- 2026-07-19 phone `/codex` slow/blank trap: if the user opens
  `http://charlie1990.duckdns.org:19888/codex`, do not treat it as a router
  outage until phone-side ADB probes confirm route timing. Failure was an app
  bug: `/codex?device=w19900422` set the cookie then redirected to `/codex`,
  which had no route; `/api/speed` also probed too many ports with 5.5s
  timeouts and could exceed a mobile page timeout. Fixed in
  `~/.local/bin/mobile-ai-workbench` by aliasing `/codex`/`/codex/` to the
  Workbench page and bounding `/api/speed` with
  `MOBILE_AI_SPEED_KEYS`, `MOBILE_AI_SPEED_PROBE_TIMEOUT_MS=1800`, and
  `MOBILE_AI_SPEED_PROBE_CONCURRENCY=24`. Follow-up fix: Workbench shell
  `wb:19888` is now included in `~/.local/bin/phone-webtty-route-probe`, and
  `/codex` plus `/go/c1`-`/go/c8` use phone-measured `phone_best` routes from
  `~/.local/state/phone-webtty-route-probe/latest.json`; WebSocket checks are
  still required for WebTTY reachability, but route latency is ranked by
  `/status` + first page load, not by the long-lived WS max-time. Verify from
  the phone with
  `~/.local/bin/adb-record --tag webtty-mobile-postfix -- -s 127.0.0.1:15555 shell 'curl -L -c /data/local/tmp/maw-cookie.txt -b /data/local/tmp/maw-cookie.txt -o /dev/null -w "%{http_code} %{time_total}\n" http://charlie1990.duckdns.org:19888/codex?device=w19900422; curl -H "x-device-code: w19900422" -o /dev/null -w "%{http_code} %{time_total}\n" http://charlie1990.duckdns.org:19888/api/speed'`.
- `http://100.120.189.27:8089/` and `/user/login` no longer expect an
  interactive Appsmith login for daily use. Caddy inside the Appsmith container
  now redirects those entry paths to `http://100.120.189.27:9800/projects`
  so the control surface opens directly.
- Do not restore the old root/login page unless the goal is specifically to
  administer Appsmith itself. For routine operations, `8089` is now just a
  stable vanity entry to the Hub project/control page.

## API Contract

- Mobile AI Workbench status: `GET http://127.0.0.1:19888/api/status`
- Mobile AI Workbench network panel: `GET http://127.0.0.1:19888/api/network`
- Mobile AI Workbench speed panel:
  `GET http://127.0.0.1:19888/speed`
- Mobile AI Workbench speed API:
  `GET http://127.0.0.1:19888/api/speed`
- Mobile AI Workbench port registry: `GET http://127.0.0.1:19888/api/ports`

## 2026-07-19 Codex Kasm 手机视图与 C7/C8 限流判定

- `/kasm` 是 Kasm 内 Linux Codex desktop-client 的手机入口；页面默认手机紧凑模式，只保留顶部 `工作台 / 连接 / 竖屏 / 账号栏 / 刷新`，账号启动行用 `账号栏` 展开，避免遮住 VNC 画面。
- 2026-07-20 Kasm interaction rule: do not hide the KasmVNC control bar. The
  Workbench `/kasm` page exposes `工具`, `键盘`, and `输入`; the input panel
  writes through KasmVNC `#noVNC_keyboardinput` into the currently focused
  remote Cursor/Codex field, while `工具` preserves native reconnect, keyboard,
  clipboard, and session controls. A 20-second monitor only reconnects when
  KasmVNC reports a disconnected/failed state; it must never reload a healthy
  iframe and interrupt mobile IME composition.
- 2026-07-20 mobile native-input rule: `/kasm` must default to
  `/kasm-native`, the top-level KasmVNC page, rather than embedding KasmVNC in
  the Workbench iframe. The nested dashboard is available only at
  `/kasm?shell=1`. Native KasmVNC keeps `enable_ime=true`,
  `virtual_keyboard_visible=true`, a visible control bar, and a focusable
  `#noVNC_keyboardinput`. Its injected `visualViewport` listener keeps
  `#noVNC_container` at the post-keyboard visible height so the soft keyboard
  does not cover the remote canvas. This is the best browser path for the
  phone IME and avoids the parent/iframe focus chain. Apache Guacamole is not a replacement
  for this requirement because it is also a browser remote-display canvas. A
  truly automatic keyboard when tapping an arbitrary remote app text field
  requires a native mobile VNC/RDP client; Web remoting cannot inspect remote
  accessibility focus.
- `POST /api/kasm/mobile-fit` 会在容器内执行 `xrandr --fb 720x1280` 并用 `wmctrl` 把 Codex GUI 窗口调整到 `720x1280`；桌面回退可传 `{"mode":"desktop"}` 得到 `1024x768`。
- `/kasm-vnc/` 代理会向 KasmVNC 根 HTML 注入 `maw-kasm-phone-css/js`，用于手机隐藏 KasmVNC 侧边工具条；Workbench 自己的 `连接` 按钮仍可点击隐藏的 `noVNC_connect_button_2`。
- C7/C8 判定：如果 `/quota.json` 中 Sub2API API key/platform 剩余额度为正，但 upstream OAuth account 存在 `rate_limited_at` / `rate_limit_reset_at` 且 `/v1/responses` 返回 `503 no available accounts`，分类为“上游限流”，不是本地余额耗尽。
- 2026-07-19 证据：C7 `codex7-sub2api` 剩 `768.934964/1000`，上游 `C7 day Plus` reset `2026-07-25T06:11:41Z`；C8 `codex8-sub2api` 剩 `841.981256/1000`，上游 `C8 day Plus` reset `2026-07-25T05:56:09Z`；两者 `/v1/models=200`、`/v1/responses=503`。
- Mobile AI Workbench short URL: `GET http://127.0.0.1:19888/go/c1`
- Mobile AI Workbench Codex multi-window page:
  `GET http://127.0.0.1:19888/windows`
- Mobile AI Workbench Codex multi-window API:
  `GET http://127.0.0.1:19888/api/windows`; `POST /api/windows/action` with
  JSON `{"action":"create","account":"1","title":"任务名"}` or
  `{"action":"start|kill","id":"win-..."}`
- Mobile AI Super launcher: `GET http://127.0.0.1:19888/api/super/launcher?q=codex`
- Mobile AI Super search: `GET http://127.0.0.1:19888/api/super/search?q=codex`
- Mobile AI Super dispatch:
  `POST http://127.0.0.1:19888/api/super/dispatch` with JSON `{"text":"打开 codex5"}`
- Mobile AI Super floating notice:
  `GET http://127.0.0.1:19888/api/super/notice`
- Mobile AI Workbench browser status:
  `GET http://127.0.0.1:19888/api/browser`
- Mobile AI Workbench browser UI:
  `GET http://127.0.0.1:19888/browser`
- Mobile AI Workbench browser gesture support:
  `/browser` is screenshot-driven CDP control. On touch devices, one-finger
  drag over the screenshot sends `/api/browser/scroll`; two-finger pinch sends
  `/api/browser/zoom`; mouse/trackpad wheel also maps to CDP scroll. Keep this
  behavior in the screenshot layer so it works from iOS Safari without needing
  a real remote desktop canvas.
- Mobile AI Workbench Browsh status:
  `GET http://127.0.0.1:19888/api/browsh`
- Mobile AI Workbench Browsh UI:
  `GET http://127.0.0.1:19888/browsh`
- Mobile AI Workbench Browsh ttyd proxy:
  `GET http://127.0.0.1:19888/browsh-tty/`
- Mobile AI Workbench Browsh goto:
  `POST http://127.0.0.1:19888/api/browsh/goto` with JSON `{"url":"https://example.com"}`
- Mobile AI Workbench Browsh restart:
  `POST http://127.0.0.1:19888/api/browsh/restart`
- Browser CDP endpoints through Workbench:
  `GET /api/browser/tabs`, `GET /api/browser/screenshot?tabId=<id>`,
  `POST /api/browser/new`, `POST /api/browser/goto`,
  `POST /api/browser/click`, `POST /api/browser/type`,
  `POST /api/browser/key`, `POST /api/browser/scroll`,
  `POST /api/browser/zoom`, `POST /api/browser/reload`,
  `GET /api/browser/extensions`
- Hub snapshot: `GET http://127.0.0.1:9800/api/workspace/snapshot`
- Semantic command: `POST http://127.0.0.1:9800/api/workspace/command`
- Project control snapshot: `GET http://127.0.0.1:9800/api/projects/control`
- Project task create: `POST http://127.0.0.1:9800/api/projects/tasks`
- Project task approve/dispatch: `POST http://127.0.0.1:9800/api/projects/tasks/{task_id}/approve`
- Project task update: `POST http://127.0.0.1:9800/api/projects/tasks/{task_id}/update`
- Project task runner log: `GET http://127.0.0.1:9800/api/projects/tasks/{task_id}/log`
- Project milestone update: `POST http://127.0.0.1:9800/api/projects/{project_id}/milestones/{milestone_id}`
- Appsmith health: `GET http://127.0.0.1:9800/api/appsmith/status`
- n8n health: `GET http://127.0.0.1:9800/api/n8n/status`
- OP handoff: `POST http://127.0.0.1:9800/api/workflow/todos/{task_id}/op`
- FastGPT export: `POST http://127.0.0.1:9800/api/workflow/todos/{task_id}/fastgpt`
- Zulip send: `POST http://127.0.0.1:9800/api/workflow/todos/{task_id}/zulip`

## Appsmith Datasource

Current state: the generated Appsmith catalog entries are shortcut pages with a
`BUTTON_WIDGET` calling `navigateTo(...)`. The Appsmith database currently has
no Hub REST datasource or action queries. `AI 任务控制台` is now the first
functional wrapper: it provides an in-page guide and embeds the Hub Projects
control surface. Treat Hub as the API owner until native Appsmith REST queries
are provisioned.

Target state: replace the embedded Hub frame with native Appsmith REST queries
backed by the Hub REST datasource below. Keep the shortcut catalog for external
tools, but do not describe it as the task control plane.

In self-hosted Appsmith, connect Hub as a REST datasource:

- Base URL: `http://host.docker.internal:9800`
- Health query: `GET /api/workspace/snapshot`
- Command query: `POST /api/workspace/command`

The Appsmith compose file includes:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## Verify

```bash
systemctl --user is-active appsmith hub-api n8n hub-workspace-snapshot.timer
systemctl --user is-active mobile-ai-workbench.service mobile-ai-browser.service mobile-ai-browsh-backend.service mobile-ai-browsh-gate.service mobile-ai-speed-island.timer
curl -s --noproxy '*' -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/status | jq '.accounts[] | {id,name,gate,backend}'
curl -s --noproxy '*' -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/speed | jq '{summary,advice}'
curl -s --noproxy '*' -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/ports | jq '.[].short'
curl -I --noproxy '*' -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/go/c5
curl -s --noproxy '*' 'http://127.0.0.1:19888/api/super/search?device=w19900422&q=codex' | jq '{ok,q,count:(.results|length)}'
curl -s --noproxy '*' -H 'Content-Type: application/json' -d '{"text":"打开 codex5"}' 'http://127.0.0.1:19888/api/super/dispatch?device=w19900422' | jq '{ok,plan,open_url}'
curl -s --noproxy '*' -H 'Content-Type: application/json' -d '{"text":"点单 打开美团搜索咖啡 停在确认页"}' 'http://127.0.0.1:19888/api/super/dispatch?device=w19900422' | jq '{ok,plan,result:{ok:.result.ok,task_saved:.result.task_saved}}'
curl -s --noproxy '*' 'http://127.0.0.1:19888/api/super/notice?device=w19900422' | jq '{ok,line,services}'
curl -s --noproxy '*' http://127.0.0.1:9224/json/version | jq '{Browser}'
curl -s --noproxy '*' -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/browser | jq '{state,service,extensions}'
curl -s --noproxy '*' -H 'X-Device-Code: w19900422' -H 'Content-Type: application/json' -d '{"direction":"in"}' http://127.0.0.1:19888/api/browser/zoom | jq '{ok,direction}'
curl -fsS --noproxy '*' -H 'X-Device-Code: w19900422' -o /tmp/mobile-browser.jpg http://127.0.0.1:19888/api/browser/screenshot
curl -s --noproxy '*' -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/browsh | jq
curl -s --noproxy '*' -H 'X-Device-Code: w19900422' -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' http://127.0.0.1:19888/api/browsh/goto | jq
curl -fsS --noproxy '*' -H 'X-Device-Code: w19900422' -o /tmp/browsh-tty.html http://127.0.0.1:19888/browsh-tty/
curl -fsS --noproxy '*' -H 'X-Device-Code: w19900422' -o /tmp/public-browsh.html http://charlie1990.duckdns.org:19888/browsh
curl -s --noproxy '*' http://127.0.0.1:9800/api/appsmith/status | jq
curl -s --noproxy '*' http://127.0.0.1:9800/api/n8n/status | jq
curl -s --noproxy '*' http://127.0.0.1:9800/api/workspace/snapshot | jq '.service_health[] | {name, ok}'
```

## Rules

- Appsmith is the intended visual window, but until the REST-backed control app is provisioned, `9800/workspace` and `9800/projects` are the functional control surfaces. Do not treat `/applications` shortcuts as an API-backed dashboard.
- Hub owns state, registry, semantic command parsing, and safe local APIs.
- n8n owns multi-step workflows and webhook automation.
- OP owns execution. Do not make FastGPT/Dify write files or restart services directly.
- Automatic execution enters through `agent-dispatch`: implementation/long tasks prefer OP, runtime diagnosis/review prefers Crush, and a single failed handoff produces a Codex read-only review request through `ai-a2a`.
- Status/notification layers such as `hermes-actions` must be read-only. They
  may read `~/.local/state/agent-dispatch/tasks/*.json`, but must not call
  `agent-dispatch watch/status --auto-handoff` or resurrect old failed tasks.
- The dispatcher contract requires a final status, changed scope, and verification evidence. The Hub Projects snapshot reads live dispatch state from `~/.local/state/agent-dispatch/tasks/` so the visual board remains the status source.
- Plane/Huly remain project data systems, not the operations console.
- `9800/projects` is the lightweight project command page exposed from Codex WebTTY.
  It stores approval/progress/outlook state in
  `~/.local/state/hub/project-control.json`. Night tasks are queued as
  pending approval first; pressing approve dispatches through `agent-dispatch`
  to OP/Crush/auto. Do not enable an unapproved night auto-execution loop.
- The project command page source is `~/hub/static/projects.html`; the API and
  task workflow live in `~/hub/hub-api.py`. The page includes project progress,
  milestone controls, priority/due-date focus, a five-lane execution board,
  blocker tracking, acceptance criteria, and completion evidence.
- Project task states are `pending_approval`, `queued`, `delegated`,
  `in_progress`, `blocked`, `review`, `done`, `cancelled`, and
  `dispatch_failed`. A task with acceptance criteria cannot enter `done`
  without non-empty completion evidence. A task cannot enter `blocked` without
  a blocker reason. Approval is idempotency-guarded and only accepts tasks in
  `pending_approval` or `dispatch_failed`.
- Project control writes use an atomic temporary-file replacement. Built-in
  project milestone changes are persisted as overrides in
  `~/.local/state/hub/projects.json`; do not edit `PROJECTS_DEF` merely to
  advance a milestone.
- Codex WebTTY gates proxy the embedded project/workspace routes through Hub:
  `/projects`, `/workspace`, `/go/*`, `/static/*`, `/api/projects/*`,
  `/api/workspace/*`, `/api/workflow/*`, and `/api/ops/*`. They also route
  WebSocket upgrades for `/ws/status` and `/ws/dialogue` to Hub `:9800`.
- Hub WebSocket endpoint parameters in `~/hub/hub-api.py` must remain typed as
  `WebSocket`. Untyped parameters are treated as missing request parameters by
  current FastAPI and cause HTTP 403 during the WebSocket handshake, leaving
  workspace realtime status/dialogue functions incomplete.

## Project Page Verify

```bash
python3 -m py_compile ~/hub/hub-api.py
node -e "const fs=require('fs');const h=fs.readFileSync('$HOME/hub/static/projects.html','utf8');new Function(h.match(/<script>([\\s\\S]*?)<\\/script>/)[1])"
systemctl --user restart hub-api.service
curl --noproxy '*' -fsS http://127.0.0.1:9800/api/projects/control | jq '{summary, projects:(.projects|length), tasks:(.tasks|length)}'
curl --noproxy '*' -fsS http://127.0.0.1:9800/projects | rg '项目控制台|执行看板|完成定义'
```

## Mattermost AI intake operations (2026-07-18)

Mattermost is the phone/chat/file intake layer for the unified control plane.
Use it for quick notes, screenshots, documents, and human approval context;
Hub remains the approval/dispatch owner.

Default path:

```text
Mattermost ai-inbox/ai-images/ai-docs/ai-review -> mattermost-ai-inbox poller -> Hub pending_approval -> approved dispatch -> Mattermost ai-tasks receipt
```

Operations helper:

```bash
mattermost-ai-ops status
mattermost-ai-ops poll-once
mattermost-ai-ops test-task
mattermost-ai-ops phone-verify
```

Do not put `ai-tasks` in `MATTERMOST_WATCH_CHANNELS`; it is an output channel.
See `~/.ai-context/runbooks/mattermost.md` for the detailed loop guard and
channel classification rules.

## Kasm as primary phone GUI desktop backend

Date: 2026-07-19

Decision: use PC-side KasmVNC as the primary GUI desktop path for phone use.
Haven stays as backup SSH/VNC/RDP client and should not be treated as the main
local desktop engine.

Active service:

```text
kasm-cursor-webtop.service
container: kasm-cursor-webtop
local backend: https://127.0.0.1:19970
Workbench entry: http://<fedora>:19888/kasm?device=w19900422
Short URL: /go/kasm and /go/cursor
```

Use the Workbench proxy as the preferred phone path because it reuses the
existing protected Workbench entry and avoids exposing/directly depending on
port `19970` from the phone:

```text
LAN:     http://192.168.123.71:19888/kasm?device=w19900422
NetBird: http://100.87.238.153:19888/kasm?device=w19900422
```

Mobile AI Workbench changes:

- top quick bar includes `Kasm桌面`
- `/go/kasm` and `/go/cursor` redirect to `/kasm`
- `/api/kasm/status` reports service/container/probe and Workbench URL
- Kasm HTTP proxy now guards against duplicate response headers on upstream
  errors, preventing `ERR_HTTP_HEADERS_SENT` crashes
- Super action list includes `open-kasm`

Healthcheck:

```text
~/.local/bin/kasm-cursor-webtop-healthcheck
~/.config/systemd/user/kasm-cursor-webtop-healthcheck.service
~/.config/systemd/user/kasm-cursor-webtop-healthcheck.timer
~/.local/state/kasm-cursor-webtop/health.log
```

The timer runs every 2 minutes, checks `kasm-cursor-webtop.service` plus local
HTTPS probe, restarts the service if unhealthy, and sends ntfy to
`charlie-actions` on recovery/failure.

Verification:

```sh
systemctl --user is-active kasm-cursor-webtop.service mobile-ai-workbench.service
systemctl --user is-active kasm-cursor-webtop-healthcheck.timer
curl -sS -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/kasm/status | jq
adb-record --tag phone-kasm-page -- -s <phone> shell 'su -c "curl -sS -L -m 10 -w '\''HTTP=%{http_code} SIZE=%{size_download}\\n'\'' -o /sdcard/Download/kasm-page.html -H '\''X-Device-Code: w19900422'\'' '\''http://192.168.123.71:19888/kasm?device=w19900422'\''"'
```

Known note: direct `https://192.168.123.71:19970` may be blocked from phone by
host/container/firewall path. Prefer Workbench `/kasm` proxy unless there is a
specific reason to expose `19970` directly.

## Apache Guacamole phone remote gateway

Date: 2026-07-19

Decision: user requested the `guacamole`方案 after Kasm. Deploy Apache
Guacamole as a PC-side SSH/VNC/RDP connection gateway; phone uses Workbench web
proxy, not Haven local desktop.

Services/files:

```text
~/.local/bin/guacamole-stack-run
~/.local/bin/guacamole-seed-all-codex-ssh-connections-from-haven-key
~/.config/systemd/user/guacamole-stack.service
~/.local/share/guacamole-stack/
~/.config/guacamole-stack.env          # mode 0600; DB password only
```

Containers/images:

```text
guacamole-postgres  docker.io/library/postgres:16-alpine
guacamole-guacd     docker.io/guacamole/guacd:1.6.0
guacamole-web       docker.io/guacamole/guacamole:1.6.0
```

Local backend is bound to loopback only:

```text
http://127.0.0.1:19972/guacamole/
```

Workbench proxy is the preferred phone path:

```text
LAN:     http://192.168.123.71:19888/go/guac?device=w19900422
NetBird: http://100.87.238.153:19888/go/guac?device=w19900422
```

Workbench changes:

- `portLinks` includes `guac`
- top quick bar includes `Guac网关`
- `/go/guac` redirects to `/guac`
- `/guac` redirects to proxied `/guacamole/`
- `/guacamole/*` HTTP and WebSocket upgrade proxy to `127.0.0.1:19972`
- Super action list includes `open-guac`
- 2026-07-19 direct Guacamole connection shortcuts:
  - `/go/guac-term` -> Fedora Terminal SSH 2223
  - `/go/guac-op` -> OpenCode SSH 2224
  - `/go/guac-c1` / `/go/guac-codex1` / `/go/guac-codex` -> Codex 1 SSH 2225
  - `/go/guac-c2` -> Codex 2 SSH 2226
  - `/go/guac-c3` -> Codex 3 SSH 2229
  - `/go/guac-smart` -> Codex Smart SSH 2230
  - `/go/guac-c4`..`/go/guac-c8` -> Codex 4..8 SSH 2231..2235
  - `/go/guac-vnc` -> Fedora WayVNC 5900

Auth:

- Default `guacadmin/guacadmin` was changed immediately and verified invalid.
- Current admin username is `guacadmin`; do not write the password into runbooks.
- If reset is needed, use Guacamole API from local host after retrieving the
  intended password from the user or a secure local secret source.

Seeded connections:

```text
Fedora Terminal SSH · LAN 2223   ssh  192.168.123.71:2223  user charlie
OpenCode SSH · LAN 2224          ssh  192.168.123.71:2224  user charlie
Codex 1 SSH · LAN 2225           ssh  192.168.123.71:2225  user charlie
Codex 2 SSH · LAN 2226           ssh  192.168.123.71:2226  user charlie
Codex 3 SSH · LAN 2229           ssh  192.168.123.71:2229  user charlie
Codex Smart SSH · LAN 2230       ssh  192.168.123.71:2230  user charlie
Codex 4 SSH · LAN 2231           ssh  192.168.123.71:2231  user charlie
Codex 5 SSH · LAN 2232           ssh  192.168.123.71:2232  user charlie
Codex 6 SSH · LAN 2233           ssh  192.168.123.71:2233  user charlie
Codex 7 SSH · LAN 2234           ssh  192.168.123.71:2234  user charlie
Codex 8 SSH · LAN 2235           ssh  192.168.123.71:2235  user charlie
Fedora WayVNC · LAN 5900         vnc  192.168.123.71:5900
```

SSH connections store Guacamole's `private-key` parameter from
`~/.ssh/mosh_codex_haven` with public fingerprint
`SHA256:ZOnip/sVHlWQQqDZrs4OFd1gqjWpIn7ndLqntH5PAl0`. Never write the private
key body, Guacamole admin password, or DB password into runbooks, logs, ntfy, or
final answers. Non-secret SSH parameters currently set on every SSH connection:
`terminal-type=xterm-256color`, `server-alive-interval=30`,
`enable-sftp=false`, `font-size=12`, `color-scheme=green-black`.

If Guacamole connections disappear after DB rebuild/migration, restore all
account connections and the SSH private-key parameters with:

```sh
~/.local/bin/guacamole-seed-all-codex-ssh-connections-from-haven-key
```

Healthcheck:

```text
~/.local/bin/guacamole-stack-healthcheck
~/.config/systemd/user/guacamole-stack-healthcheck.service
~/.config/systemd/user/guacamole-stack-healthcheck.timer
~/.local/state/guacamole-stack/health.log
```

The timer runs every 2 minutes, checks `guacamole-stack.service`, local HTTP
`/guacamole/`, and all three containers, restarts the stack if unhealthy, and
sends ntfy to `charlie-actions` on recovery/failure.

Verification:

```sh
systemctl --user is-active guacamole-stack.service guacamole-stack-healthcheck.timer mobile-ai-workbench.service
curl --noproxy '*' -I http://127.0.0.1:19972/guacamole/
curl -sS -L -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/go/guac?device=w19900422 | head
adb-record --tag phone-guacamole-workbench-probe -- -s <phone> shell 'su -c "curl -sS -L -m 12 -w '\''HTTP=%{http_code} SIZE=%{size_download}\\n'\'' -o /sdcard/Download/guacamole-page.html -H '\''X-Device-Code: w19900422'\'' '\''http://192.168.123.71:19888/go/guac?device=w19900422'\''"'
```

Verified on 2026-07-19:

```text
phone /go/guac: HTTP=200 SIZE=2811
old guacadmin/guacadmin login: 403
new admin login: 200
SSH key auth accepted on ports: 2223, 2224, 2225, 2226, 2229, 2230, 2231,
2232, 2233, 2234, 2235
Guacamole DB contains 11 SSH connections with private-key length 419 redacted
and one VNC connection
Workbench direct shortcut `/go/guac-c1` redirects to `/guacamole/#/client/...`
Phone NetBird path `/go/guac-c1`: HTTP=200 SIZE=2811
```

## 2026-07-19 Kasm/Cursor Desktop phone blank repair

Symptoms:
- Phone `/kasm` or Cursor GUI page showed KasmVNC Connect/menu or blank instead of Cursor desktop.
- Local Kasm backend `https://127.0.0.1:19970/` was healthy and Cursor processes/windows existed inside `kasm-cursor-webtop`.
- Phone route classification mattered: on PKR110 5G, `100.87.238.153:19888` could time out while `charlie1990.duckdns.org:19888` was reachable.

Root cause:
- Workbench proxied Kasm under `/kasm-vnc`, but KasmVNC `path=websockify` makes the browser open root `/websockify`.
- Behind the Workbench prefix, the iframe must use `path=kasm-vnc/websockify`; otherwise the noVNC WebSocket never reaches the Kasm proxy.

Fix in `~/.local/bin/mobile-ai-workbench`:
- `/kasm` iframe params include `autoconnect=true`, `resize=scale`, `path=kasm-vnc/websockify`, and a cache-buster `r=<Date.now()>`.
- Workbench accepts both `/kasm-vnc/websockify` and legacy `/websockify` for Kasm WebSocket Upgrade.
- Kasm proxy handles socket `error` on both sides so bad WS probes do not crash `mobile-ai-workbench.service`.
- Kasm HTML/JS/CSS proxy responses set `cache-control: no-store` for phone cache recovery.

Verification commands:
```bash
node --check ~/.local/bin/mobile-ai-workbench
systemctl --user restart mobile-ai-workbench.service
python3 - <<'PY'
import websocket
for url in ['ws://127.0.0.1:19888/kasm-vnc/websockify','ws://127.0.0.1:19888/websockify']:
    ws=websocket.create_connection(url, timeout=5, header=['Cookie: mobile_ai_workbench_device=w19900422'], subprotocols=['binary','base64'])
    print(url, ws.getstatus(), ws.subprotocol)
    ws.close()
PY
```
Phone evidence: `adb` opened `http://charlie1990.duckdns.org:19888/kasm?device=w19900422`; screenshot `~/.local/state/phone-kasm-duck-final-6s-20260719184821.png` showed the Cursor login window inside Kasm.

## 2026-07-19 Kasm Cursor/Codex eight-account setup

Kasm/Cursor desktop now has eight account profiles mapped to Codex C1-C8:

- Cursor profile/user-data: `/home/kasm-user/.local/share/kasm-cursor-webtop/c<N>/user-data`
- Cursor extensions: `/home/kasm-user/.local/share/kasm-cursor-webtop/c<N>/extensions`
- Cursor workspace: `/home/kasm-user/.local/share/kasm-cursor-webtop/cursor-workspaces/c<N>`
- Kasm-private Codex home copy: `/home/kasm-user/.local/share/kasm-cursor-webtop/codex-homes/c<N>`
- Cursor process env includes `CODEX_ACCOUNT=C<N>` and `CODEX_HOME=.../codex-homes/c<N>` when launched through `/home/kasm-user/.local/share/kasm-cursor-webtop/bin/cursor-account`.

Host-side source of truth remains `~/.codex`, `~/.codex-2` ... `~/.codex-8`. Do not chmod those source homes for container access. Instead sync the minimal Kasm-private copies with:

```bash
~/.local/bin/kasm-codex-home-sync
```

The sync copies only `auth.json`, `config.toml`, `AGENTS.md`, and `skills`, then sets the Kasm copy back to the rootless-container mapped `kasm-user` ownership with private permissions. Run it after any Codex account rotation/rebind affecting C1-C8.

Workbench `/kasm` exposes:

- 8 visible `Cursor GUI` buttons: C1-C8 with labels.
- 8 visible `Codex TTY` buttons: C1-C8 with labels.
- `启动全部8个` button using `/api/kasm/cursor/start-all`, implemented as background trigger so the phone request does not wait for all Electron windows.
- `/api/kasm/cursor/status` uses one `podman top` scan, not eight sequential `podman exec`, to avoid timeouts under load.

Operational note: keep only default C5 auto-open on Kasm startup. Launching all eight Cursor/Electron windows is supported manually but can temporarily load or restart the Kasm container on small resource budgets; prefer starting only the needed accounts from the phone grid.

Verification:

```bash
node --check ~/.local/bin/mobile-ai-workbench
bash -n ~/.local/share/kasm-cursor-webtop/custom_startup.sh
bash -n ~/.local/bin/kasm-codex-home-sync
curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/kasm/cursor/status | jq '{running,accounts}'
podman exec kasm-cursor-webtop bash -lc 'for i in 1 2 3 4 5 6 7 8; do d=/home/kasm-user/.local/share/kasm-cursor-webtop/codex-homes/c$i; [ -r "$d/auth.json" ] && [ -r "$d/config.toml" ] && echo C$i-ok || echo C$i-bad; done'
```

Phone evidence: `~/.local/state/phone-kasm-eight-fixed-20260719191429.png` shows all C1-C8 Cursor and Codex buttons visible in the mobile `/kasm` grid.

## 2026-07-19 Workbench 19888 phone `ERR_NETWORK_CHANGED` / route confusion

Symptoms:
- Android Chrome reported `ERR_NETWORK_CHANGED` or 19888 disconnected.
- Fedora-side `mobile-ai-workbench.service` and `:19888` listener were healthy.
- PKR110 phone-side curl showed only DuckDNS was reachable, while NetBird/LAN timed out.
- `phone-webtty-route-probe/latest.json` was stale or generated from the tablet `192.168.123.241:5555`, which could make Workbench smart links choose LAN/NetBird routes unavailable to PKR110.

Fixes:
- Force `phone-webtty-route-probe.service` back to PKR110 serial `127.0.0.1:15555` via `~/.config/systemd/user/phone-webtty-route-probe.service.d/10-phone-pkr110.conf`; disable the old auto-serial drop-in.
- Patch `~/.local/bin/phone-webtty-route-probe` so `PHONE_WEBTTY_SERIALS` prefers `127.0.0.1:15555` and skips C1-C8 probes for a route when `wb:19888` is unreachable. This prevents LAN/NetBird timeouts from stalling the timer.
- Keep `/api/status` as the full Workbench status endpoint, but make `/status` a lightweight health check returning immediately. Phone route probe and server route-best should use `/status` for Workbench health.

Verification:
```bash
systemctl --user cat phone-webtty-route-probe.service
~/.local/bin/phone-webtty-route-probe 127.0.0.1:15555
jq '.generated_at,.serial,.best[] | select(.short=="wb")' ~/.local/state/phone-webtty-route-probe/latest.json
adb -s 127.0.0.1:15555 shell "curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code} %{time_total}\n' -H 'X-Device-Code: w19900422' http://charlie1990.duckdns.org:19888/status"
```
Expected for PKR110 on current 5G path: `wb` best is DuckDNS `charlie1990.duckdns.org:19888`; NetBird/LAN may be down and must not be chosen.

- 2026-07-19 Kasm Codex GUI clarification: user clarified the earlier “Cursor GUI” wording was a mouth slip; Kasm primary row must be **Codex GUI**, not Cursor. The default Kasm startup now launches ChatGPT/Codex web GUI C5 at `https://chatgpt.com/codex/` through isolated browser profile `/home/kasm-user/.local/share/kasm-cursor-webtop/codex-gui-profiles/c<N>`. Workbench `/kasm` exposes C1-C8 `data-codex-gui` buttons backed by `/api/kasm/codex-gui/start|start-all|status`; `Codex TTY` remains the secondary row. Keep Cursor launchers only as legacy desktop entries. The Kasm container cannot use host proxy `127.0.0.1:7890`; Codex GUI Chrome must use `--proxy-server=http://host.containers.internal:7890` and clear stale `SingletonLock/SingletonSocket/SingletonCookie` before launch after container restarts. Verify with `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/kasm/codex-gui/status` and `DISPLAY=:1 wmctrl -l -G` inside `kasm-cursor-webtop`.

- 2026-07-19 Official ChatGPT/Codex Desktop App route: user explicitly wants the official OpenAI GUI app, not Cursor, not `https://chatgpt.com/codex/`, and not the local `/codex-desktop` shell. Official docs currently say the new ChatGPT desktop app contains Chat/Work/Codex on macOS and Windows; Codex is not selectable on web/mobile except supported Remote-tab access from the ChatGPT mobile app. Fedora/Kasm cannot run this app natively. The local implementation therefore runs the official Windows package `OpenAI.Codex` on `WIN-S2D8GP89FU1` and displays it through Guacamole/RDP. Workbench entry is `http://<fedora>:19888/official-codex-app?device=w19900422`; direct Guacamole client is `/guacamole/#/client/MTMAYwBwb3N0Z3Jlc3Fs` for connection `Official ChatGPT/Codex Desktop · Windows RDP` (id `13`). Kasm default launcher is `/home/kasm-user/.local/share/kasm-cursor-webtop/bin/official-codex-app`; it only displays the Windows app, it is not a replacement app. Verification: `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/official-codex-app`, `curl -X POST -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/official-codex-app/start`, and Windows `Get-StartApps` showing `ChatGPT OpenAI.Codex_2p2nqsd0c76g0!App`. Do not save or print Windows/Guacamole passwords in runbooks or final answers.

- 2026-07-19 Official Codex client correction: user rejected the CLI/local-shell result and specifically wants the Windows-style official Codex client. Workbench `/kasm` now labels the primary entry as `官方Codex客户端` and starts/displays only the Windows official `OpenAI.Codex` client through `/official-codex-app`; C1-C8 WebTTY remains under `可选 TTY`. Legacy Kasm `codex-desktop-profiles` / `codex-gui-profiles` windows are killed during Kasm startup so they do not cover the official client. Guacamole auto-token is provided by Workbench `/api/official-codex-app/guac-token` using the non-secret path `~/.local/state/guacamole/official-codex-app-login.env` (`0600`; never print contents). Current remaining manual gate is Windows RDP password for user `G`; do not store/print it unless the user explicitly approves a secret-management path.

- 2026-07-19 Linux Codex desktop-client preference: user corrected again that they do **not** want the Windows official client; they want a Linux desktop-client experience. Official OpenAI help pages still describe ChatGPT/Codex desktop app availability as macOS/Windows, so the maintained local default is the Linux Workbench panel `/codex-desktop`, not `/official-codex-app`. Kasm startup now kills stale `official-codex-app-profile` and `codex-gui-profiles`, then auto-launches C5 via `/home/kasm-user/.local/share/kasm-cursor-webtop/bin/codex-desktop 5`. Workbench `/kasm` primary row is `Linux面板` with C1-C8 launch buttons backed by `/api/kasm/codex-desktop/start|start-all|status`; WebTTY is only `可选TTY`. Candidate third-party projects found for future evaluation: `ilysenko/codex-desktop-linux` (unofficial Linux port from macOS app) and `milisp/codexia` (Codex CLI/Claude Code workstation with scheduler/worktree/remote/skills). Prefer the local panel unless user explicitly asks to install a third-party package.

## 2026-07-19 Kasm `ilysenko/codex-desktop-linux` Linux Codex Desktop GUI

- Source/build: `~/.local/src/codex-desktop-linux` (`ilysenko/codex-desktop-linux`), built locally with `PACKAGE_WITH_UPDATER=0 MAX_BUILD_THREADS=4 make build-app`.
- Runtime in Kasm: `/home/kasm-user/.local/share/kasm-cursor-webtop/thirdparty-codex-desktop-linux`.
- Launcher: `/home/kasm-user/.local/share/kasm-cursor-webtop/bin/ilysenko-codex-desktop <1-8>`; generated by `~/.local/share/kasm-cursor-webtop/custom_startup.sh`.
- Codex CLI for the app is vendored in Kasm at `/home/kasm-user/.local/share/kasm-cursor-webtop/codex-cli-npm/bin/codex` (`codex-cli 0.144.5`).
- Each account uses isolated state:
  - `CODEX_HOME=/home/kasm-user/.local/share/kasm-cursor-webtop/codex-homes/c<N>`
  - `XDG_*=/home/kasm-user/.local/share/kasm-cursor-webtop/ilysenko-xdg/c<N>/{cache,config,state}`
  - `CODEX_WEBVIEW_PORT=527<N>` (`C5` => `5275`, `C7` => `5277`)
- Multi-account rule: launch with `CODEX_MULTI_LAUNCH_PORT_RANGE=$CODEX_WEBVIEW_PORT-$CODEX_WEBVIEW_PORT` and `start.sh --new-instance --x11`. Without `--new-instance`, C7/C8 warm-start can incorrectly hand off to the C5 Electron process.
- Kasm Ubuntu 22.04 glibc is `2.35`; host-built native modules from Fedora do not load. Fix by rebuilding native modules inside Kasm:
  - install container build deps: `apt-get install -y build-essential python3 make pkg-config`
  - build fresh `better-sqlite3@12.9.0` and `node-pty@1.1.0` with `@electron/rebuild@4.0.4` for Electron `42.3.0`
  - apply the repo's V8 external pointer patch before rebuilding `better-sqlite3`
  - copy rebuilt modules into `resources/app.asar.unpacked/node_modules/`
- Workbench APIs:
  - `GET /api/kasm/codex-desktop/status` checks account-specific pidfiles and markers, not a global Electron pgrep.
  - `POST /api/kasm/codex-desktop/start {"account":"7"}` launches the selected account.
- Phone verification on 2026-07-19: Android Chrome over DuckDNS/4G opened `http://charlie1990.duckdns.org:19888/kasm?device=w19900422` and showed the Kasm page plus ChatGPT/Codex desktop onboarding. Screenshot: `~/.local/state/phone-ilysenko-kasm.png`.
- First launch note: the upstream app may show a ChatGPT-branded onboarding page (`Hey! ... Which best describes your work?`). This is not the wrong app. Select a role such as Engineering and continue; it then lands in the Codex UI with left nav `Codex`, `New chat`, `Pull requests`, `Scheduled`, `Plugins`, `Projects`, and `Chats` plus the center prompt `What should we build?`. Verified on phone screenshot `~/.local/state/phone-ilysenko-codex-view.png`.

## 2026-07-20 Agent Comms Global Path

Problem: phone/desktop interaction was fragmented across ADB, NetBird, Workbench, ntfy, Haven SSH, FRP, route probes, screenshots, and logs. Future agents should not rediscover these paths manually.

Canonical CLI first, MCP wrapper second:

- CLI: `~/.local/bin/agent-comms`
- MCP server: `~/.local/bin/agent-comms-mcp.py`
- MCP config source: `~/.config/mcp/servers.yaml` entry `agent-comms`
- State: `~/.local/state/agent-comms/latest.json`
- AI summary: `~/.local/state/agent-comms/latest.md`

Commands:

```bash
agent-comms snapshot
agent-comms open-url 'http://192.168.123.71:19888/?device=w19900422'
agent-comms manual-action \
  --id example \
  --title '需要你操作' \
  --message '请在手机完成后点我已完成' \
  --url 'http://192.168.123.71:19888/' \
  --open-url
```

`snapshot` aggregates bounded current evidence from:

- `systemctl` service states for Workbench, Hub, phone probes, ADB keepalive, NetBird timers
- ADB devices and reverse mappings via `adb-record`
- `netbird status` distilled to ok/needs-login/IP/peers
- Workbench manual-action API
- `~/.local/state/phone-webtty-route-probe/latest.json`
- `~/.local/state/network-scenario-monitor/latest.json`

Rules:

1. Future agents should run `agent-comms snapshot` early for phone/network/interaction issues.
2. Use `agent-comms open-url` for immediate phone foreground opening; it prefers LAN ADB, then NetBird ADB, then FRP ADB.
3. Use `mobile-manual-action` or `agent-comms manual-action` for durable phone pending tasks.
4. Do not store secrets in `agent-comms` state, manual-action messages, URLs, or runbooks.
5. MCP should wrap this CLI instead of reimplementing ADB/NetBird/workbench logic in another place.

MCP tools completed on 2026-07-20:

- `agent_comms_snapshot`
- `agent_comms_open_url`
- `agent_comms_manual_action`
- `agent_comms_manual_done`

Implementation rule: keep all writes/actions bounded and logged through existing wrappers (`adb-record`, `ntfy-send`, `mobile-manual-action`). After changing MCP config, run `~/.local/bin/mcp-sync.py --apply` and restart `opencode.service` so OpenCode sees the updated tool set.

## 2026-07-20 Workbench Refresh Payload

- The Workbench home surface polls `GET /api/status/summary`, not the full
  `/api/status` payload. The summary retains per-account gate/backend,
  quota availability, task state, and account-manager counts while omitting
  task transcripts and detailed Sub2API usage records.
- Keep `/api/status` as the detailed compatibility endpoint for diagnostics and
  non-home consumers. Do not restore it as the home polling endpoint.
- Verification:

```bash
node --check ~/.local/bin/mobile-ai-workbench
systemctl --user restart mobile-ai-workbench.service
curl --noproxy '*' -fsS -H 'X-Device-Code: w19900422' \
  http://charlie1990.duckdns.org:19888/api/status/summary | jq '.accounts | length'
```

- A local `200` for Workbench does not prove phone-control panels are healthy.
  If both `adb-record -- connect 192.168.123.22:5555` and
  `adb-record -- connect 127.0.0.1:15555` fail, classify browser/network/ADB
  controls as phone-route unavailable rather than restarting Workbench.

## 2026-07-20 Workbench Account Slot Discovery

- Workbench account tabs are not limited to the static WebTTY range. Merge
  configured WebTTY slots with `~/.local/state/codex-account-manager/latest.json`
  so every managed slot is shown and refreshed through `/api/status/summary`.
- Slots without a configured WebTTY gate, currently C9/C10, are marked as
  status-only. Do not generate a fake `19008/19009` or public terminal link;
  selecting one must show the no-WebTTY state instead of opening C1.
- When serializing initial homepage data, omit `manager_group`; account-manager
  records can contain account labels and correlation hashes that must remain
  server-side. The home page only needs slot number, display metadata, terminal
  capability, and the redacted summary payload.
- Verify with:

```bash
curl -fsS -H 'X-Device-Code: w19900422' \
  http://127.0.0.1:19888/api/status/summary | jq '.accounts | length'
curl --noproxy '*' -fsSL -H 'X-Device-Code: w19900422' \
  'http://charlie1990.duckdns.org:19888/?device=w19900422' | rg '托管槽位 (9|10)'
```

- Apply the same discovery rule to every account-facing Workbench surface:
  homepage, `/buttons`, `/tasks`, `/codex-board`, `/windows`, `/kasm`, and
  the Kasm status APIs. Do not use a static `accounts` loop for presentation.
  C9/C10 currently have no WebTTY/Kasm profile, so they must appear as
  status-only instead of being hidden or mapped to C1.
