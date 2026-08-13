# Runbook: Aider

## Scope

Local Aider CLI and Codex WebTTY `/tool/aider/` integration.

## Current Topology

- CLI wrapper: `~/.local/bin/aider`
- Global config: `~/.aider.conf.yml`
- Short standing context: `~/.aider/charlie-system.md`
- Global ignore file: `~/.aiderignore`
- Architect helper: `~/.local/bin/aider-architect`
- Smart helper: `~/.local/bin/aider-smart`; typo-compatible alias:
  `~/.local/bin/aider-smalrt`
- Smart TTY loop: `~/.local/bin/aider-smart-loop`
- Codex WebTTY entry: `~/.local/bin/aider-ttyd-entry`
- WebTTY service: `aider-ttyd.service`, `127.0.0.1:7693`, base path `/tool/aider`
- Codex gate proxy path: `/tool/aider/` via `~/.local/bin/ttyd-device-gate-proxy`

## Local Rules

- Do not point Codex Aider buttons at Crush. `/tool/aider/` must stay backed by
  `aider-ttyd.service` on `127.0.0.1:7693`.
- Do not make `architect: true` the global WebTTY default. A real smoke test on
  2026-07-15 showed that global architect mode can produce a second irrelevant
  editor response for simple requests. Keep normal Aider as a reliable single
  model session.
- Current normal WebTTY default must stay in the user's available Step family:
  `openai/step-router-v1` for main/editor and `openai/step-3.5-flash-2603`
  for weak-model. Do not switch Aider defaults to non-member models such as
  Claude, DeepSeek, or GLM unless the user explicitly says those accounts are
  available.
- Use `aider-architect` explicitly for hard multi-file design/edit tasks. It
  enables architect mode and uses Step family models:
  `openai/step-3.5-flash-2603-plan` for planning,
  `openai/step-3.7-flash` for edits, and
  `openai/step-3.5-flash-2603` as weak-model.
- Use `aider-smart` when the caller wants lightweight mode selection. It keeps
  all models in the Step family and chooses:
  ask mode only for explicit no-edit prompts, architect mode for
  refactor/architecture/migration/multi-file prompts, and normal code mode for
  everything else. Smart execution passes `--yes-always`, uses `--no-git` when
  outside a repository, and detects standard Node/Make/Python/Rust/Go test
  commands for `--auto-test`. `aider-smalrt` is an alias for typo tolerance.
- Codex `/tool/aider/` should start `aider-smart-loop`, not raw `aider`, so the
  phone/WebTTY flow is Codex-like: type a natural-language task directly, use
  `cd <dir>` to change project, `aider` for raw Aider, `architect` for raw
  architect mode, and `shell` for a temporary shell. From `$HOME`, direct
  tasks mentioning `termhive`, `hub-api`/control plane, `dotfiles`/Sway, or
  `agent-hub`/OpenAgents switch to the corresponding repository first.
- For `aider`, `codex`, `webtty`, `ttyd`, `guise`, or `goose` tasks from the
  home directory, Smart TTY preloads the mapped entry scripts/configuration as
  editable files and the system map/failure history as read-only context. This
  prevents Aider from replying that it has no files to modify.
- `aider-smart-loop` marks its tmux session with `@aider_entry=smart`.
  `aider-ttyd-entry` must attach only to a marked `tool-aider` session; an
  unmarked session is stale raw Aider (`multi>` prompt) and must be replaced
  before attaching the WebTTY client.
- `Guise` is the local Goose alias. Its independent TTY is
  `guise-ttyd.service` on `127.0.0.1:7694` and must start native
  `goose-smart-loop` (native Goose backend), not `goose tui`: the npm TUI can stop on a browser-terminal
  setup screen. `~/.local/bin/goose` owns the effective model defaults and must
  keep `GOOSE_MODEL=step-router-v1`; its default overrides `config.yaml`.
- `guise-ttyd-entry` marks current Smart Goose sessions with
  `@guise_entry=smart-v2`. It must discard an older or unmarked session,
  because that is a stale npm
  TUI and presents `Setup error / Method not found` in WebTTY.
- Shared Goose/Aider delegation is intentionally one-way and approval-gated:
  `~/.local/bin/agent-goose-aider-router diagnose --workspace <repo> <task>`
  creates `~/.local/state/goose-aider-router/tasks/<id>.json` and a read-only
  Goose diagnosis. `apply <id> <file...>` explicitly leases listed files to
  Aider. Do not add recursive Goose/Aider calls or concurrent writers.
- For the simple terminal flow, Guise Smart accepts `do <task>`. This is an
  explicit user authorization to run `diagnose` followed by Aider edits, but
  only for workspace-relative files returned in Goose's `FILES:` handoff.
  If Goose returns no safe file list, it stops at `READY` instead of guessing.
- `~/.ai-context/agent-bootstrap.md` is injected into Goose through the Top Of
  Mind extension and read by delegated Aider tasks. It names the system map,
  failure blacklist, runbooks, and routing memory without dumping all history.
- Keep default read-only context short. Do not load large memory files into
  every Aider request; put only durable local rules in
  `~/.aider/charlie-system.md`.
- Keep secrets out of runbooks. The config may contain local gateway settings,
  but documentation should only name paths and verification steps.

## Verification

```bash
aider --no-git --exit
aider --no-git --message '只回复 OK 两个字母，不要解释。'
aider-architect --no-git --exit
aider-smart --no-git '分析这个问题，不要改文件：按钮为什么跳错？'
aider-smart --no-git '重构这个路由，多文件改造，先给最小方案。'
bash -n ~/.local/bin/aider-smart-loop ~/.local/bin/aider-ttyd-entry
tmux show-options -v -t tool-aider @aider_entry
goose run --no-session --max-turns 1 --text '只回复 OK，不调用工具。'
systemctl --user is-active aider-ttyd.service
curl -fsSL --noproxy '*' -H 'X-Device-Code: w19900422' \
  'http://127.0.0.1:19000/tool/aider/?device=w19900422' |
  rg -q '<title>ttyd - Terminal</title>'
```

If the Aider tmux session was already running before a config change, reset it
so the next WebTTY open reads the new config:

```bash
tmux has-session -t tool-aider 2>/dev/null && tmux kill-session -t tool-aider || true
```
