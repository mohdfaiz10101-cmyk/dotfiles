# System Map

## Required Lookup Order
Before searching broadly, agents must read:
1. `~/.ai-context/SYSTEM_MAP.md`
2. `~/.ai-context/FAILURE_BLACKLIST.md`
3. Relevant files in `~/.ai-context/runbooks/`
4. `~/memory/router-infra.md`

Do not run broad `rg` over `~/.config`, `~/.local`, browser profiles, or container overlay trees unless the map and runbooks do not cover the task.

## Host
- Host: Fedora Silverblue, Sway/wlroots Wayland
- Current LAN IP: `192.168.123.71`
- Router: `192.168.123.1` Padavan, HTTP basic auth `admin:admin`, SSH `admin@192.168.123.1`
- DuckDNS: `charlie1990.duckdns.org`
- Smart Smooth guard: `smart-smooth.timer` runs `~/.local/bin/smart-smooth`
  every 15 minutes to keep the desktop responsive by lowering priority of
  runaway Chromium renderers and known maintenance jobs, resetting transient
  failed user units, and stopping the `wolf.service` crash loop when Sunshine
  already owns GameStream port `48010`.

## Desktop Theme
- Unified theme: Codex dark
- Canonical palette: `~/.config/codex-theme/palette.md`
- Covers Sway, both Waybars, Kitty, Foot, Rofi, Wofi, OpenCode TUI, tmux,
  Mako, swaylock and GTK dark preference
- Runbook: `~/.ai-context/runbooks/desktop-theme.md`

