# Runbook: Haven & Phone Bridge

Haven 手机 MCP 桥接 + ADB 连接。

## Desired State

- `haven-mcp-bridge.service` — 本地 ADB 桥接，`127.0.0.1:8732/mcp`，默认必须是 disabled/inactive；只有配置或排查 Haven SSH 连接时才手动启动
- `haven-mcp-watchdog.timer` / `haven-mcp-watchdog.service` — 必须保持 disabled/masked；它会频繁 probe `127.0.0.1:8730/mcp` 和 `127.0.0.1:8732/mcp`，并可能前台启动 Haven
- Phone ADB: `192.168.123.22:5555`（无线调试/mDNS 当前主路径）；Tailscale `100.108.28.44:5555`；FRP fallback `127.0.0.1:15555`
- 手机上的 Magisk `/data/adb/service.d/96-haven-background-policy.sh` — 开机完成后执行 `/data/adb/haven-background-policy.sh`，为 Haven/Tailscale 写入 Doze、AppOps、active standby bucket 和计量网络白名单；这是后台保活的主策略，先于主机 ADB 可用
- `adb-phone-keepalive.timer` — 每分钟运行 `adb-phone-keepalive.service`，保活无线 ADB、按需执行 `adb tcpip 5555`，并重放上述应用级 Haven 后台策略；不得关闭全机 Doze、全机 App Standby 或全局省电模式
- Haven app (`sh.haven.app`) 不应为了 MCP 健康检查常驻；Haven SSH 终端连接由手机端用户操作触发
- OpenCode 中 `haven` MCP 必须保持 `enabled=false`，需要改 Haven SSH 配置时临时启用，任务后关闭
- Haven saved connection order:
  0. `Fedora Terminal` → public `2223` → sshd `22023` → `~/.local/bin/haven-entry-18080` → login shell
  1. `OpenCode Web` → public `2224` → sshd `22024` → `~/.local/bin/haven-entry-18910`
  2. `Windows SSH` → public `2222` → `windows-ssh-proxy.socket` → `100.91.93.99:22`
  3. `Fedora Codex` → public `2225` → keepalive proxy `22026` → sshd `22025` → `~/.local/bin/haven-entry-codex` → tmux session `haven-codex` → `CODEX_HOME=~/.codex`
  4. `Fedora Codex 2` → public `2226` → keepalive proxy `22027` → sshd `22028` → `~/.local/bin/haven-entry-codex2` → tmux session `haven-codex2` → `CODEX_HOME=~/.codex-2`
  5. `Fedora Codex 3` → Tailscale `100.120.189.27:2229` → keepalive proxy `22031` → sshd `22032` → `~/.local/bin/haven-entry-codex3` → tmux session `haven-codex3` → `CODEX_HOME=~/.codex-3`
  5a. `DuckDNS · Fedora Codex 2` (`aa255f76-aee3-4212-bf4b-b099034ddf40`) → `charlie1990.duckdns.org:2226` → same Codex2 chain
  5b. `DuckDNS · Fedora Codex 3` (`27f997b0-ef15-44b3-b688-3f004ac871b5`) → `charlie1990.duckdns.org:2229` → same Codex3 chain
  6. `Fedora Crush` → public `2227` → keepalive proxy `22029` → sshd `22030` → `~/.local/bin/haven-entry-crush` → tmux session `haven-crush`
  7. `Fedora VNC` → public `5900`
- Haven SSH profiles should have Haven-side `autoReconnect=false`; persistence is handled by Fedora wrappers/tmux. This prevents Haven from typing its Unix tmux reattach probe into Windows PowerShell or into the Codex session.
- Haven global DataStore preference `session_manager` must be `NONE`, not `TMUX`. The per-profile `sessionManager=NULL` falls back to this global value.
- `mcp_tunnel_endpoint_profile_id` must stay empty; the active Haven MCP transport is the local ADB bridge.
- `haven-codex.timer` may stay enabled; it only keeps Fedora's `haven-codex` tmux pane alive and does not touch the phone.
- `haven-session-autorecover.timer` must stay disabled; it calls Haven MCP `connect_profile` / `focus_terminal_session` and can repeatedly reopen or focus the phone-side SSH window.
- `~/.local/bin/haven-mcp-wrapper.sh` must not auto-start `haven-mcp-bridge.service` by default. Start the bridge explicitly for Haven configuration/debug tasks, or set `HAVEN_MCP_AUTOSTART=1` for a deliberate one-off.

