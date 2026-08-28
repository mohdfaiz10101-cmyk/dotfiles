# Failure Blacklist

## Do Not Repeat These Paths
- Do not assume `duckdns:18080` failure means local ttyd is down. Check local, LAN, router NAT, then public URL.
- Do not leave `tmux mouse on` for OpenClaw ttyd. It causes ttyd/xterm mouse tracking symptoms.
- Do not enable or start `ydotool-bridge.service` unless the user explicitly asks for KVM remote input.
- Do not treat Sway workspace/window flicker or drifting windows as a pure
  compositor bug before checking remote-input and auto-window churn. On this
  host, Sunshine creates `48879:57005:*_passthrough` input devices, and
  `adb-phone-keepalive.sh` must not auto-start Sunshine unless
  `ADB_PHONE_KEEPALIVE_START_SUNSHINE=1` is explicitly set. For local Codex
  Foot tabs, do not return to the old 5-second `codex-foot-tab-sort.timer` or
  a launcher that inherits `TMUX`; use the slow maintainer path that unsets
  `TMUX`, opens missing tabs with `CODEX_FOOT_FOCUS=0`, and keeps all
  discovered `foot-codex<N>` clients on Sway workspace 1.
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
- Do not treat Fedora Silverblue/composefs `/` showing `100%` full as a real
  writable disk-full condition. The immutable root image can be `59M/59M` by
  design. Check `/var`, `/var/home`, or the actual writable Btrfs filesystem
  before alerting or cleaning.
- Do not interrupt a slow `rpmi netbird` / `rpm-ostree install netbird` merely
  because it looks idle. On 2026-07-14 the official NetBird repo was slow and
  the transaction also rebuilt the host deployment, including NVIDIA akmods,
  before reporting success. Check `journalctl -u rpm-ostreed` for package
  import, deployment creation, akmods, rpmdb, and transaction success before
  assuming it is stuck.
- Do not point a systemd `.path` unit at generated OpenCode knowledge output
  directories such as `~/.ai-context/runbooks` or files rewritten by the same
  service it triggers. It can create a maintainer loop that stalls OpenCode
  tasks. Watch hand-written config/rule files only, and make queue consumers
  avoid rewriting files when there is no state change.
- Do not run full-history workflow indexing on every Codex/Crush path event or
  every few minutes. Capture must use a bounded tail, and maintenance must run
  at idle I/O priority; otherwise it can saturate the Btrfs system disk and
  make the desktop appear frozen.
- Do not enable every OpenCode MCP by default for convenience. OpenCode can
  spawn a full MCP set per active session, so 20 enabled MCPs may multiply into
  several process sets, push `opencode.service` over MemoryHigh, and make
  `:18910` look unstable. Keep only core MCPs enabled and turn heavy/UI/external
  MCPs on when a task actually needs them.
- Do not add a new MCP to OpenCode with `enabled: true` unless it has been
  classified as `core` in `~/.ai-context/MCP_POLICY.md`. New MCPs should start
  as on-demand, be matched with a recommended agent and trigger words, and be
  enabled temporarily only for tasks that need them.
- Do not broad-search MCP/Hermes config through `.hermes/profiles/**/lsp/node_modules`
  or browser cache/profile trees. For MCP diagnostics, read mapped files first:
  `~/.hermes/config.yaml`, `~/.config/mcp/servers.yaml`,
  `~/.local/bin/mcp-profile-manager.py`, MCP logs, and the relevant runbook.
- Do not use broad `rg` over `.hermes/webui/sessions`,
  `.hermes/webui/sessions/_archive_old`, `.hermes/webui/sessions/_run_journal`,
  `.hermes/profiles/*/config.yaml.bak*`, or request dump files for routine
  Hermes memory/search diagnosis. Use `workflow-intel recall`,
  `hermes-memory-brief`, and `hermes-experience-map` first; search exact
  session IDs only when the user explicitly needs raw history.
- Do not start long-lived deployment processes directly inside an OpenCode
  task session (`podman/docker run`, `compose up`, background `npm dev/start`,
  `nohup`, `disown`, etc.). Create a user systemd service under
  `~/.config/systemd/user/`, then run `systemctl --user daemon-reload` and
  `systemctl --user enable --now <service>`. Direct session-spawned services
  can remain in the OpenCode cgroup, inflate Memory/Tasks/IO pressure, interrupt
  sessions, and make `18910` appear unstable.