## AI Infrastructure
- LiteLLM: `litellm.service` (Podman) `:4002`, `litellm-strip-proxy.service` `:4000` → `:4002`
- Config: `~/ai/litellm-config.yml`, env `~/ai/litellm.env`
- Letta: `letta-stack.service` (docker compose: postgres + chromadb + letta) `:8283`
- Embedding: `embedding-server.service` `:8286`
- FastGPT v4.8.23: podman compose (app+mongo+pgvector) `0.0.0.0:3000`; 知识库/工作流问答前端，LLM 走 `host.containers.internal:4000/v1`，向量用本地 `all-MiniLM-L6-v2`
- Unified Control Plane: Appsmith `appsmith.service` `:8089` 是唯一可视化操作窗口；Hub `hub-api.service` `:9800` 是 API/状态/链接底座；n8n `n8n.service` `:5678` 是动作总线；FastGPT 是方案/知识；OP/OpenCode 是执行器；Zulip/Mattermost 是沟通层；Plane/Huly 是项目协作层。Hub 入口：`/go/appsmith`、`/workspace`、`/api/workspace/snapshot`、`/api/workspace/command`。Runbook: `~/.ai-context/runbooks/control-plane.md`
- Mobile AI Workbench: `mobile-ai-workbench.service` `:19888` 是手机远程 AI 操作台外壳；它不替代 Codex WebTTY，而是统一嵌入 `19899/19900/19902/19903/19904` 五个账号入口，并集中显示任务、额度、网络、端口、插件、Fedora Chromium 和 Browsh 文本浏览器面板。设备码仍为 `w19900422`。路由器持久规则：`19888/TCP -> 192.168.123.71:19888`；Codex 5 WebTTY 另有公网入口 `19904/TCP -> 192.168.123.71:19904`，由 FRP 转到本机 gate `19004`。短网址入口：`/ports`、`/go/br`、`/go/bw`、`/go/c1`、`/go/c2`、`/go/c3`、`/go/c4`、`/go/c5`、`/go/hub`、`/go/fgpt`、`/go/op`。
- Mobile AI Browser: `mobile-ai-browser.service` 启动真实 Fedora Chromium，使用独立 profile `~/.config/mobile-ai-chromium`，CDP 仅监听 `127.0.0.1:9224`，由 Workbench 受设备码保护的 `/browser` 和 `/api/browser/*` 控制。启动脚本 `~/.local/bin/mobile-ai-browser` 会用 `--load-extension` 从原 Chromium `~/.config/chromium/Default/Extensions` 加载扩展代码；不要把 `9224` 暴露到公网。
- Mobile AI Browser 清理: `mobile-ai-browser-cleanup.timer` 每 10 分钟运行 `~/.local/bin/mobile-ai-browser-cleanup`，通过 CDP 保守关闭扩展更新页、空白旧页和重复 Workbench 页；Workbench `/browser` 提供 `关当前`、`清旧页`，API 为 `POST /api/browser/close` 和 `POST /api/browser/cleanup`。
- Sway 旧标签/窗口清理: `sway-tab-cleanup.timer` 每 10 分钟运行 `~/.local/bin/sway-tab-cleanup`，只关闭非焦点的旧 Chromium WebTTY/Device Match/空白窗口，并跳过 Workbench-controlled Chromium 与普通网页。
- Google 登录态持久化: desktop Chrome 源 profile `~/.config/google-chrome` 通过 `~/.local/bin/google-login-state-sync` 同步到 `~/.config/chromium` 和 `~/.config/mobile-ai-chromium`；`chrome-login-backup.timer` 每小时备份并同步，`chrome-login-watchdog.timer` 每 10 分钟检测桌面 Chrome 登录标记。Runbook: `~/.ai-context/runbooks/google-login-state.md`
- Mobile AI Browsh: `~/.local/bin/browsh` v1.8.0；`mobile-ai-browsh-backend.service` 在 `127.0.0.1:19886` 跑 ttyd，base path `/browsh-tty`；Workbench `:19888` 代理 `/browsh-tty/*` 并提供 `/browsh`/`/go/bw`，所以手机公网只需要 `19888`，不要为 `19885` 新增公网依赖。`mobile-ai-browsh-gate.service` 的 `:19885` 仅作本机/LAN 备用设备码网关。
- Huly: `huly.service` (Docker/Podman compose) `:8087`; 综合工作区：项目、任务、文档、聊天和协作；入口 `http://100.120.189.27:8087/`；Hub 入口 `/go/huly`
- Mattermost: `mattermost.service` (Docker/Podman compose) `:8065`; 频道聊天、机器人、Webhook、图片和 AI 协作入口；入口 `http://100.120.189.27:8065/`；Hub 入口 `/go/mattermost`。AI Inbox bridge `mattermost-ai-inbox.service` 轮询 `charlie-hub/ai-inbox`，下载附件到 `~/.local/share/mattermost-ai-inbox/<post-id>/`，并经 Hub `/api/mattermost/inbox` 创建待审批任务；配置/密钥在 `~/.config/mattermost-ai-inbox.env`。
- Plane: `plane.service` (Docker/Podman compose) `:8090`; 项目进度、任务、周期、模块和路线图主系统；手机浏览器/PWA HTTPS 入口 `https://fedora-termhive.tail60cff7.ts.net/`；官方 Plane mobile app 不支持当前 Community Edition 自托管登录；管理兜底入口 `http://100.120.189.27:8090/god-mode/`；Hub 入口 `/go/plane`
- OpenHands GUI: podman `127.0.0.1:3001`，public
  `http://charlie1990.duckdns.org:19901/` via authenticated proxy. Runbook:
  `~/.ai-context/runbooks/openhands.md`
- n8n: podman `:5678`
- ntfy: `container-ntfy.service`, local/LAN `:2586`, DuckDNS public
  `http://charlie1990.duckdns.org:19867/`; router post-iptables inserts
  public `19867/TCP -> 192.168.123.71:19867` before the Padavan DMZ catch-all.
  Topics are defined in `~/.config/ntfy/channels.env`: `charlie-actions`
  for user actions, `charlie-network` for network monitor alerts,
  `charlie-codex` for Codex completion, and `charlie-system` for system alerts.
  Publisher helper: `~/.local/bin/ntfy-send`, including optional
  `NTFY_ACTIONS` action buttons. Android ntfy app subscriptions use the public
  base URL `http://charlie1990.duckdns.org:19867`, not the LAN URL.
- Compose: `~/ai/fastgpt/docker-compose.yml`, config `/var/mnt/ai/fastgpt/config/config.json`
- Runbook: `~/.ai-context/runbooks/ai-infra.md`, `~/.ai-context/runbooks/fastgpt.md`
- Hermes memory/session quality: for "Hermes forgets", weak task quality,
  skill misses, A2A backlog, or compression regressions, read
  `~/.ai-context/runbooks/hermes-memory-quality.md` before broad searches.
