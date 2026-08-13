# Runbook: Mattermost

Mattermost is the channel collaboration layer for Hub, OP, FastGPT, and automation.

## Desired State

- Service: `mattermost.service`
- AI Inbox bridge: `mattermost-ai-inbox.service`
- Compose directory: `/var/home/charlie/apps/mattermost-docker`
- Compose files: `docker-compose.yml` + `docker-compose.without-nginx.yml`
- Environment: `/var/home/charlie/apps/mattermost-docker/.env`
- AI Inbox bridge environment: `~/.config/mattermost-ai-inbox.env` (mode
  `0600`; contains Mattermost webhook/bot tokens and must not be pasted into
  chats, skills, or runbooks)
- URL: `http://100.120.189.27:8065/`
- NetBird URL: `http://100.87.238.153:8065/`
- Hub entry: `http://127.0.0.1:9800/go/mattermost`
- Hub health: `http://127.0.0.1:9800/api/mattermost/status`
- Hub AI Inbox status:
  `http://127.0.0.1:9800/api/mattermost/integration/status`

## AI Inbox Integration

Mattermost is the phone/chat/file intake layer for Hub:

1. User sends text/files/images to Mattermost channel `ai-inbox`.
2. `mattermost-ai-inbox.service` polls `ai-inbox` with the configured bot token.
3. Attachments are downloaded under
   `~/.local/share/mattermost-ai-inbox/<post-id>/`.
4. Hub endpoint `POST /api/mattermost/inbox` creates a `pending_approval`
   Hub project task with:
   - `source=mattermost`
   - `source_ref=http://127.0.0.1:8065/charlie-hub/pl/<post-id>`
   - `artifact_paths=[...]` for downloaded files
5. Hub posts a receipt to Mattermost through the incoming webhook when
   `MATTERMOST_INCOMING_WEBHOOK_URL` is configured.
6. Outgoing webhook is also configured for trigger words `ai` / `任务` /
   `待办` / `整理` in `ai-inbox`; the poller remains the default path because
   it can download files.

Channels expected on team `charlie-hub`:

- `ai-inbox` — phone/chat/file intake
- `ai-tasks` — Hub task receipts
- `ai-review` — human confirmation
- `ai-images` — image/OCR results
- `ai-docs` — document/material summaries
- legacy operational channels: `hub`, `op`, `alerts`, `fastgpt`, `sourcing`

Admin bootstrap secrets created during repair are stored only under
`~/.local/state/mattermost-ai-inbox/` with mode `0600`.

## Verify

```bash
systemctl --user is-active mattermost.service
systemctl --user is-active mattermost-ai-inbox.service
curl -sS http://127.0.0.1:8065/api/v4/system/ping | jq
curl -sS http://127.0.0.1:9800/api/mattermost/integration/status | jq
mattermost-ai-inbox status
mattermost-ai-inbox poll-once
docker ps --format 'table {{.Names}}\t{{.Status}}' | rg 'mattermost-docker|NAMES'
```

## Restart

```bash
systemctl --user restart mattermost.service
systemctl --user restart mattermost-ai-inbox.service
```

## Notes

- Uses Mattermost Team Edition `11.7.0`.
- The app runs without the bundled nginx; direct app port is `8065`.
- Mattermost app bind mounts need `:Z` under rootless Podman/Silverblue, otherwise `/mattermost/config/config.json` can fail with permission denied.
- The Docker Hub path can fail through the local proxy; `mattermost/mattermost-team-edition` was pulled through `docker.m.daocloud.io`.
- Postgres must mount the configured data directory to
  `/var/lib/postgresql/data:Z`, not `/var/lib/postgresql`. If it is mounted to
  `/var/lib/postgresql`, Podman creates an anonymous volume at
  `/var/lib/postgresql/data`, data appears to work until `docker compose down`,
  then the next `up` can start an empty Mattermost database. The corrected
  compose line is:
  `- ${POSTGRES_DATA_PATH}:/var/lib/postgresql/data:Z`.
- A repaired SQL dump was written under
  `~/.local/state/mattermost-ai-inbox/mattermost-*.sql`; do not paste its
  contents because it may include tokens/hashes.
