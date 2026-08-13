# Runbook: OpenHands

Local OpenHands GUI runs as a user systemd service and is intentionally
separate from OpenCode.

## Desired State

- Service: `openhands-gui.service`
- URL: `http://127.0.0.1:3001/`
- Ownership: on this host `127.0.0.1:3001` is OpenHands, not Open WebUI.
- Public URL: `http://charlie1990.duckdns.org:19901/` through
  `openhands-public-proxy.service` BasicAuth and FRP proxy `fedora-openhands`
- Persistent state: `~/.openhands`
- Runtime env: `~/.config/openhands/openhands.env`
- Local patch mounts:
  `~/.config/openhands/patches/app_server_config.py` and
  `~/.config/openhands/patches/live_status_app_conversation_service.py`
- Main workspace rules/hooks:
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/.openhands/`
- Main image: pinned `docker.openhands.dev/openhands/openhands:1.2.0`
- Agent server image: do not override `AGENT_SERVER_IMAGE_REPOSITORY` or
  `AGENT_SERVER_IMAGE_TAG` for OpenHands 1.2.0. Let the pinned app image use
  its built-in default tag.
- LLM route: local LiteLLM at `http://host.docker.internal:4000/v1`,
  `LLM_MODEL=openai/step-router-v1`
- OP-style context: workspace repo microagent
  `/workspace/project/.openhands/microagents/op-runtime.md` plus
  `memory-engine` and `letta` MCPs in `~/.openhands/settings.json`
- Letta fallback for OpenHands sandboxes:
  `letta-podman-proxy.service` listens on Podman gateway `10.88.0.1:18283`
  and forwards to local Letta `127.0.0.1:8283`.
- Periodic OpenHands task summaries to Letta are implemented by
  `~/.local/bin/openhands-letta-sync` plus
  `openhands-letta-sync.service/timer`. The timer is enabled and runs every
  15 minutes after a successful manual sync against healthy Letta.

## Verify

```bash
systemctl --user is-active openhands-gui.service
systemctl --user is-active openhands-public-proxy.service
curl --noproxy '*' --connect-timeout 3 --max-time 8 -sS -o /dev/null \
  -w 'openhands=%{http_code} %{time_total}\n' http://127.0.0.1:3001/
curl --noproxy '*' --connect-timeout 5 --max-time 12 -sS -o /dev/null \
  -w 'public=%{http_code} %{time_total}\n' http://charlie1990.duckdns.org:19901/
podman exec openhands-app env | grep -E '^(AGENT_SERVER_IMAGE|LLM_|OH_|SANDBOX_)' | sort
curl --noproxy '*' -sS -u 'openhands:<password>' http://127.0.0.1:3001/api/settings \
  | jq '.mcp_config'
systemctl --user is-active letta-podman-proxy.service
python3 -m py_compile ~/.local/bin/openhands-letta-sync
~/.local/bin/openhands-letta-sync
podman --url unix:///run/podman/podman.sock ps --format '{{.Names}} {{.Status}}' \
  | rg '^oh-agent-server-'
curl --noproxy '*' --connect-timeout 5 --max-time 20 -sS \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:3001/api/v1/app-conversations \
  -d '{"title":"smoke","initial_message":{"role":"user","content":[{"type":"text","text":"Say ready and stop."}]}}'
```

## Local Decisions

- Do not use `latest`: it previously created DB migration drift and
  `DuplicateColumnError` / missing Alembic revision failures. Use a pinned image
  until a planned upgrade can migrate state cleanly.
- Do not set `AGENT_SERVER_IMAGE_TAG=1.2.0-python`; that tag does not exist on
  GHCR and causes `/api/conversations` to fail with
  `Error Getting Docker Image: ghcr.io/openhands/agent-server:1.2.0-python`.
  With the override removed, the 1.2.0 app uses its own matching default.
- Pre-pull the built-in agent-server image after a clean install:
  `podman pull ghcr.io/openhands/agent-server:7c91cbe-python`. Without it the
  first user conversation may spend a long time pulling the image.
- The rootful agent-server container runs as UID/GID `10001:10001`. The mounted
  workspace must allow that UID and must have an SELinux label usable by
  containers:
  `setfacl -m u:10001:rwx,d:u:10001:rwx <workspace>` and
  `sudo chcon -Rt container_file_t <workspace>`.
- OpenHands 1.2.0 treats agent-server as failed if startup health checks miss a
  short 15s grace window. Local patch `app_server_config.py` reads
  `SANDBOX_STARTUP_GRACE_SECONDS`; keep it at `60`.