- Hermes MCP/profile quality: read
  `~/.ai-context/runbooks/hermes-mcp-quality.md` before enabling MCPs, changing
  MCP profiles, or debugging `Transport closed` / duplicate MCP starts.

## FastGPT Entry
- LAN: `http://192.168.123.71:3000`
- FRP: `http://charlie1990.duckdns.org:19894/`（frpc `fedora-fastgpt`, 3000 → 19894）
- 登录: `root` / `DEFAULT_ROOT_PSW` 环境变量；自动登录不可行（POST+JWT）
- 职责边界: FastGPT 管**知识+问答流程**，opencode 管**写代码+执行**

## FRP Tunnel
- Server: `frps.service` (system)
- Client: `frpc.service` (user), config `~/.config/frpc/frpc.toml`
- Dashboard: `http://127.0.0.1:7500` (admin / frp@charlie2026)
- Runbook: `~/.ai-context/runbooks/frp.md`

## NetBird
- Fedora NetBird client: `netbird.service` (system), v0.74.6, connected to
  management/signal. Interface `wt0`; current Fedora NetBird IP
  `100.87.171.39/16`; FQDN `fedora-171-39.netbird.cloud`; WireGuard UDP
  `44362`.
- firewalld: `wt0` is assigned to zone `trusted` so NetBird peers can reach
  Fedora services/SSH ports that already listen on `0.0.0.0`.
- iPhone peer `iphone-w422417869.netbird.cloud` is `100.87.23.147`; this is
  the iPhone's own NetBird address, not the Fedora/Hermes server address. On
  2026-08-01 it was `Connecting` with no WireGuard handshake, and Fedora ping
  to `100.87.23.147` returned destination host unreachable. Do not publish
  Hermes/WebTTY links using this address.
- Phone peer known to NetBird: `pkr110.netbird.cloud` / `100.87.37.3`, but on
  2026-07-18 it had to be unlocked and NetBird manually connected. Verified
  state after connection: Fedora `Peers count: 1/1 Connected`; Android `tun0`
  `100.87.37.3/16`; Mattermost UID `10447` and Haven UID `10371` can reach
  Fedora NetBird IP `100.87.238.153`.
- Mattermost Android app `com.mattermost.rn` was updated on 2026-07-18 to use
  `http://100.87.238.153:8065` as its active server URL.
- Haven Android app `sh.haven.app` has a `Codex · NetBird` group with NetBird
  profiles using host `100.87.238.153` for ports `2222`, `2223`, `2224`,
  `2225`, `2226`, `2227`, `2229`, `2230`, `2231-2235`, and `5900`.
  `2231-2235` are C4-C8 Haven SSH keepalive entry ports on Fedora/NetBird,
  not DuckDNS public SSH forwards.
- Runbook: `~/.ai-context/runbooks/netbird.md`; Haven details:
  `~/.ai-context/runbooks/haven.md`; helper: `~/.local/bin/netbird-selfhost-kit`.
- Android app crash/error monitor: `phone-error-log-watch.timer` runs `~/.local/bin/phone-error-log-watch` every 10 minutes; summary `~/.local/state/phone-error-log-watch/latest.md`; runbook `~/.ai-context/runbooks/phone-error-log-watch.md`.

## Unified Mihomo Control
- Sub-Store: `sub-store.service` (Podman), dashboard `127.0.0.1:19887`, data
  `~/.local/share/sub-store/`; it is deliberately loopback-only.
- Versioned rules/overlays: `~/dotfiles/mihomo/`; runbook:
  `~/.ai-context/runbooks/mihomo-control.md`.
- Android root Mihomo runtime: `/data/adb/mihomo_netbird`, service script
  `/data/adb/service.d/97-mihomo.sh`; it redirects device TCP/DNS in root
  transparent mode while leaving Android's single `VpnService` slot for
  Tailscale/NetBird. On PKR110, do not globally pin `interface-name: wlan0`
  because 5G uses `rmnet_data*`; Tailscale UID `10352` and UDP-heavy games
  such as League of Legends: Wild Rift use owner-UID bypass rules.

