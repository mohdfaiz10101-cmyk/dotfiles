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
- Huly: `huly.service` (Docker/Podman compose) `:8087`; 综合工作区：项目、任务、文档、聊天和协作；入口 `http://100.120.189.27:8087/`；Hub 入口 `/go/huly`
- Mattermost: `mattermost.service` (Docker/Podman compose) `:8065`; 频道聊天、机器人、Webhook、图片和 AI 协作入口；入口 `http://100.120.189.27:8065/`；Hub 入口 `/go/mattermost`
- Plane: `plane.service` (Docker/Podman compose) `:8090`; 项目进度、任务、周期、模块和路线图主系统；手机浏览器/PWA HTTPS 入口 `https://fedora-termhive.tail60cff7.ts.net/`；官方 Plane mobile app 不支持当前 Community Edition 自托管登录；管理兜底入口 `http://100.120.189.27:8090/god-mode/`；Hub 入口 `/go/plane`
- Open WebUI: podman `:3001`，通用对话前端（无知识库编排）
- n8n: podman `:5678`
- ntfy: `container-ntfy.service`, local/LAN `:2586`, DuckDNS public
  `http://charlie1990.duckdns.org:19867/`; router post-iptables inserts
  public `19867/TCP -> 192.168.123.71:19867` before the Padavan DMZ catch-all.
  Main topic: `charlie-actions`.
- Compose: `~/ai/fastgpt/docker-compose.yml`, config `/var/mnt/ai/fastgpt/config/config.json`
- Runbook: `~/.ai-context/runbooks/ai-infra.md`, `~/.ai-context/runbooks/fastgpt.md`

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
- Client installed on Fedora Silverblue via official RPM repo
  `/etc/yum.repos.d/netbird.repo` and layered package `netbird`.
- Version installed on 2026-07-14: `netbird 0.74.4`.
- System service: `netbird.service` (system), enabled and running.
- Current expected post-install state before account binding:
  `netbird status` returns `Daemon status: NeedsLogin`.
- To bind this machine to a NetBird network, run either interactive SSO
  `netbird up` or setup-key mode:
  `netbird up --management-url <URL> --setup-key <KEY>`.

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

## Verification Commands
- Local: `curl --noproxy '*' http://127.0.0.1:18080/`
- LAN: `curl --noproxy '*' http://192.168.123.71:18080/`
- DuckDNS: `curl --noproxy '*' http://charlie1990.duckdns.org:18080/`
- Router snapshot: `~/.local/bin/router-config-snapshot.sh`
- FRP status: `curl -s 'http://admin:frp%40charlie2026@127.0.0.1:7500/api/proxy/tcp' | jq`
