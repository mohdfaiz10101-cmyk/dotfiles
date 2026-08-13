# Runbook: Haven & Phone Bridge

Haven 手机 MCP 桥接 + ADB 连接。

## Desired State
## System App Status

2026-07-19 verification on PKR110: `sh.haven.app` is installed as a
system/privileged updated system app (`pkgFlags=[ SYSTEM ... UPDATED_SYSTEM_APP ]`),
has `RECEIVE_BOOT_COMPLETED`, foreground-service permissions, background appops
allowed, and is in the device idle whitelist. Haven is therefore already
system-level; if NetBird profiles fail after reboot, first check NetBird VPN
`tun0` rather than converting Haven again.


## Multi-Network Access Order

For a phone or tablet with Tailscale online, use routes in this order:

1. Same-home Wi-Fi: LAN/FRPS path where supported.
2. Mobile 5G or unstable Wi-Fi: Tailscale host `100.120.189.27` (bypasses
   DuckDNS, router NAT, CGNAT, and phone-side fake-IP DNS).
3. DuckDNS/FRP public profiles: WAN-only fallback.

Do not treat a phone-side Tailscale peer marked offline as a Fedora or router
failure. The phone must be online before its Haven profiles can be changed or
validated. Fedora's C1/C6 WebTTY `/status` uses parallel, 1.5-second tmux IPC
probes so a slow tmux session is not misclassified as a network outage.

- `haven-mcp-bridge.service` — 本地 ADB 桥接，`127.0.0.1:8732/mcp`，默认必须是 disabled/inactive；只有配置或排查 Haven SSH 连接时才手动启动
- `haven-mcp-watchdog.timer` / `haven-mcp-watchdog.service` — 必须保持 disabled/masked；它会频繁 probe `127.0.0.1:8730/mcp` 和 `127.0.0.1:8732/mcp`，并可能前台启动 Haven
- Phone ADB: `192.168.123.22:5555`（无线调试/mDNS 当前主路径）；Tailscale `100.108.28.44:5555`；FRP fallback `127.0.0.1:15555`
- 手机上的 Magisk `/data/adb/service.d/96-haven-background-policy.sh` — 开机完成后执行 `/data/adb/haven-background-policy.sh`，为 Haven、Mattermost、NetBird、Tailscale 写入 Doze、AppOps、active standby bucket 和计量网络白名单；这是后台保活的主策略，先于主机 ADB 可用
- `adb-phone-keepalive.timer` — 每分钟运行 `adb-phone-keepalive.service`，保活无线 ADB、按需执行 `adb tcpip 5555`，并重放上述应用级 Haven 后台策略；不得关闭全机 Doze、全机 App Standby 或全局省电模式
- Haven app (`sh.haven.app`) 不应为了 MCP 健康检查常驻；Haven SSH 终端连接由手机端用户操作触发
- OpenCode 中 `haven` MCP 必须保持 `enabled=false`，需要改 Haven SSH 配置时临时启用，任务后关闭
- Haven saved connection order:
  0. `Fedora Terminal` → public `2223` → sshd `22023` → `~/.local/bin/haven-entry-18080` → login shell
  1. `OpenCode Web` → public `2224` → sshd `22024` → `~/.local/bin/haven-entry-18910`
  2. `Windows SSH` → public `2222` → `windows-ssh-proxy.socket` → `100.91.93.99:22`
  2a. `Codex Smart` → public/Tailscale `2230` → keepalive proxy `22033` → sshd `22034` → `~/.local/bin/haven-entry-codexsmart` → tmux session `haven-codexsmart` → `codex-smart-shell`
  3. `Fedora Codex` → public `2225` → keepalive proxy `22026` → sshd `22025` → `~/.local/bin/haven-entry-codex` → tmux session `haven-codex` → `CODEX_HOME=~/.codex`
  4. `Fedora Codex 2` → public `2226` → keepalive proxy `22027` → sshd `22028` → `~/.local/bin/haven-entry-codex2` → tmux session `haven-codex2` → `CODEX_HOME=~/.codex-2`
  5. `Fedora Codex 3` → Tailscale `100.120.189.27:2229` → keepalive proxy `22031` → sshd `22032` → `~/.local/bin/haven-entry-codex3` → tmux session `haven-codex3` → `CODEX_HOME=~/.codex-3`
  5a. `DuckDNS · Fedora Codex 2` (`aa255f76-aee3-4212-bf4b-b099034ddf40`) → `charlie1990.duckdns.org:2226` → same Codex2 chain
  5b. `DuckDNS · Fedora Codex 3` (`27f997b0-ef15-44b3-b688-3f004ac871b5`) → `charlie1990.duckdns.org:2229` → same Codex3 chain
  6. `Fedora Crush` → public `2227` → keepalive proxy `22029` → sshd `22030` → `~/.local/bin/haven-entry-crush` → tmux session `haven-crush`
  7. `Fedora VNC` → public `5900`
- 2026-07-14 Haven connection folders are intentionally grouped this way in
  `/data/user/0/sh.haven.app/databases/haven.db`:
  `Codex · DuckDNS/WAN 备用` for public fallback SSH profiles,
  `Codex · Tailscale` for Codex Smart/2/3 primary Tailscale profiles,
  `OpenCode / Terminal / Monitor` for OpenCode/Fedora terminal/Text monitor/Crush
  Tailscale, `Windows` for Windows SSH, and `Desktop / VNC` for Fedora VNC.
  Keep `autoReconnect=0` and `reconnectOnNetworkChange=0` for all of these
  profiles; Fedora tmux/wrappers provide persistence.