## Network Scenario Monitor
- `network-scenario-monitor.timer` runs every 2 minutes and writes a unified
  phone/desktop network, proxy, system-performance, and communication snapshot
  to `~/.local/state/network-scenario-monitor/latest.json`; AI-readable summary:
  `~/.local/state/network-scenario-monitor/latest.md`.
- Dashboard: `network-monitor-dashboard.service` on `0.0.0.0:19979`; local
  `http://127.0.0.1:19979/`, LAN `http://192.168.123.71:19979/`,
  Tailscale `http://100.120.189.27:19979/`. The dashboard includes
  `/actions` for bounded interactive execution: immediate capture, ntfy test,
  monitor restart, and Kuma restart.
  Uptime Kuma fallback status UI: `uptime-kuma.service` on
  `0.0.0.0:3002`; local `http://127.0.0.1:3002/`, LAN
  `http://192.168.123.71:3002/`, Tailscale `http://100.120.189.27:3002/`.
- It classifies home Wi-Fi LAN, portable/other Wi-Fi, cellular/5G, non-LAN with
  Tailnet, desktop direct/proxy HTTPS, DuckDNS, FRP ADB, ntfy, clipboard,
  Workbench, ADB paths, proxy ports, load/memory/swap/disk/PSI.
- Notification path: local ntfy `charlie-network`, only when top-level
  classification changes, when a degraded state persists for 10 minutes, or
  as a healthy heartbeat every 30 minutes. Notifications include Android ntfy
  action buttons for opening the dashboard, re-running capture, and creating a
  Hub `goose_aider` diagnosis task. Runbook:
  `~/.ai-context/runbooks/network-scenario-monitor.md`.

## DuckDNS DDNS
- Timer: `duckdns-update.timer` (300s) → `wan-ip-monitor.sh`
- Domain: `charlie1990.duckdns.org`
- Must read router `wan0_ipaddr`, never Fedora egress IP
- Runbook: `~/.ai-context/runbooks/duckdns.md`

## Haven / Phone Bridge
- Phone ADB current primary: `192.168.123.22:5555` (wireless debugging/mDNS LAN)
- Phone ADB candidates: Tailscale `100.108.28.44:5555` (not reliable; verified closed on 2026-06-25), FRP fallback `127.0.0.1:15555`
- Phone ADB keepalive: `adb-phone-keepalive.timer` runs every minute and re-applies `adb tcpip 5555` when reachable
- Haven app: `sh.haven.app`, phone MCP `127.0.0.1:8730`
- AidLux/ntfy phone agent fallback: `phone-run`, `phone-root-run`,
  `phone-status-read`, `phone-command-push`; runbook
  `~/.ai-context/runbooks/phone-agent.md`
- Local bridge: `haven-mcp-bridge.service`, `127.0.0.1:8732/mcp`, default disabled/inactive; start only for explicit Haven SSH configuration/debug tasks
- `haven-mcp-watchdog.timer` is retired/disabled; do not restore it because it repeatedly probes and starts Haven MCP
- Phone FRPC: `/data/local/tmp/frpc.toml`; proxies ADB `15555`, SSH `8022`, Haven MCP `18700`
- Phone Termux SSH: local `2222`; Magisk boot service `/data/adb/service.d/98-termux-sshd.sh`
- Haven saved entries:
  0. Fedora Terminal: `2223` → sshd `22023` → forced `haven-entry-18080`
  1. OpenCode Web: `2224` → sshd `22024` → forced `haven-entry-18910`
  2. Windows SSH: `2222` → Fedora `windows-ssh-proxy.socket` → `100.91.93.99:22`
  3. Fedora Codex: `2225` → keepalive proxy `22026` → sshd `22025` → forced `haven-entry-codex` → tmux `haven-codex` → `CODEX_HOME=~/.codex`
  4. Fedora Codex 2: phone profile currently uses Tailscale host `100.120.189.27:2226` → keepalive proxy `22027` → sshd `22028` → forced `haven-entry-codex2` → tmux `haven-codex2` → `CODEX_HOME=~/.codex-2`
  5. Fedora Codex 3: phone profile uses Tailscale host `100.120.189.27:2229` → keepalive proxy `22031` → sshd `22032` → forced `haven-entry-codex3` → tmux `haven-codex3` → `CODEX_HOME=~/.codex-3`
  5a. DuckDNS Codex 2: Haven profile `DuckDNS · Fedora Codex 2` (`aa255f76-aee3-4212-bf4b-b099034ddf40`) uses `charlie1990.duckdns.org:2226` → same Codex2 chain
  5b. DuckDNS Codex 3: Haven profile `DuckDNS · Fedora Codex 3` (`27f997b0-ef15-44b3-b688-3f004ac871b5`) uses `charlie1990.duckdns.org:2229` → same Codex3 chain
  6. Fedora VNC: `5900`