- Do not mount Mattermost Postgres `POSTGRES_DATA_PATH` to
  `/var/lib/postgresql` under Podman Compose. The Postgres image uses
  `/var/lib/postgresql/data`, so Podman creates an anonymous volume at the real
  PGDATA path and the database can appear to work until `docker compose down`
  recreates an empty Mattermost. Use
  `${POSTGRES_DATA_PATH}:/var/lib/postgresql/data:Z` and verify with
  `docker inspect mattermost-docker-postgres-1 --format '{{json .Mounts}}'`.
- Do not run Mobile AI Browsh as a fresh `browsh` process for every ttyd
  WebSocket client. Opening `/browsh` in a second tab/window then starts a
  second Browsh, it exits quickly, and the page enters reconnecting. Keep
  `~/.local/bin/mobile-ai-browsh-entry` tmux-backed on session
  `mobile-ai-browsh`, and use Workbench `/api/browsh/goto` for phone-friendly
  URL navigation.
- Do not use `goose doctor` as a lightweight Goose smoke test. Goose 1.43.0
  starts an agent session and may read local context files/tools. For bounded
  verification use `goose info` plus
  `goose run --no-session --no-profile --max-turns 1 --quiet --text 'Say OK only.'`.
- Do not assume `aider` is usable just because `command -v aider` succeeds.
  On 2026-07-14 the wrapper pointed at a deleted `/mnt/ai/apps/aider-venv`
  interpreter, and the old `openai/glm-smart` model was no longer present in
  LiteLLM. Verify both `aider --version` and a bounded temp-repo smoke; choose
  a model returned by `GET http://localhost:4000/v1/models`.
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
- Do not replace `~/.local/share/WsScrcpyWeb/dependencies/scrcpy-server/scrcpy-server`
  with official scrcpy `v4.x` just because Genymobile upstream is newer. As of
  2026-07-31, `ws-scrcpy-web` latest release `v0.1.30-beta.72` still talks to
  scrcpy client protocol `3.3.4`; forcing server `4.1` makes `18082` Connect
  fail with `The server version (4.1) does not match the client (3.3.4)` and
  the page shows no Android screen. For this host, restore the bundled APK
  (`scrcpy-server.bak` / `dist-runtime/seed/scrcpy-server/scrcpy-server`) and
  restart `ws-scrcpy-web.service` unless the web client itself has been
  upgraded in lockstep.
- Do not treat Waydroid `:18082` as the final control plane. The durable path
  is CLI/MCP/Telegram through `~/.local/bin/waydroidctl` and
  `~/.local/bin/waydroid-mcp`; `ws-scrcpy-web.service` is only a visual
  fallback. If `:18082` Connect closes or shows no Android screen, first check
  Waydroid Android framework health (`service check window`, `service check
  activity`, `getprop sys.boot_completed`, `system_server` crash loop) and
  Waydroid ADB/IP reachability before changing ports or scrcpy versions.
- Do not keep Hermes Studio `hermes-web-ui.service` / `:18648` always-on or
  probe `:8648` from background health checks. It can wake gateway, spawn
  secondary Hermes tasks plus full MCP sets, and push memory/swap into a system
  stall. Keep `hermes-8648-proxy.service` light and always-on, keep
  `hermes-web-ui.service` on-demand, and make session mesh default to queue-only
  with pressure gates before launching delegated tasks.
- Do not return Hermes session mesh dispatch/handoff defaults to `both` under
  normal system pressure. Default queue-only plus bounded drain is required on
  this host; launching child sessions must check load, MemAvailable, and
  SwapUsed thresholds first.
- Do not place future cloud-Android/redroid/container workspaces under
  `/var/home/charlie`. Use `/var/mnt/ai` and a narrow wrapper/service-specific
  storage root. Do not symlink the entire `~/.local/share/containers` tree:
  existing Podman services depend on the default rootless store.
- Do not mark redroid usable on this Fedora/Podman/crun host until the Android
  init `Failed to initialize property area` / `ExitCode 129` failure is fixed.
  redroid 12 and 14 both failed even with `androidboot.use_memfd=1`,
  `--systemd=false`, explicit binder devices, disabled SELinux label, and
  `/dev/__properties__` tmpfs. Use `~/.ai-context/runbooks/redroid-cloud-android.md`
  before retrying.
- Do not keep retrying redroid on this exact Fedora Silverblue 44 kernel
  `6.19.10-300.fc44.x86_64` by switching only between Podman/crun,
  Podman/runc, Docker/runc, redroid 12, or redroid 14. On 2026-08-01 all of
  those combinations still failed with Android init
  `Failed to initialize property area` / `ExitCode 129`. The next meaningful
  redroid route is a different host/kernel/VM known to support redroid, not
  another same-host container-flag permutation.
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
  `19881`/`19882`/`19883` backend. Desktop Fcitx/IBus changes cannot affect a
  phone WebTTY; use its native `输入` / `输入↵` panel for Chinese composition.
  If assistant output repeats or goes empty twice, stop the same reasoning
  path and reroute to `ops-dispatcher` with bounded local verification
  commands.