- 2026-07-18 C4-C8 Haven NetBird SSH profiles were added directly to
  `/data/user/0/sh.haven.app/databases/haven.db`. They use Fedora NetBird IP
  `100.87.238.153` and account-local sshd `ForceCommand` ports, not DuckDNS:
  - `NB · Codex 4 · SSH` → `100.87.238.153:2231` → keepalive proxy `2231` → sshd `22036` → `haven-entry-codex4`
  - `NB · Codex 5 · SSH` → `100.87.238.153:2232` → keepalive proxy `2232` → sshd `22038` → `haven-entry-codex5`
  - `NB · Codex 6 · SSH` → `100.87.238.153:2233` → keepalive proxy `2233` → sshd `22040` → `haven-entry-codex6`
  - `NB · Codex 7 · SSH` → `100.87.238.153:2234` → keepalive proxy `2234` → sshd `22042` → `haven-entry-codex7`
  - `NB · Codex 8 · SSH` → `100.87.238.153:2235` → keepalive proxy `2235` → sshd `22044` → `haven-entry-codex8`
  All have `autoReconnect=0`, `reconnectOnNetworkChange=0`, and
  `sessionManager=NULL`. `sshd` now uses `AddressFamily inet` in
  `/etc/ssh/sshd_config.d/60-haven-entry-ports.conf` to avoid OpenSSH
  `Too many listen sockets` after adding these local ports. SELinux `ssh_port_t`
  includes `22036/22038/22040/22042/22044`. Do not add DuckDNS/FRP SSH proxies
  for `2231-2235` unless frps `allowPorts` is also updated; local frps rejected
  them with `port not allowed`, while WebTTY public ports `19903-19907` already
  cover browser access for C4-C8.
- 2026-07-18 NetBird profile group added in
  `/data/user/0/sh.haven.app/databases/haven.db`: `Codex · NetBird`.
  All generated entries use host `100.87.238.153`, `autoReconnect=0`,
  `reconnectOnNetworkChange=0`, and `sessionManager=NULL`:
  - `NB · Codex 1 · SSH` → `100.87.238.153:2225`
  - `NB · Codex Smart · SSH` → `100.87.238.153:2230`
  - `NB · Codex 2 · SSH` → `100.87.238.153:2226`
  - `NB · Codex 3 · SSH` → `100.87.238.153:2229`
  - `NB · Fedora Terminal · SSH` → `100.87.238.153:2223`
  - `NB · OpenCode Web · SSH` → `100.87.238.153:2224`
  - `NB · Text Web Monitor · SSH` → `100.87.238.153:2223`
  - `NB · Crush · SSH` → `100.87.238.153:2227`
  - `NB · Windows SSH via Fedora` → `100.87.238.153:2222`
  - `NB · Fedora VNC` → `100.87.238.153:5900`
  Phone-side backup: `haven.db.bak-netbird-*`. These entries depend on the
  Android NetBird VPN being connected; if they fail while DuckDNS/Tailscale
  works, first unlock the phone, open NetBird, and accept/start its VPN.
- 2026-07-18 NetBird was started on PKR110 and verified from Haven UID
  `10371`: `100.87.238.153:8065` returned Mattermost ping OK, and
  `100.87.238.153` TCP probes for `2222`, `2223`, `2224`, `2225`, `2226`,
  `2227`, `2229`, `2230`, `5900`, and `8065` returned success. `wayvnc.service`
  was started and is expected to keep `5900` available because it is enabled.
  The same phone background policy now includes `com.mattermost.rn` and
  `io.netbird.client` in addition to Haven/Tailscale; keep this if
  Mattermost/Haven NetBird access is expected to survive backgrounding or
  reboot.
- Windows currently has no standalone NetBird client installed, so there is no
  direct Windows NetBird peer to add to Haven yet. The usable Windows entry is
  still `NB · Windows SSH via Fedora` through Fedora's NetBird IP
  `100.87.238.153:2222`. If a direct Windows NetBird peer is needed later,
  NetBird must first be installed and enrolled on Windows.
- 2026-07-14 Haven app-level connection test through MCP: working profiles were
  Codex 1 DuckDNS `2225`, Codex Smart Tailscale `2230`, Windows DuckDNS `2222`,
  OpenCode Tailscale `2224`, Codex 2 Tailscale `2226`, Fedora Terminal
  Tailscale `2223`, Codex 3 Tailscale `2229`, Text Web Monitor Tailscale
  `2223`, and Crush Tailscale `2227`. Failing public fallback profiles were
  Codex 2 DuckDNS/WAN `2226`, Codex 3 DuckDNS `2229`, and Crush DuckDNS `2227`.
  `2226`/`2229` can show `Connecting to 198.18.x.x` plus `connection is closed
  by foreign host`, which usually means phone-side fake-ip/proxy DNS; prefer the
  Tailscale profiles. Crush DuckDNS `2227` and VNC `5900` were not present in
  the router manual forwarding table during this test, and `upnpc` from Fedora
  could not discover an IGD device.
- 2026-07-14 `wayvnc.service` was enabled and can be started manually with
  `systemctl --user start wayvnc.service`; it should listen on `0.0.0.0:5900`.
  If Haven VNC logs stay empty, first verify the router has a `5900/TCP ->
  192.168.123.71:5900` mapping and that `ss -ltnp | rg ':5900\b'` shows
  `wayvnc-patched`.
- Haven SSH profiles should have Haven-side `autoReconnect=false`; persistence is handled by Fedora wrappers/tmux. This prevents Haven from typing its Unix tmux reattach probe into Windows PowerShell or into the Codex session.
- Haven global DataStore preference `session_manager` must be `NONE`, not `TMUX`. The per-profile `sessionManager=NULL` falls back to this global value.
- `mcp_tunnel_endpoint_profile_id` must stay empty; the active Haven MCP transport is the local ADB bridge.
- `haven-codex.timer` may stay enabled; it only keeps Fedora's `haven-codex` tmux pane alive and does not touch the phone.
- `haven-session-autorecover.timer` must stay disabled; it calls Haven MCP `connect_profile` / `focus_terminal_session` and can repeatedly reopen or focus the phone-side SSH window.
- `~/.local/bin/haven-mcp-wrapper.sh` must not auto-start `haven-mcp-bridge.service` by default. Start the bridge explicitly for Haven configuration/debug tasks, or set `HAVEN_MCP_AUTOSTART=1` for a deliberate one-off.


- 2026-07-18 full Codex account matrix added to Haven DB and verified from USB ADB:
  `TS · Codex Smart/1/2/3/4/5/6/7/8 · SSH`,
  `NB · Codex Smart/1/2/3/4/5/6/7/8 · SSH`, and
  `DD · Codex Smart/1/2/3/4/5/6/7/8 · SSH`. Hosts/ports are:
  Tailscale `100.120.189.27`, NetBird `100.87.238.153`, DuckDNS
  `charlie1990.duckdns.org`; Smart=`2230`, C1=`2225`, C2=`2226`,
  C3=`2229`, C4-C8=`2231-2235`. Phone DB verification showed
  `pragma integrity_check=ok`, `TS=9`, `NB=9`, `DD=9`,
  `connection_profiles=48`, `ssh_keys=3`. Fedora local TCP probes for
  `2225/2226/2229/2230/2231-2235` all returned `rc=0`. DuckDNS phone-side
  Haven UID `10371` probes for all nine ports returned `rc=0` after adding
  FedoraWorkstation firewalld ports `2225-2227/tcp`, `2229-2230/tcp`,
  `2231-2235/tcp` and Padavan persistent NAT for `2230-2235`. At that time
  Tailscale/NetBird phone validation was blocked because Android had no active
  VPN interface (`tun0` absent; default route only `rmnet_data4` cellular);
  open the desired VPN app and then rerun Haven UID `nc` probes before blaming
  Haven profiles.