- sshd routing config: `/etc/ssh/sshd_config.d/60-haven-entry-ports.conf`
- entry wrappers: `~/.local/bin/haven-entry-{18080,18910,codex}`; Codex entry is tmux-backed so phone reconnects do not kill running tasks
- Haven global DataStore `session_manager=NONE`; do not leave it as `TMUX` or Windows/Codex terminals inherit tmux reattach probes
- Windows SSH public chain: router `2222` -> Fedora `windows-ssh-proxy.socket` -> `100.91.93.99:22`
- DuckDNS updater: `duckdns-update.timer` -> `~/.local/bin/wan-ip-monitor.sh`; it must read router `wan0_ipaddr` and submit that IP explicitly
- Runbook: `~/.ai-context/runbooks/haven.md`

## OpenCode Core
- Main: `opencode.service`, API `127.0.0.1:4097`
- Web proxy: `opencode-4096-proxy.service` `:4096`
- LAN proxy: `opencode-18910-local.service` `:18910` → `:4096`
- Session guard: `session-guard.service` (auto memory sync + context save)
- Config: `~/.config/opencode/opencode.json`
- Runbook: `~/.ai-context/runbooks/opencode-core.md`

## OpenAgents
- Service: `openagents-network.service`
- Config/workspace: `~/.openagents/network/network.yaml`, `~/.openagents/network/agents/`
- HTTP/MCP/Studio: `0.0.0.0:8700`
- gRPC agent transport: `0.0.0.0:8600`
- Auth: passwordless `public` default group for browser/local agents; `admin` and `worker` password hashes retained for privileged agent registration.
- Healthcheck: `openagents-healthcheck.timer`
- Healthcheck allowlisted entry agents: `codex-entry`, `opencode-entry`, `crush-entry`; legacy YAML collaborator agents are manual.
- Runbook: `~/.ai-context/runbooks/openagents.md`

## Telegram / OpenCode Control
- Control bot gateway: `opencode-telegram-gateway.service`
- Source: `~/opencode-telegram-gateway`
- Local health: `127.0.0.1:9811/health`
- Sole inbound owner: gateway long polling; Telegram MCP is outbound/query-only
- Non-secret architecture registry: `~/.config/telegram/architecture.json`
- OpenCode tool owner: `telegram-operator`
- Control group should use Forum topics; non-Forum fallback is one group session
- Runbook: `~/.ai-context/runbooks/telegram.md`

## Syncthing
- Service: `syncthing.service`, Web UI `127.0.0.1:8384`, sync `:22000`
- Config: `~/.config/syncthing/`
- Runbook: `~/.ai-context/runbooks/syncthing.md`

## OpenCode / OpenClaw Entry Chain
- Public OpenCode web: `http://charlie1990.duckdns.org:18910/`
- Router persistent rule: `18910/TCP -> 192.168.123.71:4096`
- LAN compatibility listener: `opencode-18910-local.socket` proxies `:18910` to `127.0.0.1:4096`
- Public URL: `http://charlie1990.duckdns.org:18080/`
- Router persistent rule: `18080/TCP -> 192.168.123.71:18080`
- Local FRP server: `frps.service`, config `/etc/frp/frps.toml`
- Local FRP client: `frpc.service`, config `~/.config/frpc/frpc.toml`
- FRP proxy: `fedora-console-18080`, `remotePort=18080`, `localPort=8080`
- Local ttyd: `ttyd-8080.service`, listens `0.0.0.0:8080`
- ttyd entry: `~/.local/bin/ttyd-openclaw-entry`
- tmux wrapper: `~/.local/bin/openclaw-tmux-wrap`
- attach loop: `~/.local/bin/opencode-openclaw-attach-loop`
- `oc` and the wrapper connect directly to `127.0.0.1:4097`; they silently
  start `opencode.service` and wait for the API before creating the tmux pane