- 2026-07-18 Android Mattermost app `com.mattermost.rn` on PKR110 was switched
  to NetBird server URL `http://100.87.238.153:8065`. The app database is
  `/data/user/0/com.mattermost.rn/files/databases/app.db`; server row in
  `Servers` now has `display_name=charlie-netbird`, `url=http://100.87.238.153:8065`,
  and `db_path=file:///data/user/0/com.mattermost.rn/files//databases/aHR0cDovLzEwMC44Ny4yMzguMTUzOjgwNjU=.db`.
  Phone-side backups are named `app.db.bak-netbird-*` and
  `aHR0cDovLzEwMC4xMjAuMTg5LjI3OjgwNjU=.db.bak-netbird-*`.
  This only works after the Android NetBird VPN is active. Later on
  2026-07-18 the phone NetBird VPN was started, Fedora showed
  `Peers count: 1/1 Connected`, and Mattermost UID `10447` successfully
  reached `http://100.87.238.153:8065/api/v4/system/ping`. The phone
  background policy `/data/adb/haven-background-policy.sh` now includes
  `com.mattermost.rn` so the app is not blocked by background network policy.
- Mattermost Android white-screen repair found on 2026-07-18: after changing
  `Servers.url` to NetBird, `RN_KEYCHAIN.preferences_pb` still had credential
  keys under the old URL `http://100.120.189.27:8065:{u,p,c}`. This caused
  `SecurityManager: Failed to initialize` and a blank React Native page. The
  safe repair was to force-stop the app, back up
  `/data/user/0/com.mattermost.rn/files/datastore/RN_KEYCHAIN.preferences_pb`,
  then replace only the URL bytes in key names with
  `http://100.87.238.153:8065` (same string length; do not print token
  values). Also update the NetBird server DB `Config` row `SiteURL` from the
  old URL to the NetBird URL. Verified result: blank page changed back to the
  normal Mattermost server/onboarding UI.

## Android mobile NetBird migration failure mode (2026-07-18)

Symptom after changing `com.mattermost.rn` from Tailscale URL to NetBird URL:

- White screen was fixed by updating `RN_KEYCHAIN.preferences_pb` key names and the server DB `Config.SiteURL`, but the app still stayed on the unauthenticated `连接服务器` page.
- Tapping the blue `server_form.connect.button` did not issue any Mattermost HTTP request and did not navigate to login.
- App log repeatedly showed only startup failures such as:
  - `DatabaseManager: Initializing`
  - `SecurityManager: Failed to initialize`
  - earlier: `Cannot run database method query because database failed to open. Hint: Did you install JSI correctly?`
- Phone UID network was not the cause; Mattermost UID `10447` could still reach `http://100.87.238.153:8065/api/v4/system/ping`.
- SQLite integrity of both `app.db` and the NetBird server DB was OK from host-side `sqlite3`, so the failure is likely the app's WatermelonDB/JSI/native DB open state or keychain/launch state, not the server/network.

Safe handling notes:

1. Do not keep blind-tapping `server_form.connect.button`; if the app log has no new network request, the button path is stuck before `pingServer()`.
2. Before destructive repairs, take a private backup (contains credentials; do not paste contents):
   ```bash
   mkdir -p ~/.local/state/mattermost-mobile-backups
   adb-record --tag mattermost-full-backup -- -s 127.0.0.1:15555 shell 'su -c "tar -C /data/user/0 -czf /sdcard/mm-mobile-backup.tar.gz com.mattermost.rn/files/databases com.mattermost.rn/files/datastore com.mattermost.rn/cache/logs 2>/dev/null && chmod 0600 /sdcard/mm-mobile-backup.tar.gz"'
   adb-record --tag mattermost-full-backup -- -s 127.0.0.1:15555 pull /sdcard/mm-mobile-backup.tar.gz ~/.local/state/mattermost-mobile-backups/
   adb-record --tag mattermost-full-backup -- -s 127.0.0.1:15555 shell 'rm -f /sdcard/mm-mobile-backup.tar.gz'
   ```
3. Verify network separately from the app UI:
   ```bash
   adb-record --tag mattermost-uid-net -- -s 127.0.0.1:15555 shell 'su -c "su 10447 -c \"curl -4 -m 8 -sS http://100.87.238.153:8065/api/v4/system/ping\""'
   ```
