# Runbook: Crush

Crush CLI/TUI、WebTTY、按钮 API 和本地 LiteLLM 网关。

## Desired State

- Config: `/var/home/charlie/.config/crush/crush.json`
- Rules: `/var/home/charlie/.config/crush/CRUSH.md`
- Data/logs: `/var/home/charlie/.crush`
- Shared API: `crush-tailscale.service`, `0.0.0.0:7766`, data dir `/var/home/charlie/.crush`
- Auxiliary server: `crush-server.service`, `0.0.0.0:8081`, data dir `/var/home/charlie/.crush`
- WebTTY: `crush-ttyd-backend.service`, `0.0.0.0:17766`, BasicAuth `crush:w19900422`
- Button API: `crush-button-api.service`, `0.0.0.0:17768`, token `w19900422`
- SSH/Haven entry: public `2227` → `ssh-keepalive-proxy-crush.service` `127.0.0.1:22029` → sshd `22030` → `~/.local/bin/haven-entry-crush`
- Shared TUI tmux: socket `/run/user/1000/tmux/crush.sock`, session `haven-crush`
- WebTTY tool buttons: `Aider` and `Goose` are injected by
  `~/.local/bin/crush-ttyd-proxy.py`. They call
  `/__crush/tool/open/{aider,goose}` and switch the shared WebTTY to tmux
  sessions `tool-aider` or `tool-goose`; the legacy `guise` API alias remains
  available but has no separate visible button.
- Healthcheck: `crush-healthcheck.timer` recreates dead services/TUI every minute
- Large model: `step-router-v1`
- Small model: `deepseek-v4-flash`
- Core MCPs enabled: `fetch`, `codegraph`, `memory-engine`

## Verify

```bash
systemctl --user is-active crush-server crush-tailscale crush-ttyd-backend crush-button-api crush-healthcheck.timer
systemctl --user is-active ssh-keepalive-proxy-crush.service
systemctl --user is-active agent-dispatch-watch.timer
ss -ltnp | rg ':(7766|8081|17766|17768)\b'
ss -ltnp | rg ':(22029|22030|2227)\b'
tmux -S /run/user/1000/tmux/crush.sock list-panes -t haven-crush -F '#{pane_dead} #{pane_current_command} #{pane_pid}'
curl -sSI -u crush:w19900422 --noproxy '*' http://127.0.0.1:17766/
curl -sS -H 'X-Crush-Token: w19900422' --noproxy '*' http://127.0.0.1:17768/__crush/status
curl -fsSL -u crush:w19900422 --noproxy '*' http://127.0.0.1:17766/ | rg 'crush-aider|crush-goose|crush-guise'
curl -sS -u crush:w19900422 --noproxy '*' -X POST http://127.0.0.1:17766/__crush/tool/open/aider | jq '{ok,current,tool}'
curl -sS -u crush:w19900422 --noproxy '*' -X POST http://127.0.0.1:17766/__crush/tool/open/guise | jq '{ok,current,tool}'
agent-dispatch decide 'op任务停止了，检查18910和4097并修复'
timeout 120s /var/home/charlie/.local/bin/crush.real run '只回复 OK' --cwd /var/home/charlie
```

## OP / Crush Auto Dispatch

- Entrypoint: `/var/home/charlie/.local/bin/agent-dispatch`
- Watcher: `agent-dispatch-watch.timer` runs every minute.
- Submit immediately:
  ```bash
  agent-dispatch submit '任务内容'
  ```
- Preview target and score:
  ```bash
  agent-dispatch decide '任务内容'
  ```
- Check latest task and allow one handoff:
  ```bash
  agent-dispatch status latest --auto-handoff
  ```
- List queue:
  ```bash
  agent-dispatch list
  ```
- Watcher now treats missing unit + stale log, explicit deadline overrun, or missing final `STATUS:` block as non-success; tasks no longer remain `running` forever after the transient unit disappears.
- Crush-dispatched tasks must end with the structured final block from `/var/home/charlie/.config/crush/CRUSH.md`. `exit=0` alone is no longer enough for `completed`.
- Session quality baseline report:
  ```bash
  crush-session-eval --limit 10
  ```
  Default report path: `/var/home/charlie/.local/state/crush-eval/latest.md`
  Automation:
  - `agent-dispatch watch` refreshes the report after each watcher pass
  - `crush-session-eval.timer` refreshes it every 15 minutes
