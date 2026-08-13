# Runbook: Communication Project Sync

Created: 2026-07-18

This runbook covers the near-realtime project/status synchronization layer across
Mattermost, Zulip, and ntfy, plus the NetBird/LAN URL comparison matrix.

## Purpose

- Keep Hub project/task state visible in all three communication surfaces:
  Mattermost, Zulip, and ntfy.
- Prefer two internal phone-safe address families in every user-facing link:
  - NetBird: `100.87.238.153`
  - LAN: `192.168.123.71`
- Keep DuckDNS only as the public ntfy/app fallback where it is explicitly
  useful.
- Do not sync secrets.  Sync only titles, task IDs, statuses, counts, timestamps,
  channel tags, and non-secret URLs.

## Durable artifacts

- Sync helper: `~/.local/bin/comm-project-sync`
- Timer/service:
  - `~/.config/systemd/user/comm-project-sync.timer`
  - `~/.config/systemd/user/comm-project-sync.service`
- Latest comparable state:
  - `~/.local/state/comm-project-sync/latest.json`
  - `~/.local/state/comm-project-sync/history.jsonl`
- Hub API view:
  - `GET http://127.0.0.1:9800/api/projects/comm-sync`
  - NetBird: `http://100.87.238.153:9800/api/projects/comm-sync`
  - LAN: `http://192.168.123.71:9800/api/projects/comm-sync`
- Workbench port registry now exposes `url`, `netbird_url`, `lan_url`, and
  `local_url` from `GET /api/ports`.

## Current URL matrix

| Service | NetBird | LAN |
|---|---|---|
| Hub projects | `http://100.87.238.153:9800/projects` | `http://192.168.123.71:9800/projects` |
| Mattermost | `http://100.87.238.153:8065/` | `http://192.168.123.71:8065/` |
| Workbench | `http://100.87.238.153:19888/?device=w19900422` | `http://192.168.123.71:19888/?device=w19900422` |
| ntfy | `http://100.87.238.153:2586/` | `http://192.168.123.71:2586/` |
| FastGPT | `http://100.87.238.153:3000/` | `http://192.168.123.71:3000/` |
| OpenCode | `http://100.87.238.153:18910/` | `http://192.168.123.71:18910/` |
| Network panel | `http://100.87.238.153:19979/` | `http://192.168.123.71:19979/` |

Zulip is SaaS for this host: `https://charlie.zulipchat.com/`.

## Sync behavior

`comm-project-sync sync` reads `GET http://127.0.0.1:9800/api/projects/control`
and falls back to `~/.local/state/hub/project-control.json` if Hub is down.
It computes a SHA1 hash from project/task IDs, titles, statuses, approvals, and
updated timestamps. If unchanged, it records `deliveries.skipped=unchanged` and
does not spam channels.

On a changed snapshot or `--force`, it sends:

- Mattermost: incoming webhook to `MATTERMOST_TASKS_CHANNEL` (normally
  `ai-tasks`).
- Mattermost per-channel mirrors via the bot token to any relevant agent
  channel among `cursor`, `goose`, `aider`, `ai-images`, `ai-docs`,
  `ai-review`, and `ai-inbox`. This fixes the failure mode where ntfy received a
  Cursor/executor update but Mattermost only had a generic `ai-tasks` summary.
- Zulip: Hub `POST /api/zulip/send`, topic `Project Sync`.
- ntfy: `ntfy-send projects`, topic from `NTFY_TOPIC_PROJECTS` (default
  `charlie-projects`), with NetBird/LAN Hub action buttons.

Hub `_save_project_control()` fire-and-forgets the helper with event
`project_control_saved`, so project creates/updates/approvals are near-realtime.
The timer also runs once per minute as a safety net.

## Commands

```bash
comm-project-sync status
comm-project-sync sync --event manual --force
systemctl --user status comm-project-sync.timer --no-pager
curl --noproxy '*' -fsS http://127.0.0.1:9800/api/projects/comm-sync | jq '{ok, counts, deliveries, hub:.urls.hub}'
curl --noproxy '*' -fsS 'http://127.0.0.1:19888/api/ports?device=w19900422' | jq 'map(select(.key=="hub" or .key=="mattermost" or .key=="ntfy" or .key=="project-sync")|{key,netbird_url,lan_url})'
```

Expected:

- `comm-project-sync.timer` is `active` and `enabled`.
- `latest.json` has accurate non-zero project/task counts when Hub has tasks.
- `deliveries` contains `mattermost`, `mattermost_mirrors`, `zulip`, and `ntfy`
  when changed/forced; otherwise it contains `skipped=unchanged`.
- `deliveries.mattermost_mirrors.cursor/goose/aider` should contain HTTP `201`
  post IDs when recent tasks match those channels.
- All exposed Hub/Mattermost/Workbench/ntfy links include both NetBird and LAN
  forms.

## ntfy project topic

`~/.config/ntfy/channels.env` contains non-secret topic keys:

```text
NTFY_TOPIC_PROJECTS=charlie-projects
NTFY_TAG_PROJECTS=clipboard,robot
```

`~/.local/bin/ntfy-send` accepts:

```bash
ntfy-send projects "项目同步" "message"
```

Do not print bearer tokens from `~/ai/ntfy/data/user.db`.

## Safety

- Never sync passwords, API keys, Mattermost database rows, webhook URLs, or
  Zulip API keys into Mattermost/Zulip/ntfy/runbooks.
- Project sync is notification/state-only.  Destructive actions, payment, public
  posting, external messages, login/authorization, and network/firewall changes
  still require Hub approval or `ai-review` confirmation.
- If a bad zero-count snapshot was sent while Hub was restarting, run:

```bash
comm-project-sync sync --event corrected --force
```

Then verify the fallback path is `~/.local/state/hub/project-control.json`.

## Cursor / Goose / Aider imported into comparison matrix (2026-07-18)

`comm-project-sync` now includes executor/IDE surfaces in `urls` so future
comparisons can show not only chat systems, but also where a task should be
opened/executed:

| Surface | NetBird | LAN |
|---|---|---|
| Cursor GUI | `http://100.87.238.153:19970/` | `http://192.168.123.71:19970/` |
| Goose | `http://100.87.238.153:7694/tool/guise/` | `http://192.168.123.71:7694/tool/guise/` |
| Aider | `http://100.87.238.153:7693/tool/aider/` | `http://192.168.123.71:7693/tool/aider/` |

Verify:

```bash
comm-project-sync status | jq '{cursor:.urls.cursor, goose:.urls.goose, aider:.urls.aider}'
```
