# Runbook: Unified Control Plane

One architecture for operating Charlie's local AI/work/project stack.

## Desired State

- `appsmith.service` — Appsmith launcher/catalog on `:8089`; current generated apps are shortcut wrappers, not yet the Hub API control plane
- `hub-api.service` — API gateway, service registry, snapshots, semantic command endpoint, listens on `:9800`
- `n8n.service` — automation/workflow bus, listens on `:5678`
- FastGPT `:3000` — knowledge, plans, reviews
- OpenCode `:4097` / Web `:18910` — execution layer
- Zulip/Mattermost — discussion and bot feedback
- Plane/Huly — project and workspace systems

## Entry Points

```bash
http://100.120.189.27:9800/go/appsmith
http://100.120.189.27:9800/workspace
http://100.120.189.27:9800/projects
http://100.120.189.27:8089/
http://100.120.189.27:5678/
```

Current direct-entry rule:

- `http://100.120.189.27:8089/` and `/user/login` no longer expect an
  interactive Appsmith login for daily use. Caddy inside the Appsmith container
  now redirects those entry paths to `http://100.120.189.27:9800/projects`
  so the control surface opens directly.
- Do not restore the old root/login page unless the goal is specifically to
  administer Appsmith itself. For routine operations, `8089` is now just a
  stable vanity entry to the Hub project/control page.

## API Contract

- Hub snapshot: `GET http://127.0.0.1:9800/api/workspace/snapshot`
- Semantic command: `POST http://127.0.0.1:9800/api/workspace/command`
- Project control snapshot: `GET http://127.0.0.1:9800/api/projects/control`
- Project task create: `POST http://127.0.0.1:9800/api/projects/tasks`
- Project task approve/dispatch: `POST http://127.0.0.1:9800/api/projects/tasks/{task_id}/approve`
- Project task update: `POST http://127.0.0.1:9800/api/projects/tasks/{task_id}/update`
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
