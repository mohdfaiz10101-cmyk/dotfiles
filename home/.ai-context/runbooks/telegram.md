# Telegram Bot and Group Architecture

## Scope

This runbook is authoritative for Telegram bots, OpenCode control, notifications,
group administration, update delivery, and Telegram MCP tools.

## Invariants

1. `opencode-telegram-gateway.service` is the only `getUpdates` consumer for the
   OpenCode control bot.
2. Telegram MCP is outbound/query-only by default. It must not expose
   `getUpdates`, offset reset, `setWebhook`, or `deleteWebhook`.
3. The control bot accepts only the configured owner and either the owner's
   private chat or the configured control supergroup.
4. Bot tokens live only in mode `0600` secret files. Registries, logs, tool
   results, and generated download URLs must never contain a token.
5. Device operations belong to `ops-dispatcher`; Telegram operations belong to
   `telegram-operator`; the main Agent has neither direct permission.

## Components

- Gateway source: `~/opencode-telegram-gateway`
- Service: `opencode-telegram-gateway.service`
- Health: `http://127.0.0.1:9811/health`
- Secret config: `~/.config/opencode-telegram/.env`
- Non-secret architecture registry: `~/.config/telegram/architecture.json`
- Telegram MCP: `~/.local/share/mcp-servers/telegram/server.py`
- OpenCode Agent: `telegram-operator`

## Group Layout

The control group should be a Forum supergroup. Recommended topics:

- `00 Inbox`: commands and triage
- `10 OpenCode Tasks`: one task/session per topic
- `20 Operations`: infrastructure work
- `30 Alerts`: automated outbound notifications
- `40 Memory & Knowledge`: learning/runbook reports
- `90 Archive`: completed work

If Forum mode is unavailable, the gateway intentionally falls back to one
session for the whole group. Private chat remains one isolated session.

Current control group is `OpenCode Control`, is a Forum supergroup, and
`@charlie_1688_bot` has `can_change_info` and `can_manage_topics`. The userbot
management script is `~/.local/bin/telegram-admin-opencode`; it reads secrets
from `~/.config/tg-user-client.json`, uses migrated Telethon sessions under
`~/.local/share/telegram/` and `~/.local/share/tg-user-client/`, and stores the
topic state in `~/.local/state/telegram-opencode-control.json`.

Target group split follows the WeChat-style rule: one group, one bot, one
function. `OpenCode Control` owns OpenCode tasks; `Haven MCP Control` owns phone
bridge/device operations; `Ops Alerts` owns outbound alerts; `Knowledge Log`
owns memory/runbook/lifecycle reports.

## Commands

- `/ask <task>` execute through OpenCode
- `/task <task>` create a tracked task; in Forum groups create a dedicated topic
  and bind it to a new OpenCode session
- `/new [title]` replace the session bound to the current chat/topic
- `/project [name] [path]` show, create, or select the active project for the
  current chat/topic context
- `/projects` list recent projects
- `/status` check Telegram/OpenCode/session
- `/list` list current mappings
- `/tasks` list recent tracked tasks
- `/close` mark the current task/session done and close the Forum topic when
  available
- `/cancel` abort the active task
- `/help` usage and routing

HTTP diagnostics:

- `GET /health`
- `GET /sessions`
- `GET /projects?limit=50`
- `GET /tasks?limit=50`

## Extension Rules

When a bot, MCP, Agent, rule, service, or group is added:

1. Update `architecture.json` with its single responsibility and owner.
2. Assign exactly one inbound update owner; outbound-only bots have none.
3. Run `opencode-knowledge-maintainer.py`; the capability registry and
   adaptation queue detect new MCPs, Agents, services, overlaps, and missing
   ownership.
4. Add only the required tool allowlist to the owning Agent.
5. Verify no existing bot token is reused for an independent inbound process.

## Verify

```sh
systemctl --user is-active opencode-telegram-gateway.service
curl -fsS http://127.0.0.1:9811/health | jq .
journalctl --user -u opencode-telegram-gateway.service --since -10m --no-pager
python3 -m py_compile ~/.local/share/mcp-servers/telegram/server.py
python3 -m json.tool ~/.config/telegram/architecture.json >/dev/null
```

Healthy polling has a recent `lastSuccessAt`, zero or transient
`consecutiveErrors`, and no second `getUpdates` process.

The gateway uses `TELEGRAM_POLL_TIMEOUT=0` plus
`TELEGRAM_POLL_INTERVAL_MS=2000` to avoid long-poll conflicts with stale legacy
consumers. Legacy local scripts `tg-command` and `tg-bot-tasks` are blocked from
inbound polling; `haven-mcp-telegram.sh` also refuses inbound polling unless
`HAVEN_TELEGRAM_ALLOW_INBOUND=1` is explicitly set. Telegram MCP control-plane
APIs (`getUpdates`, webhook writes, offset reset) hard-fail if called.

## Recovery

1. Check proxy `127.0.0.1:7890`.
2. Check `getWebhookInfo`; URL must be empty in polling mode.
3. Stop any legacy polling script before restarting the gateway.
4. Do not reset offsets through MCP.
5. Build from source, then restart and verify `/health`.