- Routing model:
  - OP runtime / task-stop / 18910 / 4097 / watchdog issues score high for Crush.
  - implementation / frontend / app / workflow / long project tasks score high for OP.
  - review / verification / failure analysis score high for Crush.
  - The router also scores live health: OP resilience and Crush service/TUI status.
  - Failed tasks may hand off once to the other executor; after both fail, a Codex copy pack is written under `/var/home/charlie/.local/state/agent-dispatch/failures/`.
  - Every `agent-dispatch submit` records a machine-readable `contract` with goal, cwd/target scope, acceptance, verification requirement, and one-handoff policy.
  - After both executor attempts fail, `agent-dispatch` writes the failure pack and submits a read-only Codex `failure_review` request through `~/.local/bin/ai-a2a`; the request is queued even when the local Codex budget window is off, and the worker returns `SKIPPED_BUDGET` instead of spending quota.
  - Dispatch state is exposed in Hub project snapshots from `~/.local/state/agent-dispatch/tasks/<dispatch-id>.json`; the Projects board shows the current executor and dispatch state.
  - Verification: `agent-dispatch decide '实现一个前端页面并修复代码 bug'`, `agent-dispatch decide '检查 4097 和 18910，诊断 OpenCode 停止原因'`, `ai-a2a status --limit 10`, and `curl --noproxy '*' -fsS http://127.0.0.1:9800/api/projects/control | jq '.tasks[0].dispatch_state'`.

## Restart

```bash
systemctl --user restart crush-server crush-tailscale crush-ttyd-backend crush-button-api
systemctl --user start crush-healthcheck.service
systemctl --user restart agent-dispatch-watch.timer
```

## Known Issues

- Do not split Crush state between `/var/home/charlie/.crush` and `/var/home/charlie/.local/share/crush`; services should use `/var/home/charlie/.crush`.
- The TUI wrapper connects to `tcp://127.0.0.1:7766`; the shared API must listen on `0.0.0.0:7766` or `127.0.0.1:7766`.
- Do not use `tmux attach-session -d` in `crush` or `crush-ttyd-entry`; it detaches other clients and makes WebTTY/SSH viewers look mutually exclusive.
- Keep `KillMode=process` on `crush-ttyd-proxy.service` and `crush-healthcheck.service`; these helpers can create or recover the long-lived tmux session, and normal service restarts must not kill the active Crush pane.
- `crush-ttyd-proxy.py` must re-raise `web.HTTPException` redirects. Catching `web.HTTPFound` as a generic exception produces visible `switch failed: Found` / `crush session switch failed: Found` errors.
- Opening a historical Crush task from `/__crush/crush-session/open/<id>` should create/reuse a `task-<id8>` tmux session instead of killing `haven-crush`; killing the default session interrupts current work.
- `glm-5-turbo` can return reasoning-only output with tiny `max_tokens`; use `deepseek-v4-flash` for small/title tasks.
- Keep broad-search protection active in `/var/home/charlie/.config/crush/hooks/pre_tool_guard.py`; orphaned `grep`/Agent calls previously caused stuck sessions.
- Clipboard warnings in headless/tmux sessions are expected and not a task failure.
- `http://127.0.0.1:17768/__crush/status` now includes `latest_dispatch`, exposing the latest task status, attempt deadline, last activity, and Codex failure pack path for the 17766 UI.
- The same status API now includes `latest_eval`, exposing the latest report timestamp, average score, status mix, and top flags so the UI can surface quality drift without a manual command.
- `17766` toolbar now has explicit sections for `Overview`, `Sessions`, `Move`, `Actions`, and custom buttons. The `Overview` card reads `latest_dispatch` and `latest_eval` directly from `/__crush/status`.
- On mobile, the toolbar should stay on the right side, default to a collapsed floating button, and must not reduce `#terminal-container` height. Expanded mobile mode may reserve only right-side width for the toolbar; never move it to the bottom.
- Keep mobile right-toolbar controls readable: use a wide enough side rail for full button labels, and keep auto-eval/score as a compact summary that expands on tap instead of permanent large cards.
- `agent-dispatch` now treats active `task-*` tmux sessions with a live `crush.real` pane as healthy; opening a task session no longer falsely degrades Crush health scoring.