4. If the app database path is suspected, inspect these files only; avoid dumping tokens:
   - `/data/user/0/com.mattermost.rn/files/databases/app.db`
   - `/data/user/0/com.mattermost.rn/files/databases/aHR0cDovLzEwMC44Ny4yMzguMTUzOjgwNjU=.db`
   - `/data/user/0/com.mattermost.rn/files/datastore/RN_KEYCHAIN.preferences_pb`
5. If `pm clear com.mattermost.rn` is used for a clean login test, note that it wipes the app-local DB/keychain. Restore from the private backup or complete a fresh login immediately; do not leave the app half-cleared.

## Android mobile login repair result (2026-07-18)

After `pm clear com.mattermost.rn`, the NetBird server setup was completed with:

- Server URL: `http://100.87.238.153:8065`
- Display name: `charlie-netbird`
- Login user: `charlie`

The remaining login failure was not caused by Mattermost credentials or network.
Host-side API login with the password file under
`~/.local/state/mattermost-ai-inbox/admin-password` succeeded, but ordinary
`adb shell input text "$password"` lost shell-special characters on Android and
submitted the wrong password.

Default safe password-entry path for future phone repairs:

```bash
adb-input-file-text \
  --serial 127.0.0.1:15555 \
  --tag mm-login-pass \
  --file ~/.local/state/mattermost-ai-inbox/admin-password
```

The helper pushes a temporary copy to `/data/local/tmp/`, has the phone read it,
types it one character at a time into the focused field, and removes the phone
temporary file. It prints only byte count and `adb-record` metadata; it must not
print the password. It is intended for ASCII passwords/tokens with special
characters. For Chinese/free text, prefer the phone MCP `phone_type` tool.

Verification after the successful login:

```bash
adb-record --tag mm-login-verify -- -s 127.0.0.1:15555 shell 'uiautomator dump /sdcard/mm.xml >/dev/null 2>&1'
adb-record --tag mm-login-verify -- -s 127.0.0.1:15555 pull /sdcard/mm.xml /tmp/mm.xml
```

Parse the pulled XML locally and redact `login_form.password.input` if the login
screen is still present. Success on 2026-07-18 showed `Charlie Hub`, server
`charlie-netbird`, and `channel.screen` after opening `AI 收件箱` / `ai-inbox`.

## Mature AI intake integration pattern (2026-07-18)

Mattermost is now the phone-first intake and collaboration surface for AI tasks,
images, documents, approvals, and receipts. The implemented pattern follows the
stable Mattermost integration split:

- Bot/PAT API polling downloads files and reads private/public intake channels.
- Incoming webhook posts Hub receipts back to Mattermost.
- Outgoing webhook/slash-command style payloads can hit Hub
  `/api/mattermost/outgoing`, but the poller remains the reliable default for
  attachments because it can fetch Mattermost file IDs through the REST API.
- Output channels must not be watched as input channels; otherwise Hub receipts
  can recursively create new Hub tasks.

Current watched input channels:

```text
ai-inbox, ai-images, ai-docs, ai-review
```

`ai-tasks` is an output/receipt channel only. Keep it out of
`MATTERMOST_WATCH_CHANNELS`.

Current local operations helper:

```bash
mattermost-ai-ops status
mattermost-ai-ops poll-once
mattermost-ai-ops test-task --channel ai-inbox --text 'Mattermost AI Ops 自测'
mattermost-ai-ops phone-verify
```

The helper prints only non-secret topology/status. It must not print webhook
URLs, PATs, bot tokens, passwords, or Mattermost database contents.

Implemented Hub routing behavior:

- `ai-inbox` / generic text -> Hub `pending_approval` task tagged
  `mattermost`, `ai-inbox`, `inbox` or `task`.
- `ai-images` or image-like attachments (`jpg/png/webp/heic/...`) -> task goal
  asks for image/OCR/renaming/classification/follow-up actions.
- `ai-docs` or document-like attachments (`pdf/docx/xlsx/md/txt/csv/json/...`)
  -> task goal asks for summary, key facts, archive path, and next actions.
- `ai-review` or messages mentioning confirmation/review -> task goal stops at
  human decision support and must not execute destructive actions.