- Do not treat Codex startup `skipped loading N skills` as an account, model,
  or network issue first. Check malformed `SKILL.md` frontmatter under
  `~/.codex/skills` / `~/.shared-agent/skills`: every loadable skill must start
  with `---` and include `name:` plus `description:` in the YAML header. On
  2026-08-28 the two skipped skills were
  `external-candidates/remotion-best-practices` and
  `external-candidates/styleseed`; fixing their frontmatter removed the
  startup warning.
- Do not point `~/.codex/skills` at the full shared skill library by default.
  On 2026-08-28 the full link exposed 461 skills and made trivial Codex tasks
  risk `exceeded skill budget` / huge startup context. Keep the default in lean
  mode with `~/.local/bin/codex-skills-mode lean`; switch temporarily with
  `~/.local/bin/codex-skills-mode full` only when a rare skill is needed, then
  return to lean.

## Known Traps
- If Fcitx5 starts but its Pinyin addon logs `libIMECore.so.0: undefined
  symbol ... consumeMaybeEscapedValue`, it is a `libime` /
  `fcitx5-chinese-addons` ABI mismatch. Stage `fcitx5-rime` with
  `rpmi fcitx5-rime` and reboot when rpm-ostree cannot apply the package set
  live. For a non-Fcitx backup before reboot, use
  `~/.local/bin/input-use-ibus`, which stops Fcitx and starts IBus LibPinyin
  through Sway; `~/.local/bin/input-use-fcitx` restores Fcitx. Never run both
  frameworks together. IBus defaults to `Super+Space` on this host; set
  `org.freedesktop.ibus.general.hotkey triggers` to `['<Control>space']`.
  `input-use-ibus` must export the IBus variables locally before calling
  `dbus-update-activation-environment --systemd`; otherwise that command can
  re-import the caller's old Fcitx values and silently undo
  `systemctl --user set-environment`. It must also publish the live
  `IBUS_ADDRESS`. For no-reboot app launches from Sway, use
  `~/.local/bin/with-ibus <command>` or keybindings wired through that wrapper,
  because the already-running Sway process can keep its old inherited
  environment until the graphical session is restarted. If IBus is active but
  nothing appears, verify `org.freedesktop.ibus.panel show` is not `0` and
  `com.github.libpinyin.ibus-libpinyin.libpinyin english-input-mode` is
  `false`; `show=0` hides the property panel and `english-input-mode=true`
  leaves LibPinyin typing English with no candidate popup. Also set
  `org.freedesktop.ibus.general enable-by-default` to `true` so new text
  fields do not stay in direct English mode, and use LibPinyin
  `display-style=2` (`Compatibility`) on Sway/wlroots if candidate UI does not
  appear. `ibus-rime` is a better non-Fcitx backup, but on this Silverblue host
  `rpmi ibus-rime` may stage successfully while live apply fails with
  `packages would be changed: 32`; it then requires reboot or an explicit
  risky `rpm-ostree apply-live --allow-replacement`.
  Direct edits to `~/.config/fcitx5/profile` are overwritten by the running
  daemon; use its D-Bus controller when needed.
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

- Do not do one-shot broad cleanup or cross-disk moves of large OpenCode DB restore/archive trees inside an interactive Codex turn. Use `opencode-cold-archive-migrate.timer` / `~/.local/bin/opencode-cold-archive-migrate`, which moves one cold backup item per run to `/var/mnt/ai/cache/archive/opencode-db-backups/20260718-home-clean`. Keep the active DB `~/.local/share/opencode/opencode.db` in place.
- Do not expand `system-sanity-evolve` into an aggressive cleaner. Its allowed scope is conservative user-unit structure fixes, stale symlink removal, `~/.local/bin` backup archival, old/duplicate AI browser tab cleanup, and failed-marker cleanup. Do not delete caches, coredumps, browser profiles, container volumes, project sources, `~/memory`, or active databases without explicit user approval.
- Do not restore OpenCode MCP config to the pre-1.17 legacy schema. `~/.config/opencode/opencode.json` MCP entries must include `type: local|remote`, array `command` for local servers, and explicit `enabled`; remote MCP uses `type: remote`, not `type: http`. Legacy schema makes `opencode.service` exit 1 and cascades into `opencode-4096-proxy` start-limit and `opencode-18910-local.socket` trigger-limit. Use `system-sanity-evolve --fix` or convert with a timestamped backup.
