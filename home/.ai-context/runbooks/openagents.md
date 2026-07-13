# Runbook: OpenAgents

OpenAgents Network Hub for coordinating Codex, OpenCode, and Crush status/entry agents.

## Desired State

- Service: `openagents-network.service`
- Healthcheck: `openagents-healthcheck.timer`
- Workspace: `/var/home/charlie/.openagents/network`
- Config: `/var/home/charlie/.openagents/network/network.yaml`
- HTTP/MCP/Studio: `0.0.0.0:8700`
- gRPC agent transport: `0.0.0.0:8600`
- Auth: passwordless `public` default group for browser/local agents; `admin` and `worker` groups keep password hashes.
- Healthcheck starts only the stable entry agents; legacy YAML collaborator agents stay manual because they can fail gRPC detection and leave high-load `openagents agent start` processes.
- Entry agents:
  - `codex-entry`
  - `opencode-entry`
  - `crush-entry`

## Verify

```bash
systemctl --user is-active openagents-network openagents-healthcheck.timer
curl -fsS --noproxy '*' http://127.0.0.1:8700/api/health | jq
curl -fsS --noproxy '*' http://127.0.0.1:8700/api/agents/service | jq '.agents[] | {agent_id,status,pid}'
```

## Restart

```bash
systemctl --user restart openagents-network
systemctl --user start openagents-healthcheck.service
```

## Known Issues

- If `requires_password=false`, `default_agent_group` must not be a group with `password_hash`; use the passwordless `public` group.
- Do not put `StartLimitIntervalSec` under `[Service]`; systemd ignores it there.
- Keep OpenAgents as the coordination/status surface. Do not run arbitrary shell through browser agents; Codex, OpenCode, and Crush keep their own tmux/API/service isolation.
- Do not auto-start all YAML collaborator agents until their `localhost:8600` detection issue is fixed; keep healthcheck allowlisted to `codex-entry`, `opencode-entry`, and `crush-entry`.
