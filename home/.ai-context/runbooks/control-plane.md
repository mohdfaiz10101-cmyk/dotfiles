# Runbook: Unified Control Plane

One architecture for operating Charlie's local AI/work/project stack.

## Desired State

- `appsmith.service` — single visual operations console, listens on `:8089`
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
http://100.120.189.27:8089/
http://100.120.189.27:5678/
```

## API Contract

- Hub snapshot: `GET http://127.0.0.1:9800/api/workspace/snapshot`
- Semantic command: `POST http://127.0.0.1:9800/api/workspace/command`
- Appsmith health: `GET http://127.0.0.1:9800/api/appsmith/status`
- n8n health: `GET http://127.0.0.1:9800/api/n8n/status`
- OP handoff: `POST http://127.0.0.1:9800/api/workflow/todos/{task_id}/op`
- FastGPT export: `POST http://127.0.0.1:9800/api/workflow/todos/{task_id}/fastgpt`
- Zulip send: `POST http://127.0.0.1:9800/api/workflow/todos/{task_id}/zulip`

## Appsmith Datasource

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

- Appsmith is the main window. Do not create another top-level dashboard for the same purpose.
- Hub owns state, registry, semantic command parsing, and safe local APIs.
- n8n owns multi-step workflows and webhook automation.
- OP owns execution. Do not make FastGPT/Dify write files or restart services directly.
- Plane/Huly remain project data systems, not the operations console.