- Hub receipts starting with `✅ 已进入 Hub 待审批`, `✅ Mattermost 对接自测已创建任务`,
  or `⚠️ Mattermost 收件失败` are skipped by the poller even if they appear in a
  watched channel.

Verification on 2026-07-18:

```text
mattermost-ai-ops status: all service/API/poller checks OK
mattermost-ai-ops poll-once: handled=0 after loop guard, channels=ai-inbox/ai-images/ai-docs/ai-review
mattermost-ai-ops phone-verify: Android Mattermost UID 10447 reached http://100.87.238.153:8065/api/v4/system/ping
```

A previous self-test briefly watched `ai-tasks` and created self-referential
Hub receipt tasks. They were cancelled with reason
`self-generated receipt from ai-tasks output channel`; the real self-test task
`pt_20260718165140_7fe9428f` was preserved.

## Android `server unreachable` / NetBird + session repair runbook (2026-07-18)

Symptom: Android Mattermost shows `Server unreachable` or `Limited network connection`
while Fedora Mattermost itself is healthy.

Default deterministic helper:

```bash
mattermost-phone-repair status
mattermost-phone-repair fix-siteurl
mattermost-phone-repair netbird-login   # only when Fedora netbird status says NeedsLogin
mattermost-phone-repair clear-login     # backs up phone app data, root pm clear, re-adds server, logs in
```

If Android opens normally but newly-created agent channels such as `cursor`,
`goose`, or `aider` do not appear in the sidebar, do not treat it as NetBird or
server cache first. Check whether the logged-in mobile user is a channel member:

```bash
mattermost-ai-ops agent-guides --create
```

`mattermost-agent-channels apply` now joins the configured mobile user
`MATTERMOST_AGENT_MEMBER_USER` (default `charlie`) to all agent channels so the
mobile sidebar can sync them. Verify from the phone with:

```bash
adb-record --tag mm-open -- -s 127.0.0.1:15555 shell 'monkey -p com.mattermost.rn -c android.intent.category.LAUNCHER 1'
adb-record --tag mm-ui-dump -- -s 127.0.0.1:15555 shell 'uiautomator dump /sdcard/mm.xml >/dev/null && cat /sdcard/mm.xml' | grep -E 'Cursor|Goose|Aider|Server unavailable|Server unreachable'
```

If `Your servers` shows `Server is unreachable.` while channels still load and
phone UID HTTP ping succeeds, check WebSocket Origin/CORS before clearing the
app. Mattermost Mobile displays this text from
`WebsocketManager.observeWebsocketState(serverUrl)`, not from the ordinary HTTP
ping. The 2026-07-18 confirmed failure was:

```text
URL Blocked because of CORS. Url: http://100.87.238.153:8065
websocket: request origin not allowed by Upgrader.CheckOrigin
status_code=400
```

Repair by allowing the private origins in `ServiceSettings.AllowCorsFrom`; this
rootless Podman volume must be edited through `podman unshare`, not plain sudo:

```bash
mattermost-phone-repair fix-siteurl
systemctl --user restart mattermost.service
mattermost-phone-repair status
```

Expected `status` now includes both:

```text
phone_uid_http_ok=true
phone_uid_websocket_origin_ok=true
```

Manual WebSocket check from the Android Mattermost UID:

```bash
adb-record --tag mm-ws-origin-test -- -s 127.0.0.1:15555 shell 'su -c "su 10447 -c '\''curl -4 -m 8 -sS -i -N -H Origin:http://100.87.238.153:8065 -H Connection:Upgrade -H Upgrade:websocket -H Sec-WebSocket-Version:13 -H Sec-WebSocket-Key:dGhlIHNhbXBsZSBub25jZQ== http://100.87.238.153:8065/api/v4/websocket | head -n 6'\''"'
```

Expected first line: `HTTP/1.1 101 Switching Protocols`. Then force-stop/reopen
Mattermost and re-open the server sheet; `Server is unreachable.` should be
absent.

Observed root causes in the 2026-07-18 repair:

1. Phone NetBird initially lacked an active `tun0` route.
2. Fedora NetBird then reported `Daemon status: NeedsLogin`; setup-key re-enroll
   returned `peer login has expired, please log in once more`. The working path
   was SSO login from a Fedora-hosted browser, then `netbird status` returned
   `Management: Connected`, `Signal: Connected`, `Peers count: 1/1 Connected`.
3. After NetBird recovered, Mattermost UID `10447` could reach
   `http://100.87.238.153:8065/api/v4/system/ping` with `HTTP:200`, but the
   mobile app still had stale local session state and logged websocket
   `Forbidden`. A normal shell `pm clear` can be denied on ColorOS; use root:

   ```bash
   adb-record --tag mm-root-clear-session -- -s 127.0.0.1:15555 shell \
     'su -c "am force-stop com.mattermost.rn; pm clear --user 0 com.mattermost.rn"'
   ```

4. Before destructive mobile repairs, take a private backup; the helper stores
   it under `~/.local/state/mattermost-mobile-backups/` and must not print
   tokens/passwords.
5. Re-login uses server URL `http://100.87.238.153:8065`, display `netbird`,
   username `charlie`, and password from
   `~/.local/state/mattermost-ai-inbox/admin-password` through
   `adb-input-file-text` so special characters are not corrupted or logged.
6. Server `ServiceSettings.SiteURL` must stay aligned to the Android NetBird
   URL for this mobile path:

   ```text
   ServiceSettings.SiteURL=http://100.87.238.153:8065
   ServiceSettings.WebsocketURL=
   ```

Verification after the repair:

```bash
mattermost-phone-repair status
adb-record --tag mm-uid-final -- -s 127.0.0.1:15555 shell \
  'su -c "su 10447 -c \"curl -4 -m 8 -sS -w \\\"\\nHTTP:%{http_code}\\n\\\" http://100.87.238.153:8065/api/v4/system/ping\""'
```

Expected: `Peers count: 1/1 Connected`, `HTTP:200`, Mattermost UI shows
`Charlie Hub`, server display `netbird`, and no `Server unreachable` or
`Limited network connection` banner. If the log still shows websocket
`Forbidden` but the UI has no unreachable banner and channel switches are logged,
record it as a follow-up WebSocket/auth optimization rather than redoing NetBird
or clearing the app repeatedly.

## Channel-as-Agent guide layer (2026-07-18)

Mattermost channels are now treated as lightweight agents, not bare titles.  The
canonical refresh command is:

```bash
mattermost-ai-ops agent-guides
# lower-level helper:
mattermost-agent-channels apply
```

What the helper does without printing secrets:

- Reads `~/.config/mattermost-ai-inbox.env` for local Mattermost URL, team, and
  bot token.
- Updates channel display name/purpose/header for these agent channels:
  `ai-inbox`, `ai-images`, `ai-docs`, `ai-review`, `ai-tasks`, `hub`, `op`,
  `fastgpt`, `alerts`, and `sourcing`.
- Posts/pins an idempotent guide message containing a marker like
  `<!-- charlie-agent-guide:<channel>:v20260718-agent-router -->`.
- Sends a direct-message guide to Mattermost user `charlie` by default; override
  with `mattermost-ai-ops agent-guides --dm-user <username>`.
- If the bot cannot edit a channel header through the REST API, the helper can
  fall back to the local Mattermost Postgres container and updates only
  `channels.displayname`, `channels.purpose`, `channels.header`, and
  `channels.updateat`. Do not paste database rows or tokens into logs.

Agent mapping:

- `ai-inbox`: total intake Agent for text, links, images, docs, and phone tasks.
- `ai-images`: image/OCR/screenshot organization Agent.
- `ai-docs`: document/link/material summary and archive Agent.
- `ai-review`: redline approval Agent; destructive/payment/external-message/
  login/network changes stop here until the user confirms.
- `ai-tasks`: output-only receipt/status Agent. Keep it out of
  `MATTERMOST_WATCH_CHANNELS`.
- `hub`: Hub project/approval/status Agent.
- `op`: OpenCode/OP execution Agent for code/scripts/services after Hub approval.
- `fastgpt`: knowledge/FAQ/best-practice Agent.
- `alerts`: network/service/phone alert Agent.
- `sourcing`: web/product/open-source/vendor sourcing Agent.