- 2026-07-18 automatic phone-side full-matrix test over USB ADB:
  after `monkey -p io.netbird.client 1`, Haven UID `10371` reached NetBird
  `100.87.238.153` on all Codex SSH ports `2225/2226/2229/2230/2231-2235`
  with `rc=0`. DuckDNS `charlie1990.duckdns.org` also reached all nine ports
  with `rc=0`. After `monkey -p com.tailscale.ipn 1`, Tailscale
  `100.120.189.27` probes still timed out on all nine ports (`rc=1`), and no
  Tailscale VPN interface was reported; treat this as phone Tailscale not
  connected/authorized, not a Haven DB or Fedora port failure. Android can use
  only one VPN slot, so NetBird and Tailscale cannot be simultaneously active.

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
tmux -S /run/user/1000/tmux/codexsmart.sock ls
tmux -S /run/user/1000/tmux/codexsmart.sock list-panes -t haven-codexsmart -F '#{pane_dead} #{pane_current_command} #{pane_pid}'
tmux -S /run/user/1000/tmux/codex2.sock ls
tmux -S /run/user/1000/tmux/codex2.sock list-panes -t haven-codex2 -F '#{pane_dead} #{pane_current_command} #{pane_pid}'
tmux -S /run/user/1000/tmux/codex3.sock ls
tmux -S /run/user/1000/tmux/codex3.sock list-panes -t haven-codex3 -F '#{pane_dead} #{pane_current_command} #{pane_pid}'
# Android/Haven background connection checks
adb -s 100.108.28.44:5555 shell dumpsys deviceidle whitelist | rg 'sh\.haven\.app'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22023 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22024 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22034 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22025 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22028 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22030 | rg -i 'clientalive|forcecommand'
sudo sshd -T -C user=charlie,host=localhost,addr=127.0.0.1,lport=22032 | rg -i 'clientalive|forcecommand'
```

## Known Issues

- 2026-07-16 Haven UID `10371` could not resolve DuckDNS because root Mihomo
  redirected DNS to an unopened `5354`. Repair: one `mihomo_netbird` instance,
  Tailscale UID bypass, and `dns.listen: 0.0.0.0:5354`. Verify using Haven's
  UID: `su 10371 -c 'toybox nc -4 -z -w 7 charlie1990.duckdns.org 2225'`.

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
- 2026-07-12 保活策略固化，2026-07-18 扩展：手机本机 Magisk 服务 `/data/adb/service.d/96-haven-background-policy.sh`，在开机完成后应用 Haven/Mattermost/NetBird/Tailscale 应用级豁免；主机脚本不再用 `cmd deviceidle disable`、`app_standby_enabled=0` 或关闭全局省电。这既消除了重启后 ADB 尚不可用的策略窗口，也保留正常的系统省电。当前验证应同时看到 `mLightEnabled=true mDeepEnabled=true`、Haven/Mattermost/NetBird 在 deviceidle 或 netpolicy 白名单中、`SshConnectionService isForeground=true`，以及 Host tmux pane 未死亡。
- 2026-07-04 实测 Haven 后台断线时，`SshConnectionService` 仍是 foreground service，进程 `isFrozen=false`，tmux 会话仍存活；若仍需手点重连，优先排查 Haven profile 自动重连/客户端 UI 恢复，而不是继续加 Android 省电白名单。
- Magisk `/data/adb/service.d` 在普通 `su -c` namespace 下会 Permission denied；需要 `su -mm` 才能列目录。不要把这个误判成没有 root。
- Codex 入口不能直接 `exec codex`，否则手机/Haven 断线重连会杀掉正在执行的任务；必须通过 tmux `haven-codex` attach
- 2026-07-07 修复 2225/2226 重复打开：`tcp-keepalive-proxy` 原先每个 SSH 连接 `fork()` 子进程，user pids 接近 `ulimit -u=2048` 时 `fork()` 抛 `BlockingIOError`，父进程崩溃后 systemd 重启，旧连接子进程仍在，手机端 profile 3/4 会堆出多个 disconnected session。现已在 `~/.local/bin/tcp-keepalive-proxy` 中捕获 fork 失败并丢弃该次连接、继续服务，且 `ssh-keepalive-proxy{,-codex2}.service` 设置 `LimitNPROC=8192`。排查时先看 `pgrep -af 'tcp-keepalive-proxy 2202[67]'`、`journalctl --user -u ssh-keepalive-proxy.service -u ssh-keepalive-proxy-codex2.service`，不要恢复 `haven-session-autorecover.timer`。
- Codex 多账号必须隔离 `CODEX_HOME`，不要在同一个 `~/.codex/auth.json` 上切换登录。当前主账号入口是 `2225`/`haven-codex`/`~/.codex`，第二账号入口是 `2226`/`haven-codex2`/`~/.codex-2`，第三账号入口是 `2229`/`haven-codex3`/`~/.codex-3`。Haven 中应保存三个独立 SSH profile；打开哪个 profile 就使用哪个账号。
- 2026-07-13 新增统一前门 `Codex Smart`：它不是绑定某个固定账号的直达入口，而是进入 `codex-smart-shell`，把自然语言任务交给 `codex-smart` / `codex-router` 去自动判定项目、cwd、账号、模型。适合手机侧混合小任务、路由、续跑和统一投递；需要直接进入某个账号的长会话时，仍使用 `2225` / `2226` / `2229`。
- Haven 手机 profile 建议值：名称 `Codex Smart`；host 优先 `100.120.189.27`，公网备用 `charlie1990.duckdns.org`；port `2230`；user `charlie`；auth 复用现有 Codex/Haven SSH key；`autoReconnect=0`、`reconnectOnNetworkChange=0`。
- 2026-07-13 尝试通过 Haven MCP 写入 `Codex Smart` profile 时观察到：`127.0.0.1:18700/mcp` 可返回 `initialize`，但 `tools/call list_connections` 长时间无响应或 empty reply；同时手机端 frpc 会反复关闭 `phone-adb`/`phone-haven-mcp`，本机 `15555`/`18700` 监听随之消失。此时不要继续并发打 `tools/list`/`list_connections`；先修手机侧 `/data/adb/service.d/frpc.sh` 或 `/data/local/tmp/frpc_smart.sh` 常驻，再写 profile。
- 2026-07-13 若需要直接编辑 Haven DB，路径是 `/data/user/0/sh.haven.app/databases/haven.db`。手机没有可用 `sqlite3`；不要依赖 `adb exec-out su -c 'cat ...'`，它可能只拉出 4KB 假备份。正确顺序是先临时停止 `adb-phone-keepalive.timer` 避免它对 FRP ADB 执行 `adb tcpip 5555` 打断连接，抓到 `adb -s 127.0.0.1:15555 shell echo ok` 后用 root `cp` 到 `/sdcard/Download/` 再 `adb pull`，完成后必须恢复 `adb-phone-keepalive.timer`。
- 2026-07-13 USB ADB 恢复：`adb-phone-keepalive.sh` 已改为优先使用 USB
  serial（如 `ff3ef385`）执行 Haven/Tailscale 后台策略和 `tcpip 5555` 保活。
  如果 `adb devices` 和 `lsusb` 都看不到手机，问题在 USB 物理连接/手机 USB
  模式，不是 adb server；重新插拔并在手机上允许 USB 调试。
- Codex 多账号的合规共享边界：`auth.json`、`installation_id`、history、SQLite 状态、logs、cache、shell snapshots 必须账号隔离；`config.toml`、skills、项目 `AGENTS.md`、`~/.ai-context`、runbooks、`~/memory`、MCP 资源可以共享。主源是 `~/.codex/config.toml` 和 `~/.codex/skills`，`codex-shared-sync.path` 自动同步到 `~/.codex-2`；`codex2` 和 `haven-entry-codex2` 启动前也会主动运行 `~/.local/bin/codex-shared-sync --apply`。
- 2026-07-07 Codex 2 启动卡住时，先抓 `tmux -S /run/user/1000/tmux/codex2.sock capture-pane -pt haven-codex2 -S -80`。若画面停在 `Starting MCP servers ... codegraph`，问题是 Codex MCP 启动阻塞，不是账号登录或 SSH 链路。当前 `~/.config/mcp/servers.yaml` 保留 `codegraph`、`haven`、`macg` 配置但对 Codex 写入 `enabled = false`；`~/.local/bin/mcp-sync.py` 支持该字段。修复后重跑 `mcp-sync.py --apply`、杀掉 `haven-codex2` tmux 会话并重新进入。
- 2026-07-08 Codex 2 profile 打不开时，先查手机 DB 中 `4 · Fedora Codex 2` 是否被改成 `authType=PASSWORD` 且 `sshPassword/keyId` 为空。正确值是 `host=100.120.189.27`、`port=2226`、`authType=KEY`、`keyId=2ca35bc0-f05c-4313-8eba-7ed6e2e39d18`、`authMethods=KEY:2ca35bc0-f05c-4313-8eba-7ed6e2e39d18`、`autoReconnect=0`、`reconnectOnNetworkChange=0`、`lastSessionName=NULL`、`postLoginBeforeSessionManager=0`。2026-07-12 另新增 DuckDNS 备用 profile `DuckDNS · Fedora Codex 2` 指向 `charlie1990.duckdns.org:2226`，不要覆盖原 Tailscale profile。
- 2026-07-12 Codex3 DuckDNS SSH：路由器持久转发 `2229/TCP -> 192.168.123.71:2229`，Haven profile `DuckDNS · Fedora Codex 3` 指向 `charlie1990.duckdns.org:2229`。手机端 `nc` 实测 `2226`/`2229` 均 open。保留原 Tailscale profile 作为主/低延迟入口。
- 2026-07-12 如果 Haven 里的 DuckDNS Codex profile 日志显示 `Connecting to 198.18.x.x port 2226/2229` 后 `connection is closed by foreign host`，问题通常不是 Fedora 端 sshd/FRP，而是手机侧代理/DNS 把 `charlie1990.duckdns.org` 解析成 fake-ip。此时主用入口应是 Tailscale profile：账号 2 用 `01 · Codex 2 · Tailscale SSH`，账号 3 用 `02 · Codex 3 · Tailscale SSH`；DuckDNS profile 仅保留为备用。
- 2026-07-08 Codex WebTTY 入口：两个账号除了 SSH/Haven 外，还有公网浏览器入口，均为设备码代理 + ttyd + tmux，不会因浏览器断线杀 Codex。Codex 1：`http://charlie1990.duckdns.org:19899/` → frps `19899` → local device gate `127.0.0.1:19000` → backend ttyd `127.0.0.1:19881` → `ttyd-codex-entry` → tmux socket `/run/user/1000/tmux/codex.sock` session `haven-codex` → `CODEX_HOME=~/.codex`。Codex 2：`http://charlie1990.duckdns.org:19900/` → frps `19900` → local device gate `127.0.0.1:19001` → backend ttyd `127.0.0.1:19882` → `ttyd-codex2-entry` → tmux socket `/run/user/1000/tmux/codex2.sock` session `haven-codex2` → `CODEX_HOME=~/.codex-2`。外层设备码是 `w19900422`，验证后分别写 `duckdns_codex1_device` / `duckdns_codex2_device` cookie；内层 BasicAuth 仍是 `codex:w19900422`，但由 `ttyd-device-gate-proxy` 自动加给 ttyd，手机用户不再需要浏览器 BasicAuth 弹窗。2026-07-10 修复：代理注入脚本必须按 `DEVICE_COOKIE_NAME` 和 `TTYD_GATE_PORT` 生成，不能硬编码 Codex1 cookie 或 `localhost:19891`；设备码页输入完整 code 后自动提交并写一年 cookie。
- 2026-07-08 Codex WebTTY/Haven 同步修复：`haven-entry-codex{,2}` 和 `ttyd-codex{,2}-entry` 必须 attach 到同一 tmux socket/session，且不能使用 `tmux attach-session -d`。`-d` 会在新客户端连接时踢掉旧客户端，导致 Haven 和 `19899/19900` 看起来不是同一个窗口、状态不能实时同步。当前四个入口都使用 `tmux attach-session -t "$SESSION"`，允许 Haven SSH 和 WebTTY 同时挂在同一个 pane；若用户说不同步，先让手机 Haven profile 断开重连、刷新 WebTTY，再查 `tmux -S /run/user/1000/tmux/codex{,2}.sock list-clients`。
- 2026-08-10 本地交互 shell 里直接输入 `codex` 应进入 C1 的同步 tmux 窗口，
  不再直接新启一个独立 Codex TUI。`~/.zshrc` 和交互式
  `~/.config/codex-shell-env/env.sh` 都定义了 `codex()`：无参数时执行
  `~/.local/bin/codex-foot-tab-entry 1`，带参数时仍调用真实
  `~/.local/bin/codex "$@"`，所以 `codex --version` / `codex exec ...` 不受影响。