- In this mixed rootless OpenHands + rootful sandbox setup, the default
  OpenHands MCP URL is injected as `127.0.0.1:3001`, which points to the
  sandbox itself and makes `/api/conversations` return 500. Local patch
  `live_status_app_conversation_service.py` honors
  `OPENHANDS_DISABLE_DEFAULT_MCP=true`; keep it enabled unless a proper
  container-reachable MCP bridge is added.
- Do not confuse `OPENHANDS_DISABLE_DEFAULT_MCP=true` with "no MCP". Keep the
  broken default OpenHands MCP disabled, but configure explicit user MCPs in
  `~/.openhands/settings.json`. The current default user MCPs are:
  `memory-engine` with stdio command
  `python3 /mnt/ai/data/memory-engine/memory-mcp-server.py`, and `letta` with
  `python3 /mnt/ai/data/memory-engine/openhands-letta-mcp.py`.
- Letta itself binds only `127.0.0.1:8283`, so rootful agent-server containers
  cannot reach it directly. Keep `letta-podman-proxy.service` enabled and point
  OpenHands Letta MCP env `LETTA_API` to `http://10.88.0.1:18283`.
- If OpenHands Letta fallback tools exist but writes/searches hang, check Letta
  health and embedding first:
  `curl http://127.0.0.1:8283/v1/health/`,
  `curl http://127.0.0.1:8286/`, and the Letta agent
  `embedding_config.embedding_endpoint`. On this host the endpoint should be
  `http://10.88.0.1:8286/v1`, not `host.containers.internal:8286`.
- OpenHands 1.2.0 loads repo skills from `/workspace/project`, not from the
  parent `/workspace`. Keep `.openhands/skills`, `.openhands/microagents`, and
  `.openhands/hooks*` mirrored under
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/project/.openhands/`.
  If logs show `Loaded 0 repo skills`, check this path first.
- Agent-server containers need these extra sandbox mounts for OP-style memory:
  `/var/home/charlie/.ai-context:/ai-context:ro`,
  `/mnt/ai/data/memory-engine:/mnt/ai/data/memory-engine:ro`, and
  `/var/home/charlie/.local/share/memory-engine:/home/openhands/.local/share/memory-engine:rw`.
  The memory DB directory and file must grant UID 10001 access:
  `setfacl -m u:10001:rwx ~/.local/share/memory-engine` and
  `setfacl -m u:10001:rw ~/.local/share/memory-engine/memory.db`. SELinux labels
  for `.ai-context`, `memory-engine`, and the MCP script directory must be
  `container_file_t`.
- Agent-server browser actions must use the host-mounted Chromium wrapper
  `/var/home/charlie/.config/openhands/sandbox-bin/chromium:/usr/local/bin/chromium:ro`.
  Plain `/usr/bin/chromium --headless=new` can hang in this sandbox with EGL/XCB
  initialization errors. The wrapper always adds `--disable-software-rasterizer`;
  when `DISPLAY` is set for VNC/noVNC it uses `--ozone-platform=x11`, otherwise it
  uses `--ozone-platform=headless`.
- For Charlie's own DuckDNS/local service URLs such as `19899/19900` WebTTY,
  do not start by opening the browser. First read the map/runbook and locate the
  owning local service or file. A `401 Device Match` response is expected for an
  unauthenticated browser and is not the application page to edit.
- To verify MCP inside a new agent-server container, check logs for
  `Created 12 MCP tools` and event history for `MCPToolAction` with
  `memory_search` / `letta_search`. Direct container smokes are:
  `printf ...tools/call memory_search... | python3 /mnt/ai/data/memory-engine/memory-mcp-server.py`.
  For Letta:
  `printf ...tools/call letta_search... | LETTA_API=http://10.88.0.1:18283 python3 /mnt/ai/data/memory-engine/openhands-letta-mcp.py`.
- `~/.openhands/openhands.db` may need backup/rebuild after version drift. Keep
  `settings.json` and `.jwt_secret`; move only the DB to
  `openhands.db.bak-<timestamp>`.
- In this rootless Podman setup, keep `SANDBOX_USER_ID=0`. Container root maps
  to the host user and can write `~/.openhands`; `SANDBOX_USER_ID=1000` without
  compatible user namespace mapping causes SQLite `unable to open database file`,
  while `--userns=keep-id` conflicts with OpenHands 1.2.0 entrypoint user
  creation.
- Bind the web UI to `127.0.0.1:3001` by default. Add an authenticated proxy if
  phone/LAN access is needed; do not expose the raw UI on all interfaces.
- Public `19901` path is: router DNAT `19901/TCP -> 192.168.123.71:19901`,
  Fedora firewalld `19901/tcp`, local `frps :19901`, `frpc fedora-openhands`
  to `127.0.0.1:13001`, `openhands-public-proxy` BasicAuth to
  `127.0.0.1:3001`.