- active OpenCode session is pinned in
  `~/.local/share/opencode/openclaw-session`; only `oc sync` or `oc ses_...`
  changes it, so unrelated background session updates cannot interrupt attach

## Haven / Phone
- Phone ADB current primary: `192.168.123.22:5555` (wireless debugging/mDNS LAN)
- Phone ADB candidates: Tailscale `100.108.28.44:5555` (not reliable; verified closed on 2026-06-25), FRP fallback `127.0.0.1:15555`
- Phone ADB keepalive: `adb-phone-keepalive.timer` runs every minute and re-applies `adb tcpip 5555` when reachable
- Haven package: `sh.haven.app`; MCP listens on phone `127.0.0.1:8730`
- AidLux/ntfy phone agent fallback: `phone-run`, `phone-root-run`,
  `phone-status-read`, `phone-command-push`; runbook
  `~/.ai-context/runbooks/phone-agent.md`
- Local Haven bridge: `haven-mcp-bridge.service`, `127.0.0.1:8732/mcp`, default disabled/inactive; start only for explicit Haven SSH configuration/debug tasks
- `haven-mcp-watchdog.timer` is retired/disabled; do not restore it because it repeatedly probes and starts Haven MCP
- OpenCode uses local `mcp-remote@0.1.38` stdio adapter for Haven Streamable HTTP
- Phone FRPC: `/data/local/tmp/frpc.toml`; proxies ADB `15555`, SSH `8022`, Haven MCP `18700`
- Phone Termux SSH: local `2222`; Magisk boot service `/data/adb/service.d/98-termux-sshd.sh`
- Haven saved entries:
  0. Fedora Terminal: `2223` → sshd `22023` → forced `haven-entry-18080` (login shell)
  1. OpenCode Web: `2224` → sshd `22024` → forced `haven-entry-18910` (OpenCode attach to local 4096/public 18910 backend)
  2. Windows SSH: `2222` → Fedora `windows-ssh-proxy.socket` → `100.91.93.99:22`
  3. Fedora Codex: `2225` → keepalive proxy `22026` → sshd `22025` → forced `haven-entry-codex` (attaches tmux session `haven-codex`, starts Codex with `CODEX_HOME=~/.codex`)
  4. Fedora Codex 2: phone profile currently uses Tailscale host `100.120.189.27:2226` → keepalive proxy `22027` → sshd `22028` → forced `haven-entry-codex2` (attaches tmux session `haven-codex2`, starts Codex with `CODEX_HOME=~/.codex-2`)
  5. Fedora Codex 3: phone profile uses Tailscale host `100.120.189.27:2229` → keepalive proxy `22031` → sshd `22032` → forced `haven-entry-codex3` (attaches tmux session `haven-codex3`, starts Codex with `CODEX_HOME=~/.codex-3`)
  5a. DuckDNS Codex 2: Haven profile `DuckDNS · Fedora Codex 2` (`aa255f76-aee3-4212-bf4b-b099034ddf40`) uses `charlie1990.duckdns.org:2226`
  5b. DuckDNS Codex 3: Haven profile `DuckDNS · Fedora Codex 3` (`27f997b0-ef15-44b3-b688-3f004ac871b5`) uses `charlie1990.duckdns.org:2229`
  6. Fedora VNC: `5900`
- sshd routing config: `/etc/ssh/sshd_config.d/60-haven-entry-ports.conf`
- entry wrappers: `~/.local/bin/haven-entry-{18080,18910,codex}`
- Haven global DataStore `session_manager=NONE`; do not leave it as `TMUX` or Windows/Codex terminals inherit tmux reattach probes
- Windows SSH public chain: router `2222` -> Fedora `windows-ssh-proxy.socket` -> `100.91.93.99:22`
- DuckDNS updater: `duckdns-update.timer` -> `~/.local/bin/wan-ip-monitor.sh`; it must read router `wan0_ipaddr` and submit that IP explicitly