- 同日追加修正：部分本地窗口的 `PATH` 优先命中
  `~/.nvm/versions/node/current/bin/codex`，绕过 shell function 和
  `~/.local/bin`。现在 `~/.local/bin/codex` 与
  `~/.nvm/versions/node/current/bin/codex` 都是 TTY-aware wrapper：交互式无参数
  `codex` attach C1 tmux；带参数或非 TTY 透传到真实
  `/var/mnt/ai/home-offload/.nvm/versions/node/v23.11.1/lib/node_modules/@openai/codex/bin/codex.js`。
  旧 symlink 备份为 `codex.node-link`。
- 2026-07-08 Codex WebTTY 翻页修复：backend `ttyd-codex-backend.service` 和 `ttyd-codex2-backend.service` 使用自定义 index `/var/home/charlie/.local/share/ttyd-codex/index-codex1.html`、`index-codex2.html`。两个 backend 都传 `-t scrollback=50000`，对应 tmux server 也设置 `history-limit 50000`、`mouse off`；不要让 Haven 和 WebTTY wrapper 互相改 `mouse`。手机浏览器里不要只依赖 xterm 原生滚动；tmux 重连后浏览器往往只能看到当前屏，Codex TUI 还会吃掉滚轮和 PageUp/PageDown。`ttyd-device-gate-proxy` 现在提供同域 `/history` 和 `/tmux-scroll?action=up|down|bottom`；页面右下角有“上翻/下翻/到底/历史”按钮，按钮直接控制对应 tmux copy-mode。`/history` 直接从对应 tmux socket 抓最近 50000 行并用普通 HTML `<pre>` 展示，手机可正常上下滚动。
- 2026-07-13 Codex WebTTY 触摸阅读修复：三个 Codex TTY 页面必须支持手指在终端区域上下滑动历史、长按/拖选文本、系统复制。注意 Codex/tmux TUI 常在 alternate screen 里，单纯滚动 xterm viewport 不可靠；`ttyd-device-gate-proxy` 现在注入 `codex_touch_read_select`。终端区域上下滑动应调用同域 `/tmux-scroll?action=up|down&transient=1` 控制 tmux copy-mode，并由服务端短暂延迟后自动 cancel，避免页面停在历史模式导致“文字不动”；不要再加入全局 `touchmove preventDefault`、readonly textarea 保护或把终端区域设成不可选择；只允许按钮/面板区域自己拦截点击。右上角和稳定 dock 的 `1/2/3/4` 必须被拦截成常驻 iframe 标签页切换，不应整页跳转或触发离开页面确认。
- 2026-07-13 Codex WebTTY 统一界面修复：账号切换 iframe 里不得再显示自己的顶部账号切换、额度条、稳定 dock、旧右侧按钮栏或管理/Router 面板；否则父页面和子页面会叠出两个 bar。`ttyd-device-gate-proxy` 注入 `codex_child_frame_cleanup`，子 iframe 只保留终端本体；`codex_stable_router_dock`、`codex_safe_router_switch` 和 `codex_smart_account_zero` 必须只在顶层页面承担统一 UI/切换职责。排查重复 bar 时先 curl 首页确认只看到顶层一套 `codex-stable-dock`，子 iframe 应由 cleanup 隐藏自己的控件。
- 2026-07-13 Codex WebTTY 账号切换状态修复：账号 `1/2/3/4` 切换必须保持顶层 WebTTY shell 不跳转，用 `codex_smart_account_zero` 显示对应常驻 iframe，并把选中账号写入 `localStorage.codex-active-account` 和 `document.documentElement.dataset.codexActiveAccount`。不要恢复 `codex_account_navigate_switch` 顶层跳端口方案；它会丢失后台前界面。点击账号 4 后顶层 URL 可保持 `:19000/`，标题 `C4`，只有账号 4 高亮，左上额度条只显示短文本 `已用 1 天`。右侧 dock 和账号按钮是两列布局；`收` 必须收起整个 bar，只留 `展`。
- 2026-07-09 Codex WebTTY iOS 输入法修复：iOS Safari/WebKit + xterm.js hidden textarea 容易出现中文/联想输入重复、卡顿，Android 不一定复现。当前 `index-codex1.html`/`index-codex2.html`/`index-codex3.html` 已移除旧的 `codex-touch-scroll` 全局 touchmove preventDefault，并把 `.xterm-helper-textarea` 设置 `autocomplete=off`、`autocorrect=off`、`autocapitalize=none`、`spellcheck=false`。2026-07-10 用户要求恢复鼠标键盘直输，曾移除 `codex-ios-safe-input` / readonly 保护并新增 `codex-focus-input`。2026-07-11 因账号2再次出现重复输入和输入拉断，`codex-focus-input` 改为只在非 iOS 浏览器运行；iOS 不再在 `pointerdown/click/touchend` 上额外强制聚焦 xterm hidden textarea。`ttyd-device-gate-proxy` 仍提供 `POST /tmux-send?enter=0|1`，页面右侧保留“输入/输入↵”按钮作为 iOS 备用输入路径。
- 2026-07-11 Codex WebTTY 三账号 iOS 不能点出输入：`codex-ios-safe-input` 把 `.xterm-helper-textarea` 设为 `readonly` / `inputmode=none` 后，iOS Safari 点终端区域不会弹键盘，而 Android 正常。当前 `index-codex1.html`/`index-codex2.html`/`index-codex3.html` 已移除该只读保护；右侧“输入/输入↵”按钮改为打开页面内真实 `<textarea>` 面板，提交仍走 `POST /tmux-send?enter=0|1`。排查同类问题时先确认页面中不存在 `codex-ios-safe-input`，并用 `curl -u codex:w19900422 http://127.0.0.1:1988{1,2,3}/ | rg 'codex-input-panel|codex-ios-safe-input'` 验证。
- 2026-07-11 Codex WebTTY 任务管理：右侧 `Session` 按钮必须打开 `/sessions`，不是简单 `/status` 弹窗。`ttyd-device-gate-proxy` 提供 `/sessions` 和 `/sessions.json`，同页列出 Codex 1/2/3 的 tmux session、pane、客户端数、最近画面、最近归档，并提供“打开终端 / 进度 / 归档 / 立即归档 / 恢复 / 归档重启”。验证：`curl -L 'http://127.0.0.1:19000/sessions?device=w19900422' | rg 'Codex 任务管理|Codex 1|Codex 2|Codex 3'`，三个 gate `19000/19001/19002` 都应可打开。不要把这个入口退回成只显示 pane 状态的按钮。
- 2026-07-11 Codex WebTTY 额度按钮：右侧必须有 `额度` 按钮，打开 `/quota`；左下“管理”和 `/sessions` 页也应能进入额度页。`ttyd-device-gate-proxy` 从各账号 `~/.codex*/sessions/**/*.jsonl` 最新 `token_count.rate_limits` 事件读取额度，`/quota` 显示动态 bar 并每 30 秒拉 `/quota.json` 更新，包含 5 小时额度、7 天额度、重置时间、plan、tokens。Codex3 若官方 `rate_limits.primary/secondary` 为 null，则额外只读查询 `sub2api-postgres`，但只有 `usage_logs` 存在时才可信显示 sub2api 剩余额度百分比；当前 Codex3 走 `127.0.0.1:19093` 自写代理绕过 sub2api，`usage_logs=0`，因此不得把 `api_keys.quota=1000/quota_used=0` 显示为真实 100%。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19002/quota.json | jq '.accounts[] | select(.account=="3") | {official:.rate_limits.primary, trusted:.sub2api.usage_trusted, percent:.sub2api.api_key_remaining_percent, tokens:.token_usage.total_token_usage.total_tokens}'`。
- 2026-07-11 Codex3 -> sub2api TTY 用量同步：`~/.local/bin/codex3-sub2api-usage-sync` 每分钟由 `codex3-sub2api-usage-sync.timer` 执行，读取 `~/.codex-3/sessions/**/*.jsonl` 的 `token_count.total_token_usage` 增量，幂等写入 sub2api `usage_logs`，`user_agent='codex3-tty-sync'`、`inbound_endpoint='/codex3/tty'`。它同步的是真实 TTY token 用量，不是官方 5h/7d 剩余额度；当前 sub2api 没有 channel/pricing 配置，所以 `total_cost=0`，`money_usage_trusted=false`，不得显示金额剩余额度百分比。验证：`systemctl --user is-active codex3-sub2api-usage-sync.timer`；`sudo podman exec sub2api-postgres psql -U sub2api -d sub2api -c \"select count(*),sum(input_tokens),sum(cache_read_tokens),sum(output_tokens),sum(total_cost) from usage_logs where user_agent='codex3-tty-sync';\"`。
- 2026-07-11 Codex WebTTY 首页额度状态条：除右侧 `额度` 按钮外，三个首页 `index-codex1.html`/`index-codex2.html`/`index-codex3.html` 必须有 `#codex-quota-strip`，固定在左上方，直接显示当前账号 `5h xx%` 和 `7d yy%` 两条小 bar，并每 30 秒从 `/quota.json` 刷新当前账号数据。Codex3 官方额度为空且 sub2api 没有可信 usage logs 时，首页显示 `真实 <tokens>k tok` / `未记账`，浮窗卡片显示 `真实 tokens` 和 warning；不得显示 `后台 100%`。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19002/ | rg 'codex-quota-strip|真实 tokens|未记账'`。
- 2026-07-13 Codex WebTTY 额度条恢复：`#codex-quota-strip` 由 `~/.local/bin/ttyd-device-gate-proxy` 注入，不是 backend ttyd 自带。若左上角额度条消失，先确认 `injectDeviceCodeScript()` 包含 `codex_simple_top_bars`、`codex_quota_panel_enhance` 和 `codex_ui_override`，且不要引用已不存在的旧函数；再重启 `ttyd-codex{,2,3,4}.service`。`/quota.json` 现在还应返回 `account_age.used_days/days_text`，首页条和额度浮窗显示“已用 N 天”。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | rg 'codex_simple_top_bars|codex-quota-strip|已用'`；`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/quota.json | jq '.accounts[] | {account,age:.account_age.days_text}'`。
- 2026-07-13 Codex WebTTY 离开确认/静默重连：`ttyd-device-gate-proxy` 必须注入 `codex_no_leave_confirm_reconnect`，拦截 `beforeunload` 注册并在 WebSocket close/error 后轮询 `/status`。不要再对隐藏账号 iframe 或当前未选中的账号触发整页 reload；只有当前可见终端对应的账号断连并且 `/status` 连续恢复后，才允许它自己的页面 reload。页面右下角应显示轻量“连接恢复中/连接中断”状态，并保留一个手动“重连”按钮作为兜底。用户已要求取消所有跳转离开确认，服务或配置变化后浏览器应尽量无感恢复，不再要求手动按 Enter。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | rg 'codex_no_leave_confirm_reconnect|visibleSurface|连接恢复中|重连'`。
- 2026-07-13 Codex WebTTY 稳定性加固：`codex_no_leave_confirm_reconnect` 不能在 WebSocket 一次 close 后立刻刷新。当前策略是至少等待 10 秒、`/status` 连续 3 次健康、页面是当前可见账号、页面不在后台且没有聚焦输入框时才自动 reload；否则只显示手动“重连”。`codex_ui_auto_reload` 每 60 秒检查 UI 版本，且要求连续 2 次版本不一致，仅当前可见 surface 才刷新。`/quota.json` 有 10 秒进程内缓存，sub2api 查询有 15 秒 `/run/user/1000/codex-webtty-sub2api-quota.json` 共享缓存，避免多账号 iframe 同时刷新时反复 `sudo podman exec sub2api-postgres`。WebTTY gate/backend 的 `RestartSec` 为 `2s`，不要恢复到 `500ms`。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | rg 'MIN_RELOAD_MS=10000|setInterval\\(check,60000\\)|codex_ui_auto_reload'`，连续两次 `curl http://127.0.0.1:19000/quota.json` 第二次应明显更快。
- 2026-07-17 Codex WebTTY 手机 IME 闪烁修复：手机上“终端一直闪烁/打断输入法输入”通常是前端自动 reload、WebSocket 重连扫描、UI 版本刷新或 iframe 焦点变化打断 Android/iOS 组合输入，不是 tmux/Codex 后端优先问题。`ttyd-device-gate-proxy` 必须注入 `codex_mobile_ime_stability`，并把所有自动 `location.reload()` 改走 `codexSafeReload('auto')`；手机处于 composition、`input/textarea/select/contenteditable`、iframe 聚焦或最近 5 秒有输入事件时，只显示“自动刷新已暂停”与手动刷新按钮，不得刷新当前页面。Workbench 首页只应懒加载当前账号 iframe；状态轮询在 `document.activeElement` 是 iframe/input 时必须跳过。验证：`node --check ~/.local/bin/ttyd-device-gate-proxy`；`for p in 19000 19001 19002 19003 19004 19005 19006; do curl -fsS -H 'X-Device-Code: w19900422' "http://127.0.0.1:$p/?view=frame" | rg 'codex_mobile_ime_stability|codexSafeReload'; done`；同时确认 backend 仍满足 `curl -u codex:w19900422 http://127.0.0.1:19881/ | rg 'codex-input-panel'` 且不命中 `codex-ios-safe-input`。修改后重启 `ttyd-codex{,2,3,4,5,6,7}.service` 和 `mobile-ai-workbench.service`。
- 2026-07-17 C7 WebTTY 仍闪烁的追加修复：`codex_ttyd_reconnect_autofix` 旧扫描器会每 3 秒扫描 ttyd 断线文本并在 WebSocket close/error 后快速刷新，手机输入法场景下可形成反复 close/open。`~/.local/bin/ttyd-device-gate-proxy` 的 `injectDeviceCodeScript()` 不应再注入 `codex_ttyd_reconnect_autofix`，只保留 `codex_no_leave_confirm_reconnect`；该脚本必须包含 `MIN_RELOAD_MS=10000` 和 `OK_REQUIRED=3`，并在输入/后台/非可见账号时只显示手动重连。C7 修复只需重启 gate：`systemctl --user restart ttyd-codex7.service`，不要为这个问题重启 `ttyd-codex7-backend.service` 或杀 tmux。验证：`curl -fsS -H 'X-Device-Code: w19900422' 'http://127.0.0.1:19006/?view=frame' | node -e "let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>console.log({ime:s.includes('codex_mobile_ime_stability'),safe:s.includes('codexSafeReload'),slow:s.includes('MIN_RELOAD_MS=10000'),stable:s.includes('OK_REQUIRED=3'),old:s.includes('codex_ttyd_reconnect_autofix')}))"`，`old` 必须为 `false`。
- 2026-07-17 多账号页面仍闪烁的追加修复：顶层 WebTTY 页里高频装饰状态脚本也会造成手机端重绘/resize 闪烁，尤其是账号卡片、额度条、节点标签、工作区可用性、任务状态这些 1-5 秒轮询 + MutationObserver 的脚本。当前 `~/.local/bin/ttyd-device-gate-proxy` 通过后置覆盖函数停止注入 `codex_simple_account_surface`、`codex_account_status_list`、`codex_main_bar_task_status`、`codex_account_button_stable_layout`、`codex_account_button_quota_bars`、`codex_account_egress_labels`、`codex_account_workspace_availability`；保留基础终端、输入、打断、账号切换和慢重连。修改后只重启 gate：`systemctl --user restart ttyd-codex.service ttyd-codex2.service ttyd-codex3.service ttyd-codex4.service ttyd-codex5.service ttyd-codex6.service ttyd-codex7.service`。验证 19000-19006 顶层和 `?view=frame` 均不含上述脚本、不含 `codex_ttyd_reconnect_autofix`，但含 `MIN_RELOAD_MS=10000` 和 `setInterval(check,60000)`；再观察 `journalctl --user -u ttyd-codex*.service --since '30 seconds ago'` 不应出现成片 `WS closed`/`WS /ws` 循环。
- 2026-07-17 页面像被上下拖动的追加修复：若手机 WebTTY/Workbench 不是刷新而是页面跟手上下位移、rubber-band、地址栏/键盘引起 viewport 抖动，修触摸滚动层。`~/.local/bin/ttyd-device-gate-proxy` 必须给普通页、`?view=frame` 和 iOS fallback 注入 `codex_mobile_viewport_lock`，它设置 `--codex-vvh`、`position:fixed`、`overflow:hidden`、`visualViewport` resize/scroll 归零，并拦截非输入/面板区域的 `touchmove`。`~/.local/bin/mobile-ai-workbench` 必须给 Workbench 首页、`/windows` 和 `/browsh` 容器页注入 `maw_mobile_viewport_lock`，避免父容器 iframe 被拖动。验证：`curl -H 'X-Device-Code: w19900422' 'http://127.0.0.1:19000/?view=frame' | rg 'codex_mobile_viewport_lock|--codex-vvh|visualViewport'`；`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/ | rg 'maw_mobile_viewport_lock|--maw-vvh|visualViewport'`。改完重启 `ttyd-codex{,2,3,4,5,6,7}.service` 和 `mobile-ai-workbench.service`。
- 2026-07-17 三四秒仍动的追加修复：继续从实际 HTML 抽 `setInterval`/`setTimeout`，不要只看源码函数是否存在。最终手机稳定版停掉了 `codex_smart_account_zero`、`codex_safe_router_switch`、`codex_external_tools`、`codex_project_float`、`codex_dock_dedupe`、`codex_safe_sub2api_import` 以及所有账号状态/额度/年龄装饰脚本；同时移除了 `codex_mobile_viewport_lock` 和 `maw_mobile_viewport_lock` 里的 `setInterval(lockScroll,1000)`，只在真实 scroll/resize/visualViewport 事件时归零。验证命令：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | node -e "let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{for(const m of s.matchAll(/setInterval\\((.{0,80}?),\\s*(\\d+)\\)/gs)) console.log(m[2], m[1].replace(/\\s+/g,' '))})"`；WebTTY 不应再有 1-5 秒定时器，当前只保留 15s `codex_interrupt_watch`、30s quota strip、60s UI version check。Workbench 首页不应再有 `setInterval(lockScroll,1000)`，只保留 15s 任务状态刷新。
- 2026-07-13 Codex WebTTY 连接评分：`ttyd-device-gate-proxy` 注入 `codex_connectivity_score`，每个可见账号页面左上显示“连接”评分、最近 20 次 `/status` 成功率、平均网页延迟，以及持久化的“今日/本周”断线与失败率。统计保存在浏览器 `localStorage`，按账号分桶；页面刷新、切账号、短时重连后，历史断线不应归零。一次 WebSocket 异常可能同时触发 `error` 和 `close`，脚本需要按时间窗去重，只记一次断线。评分在浏览器端测量，反映手机/公网实际网页访问体验，不是只看 Fedora 本地进程。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | rg 'codex_connectivity_score|ccs-hist|codex-connectivity-v2'`。无头 curl/iframe 探测可能留下 `2x1` tmux client；若画面变窄，先 `tmux -S /run/user/1000/tmux/codex.sock list-clients -F '#{client_name} #{client_width}x#{client_height}'`，detach `2x1` client 后对对应 `haven-codex*:0` 执行 `set-window-option window-size manual` 和 `resize-window -x 100 -y 30`。
- 2026-07-13 Codex CLI wrapper 修复：账号 1/2 WebTTY 若显示 server/backend 问题且 `haven-codex{,2}.service` 日志反复 `FAILED reason=pane-exited`，先跑 `~/.local/bin/codex --version`。`~/.local/bin/codex` 不得硬编码已不存在的 `~/.nvm/.../bin/codex`；应调用当前全局包入口。若报 `Missing optional dependency @openai/codex-linux-x64` 或二进制 core dump，说明 npm 全局安装损坏；清理阻塞的 `~/.nvm/versions/node/v22.22.3/lib/node_modules/@openai/.codex-*` 临时目录后重跑 `~/.nvm/versions/node/v22.22.3/bin/npm install -g @openai/codex@latest`，再验证 `codex-cli 0.144.x`、重启 `haven-codex.service haven-codex2.service ttyd-codex{,2}.service`。
- 2026-07-11 Codex WebTTY 额度语义修正：所有额度 UI 必须显示“剩余额度”，不是 `rate_limits.*.used_percent` 的已用值；计算为 `100 - used_percent`。首页状态条文案为 `剩余`，浮窗和 `/quota` 详细页文案为 `5h/7d 剩余`。右侧 `额度` 按钮在首页必须打开 `#codex-quota-modal` 浮窗，不应直接跳离终端；浮窗内三账号卡片显示剩余 bar，并点击跳转到对应账号 WebTTY，用于选择剩余额度最多的账号执行任务。`/quota.json` 应返回 `account_url`。验证：`curl -L 'http://127.0.0.1:19000/quota.json?device=w19900422' | jq '.accounts[] | {label, used:.rate_limits.primary.used_percent, account_url}'`；首页 HTML 应命中 `codex-quota-modal|5h 剩余|点击切换到该账号执行任务`。
- 2026-07-11 Codex WebTTY 额度档位：给手机首页和额度浮窗显示 `高/中/少/紧张/未知`，并保留百分比。档位基于剩余值：`>=70 高`、`35-69 中`、`15-34 少`、`<15 紧张`。官方 `rate_limits.primary/secondary` 缺失时不要用 token 总量臆测官方额度；Codex3 只有在 `sub2api.usage_trusted=true` 时才可显示 `sub2api 后台` 百分比，否则只显示真实 token 消耗和“未记账/无法计算剩余额度”。
- 2026-07-11 Codex WebTTY 账号切换：右上角 `1/2/3` 必须像浏览器标签页一样切换常驻页面，不应触发“是否离开页面”或整页刷新。`ttyd-device-gate-proxy` 的 `accountSwitchScript()` 只在顶层页面渲染切换器，`1/2/3` 是按钮不是跨端口裸链接；其他账号用常驻隐藏 iframe 预热，点击只切换 iframe 可见性。子 iframe 里不会再渲染账号切换器。iframe 层级必须是 `z-index:2147483646`，仅低于顶层 `1/2/3` 切换器，高于父页面额度/管理按钮，这样切到账号 2/3 时显示对应账号自己的额度按钮和额度条。验证：`curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | rg 'window\\.top!==window\\.self\\)return|document\\.createElement\\('\"'\"'button'\"'\"'\\)|z-index:2147483646'`，且不应命中 `location.href=href` 或旧的 `z-index:99990`。
- 2026-07-08 Codex WebTTY 账号标识：19899/19900 仍是两套独立账号入口。backend 分别使用 `/var/home/charlie/.local/share/ttyd-codex/index-codex1.html` 与 `index-codex2.html`，页面 title 和右上角角标分别显示 `Codex 1 | ~/.codex`、`Codex 2 | ~/.codex-2`，避免手机浏览器缓存或多标签切换时误看成同一个账号。
- 2026-07-08 Crush SSH 入口：服务端已新增 `haven-entry-crush`、`ssh-keepalive-proxy-crush.service`、sshd `Port 22030`/`ForceCommand haven-entry-crush`、SELinux `ssh_port_t:22030`、FRP `fedora-ssh-crush-2227`。手机 SSH app/Haven profile 应新增 `Fedora Crush`，host 优先 `100.120.189.27` 或公网 `charlie1990.duckdns.org`，port `2227`，user `charlie`，auth key 复用 Codex/Haven key，autoReconnect=false。若需要自动写手机 profile，先恢复 ADB `192.168.123.22:5555`。
- Do not enable Haven's built-in SSH session-manager reconnect for Windows/Codex/Fedora entries. Connection logs showing `pending/reattach sent on prompt ... exec sh -c 'if ! command -v tmux ...'` mean Haven is typing a long Unix reattach command into the shell and blocking input until it finishes.
- If `list_sessions` shows `sessionManager: "TMUX"` for Windows or plain Fedora terminals, pull `/data/user/0/sh.haven.app/files/datastore/haven_preferences.preferences_pb`, verify `strings` shows `session_manager` + `NONE`, and only restore from backup if the app rejects the preference.
