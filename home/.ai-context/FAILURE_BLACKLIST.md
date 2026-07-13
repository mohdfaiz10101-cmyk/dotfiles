# Failure Blacklist

## Do Not Repeat These Paths
- Do not assume `duckdns:18080` failure means local ttyd is down. Check local, LAN, router NAT, then public URL.
- Do not leave `tmux mouse on` for OpenClaw ttyd. It causes ttyd/xterm mouse tracking symptoms.
- Do not enable or start `ydotool-bridge.service` unless the user explicitly asks for KVM remote input.
- Do not broad-search browser profiles or container overlay directories for port/config tasks.
- Do not use `path` as a zsh loop variable; it overwrites the shell `PATH`.
- Do not use router Web form as the first write path when it times out. Prefer SSH `/usr/sbin/nvram` plus `/sbin/restart_firewall`.
- Do not reinstall CodeGraphContext with system Python 3.14. Use the existing `uv` Python 3.12 tool environment so Tree-sitter remains available.
- Do not force-rebuild every repository when CodeGraphContext reports a cross-repository relative-path error. First run `codegraphcontext list`, `stats`, and a symbol query; version 0.5.1 can finish indexing before its global post-processing emits that error.
- Do not treat MCP `Transport closed` as a server defect before checking `mcp-orphan-killer`. The orphan cleaner must preserve both `opencode` and `codex` ancestors.
- Do not configure Haven as a direct OpenCode `type:remote` MCP. OpenCode attempts legacy SSE GET and Haven serves Streamable HTTP; use the local `mcp-remote` stdio adapter.
- Do not cold-start phone Haven while the phone remains locked and assume MCP is healthy just because `:8730` is listening. Haven can enter a half-started state where TCP accepts connections but `initialize` never responds; wake/unlock the phone, foreground `sh.haven.app/.MainActivity`, and probe `127.0.0.1:8730/mcp`.
- Do not proxy Haven Streamable HTTP with `http.client.HTTPResponse.read(65536)`. Long-lived MCP responses may never reach EOF; use `read1()` so available response data is forwarded immediately.
- Do not point FRP proxy `fedora-console-18080` at desktop PiP `19092`. Public `18080` must map to local ttyd `8080`.
- Do not turn `opencode-18910-local.service` into a second `opencode serve`
  backend for review workspaces. `18910` is the LAN/public Web entry and must
  remain a proxy to `4096` so Device Match, Fast panel, OP dock, Task, Verify,
  Queue, Logs and rollback controls keep working. Use a separate port or
  OpenCode workspace/session metadata for review isolation. The current review
  isolation path is the fixed worktree
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace-review`, not a second
  backend.
- Do not set a Haven SSH profile's TCP port to HTTP ports `18080` or `18910`. Use the dedicated SSH ingress ports `2223`/`2224`; sshd `ForceCommand` selects the matching OpenCode entry.
- Do not assign Haven profile 2 (`OpenCode 18910`) as `mcp_tunnel_endpoint_profile_id`; it becomes a headless tunnel with no terminal. The local ADB MCP bridge is the active Haven transport, so keep that preference empty.
- Do not re-enable `haven-mcp-watchdog.timer` or keep `haven-mcp-bridge.service` always-on. The watchdog repeatedly calls phone `127.0.0.1:8730/mcp`, local `127.0.0.1:8732/mcp`, restarts the bridge, and can foreground Haven. Haven MCP should start only for explicit Haven SSH configuration/debug tasks.
- Do not update DuckDNS from Fedora's observed external IP or with an empty `ip=` parameter. Fedora may egress through a proxy/VPN; read the router's `wan0_ipaddr` and submit it explicitly.
- OpenCode 1.17.8 MCP entries require `type`, array-form `command`, and
  `enabled`; the older `command` string plus separate `args` format prevents
  `opencode.service` from starting.
- Do not use `session-guard.sh` as an OpenCode 1.17.8 hook. It watches the stale
  `~/.config/opencode/sessions/*.md` export, not the live API/database, and can
  overwrite `memory/context.md` with obsolete context. Use the OpenCode plugin
  `session.idle` event and live `/session/<id>/message` API.
- Do not require every task to call Letta, memory-engine, and server-memory
  mechanically. It inflates context and is routinely skipped. Broad recall is
  performed by `agent-lifecycle`; direct MCP calls are for deep/conflicting or
  high-risk history only.
- Do not repeatedly hammer Windows SSH for phone USB ADB fallback after
  OpenSSH returns `Exceeded MaxStartups` or immediate `Connection reset`.
  Windows is reachable at TCP level, but `sshd` is refusing sessions; restart
  Windows OpenSSH Server or wait for stale unauthenticated sessions to clear.
- Do not type `rpm ostree` with a space on Fedora Silverblue. The command is
  `rpm-ostree` with a hyphen. OpenCode has a local wrapper that auto-adds
  non-interactive sudo for write actions. For ordinary new package installs,
  agents must use `rpmi <package...>` first; it wraps
  `rpm-ostree install --apply-live --idempotent -y` to reduce required
  reboots. Use bare `rpm-ostree install|uninstall|upgrade|rebase ...` only
  when `rpmi` is not applicable or has failed, and report when a reboot is
  still required.
- Do not point a systemd `.path` unit at generated OpenCode knowledge output
  directories such as `~/.ai-context/runbooks` or files rewritten by the same
  service it triggers. It can create a maintainer loop that stalls OpenCode
  tasks. Watch hand-written config/rule files only, and make queue consumers
  avoid rewriting files when there is no state change.
- Do not enable every OpenCode MCP by default for convenience. OpenCode can
  spawn a full MCP set per active session, so 20 enabled MCPs may multiply into
  several process sets, push `opencode.service` over MemoryHigh, and make
  `:18910` look unstable. Keep only core MCPs enabled and turn heavy/UI/external
  MCPs on when a task actually needs them.
- Do not add a new MCP to OpenCode with `enabled: true` unless it has been
  classified as `core` in `~/.ai-context/MCP_POLICY.md`. New MCPs should start
  as on-demand, be matched with a recommended agent and trigger words, and be
  enabled temporarily only for tasks that need them.
- Do not start long-lived deployment processes directly inside an OpenCode
  task session (`podman/docker run`, `compose up`, background `npm dev/start`,
  `nohup`, `disown`, etc.). Create a user systemd service under
  `~/.config/systemd/user/`, then run `systemctl --user daemon-reload` and
  `systemctl --user enable --now <service>`. Direct session-spawned services
  can remain in the OpenCode cgroup, inflate Memory/Tasks/IO pressure, interrupt
  sessions, and make `18910` appear unstable.
- Do not keep on-demand/high-cost MCPs enabled by default just because they are
  useful sometimes. On 2026-07-05 OpenCode ABRT plus near-NPROC pressure killed
  MCP/codex child processes and stopped OP tasks; keep `codex` and `gelab-zero`
  disabled by default and enable them only for matching tasks.
- Do not treat OP task stops as only a post-task learning problem. First inspect
  runtime evidence: `journalctl --user -u opencode.service -u
  opencode-health-watchdog.service`, `opencode-resilience-score --json`, pids
  pressure, enabled MCPs, and `opencode-crash-auditor` output.
- Do not judge delegated OP tasks from the title list alone. Check
  `~/.local/bin/op-task-reliability --json` first; it combines queue state,
  heartbeat freshness, checkpoint presence, watchdog/fallback state, and
  post-task review readiness. A task can have a session row but still be
  `failed` if `opencode run --attach` exited before assistant output.
- Do not diagnose phone `frpc` `EOF` / `session shutdown` as an FRPS outage
  before checking proxy and DNS state. On 2026-07-08 Fedora shell had
  `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY=127.0.0.1:7890`, which made manual
  frpc tests fail until those vars were unset; the phone resolved
  `charlie1990.duckdns.org` to fake-ip `198.18.0.29`, and phone shell UID was
  not included in Tailscale VPN UID routing. Verify clean env, DNS answer, UID
  VPN inclusion, and direct TCP reachability before changing FRPS.
- Do not use `tmux attach-session -d` in the Codex Haven/WebTTY entry scripts.
  `-d` detaches other clients, so Haven SSH and `19899`/`19900` WebTTY cannot
  stay realtime-synced on the same tmux pane. Use plain
  `tmux attach-session -t "$SESSION"` for `haven-entry-codex{,2}` and
  `ttyd-codex{,2}-entry`.
- Do not save Termix server-side SSH targets as `charlie1990.duckdns.org` when
  Termix itself runs on Fedora. The Termix backend connects from Fedora, so
  DuckDNS can hairpin to the public WAN IP and fail with `EHOSTUNREACH`; use
  `127.0.0.1` with the mapped ports instead.
- Do not run broad/bursty `ssh-keyscan` loops against local SSH ports during
  health checks. OpenSSH can activate `srclimit_penalise` for connections that
  do not authenticate, temporarily dropping 22028/22030 and making
  Codex2/Crush look offline.
- Do not debug Codex WebTTY input failures on `19899`/`19900`/`19901` by
  repeatedly guessing ttyd/xterm causes, restarting ttyd first, or doing broad
  web searches. For symptoms like "输入框无法点击/无响应/重复输入" on iOS
  Safari, first read `haven.md` and `input-capture.md`, then verify the known
  local state: `codex-ios-safe-input` must be absent, `codex-input-panel` must
  be present, and `/tmux-send?enter=0|1` must work on the matching
  `19881`/`19882`/`19883` backend. If assistant output repeats or goes empty
  twice, stop the same reasoning path and reroute to `ops-dispatcher` with
  bounded local verification commands.

## Known Traps
- Padavan Web UI may intermittently time out even when router is reachable.
- Runtime `iptables` fixes on the router are not persistent. Persist port forwards with `/usr/sbin/nvram set ...`, `/usr/sbin/nvram commit`, then `/sbin/restart_firewall`.
- Phone root/shell network tests can differ from app behavior. Tailscale on
  Android may be per-UID; a service started as `shell` or root can miss the
  VPN routes even when the Tailscale app itself is online.
- `wlr_virtual_keyboard_v1` can appear in Sway inputs and is not by itself evidence of mouse capture.
- CodeGraphContext 0.5.1 global mode may mention a file from another indexed repository while finalizing a new repository. The graph can still be usable; verify the target symbol before retrying.
- Codex MCP paths must use current absolute locations under `/var/home/charlie`; old `.npm-global`, removed `~/agi`, and missing `~/.local/lib` paths are stale migration artifacts.
- Do not let `opencode-post-review` prompt wording trigger a continue loop on FAIL/UNCLEAR tasks. The post-review prompt must explicitly say "停止执行，直接回复用户" for non-PASS grades; "下一轮必须先补可复测验证" is interpreted as "continue working" and creates infinite retry loops.
- Do not create feedback cards, learning, auto-verify, or another visible
  post-review for sessions whose user/assistant text contains
  `[agent-lifecycle-post-review]`. Those are already visible review summaries;
  treating them as ordinary completed tasks creates "review of review" loops
  and floods the session list.