## TermHive
- Repository: `~/termhive`
- Web service: `termhive-web.service`, authenticated, listens `127.0.0.1:3200`
- Agent runtime: `termhive-daemon.service`, listens `127.0.0.1:3210`
- Auth environment: `~/.config/termhive/server.env` (mode `0600`)
- LAN compatibility entry: `http://192.168.123.71:18081/` through local FRP
- Public router port `18081` is intentionally disabled until encrypted access is ready
- Phone HTTPS entry: `https://fedora-termhive.tail60cff7.ts.net/` (Tailnet only)
- Tailscale Serve: HTTPS `443` root → Plane `http://127.0.0.1:8090`; `/hub` and `/search` → Hub `http://127.0.0.1:9800`
- Login username: `charlie`; password is stored only in the auth environment file
- UI features: account login, project restore, command Snippets, Local Shell, saved key-based SSH connections, six-button phone quick dock
- Runbook: `~/.ai-context/runbooks/termhive.md`

## Code Graph
- Tool: CodeGraphContext `0.5.1`
- Executable: `~/.local/bin/codegraphcontext`
- Runtime: isolated Python `3.12` managed by `uv`
- Database: embedded FalkorDB Lite under `~/.codegraphcontext/`
- OpenCode MCP name: `codegraph`
- Codex MCP name: `codegraph`
- Indexed repositories: `~/termhive`, `~/dotfiles`, `~/hub`
- Refresh one repository: `codegraphcontext update /absolute/repo/path`
- Verify: `codegraphcontext doctor`, `codegraphcontext list`, `codegraphcontext stats`
- Git refresh hooks: `post-commit` and `post-checkout` installed in all indexed repositories
- Runbook: `~/.ai-context/runbooks/codegraph.md`

## Agent Knowledge Lifecycle
- OpenCode plugin: `~/.config/opencode/.opencode/plugins/agent-lifecycle.mjs`
- Lifecycle helper: `~/.local/bin/opencode-lifecycle.py`
- Generated verified knowledge: `~/.ai-context/AUTO_LEARNED.md`
- Generated runbook index: `~/.ai-context/runbooks/INDEX.md`
- Audit report: `~/memory/runbook-audit.md`
- Workflow Intelligence target design: `~/.ai-context/runbooks/workflow-intelligence.md`; intended shared workflow extraction/index/recall layer for Codex, OpenCode, Crush, `agent-dispatch`, and `ai-a2a`
- Workflow Intelligence helper: `~/.local/bin/workflow-intel`; timer `workflow-intel-maintain.timer` runs hourly at idle I/O priority; state in `~/memory/workflows/`
- Workflow Intelligence immediate watchers: `workflow-intel-codex-capture.path` watches `~/.codex/history.jsonl`; `workflow-intel-crush-capture.path` watches `~/.local/state/crush-eval/latest.md`
- Maintenance timer: `opencode-knowledge-maintainer.timer` (every 6h)
- Immediate config watcher: `opencode-capability-adapter.path`
- Task journal: `~/memory/opencode-task-journal.jsonl`
- Capability registry: `~/.ai-context/CAPABILITY_REGISTRY.md`
- Adaptation queue: `~/memory/agent-adaptation-queue.md`
- New MCPs, agents, relevant systemd services, rules, and CodeGraph repositories are rediscovered every maintenance cycle.
- Runbook source text remains manually curated; high-confidence runtime findings are generated separately to prevent model-written corruption.

## Codex MCP
- Config: `~/.codex/config.toml`
- `fetch`: `~/.nvm/versions/node/v22.22.3/bin/mcp-fetch-server`
- `memory-engine`: `/usr/bin/python3 /mnt/ai/data/memory-engine/memory-mcp-server.py`
- `codegraph`: `~/.local/bin/codegraphcontext mcp start`
- `macg`: `~/.local/share/macg-mcp-venv/bin/python /mnt/ai/home-offload/agi/macg_mcp.py`
- `claude-knowledge`: `~/.nvm/versions/node/v22.22.3/bin/node ~/.local/lib/windsurf-knowledge-mcp/server.js`
- MCP orphan cleaner: `~/.local/bin/mcp-orphan-killer.sh`; must preserve both Codex and OpenCode ancestors
- Verify configuration: `codex mcp list`