## Verify

```bash
systemctl --user is-enabled haven-mcp-bridge haven-mcp-watchdog.timer
systemctl --user is-active haven-mcp-bridge haven-mcp-watchdog.timer
systemctl --user is-enabled haven-codex.timer haven-session-autorecover.timer
systemctl --user is-active haven-codex.timer haven-session-autorecover.timer
# ADB 连通
adb devices
# Haven MCP 桥接；只在明确要配置/排查 Haven SSH 时先 `systemctl --user start haven-mcp-bridge`
curl -s --noproxy '*' http://127.0.0.1:8732/mcp -X POST \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}' | jq
# Codex SSH entry persistence
tmux -S /run/user/1000/tmux/codex.sock ls
tmux -S /run/user/1000/tmux/codex.sock list-panes -t haven-codex -F '#{pane_dead} #{pane_current_command} #{pane_pid}'
tmux -S /run/user/1000/tmux/codex2.sock ls
tmux -S /run/user/1000/tmux/codex2.sock list-panes -t haven-codex2 -F '#{pane_dead} #{pane_current_command} #{pane_pid}'
tmux -S /run/user/1000/tmux/codex3.sock ls
tmux -S /run/user/1000/tmux/codex3.sock list-panes -t haven-codex3 -F '#{pane_dead} #{pane_current_command} #{pane_pid}'
# Android/Haven background connection checks
adb -s 100.108.28.44:5555 shell dumpsys deviceidle whitelist | rg 'sh\.haven\.app'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22023 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22024 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22025 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22028 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22030 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22032 | rg -i 'clientalive|forcecommand'
```

## Known Issues