- `openhands-public-proxy` accepts BasicAuth and sets an `openhands_auth`
  cookie. The cookie is required for browser follow-up requests and WebSocket
  upgrades that do not repeat the BasicAuth header.
- The public proxy also rewrites agent-server runtime URLs from
  `http://localhost:<port>/...` to
  `http://charlie1990.duckdns.org:19901/runtime/<port>/...` and proxies
  `/runtime/<port>/...` to `127.0.0.1:<port>`. This is required for phone/WAN
  browsers; otherwise the frontend tries to connect to the phone's own
  `localhost` and stays on Starting/Loading/Disconnected.
- Agent-server webhook callbacks must not use the OpenHands default
  `http://host.docker.internal:3000/api/v1/webhooks` on this host: port 3000 is
  FastGPT, so agent replies are generated in the runtime but the OpenHands app
  list stays stale. Keep the local `docker_sandbox_service.py` patch mounted and
  set `SANDBOX_WEBHOOK_BASE_URL` to the authenticated `19901` OpenHands proxy.
  Verify with `podman --url unix:///run/podman/podman.sock exec
  <oh-agent-server> env | grep OH_WEBHOOKS_0_BASE_URL` and look for
  `POST /api/v1/webhooks/... 200 OK` in `openhands-gui.service` logs.
- If the page intermittently shows `network error`, check stale rootful
  agent-server containers first. Old `oh-agent-server-*` containers can keep
  POSTing webhook events for deleted/archived conversations and produce 401s or
  stale runtime URLs. Keep only current active containers unless deliberately
  preserving older tasks.
- If new OpenHands tasks stall and logs show
  `sqlite3.IntegrityError: NOT NULL constraint failed: event_callback_result.id`,
  stop `openhands-gui.service`, back up `~/.openhands/openhands.db`, and ensure
  table `event_callback_result.id` has a SQLite UUID default. This host was
  migrated on 2026-07-09 and smoke-tested with an insert without an explicit
  `id`.
- Agent-server desktop/browser UI needs the local `docker_sandbox_service.py`
  patch to force `OH_ENABLE_VNC=true`, expose container port `8002` as
  `DESKTOP`, and mount the VNC clean-env files from
  `~/.config/openhands/patches/`. The `vncserver-clean-env` wrapper restores
  `LD_LIBRARY_PATH_ORIG` before running the real TigerVNC script mounted as
  `/usr/local/libexec/tigervncserver-real`; without this, PyInstaller's
  `/tmp/_MEI*/libstdc++.so.6` causes `CXXABI_1.3.15 not found` and the browser
  tab stays loading.
- `openhands-public-proxy` must handle client and upstream socket errors. A
  missing `error`/`close` handler previously let browser disconnects raise
  `write EPIPE` and restart the proxy, which looked like intermittent
  OpenHands `network error`.
- OpenHands workspace hooks mirror OP guardrails: no unbounded curl, no direct
  long-lived containers/services in session shells, no OP self-restart, no raw
  secret output, no unbounded filesystem scans, and bounded log reads only.

## Fast 500 Triage

If `GET /` and `/api/settings` return 200 but
`POST /api/v1/app-conversations` returns 500, check dependent AI services
before editing OpenHands code:

```bash
systemctl --user is-active litellm.service litellm-strip-proxy.service letta-stack.service letta-podman-proxy.service
curl --noproxy '*' --connect-timeout 5 --max-time 12 -sS http://127.0.0.1:4000/v1/models
curl --noproxy '*' --connect-timeout 5 --max-time 12 -sS http://127.0.0.1:8283/v1/agents/
```

Known repair state:

- `~/.config/openhands/openhands.env` must keep
  `SANDBOX_STARTUP_GRACE_SECONDS=60`.
- `litellm.container` and `letta-stack.service` should allow long image pulls
  with `TimeoutStartSec=900`; a 300-second startup timeout can kill the pull and
  leave OpenHands healthy at `/` but broken at conversation creation.
- `~/.openhands/settings.json` Letta MCP env must use
  `LETTA_API=http://10.88.0.1:18283` so rootful sandboxes can reach host Letta
  through `letta-podman-proxy.service`.
- Restart `openhands-gui.service` after changing either file, then smoke-test
  `POST /api/v1/app-conversations`.

## Sources

- Official local setup documents Docker direct-run and V1 agent-server image
  variables.
- Official configuration docs document V1 env configuration such as
  `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `OH_PERSISTENCE_DIR`,
  `OH_WEB_URL`, `SANDBOX_VOLUMES`, and agent-server image variables.
- Official repository customization and hooks docs document `.openhands/skills`
  and `.openhands/hooks.json`.