## Crush
- Config: `~/.config/crush/crush.json`; rules `~/.config/crush/CRUSH.md`
- Data/logs: `~/.crush`
- Shared API: `crush-tailscale.service` `0.0.0.0:7766`
- Auxiliary server: `crush-server.service` `0.0.0.0:8081`
- WebTTY: `crush-ttyd-backend.service` `:17766` with BasicAuth `crush:w19900422`
- Button API: `crush-button-api.service` `:17768`, token `w19900422`
- Shared TUI: tmux socket `/run/user/1000/tmux/crush.sock`, session `haven-crush`
- Healthcheck: `crush-healthcheck.timer`
- Models: large `step-router-v1`, small `deepseek-v4-flash`
- Runbook: `~/.ai-context/runbooks/crush.md`

## System Sanity / Desktop Cleanup
- Conservative self-clean/evolution timer: `system-sanity-evolve.timer` runs `~/.local/bin/system-sanity-evolve --fix` every 6h.
- Reports: `~/.local/state/system-sanity-evolve/latest.json` and `latest.md`.
- Scope: user systemd StartLimit section fixes, stale user-unit symlink cleanup, `~/.local/bin` backup archival, browser/tab cleanup, user failed reset, and stale `systemd-coredump@*.service` failed-marker reset only.
- Browser/workspace cleanup: `mobile-ai-browser-cleanup.timer` and `sway-tab-cleanup.timer` close only conservative old/duplicate AI tabs/windows. Workbench buttons call `/api/browser/close` and `/api/browser/cleanup`.
- OpenCode cold archive migration: `opencode-cold-archive-migrate.timer` moves old OpenCode restore/archive DB backups one item per day to `/var/mnt/ai/cache/archive/opencode-db-backups/20260718-home-clean`; active `opencode.db` is not touched.
- Runbook: `~/.ai-context/runbooks/system-sanity-evolve.md`; OpenCode archive details: `~/.ai-context/runbooks/opencode-core.md`.

## Verification Commands
- Local: `curl --noproxy '*' http://127.0.0.1:18080/`
- LAN: `curl --noproxy '*' http://192.168.123.71:18080/`
- DuckDNS: `curl --noproxy '*' http://charlie1990.duckdns.org:18080/`
- Router snapshot: `~/.local/bin/router-config-snapshot.sh`
- FRP status: `curl -s 'http://admin:frp%40charlie2026@127.0.0.1:7500/api/proxy/tcp' | jq`

## Communication Project Sync
- Near-realtime project/status sync: `comm-project-sync.timer` runs
  `~/.local/bin/comm-project-sync sync --event timer` every 60s, and Hub
  `_save_project_control()` also fire-and-forgets the helper on project changes.
- Sync targets: Mattermost `ai-tasks`, Zulip topic `Project Sync`, and ntfy
  topic `charlie-projects` via `ntfy-send projects`.
- State for comparison: `~/.local/state/comm-project-sync/latest.json` and
  `history.jsonl`; Hub exposes `GET /api/projects/comm-sync`.
- User-facing links should prefer both NetBird `100.87.238.153` and LAN
  `192.168.123.71`.  Do not revert to local-only `127.0.0.1` in Mattermost,
  ntfy, Workbench port registry, or Hub project receipts.
- Runbook: `~/.ai-context/runbooks/communication-project-sync.md`.

## Mattermost Executor Channels
- Mattermost now has explicit watched executor/IDE channels: `cursor`, `goose`,
  and `aider` in addition to `ai-inbox`, `ai-images`, `ai-docs`, and
  `ai-review`.
- `cursor`: Cursor/KasmVNC GUI IDE task intake, default Hub assignee `plan`;
  links NetBird `http://100.87.238.153:19970/`, LAN `http://192.168.123.71:19970/`.
- `goose`: read-only Goose/Guise planning/diagnosis intake, default Hub assignee
  `plan`; links NetBird `http://100.87.238.153:7694/tool/guise/`, LAN
  `http://192.168.123.71:7694/tool/guise/`.
- `aider`: approved single-writer execution intake, default Hub assignee
  `goose_aider`; links NetBird `http://100.87.238.153:7693/tool/aider/`, LAN
  `http://192.168.123.71:7693/tool/aider/`.
- `ai-tasks` remains output-only. Do not add it to watched inputs.