- Haven 不能冷启动在锁屏手机上——TCP 接受连接但 `initialize` 不响应
- 不要启用 `haven-mcp-watchdog.timer`。它是 2026-06-28 发现的频繁调用来源：周期性 initialize、重启 bridge、必要时启动 Haven app。
- 需解锁手机、前台 `sh.haven.app/.MainActivity`、探测 `127.0.0.1:8730/mcp`
- 手机接在 Windows USB 上时，`phone-connect-mcp.py` 会尝试 `G@127.0.0.1:2222`、`G@100.91.93.99`、`G@192.168.123.136` 执行 Windows `adb devices`；识别到 USB 设备后会先跑 `adb tcpip 5555`，再回连 `100.108.28.44:5555`。如果 SSH 返回 `Exceeded MaxStartups` 或 `Connection reset`，问题在 Windows OpenSSH 服务端，不在 Fedora ADB。
- 2026-06-25 实测 `adb tcpip 5555` 后，`192.168.123.22:5555` 可用但 `100.108.28.44:5555` 仍关闭；优先走 LAN/mDNS，不要把 Tailscale 5555 不通误判为无线 ADB 未开启。
- 不要将 Haven 配置为 OpenCode 直接 `type:remote` MCP（OpenCode 用 legacy SSE GET，Haven 用 Streamable HTTP）
- 桥接代码不能用 `HTTPResponse.read(65536)` 读长响应，用 `read1()` 即时转发
- Haven SSH profile 不能用 HTTP 端口（18080/18910），用专用 SSH 入口 2223/2224
- `~/.local/bin/haven-entry-18910` 作为 Haven 的 OpenCode TUI 入口必须 `opencode attach http://127.0.0.1:4097`，不能连 `4096`。`4096/18910` 是带 Device Match 的 Web 代理，CLI attach 连它会收到 HTML 登录页并报 `can't connect to api`。
- Haven 切到后台后如果终端提示重新连接，先确认 `sh.haven.app` 在 Android Doze 白名单里，并确认 `/etc/ssh/sshd_config.d/60-haven-entry-ports.conf` 的 22023/22024/22025 Match 块都有 `ClientAliveInterval 15` / `ClientAliveCountMax 8`；2026-07-04 已实测三条入口生效。
- 2026-07-04 进一步处理后台断线：手机有 Magisk root，`adb-phone-keepalive.timer` 每分钟通过 `~/.local/bin/adb-phone-keepalive.sh` 重放 Haven 后台策略：Doze whitelist、`RUN_IN_BACKGROUND`、`RUN_ANY_IN_BACKGROUND`、`START_FOREGROUND`、standby bucket active、`netpolicy restrict-background-whitelist`。实测 `dumpsys netpolicy` 中 Haven UID `10371` 为 `ALLOW_METERED_BACKGROUND` 且 `effective=NONE`。
- 2026-07-12 保活策略固化：新增手机本机 Magisk 服务 `/data/adb/service.d/96-haven-background-policy.sh`，在开机完成后应用同一组 Haven/Tailscale 应用级豁免；主机脚本不再用 `cmd deviceidle disable`、`app_standby_enabled=0` 或关闭全局省电。这既消除了重启后 ADB 尚不可用的策略窗口，也保留正常的系统省电。当前验证应同时看到 `mLightEnabled=true mDeepEnabled=true`、Haven 在 deviceidle whitelist、`SshConnectionService isForeground=true`，以及 Host tmux pane 未死亡。
- 2026-07-04 实测 Haven 后台断线时，`SshConnectionService` 仍是 foreground service，进程 `isFrozen=false`，tmux 会话仍存活；若仍需手点重连，优先排查 Haven profile 自动重连/客户端 UI 恢复，而不是继续加 Android 省电白名单。
- Magisk `/data/adb/service.d` 在普通 `su -c` namespace 下会 Permission denied；需要 `su -mm` 才能列目录。不要把这个误判成没有 root。
- Codex 入口不能直接 `exec codex`，否则手机/Haven 断线重连会杀掉正在执行的任务；必须通过 tmux `haven-codex` attach
- 2026-07-07 修复 2225/2226 重复打开：`tcp-keepalive-proxy` 原先每个 SSH 连接 `fork()` 子进程，user pids 接近 `ulimit -u=2048` 时 `fork()` 抛 `BlockingIOError`，父进程崩溃后 systemd 重启，旧连接子进程仍在，手机端 profile 3/4 会堆出多个 disconnected session。现已在 `~/.local/bin/tcp-keepalive-proxy` 中捕获 fork 失败并丢弃该次连接、继续服务，且 `ssh-keepalive-proxy{,-codex2}.service` 设置 `LimitNPROC=8192`。排查时先看 `pgrep -af 'tcp-keepalive-proxy 2202[67]'`、`journalctl --user -u ssh-keepalive-proxy.service -u ssh-keepalive-proxy-codex2.service`，不要恢复 `haven-session-autorecover.timer`。
- Codex 多账号必须隔离 `CODEX_HOME`，不要在同一个 `~/.codex/auth.json` 上切换登录。当前主账号入口是 `2225`/`haven-codex`/`~/.codex`，第二账号入口是 `2226`/`haven-codex2`/`~/.codex-2`，第三账号入口是 `2229`/`haven-codex3`/`~/.codex-3`。Haven 中应保存三个独立 SSH profile；打开哪个 profile 就使用哪个账号。
- Codex 多账号的合规共享边界：`auth.json`、`installation_id`、history、SQLite 状态、logs、cache、shell snapshots 必须账号隔离；`config.toml`、skills、项目 `AGENTS.md`、`~/.ai-context`、runbooks、`~/memory`、MCP 资源可以共享。主源是 `~/.codex/config.toml` 和 `~/.codex/skills`，`codex-shared-sync.path` 自动同步到 `~/.codex-2`；`codex2` 和 `haven-entry-codex2` 启动前也会主动运行 `~/.local/bin/codex-shared-sync --apply`。
- 2026-07-07 Codex 2 启动卡住时，先抓 `tmux -S /run/user/1000/tmux/codex2.sock capture-pane -pt haven-codex2 -S -80`。若画面停在 `Starting MCP servers ... codegraph`，问题是 Codex MCP 启动阻塞，不是账号登录或 SSH 链路。当前 `~/.config/mcp/servers.yaml` 保留 `codegraph`、`haven`、`macg` 配置但对 Codex 写入 `enabled = false`；`~/.local/bin/mcp-sync.py` 支持该字段。修复后重跑 `mcp-sync.py --apply`、杀掉 `haven-codex2` tmux 会话并重新进入。
- 2026-07-08 Codex 2 profile 打不开时，先查手机 DB 中 `4 · Fedora Codex 2` 是否被改成 `authType=PASSWORD` 且 `sshPassword/keyId` 为空。正确值是 `host=100.120.189.27`、`port=2226`、`authType=KEY`、`keyId=2ca35bc0-f05c-4313-8eba-7ed6e2e39d18`、`authMethods=KEY:2ca35bc0-f05c-4313-8eba-7ed6e2e39d18`、`autoReconnect=0`、`reconnectOnNetworkChange=0`、`lastSessionName=NULL`、`postLoginBeforeSessionManager=0`。2026-07-12 另新增 DuckDNS 备用 profile `DuckDNS · Fedora Codex 2` 指向 `charlie1990.duckdns.org:2226`，不要覆盖原 Tailscale profile。
- 2026-07-12 Codex3 DuckDNS SSH：路由器持久转发 `2229/TCP -> 192.168.123.71:2229`，Haven profile `DuckDNS · Fedora Codex 3` 指向 `charlie1990.duckdns.org:2229`。手机端 `nc` 实测 `2226`/`2229` 均 open。保留原 Tailscale profile 作为主/低延迟入口。
- 2026-07-12 如果 Haven 里的 DuckDNS Codex profile 日志显示 `Connecting to 198.18.x.x port 2226/2229` 后 `connection is closed by foreign host`，问题通常不是 Fedora 端 sshd/FRP，而是手机侧代理/DNS 把 `charlie1990.duckdns.org` 解析成 fake-ip。此时主用入口应是 Tailscale profile：账号 2 用 `01 · Codex 2 · Tailscale SSH`，账号 3 用 `02 · Codex 3 · Tailscale SSH`；DuckDNS profile 仅保留为备用。
- 2026-07-08 Codex WebTTY 入口：两个账号除了 SSH/Haven 外，还有公网浏览器入口，均为设备码代理 + ttyd + tmux，不会因浏览器断线杀 Codex。Codex 1：`http://charlie1990.duckdns.org:19899/` → frps `19899` → local device gate `127.0.0.1:19000` → backend ttyd `127.0.0.1:19881` → `ttyd-codex-entry` → tmux socket `/run/user/1000/tmux/codex.sock` session `haven-codex` → `CODEX_HOME=~/.codex`。Codex 2：`http://charlie1990.duckdns.org:19900/` → frps `19900` → local device gate `127.0.0.1:19001` → backend ttyd `127.0.0.1:19882` → `ttyd-codex2-entry` → tmux socket `/run/user/1000/tmux/codex2.sock` session `haven-codex2` → `CODEX_HOME=~/.codex-2`。外层设备码是 `w19900422`，验证后分别写 `duckdns_codex1_device` / `duckdns_codex2_device` cookie；内层 BasicAuth 仍是 `codex:w19900422`，但由 `ttyd-device-gate-proxy` 自动加给 ttyd，手机用户不再需要浏览器 BasicAuth 弹窗。2026-07-10 修复：代理注入脚本必须按 `DEVICE_COOKIE_NAME` 和 `TTYD_GATE_PORT` 生成，不能硬编码 Codex1 cookie 或 `localhost:19891`；设备码页输入完整 code 后自动提交并写一年 cookie。
- 2026-07-08 Codex WebTTY/Haven 同步修复：`haven-entry-codex{,2}` 和 `ttyd-codex{,2}-entry` 必须 attach 到同一 tmux socket/session，且不能使用 `tmux attach-session -d`。`-d` 会在新客户端连接时踢掉旧客户端，导致 Haven 和 `19899/19900` 看起来不是同一个窗口、状态不能实时同步。当前四个入口都使用 `tmux attach-session -t "$SESSION"`，允许 Haven SSH 和 WebTTY 同时挂在同一个 pane；若用户说不同步，先让手机 Haven profile 断开重连、刷新 WebTTY，再查 `tmux -S /run/user/1000/tmux/codex{,2}.sock list-clients`。
- 2026-07-08 Codex WebTTY 翻页修复：backend `ttyd-codex-backend.service` 和 `ttyd-codex2-backend.service` 使用自定义 index `/var/home/charlie/.local/share/ttyd-codex/index-codex1.html`、`index-codex2.html`。2026-07-10 用户要求取消页面自动刷新，当前不注入 `codex-mobile-resume`，也不在 WebSocket close/error 时自动 reload；登录保持依赖设备码 cookie。两个 backend 都传 `-t scrollback=50000`，对应 tmux server 也设置 `history-limit 50000`、`mouse off`；不要让 Haven 和 WebTTY wrapper 互相改 `mouse`。手机浏览器里不要只依赖 xterm 原生滚动；tmux 重连后浏览器往往只能看到当前屏，Codex TUI 还会吃掉滚轮和 PageUp/PageDown。`ttyd-device-gate-proxy` 现在提供同域 `/history` 和 `/tmux-scroll?action=up|down|bottom`；页面右下角有“上翻/下翻/到底/历史”按钮，按钮直接控制对应 tmux copy-mode。`/history` 直接从对应 tmux socket 抓最近 50000 行并用普通 HTML `<pre>` 展示，手机可正常上下滚动。
- 2026-07-13 Codex WebTTY 触摸阅读修复：三个 Codex TTY 页面必须支持手指在终端区域上下滑动历史、长按/拖选文本、系统复制。注意 Codex/tmux TUI 常在 alternate screen 里，单纯滚动 xterm viewport 不可靠；`ttyd-device-gate-proxy` 现在同时注入 `codex_touch_read_select` 和 `codex_mobile_unified_touch`。终端区域上下滑动应调用同域 `/tmux-scroll?action=up|down&transient=1` 控制 tmux copy-mode，并由服务端短暂延迟后自动 cancel，避免页面停在历史模式导致“文字不动”；长按或双击终端区域打开 `#codex-copy-layer`，从 `/history.txt` 加载普通 `<pre>`，用于系统选择和复制。不要再加入全局 `touchmove preventDefault`、readonly textarea 保护或把终端区域设成不可选择；只允许按钮/面板区域自己拦截点击。右上角和稳定 dock 的 `1/2/3/4` 必须被拦截成常驻 iframe 标签页切换，不应整页跳转或触发离开页面确认。
- 2026-07-13 Codex WebTTY 统一界面修复：账号切换 iframe 里不得再显示自己的顶部账号切换、额度条、稳定 dock、旧右侧按钮栏或管理/Router 面板；否则父页面和子页面会叠出两个 bar。`ttyd-device-gate-proxy` 注入 `codex_child_frame_cleanup`，子 iframe 只保留终端本体；`codex_stable_router_dock`、`codex_safe_router_switch`、`codex_mobile_unified_touch` 都必须只在顶层页面承担统一 UI/切换职责。排查重复 bar 时先 curl 首页确认只看到顶层一套 `codex-stable-dock`，子 iframe 应由 cleanup 隐藏自己的控件。
- 2026-07-09 Codex WebTTY iOS 输入法修复：iOS Safari/WebKit + xterm.js hidden textarea 容易出现中文/联想输入重复、卡顿，Android 不一定复现。当前 `index-codex1.html`/`index-codex2.html`/`index-codex3.html` 已移除旧的 `codex-touch-scroll` 全局 touchmove preventDefault，并把 `.xterm-helper-textarea` 设置 `autocomplete=off`、`autocorrect=off`、`autocapitalize=none`、`spellcheck=false`。2026-07-10 用户要求恢复鼠标键盘直输，曾移除 `codex-ios-safe-input` / readonly 保护并新增 `codex-focus-input`。2026-07-11 因账号2再次出现重复输入和输入拉断，`codex-focus-input` 改为只在非 iOS 浏览器运行；iOS 不再在 `pointerdown/click/touchend` 上额外强制聚焦 xterm hidden textarea。`ttyd-device-gate-proxy` 仍提供 `POST /tmux-send?enter=0|1`，页面右侧保留“输入/输入↵”按钮作为 iOS 备用输入路径。
- 2026-07-11 Codex WebTTY 三账号 iOS 不能点出输入：`codex-ios-safe-input` 把 `.xterm-helper-textarea` 设为 `readonly` / `inputmode=none` 后，iOS Safari 点终端区域不会弹键盘，而 Android 正常。当前 `index-codex1.html`/`index-codex2.html`/`index-codex3.html` 已移除该只读保护；右侧“输入/输入↵”按钮改为打开页面内真实 `<textarea>` 面板，提交仍走 `POST /tmux-send?enter=0|1`。排查同类问题时先确认页面中不存在 `codex-ios-safe-input`，并用 `curl -u codex:w19900422 http://127.0.0.1:1988{1,2,3}/ | rg 'codex-input-panel|codex-ios-safe-input'` 验证。
- 2026-07-11 Codex WebTTY 任务管理：右侧 `Session` 按钮必须打开 `/sessions`，不是简单 `/status` 弹窗。`ttyd-device-gate-proxy` 提供 `/sessions` 和 `/sessions.json`，同页列出 Codex 1/2/3 的 tmux session、pane、客户端数、最近画面、最近归档，并提供“打开终端 / 进度 / 归档 / 立即归档 / 恢复 / 归档重启”。验证：`curl -L 'http://127.0.0.1:19000/sessions?device=w19900422' | rg 'Codex 任务管理|Codex 1|Codex 2|Codex 3'`，三个 gate `19000/19001/19002` 都应可打开。不要把这个入口退回成只显示 pane 状态的按钮。
- 2026-07-11 Codex WebTTY 额度按钮：右侧必须有 `额度` 按钮，打开 `/quota`；左下“管理”和 `/sessions` 页也应能进入额度页。`ttyd-device-gate-proxy` 从各账号 `~/.codex*/sessions/**/*.jsonl` 最新 `token_count.rate_limits` 事件读取额度，`/quota` 显示动态 bar 并每 30 秒拉 `/quota.json` 更新，包含 5 小时额度、7 天额度、重置时间、plan、tokens。Codex3 若官方 `rate_limits.primary/secondary` 为 null，则额外只读查询 `sub2api-postgres`，但只有 `usage_logs` 存在时才可信显示 sub2api 剩余额度百分比；当前 Codex3 走 `127.0.0.1:19093` 自写代理绕过 sub2api，`usage_logs=0`，因此不得把 `api_keys.quota=1000/quota_used=0` 显示为真实 100%。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19002/quota.json | jq '.accounts[] | select(.account=="3") | {official:.rate_limits.primary, trusted:.sub2api.usage_trusted, percent:.sub2api.api_key_remaining_percent, tokens:.token_usage.total_token_usage.total_tokens}'`。
- 2026-07-11 Codex3 -> sub2api TTY 用量同步：`~/.local/bin/codex3-sub2api-usage-sync` 每分钟由 `codex3-sub2api-usage-sync.timer` 执行，读取 `~/.codex-3/sessions/**/*.jsonl` 的 `token_count.total_token_usage` 增量，幂等写入 sub2api `usage_logs`，`user_agent='codex3-tty-sync'`、`inbound_endpoint='/codex3/tty'`。它同步的是真实 TTY token 用量，不是官方 5h/7d 剩余额度；当前 sub2api 没有 channel/pricing 配置，所以 `total_cost=0`，`money_usage_trusted=false`，不得显示金额剩余额度百分比。验证：`systemctl --user is-active codex3-sub2api-usage-sync.timer`；`sudo podman exec sub2api-postgres psql -U sub2api -d sub2api -c \"select count(*),sum(input_tokens),sum(cache_read_tokens),sum(output_tokens),sum(total_cost) from usage_logs where user_agent='codex3-tty-sync';\"`。
- 2026-07-11 Codex WebTTY 首页额度状态条：除右侧 `额度` 按钮外，三个首页 `index-codex1.html`/`index-codex2.html`/`index-codex3.html` 必须有 `#codex-quota-strip`，固定在左上方，直接显示当前账号 `5h xx%` 和 `7d yy%` 两条小 bar，并每 30 秒从 `/quota.json` 刷新当前账号数据。Codex3 官方额度为空且 sub2api 没有可信 usage logs 时，首页显示 `真实 <tokens>k tok` / `未记账`，浮窗卡片显示 `真实 tokens` 和 warning；不得显示 `后台 100%`。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19002/ | rg 'codex-quota-strip|真实 tokens|未记账'`。
- 2026-07-11 Codex WebTTY 额度语义修正：所有额度 UI 必须显示“剩余额度”，不是 `rate_limits.*.used_percent` 的已用值；计算为 `100 - used_percent`。首页状态条文案为 `剩余`，浮窗和 `/quota` 详细页文案为 `5h/7d 剩余`。右侧 `额度` 按钮在首页必须打开 `#codex-quota-modal` 浮窗，不应直接跳离终端；浮窗内三账号卡片显示剩余 bar，并点击跳转到对应账号 WebTTY，用于选择剩余额度最多的账号执行任务。`/quota.json` 应返回 `account_url`。验证：`curl -L 'http://127.0.0.1:19000/quota.json?device=w19900422' | jq '.accounts[] | {label, used:.rate_limits.primary.used_percent, account_url}'`；首页 HTML 应命中 `codex-quota-modal|5h 剩余|点击切换到该账号执行任务`。
- 2026-07-11 Codex WebTTY 额度档位：给手机首页和额度浮窗显示 `高/中/少/紧张/未知`，并保留百分比。档位基于剩余值：`>=70 高`、`35-69 中`、`15-34 少`、`<15 紧张`。官方 `rate_limits.primary/secondary` 缺失时不要用 token 总量臆测官方额度；Codex3 只有在 `sub2api.usage_trusted=true` 时才可显示 `sub2api 后台` 百分比，否则只显示真实 token 消耗和“未记账/无法计算剩余额度”。
- 2026-07-11 Codex WebTTY 账号切换：右上角 `1/2/3` 必须像浏览器标签页一样切换常驻页面，不应触发“是否离开页面”或整页刷新。`ttyd-device-gate-proxy` 的 `accountSwitchScript()` 只在顶层页面渲染切换器，`1/2/3` 是按钮不是跨端口裸链接；其他账号用常驻隐藏 iframe 预热，点击只切换 iframe 可见性。子 iframe 里不会再渲染账号切换器。iframe 层级必须是 `z-index:2147483646`，仅低于顶层 `1/2/3` 切换器，高于父页面额度/管理按钮，这样切到账号 2/3 时显示对应账号自己的额度按钮和额度条。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | rg 'window\\.top!==window\\.self\\)return|document\\.createElement\\('\"'\"'button'\"'\"'\\)|z-index:2147483646'`，且不应命中 `location.href=href` 或旧的 `z-index:99990`。
- 2026-07-08 Codex WebTTY 账号标识：19899/19900 仍是两套独立账号入口。backend 分别使用 `/var/home/charlie/.local/share/ttyd-codex/index-codex1.html` 与 `index-codex2.html`，页面 title 和右上角角标分别显示 `Codex 1 | ~/.codex`、`Codex 2 | ~/.codex-2`，避免手机浏览器缓存或多标签切换时误看成同一个账号。
- 2026-07-08 Crush SSH 入口：服务端已新增 `haven-entry-crush`、`ssh-keepalive-proxy-crush.service`、sshd `Port 22030`/`ForceCommand haven-entry-crush`、SELinux `ssh_port_t:22030`、FRP `fedora-ssh-crush-2227`。手机 SSH app/Haven profile 应新增 `Fedora Crush`，host 优先 `100.120.189.27` 或公网 `charlie1990.duckdns.org`，port `2227`，user `charlie`，auth key 复用 Codex/Haven key，autoReconnect=false。若需要自动写手机 profile，先恢复 ADB `192.168.123.22:5555`。
- Do not enable Haven's built-in SSH session-manager reconnect for Windows/Codex/Fedora entries. Connection logs showing `pending/reattach sent on prompt ... exec sh -c 'if ! command -v tmux ...'` mean Haven is typing a long Unix reattach command into the shell and blocking input until it finishes.
- If `list_sessions` shows `sessionManager: "TMUX"` for Windows or plain Fedora terminals, pull `/data/user/0/sh.haven.app/files/datastore/haven_preferences.preferences_pb`, verify `strings` shows `session_manager` + `NONE`, and only restore from backup if the app rejects the preference.