The poller is not allowed to be an empty intake shell. For every non-skipped
user post in a watched input channel, `~/.local/bin/mattermost-ai-inbox` must:

1. download attachments when present;
2. create the Hub `pending_approval` task;
3. post a thread reply back to the original Mattermost channel with:
   - current channel / agent name,
   - a short direct answer generated through local LiteLLM
     (`MATTERMOST_AGENT_MODEL`, default `deepseek-v4-flash`),
   - inferred route,
   - Hub task ID,
   - next reply options,
   - NetBird/LAN Hub links,
   - 🔴 redline rules.

Explicit messages beginning with `step:`, `step ui:`, `gelab:`, `手机操作:`,
`跨app:`, or `跨应用:` also call Mobile AI Workbench / Step Router and then
force-save the clean user task to:

```text
~/.local/state/mobile-ai-super/latest-step-task.txt
```

The Step Router endpoint is:

```text
POST http://127.0.0.1:19888/api/super/dispatch?device=w19900422
```

Safety and loop guards:

- Hub and poller skip messages containing `<!-- charlie-agent-guide:` so pinned
  guide posts do not create Hub tasks.
- Hub and poller still skip Hub receipt prefixes such as `✅ 已进入 Hub 待审批`.
- Poller skips its own bot user ID and its `🤖`/agent reply prefixes, otherwise
  agent replies would create a self-loop.
- Poller does not send messages that appear to contain passwords, API keys,
  bearer tokens, private keys, or similar secrets to the model; it replies in a
  local safe mode and still creates the Hub task.
- Poller uses `~/.local/state/mattermost-ai-inbox/poller.lock` with `flock` so
  the systemd loop and manual `mattermost-ai-inbox poll-once` cannot process the
  same post concurrently. Without this lock, a manual test while the service is
  running can create duplicate Hub tasks and duplicate Mattermost replies.
- `ai-tasks` is explicitly skipped by the Hub intake API even if an outgoing
  webhook accidentally sends it there.
- If a guide post ever creates a task, cancel it with status `cancelled` and
  blocker `Mattermost agent guide post, not a user task`, then verify the marker
  skip remains in both `~/hub/hub-api.py` and `~/.local/bin/mattermost-ai-inbox`.

Verification commands:

```bash
python3 -m py_compile ~/hub/hub-api.py ~/.local/bin/mattermost-ai-inbox ~/.local/bin/mattermost-ai-ops ~/.local/bin/mattermost-agent-channels
mattermost-ai-ops agent-guides
curl --noproxy '*' -fsS http://127.0.0.1:9800/api/mattermost/integration/status | jq '{ok, guide_count:(.agent_guides|length), step_router, watch_channels:.env.watch_channels}'
mattermost-ai-ops poll-once
```

Expected:

- `guide_count` covers all agent channels, including `cursor`, `goose`, and
  `aider`.
- `watch_channels` includes `ai-inbox`, `ai-images`, `ai-docs`, `ai-review`,
  `cursor`, `goose`, and `aider`; `ai-tasks` remains output-only.
- `poll-once` returns `handled=0` immediately after refreshing guides.
- A synthetic user Mattermost intake response creates a log event with
  `reply_id`, and the reply contains `当前频道`, `直接回复`, Hub task ID, and
  `红线`.
- A synthetic `step:` intake response contains `Step Router`, and
  `latest-step-task.txt` contains the clean user instruction, not the router
  prefix.
- Full-channel verification on 2026-07-18 passed for:
  `ai-inbox`, `ai-images`, `ai-docs`, `ai-review`, `cursor`, `goose`, and
  `aider`; each test post had exactly one bot thread reply. Test Hub tasks with
  prefix `single-poller-agent-reply-` were cancelled after verification.

As of 2026-07-18, live phone ADB verification may be blocked if neither
`127.0.0.1:15555` nor `192.168.123.22:5555` is reachable.  This does not block
Mattermost channel guide visibility because the guides are stored server-side;
when the Android app reconnects to `http://100.87.238.153:8065`, the headers and
pinned guide posts sync normally.

## NetBird/LAN dual links and communication sync correction (2026-07-18)

Mattermost user-facing links must not be local-only.  For phone use, show both:

- NetBird Hub: `http://100.87.238.153:9800/projects`
- LAN Hub: `http://192.168.123.71:9800/projects`
- NetBird Mattermost: `http://100.87.238.153:8065/`
- LAN Mattermost: `http://192.168.123.71:8065/`

`~/.config/mattermost-ai-inbox.env` now contains non-secret URL keys:

```text
HUB_PROJECTS_NETBIRD_URL=http://100.87.238.153:9800/projects
HUB_PROJECTS_LAN_URL=http://192.168.123.71:9800/projects
MATTERMOST_NETBIRD_URL=http://100.87.238.153:8065
MATTERMOST_LAN_URL=http://192.168.123.71:8065
```

Receipts from Hub include both NetBird and LAN approval links.  Channel guides
were refreshed with:

```bash
mattermost-ai-ops agent-guides --force-post
```

Project/task state is synced to Mattermost/Zulip/ntfy by
`comm-project-sync.timer`; see `communication-project-sync.md`.

## Cursor / Goose / Aider execution channels imported (2026-07-18)

The user's core execution-routing need is now explicit in Mattermost.  These are
real watched input channels, not just title-only documentation:

```text
cursor, goose, aider
```

They were created/refreshed with:

```bash
mattermost-ai-ops agent-guides --create --force-post
```

Current watched channels are:

```text
ai-inbox, ai-images, ai-docs, ai-review, cursor, goose, aider
```

Keep `ai-tasks` output-only and never add it to `MATTERMOST_WATCH_CHANNELS`.

### Channel mapping

| Channel | Purpose | Hub intake kind | Default Hub assignee | Execution surface |
|---|---|---|---|---|
| `cursor` | Cursor GUI/IDE, visual frontend checks, plugins, login-state/UI tasks | `cursor` | `plan` | Cursor/KasmVNC |
| `goose` | read-only diagnosis, planning, risk review, context gathering | `goose` | `plan` | Goose/Guise |
| `aider` | approved minimal code/config writes | `aider` | `goose_aider` | Goose review -> Aider single-writer |
| `op` | general OpenCode/OP execution and repair | `task`/`inbox` | env default, usually `op` | OpenCode/agent-dispatch |

### User-facing links

- Cursor NetBird: `http://100.87.238.153:19970/`
- Cursor LAN: `http://192.168.123.71:19970/`
- Goose NetBird: `http://100.87.238.153:7694/tool/guise/`
- Goose LAN: `http://192.168.123.71:7694/tool/guise/`
- Aider NetBird: `http://100.87.238.153:7693/tool/aider/`
- Aider LAN: `http://192.168.123.71:7693/tool/aider/`

### Routing behavior

`~/hub/hub-api.py` classifies Mattermost intake as:

- `cursor` channel or text containing `cursor`/`kasm`/GUI/visual frontend terms
  -> `intake_kind=cursor`, assignee `plan`.
- `goose` channel or text containing Goose/Guise/read-only/diagnosis/plan terms
  -> `intake_kind=goose`, assignee `plan`.
- `aider` channel or text containing Aider/single-writer/minimal-change terms
  -> `intake_kind=aider`, assignee `goose_aider`.

Order matters: Aider is checked before Goose so `goose_aider` does not
misclassify an `aider` channel task as Goose.

### Verification

```bash
mattermost-ai-ops status | jq '.env.watch_channels'
curl --noproxy '*' -fsS http://127.0.0.1:9800/api/mattermost/integration/status | jq '{guide_count:(.agent_guides|length), cursor:.agent_guides.cursor, goose:.agent_guides.goose, aider:.agent_guides.aider}'
comm-project-sync status | jq '{cursor:.urls.cursor, goose:.urls.goose, aider:.urls.aider}'
```

Expected on 2026-07-18:

- `guide_count=13`.
- `cursor`, `goose`, and `aider` exist in `agent_guides`.
- `watch_channels` includes `cursor`, `goose`, `aider` and excludes `ai-tasks`.
- Synthetic route checks produced:
  - `cursor` -> assignee `plan`, tag `cursor`
  - `goose` -> assignee `plan`, tag `goose`
  - `aider` -> assignee `goose_aider`, tag `aider`

Synthetic verification tasks were cancelled after testing.
