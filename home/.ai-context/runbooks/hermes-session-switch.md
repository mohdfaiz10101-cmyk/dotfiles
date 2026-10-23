# Hermes Session Switch Issue Runbook

## Symptom
- Clicking another conversation in Hermes WebUI sometimes shows the same old chat again.
- URL keeps adding `/session/<id>` fragments or switches without actually loading the target session.
- Happens repeatedly when switching tasks/chats.

## Quick Checks
1. Frontend audit log: `/var/home/charlie/.local/state/hermes-session-switch/latest.log`
2. Hermes WebUI service: `systemctl --user status hermes-webui.service`
3. Homepage smoke: `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8787/`
4. Directed frontend verification: `node /var/home/charlie/.local/state/hermes-session-switch/verify_selected_functions.run.js`

## Fixed Code Paths
- `static/sessions.js` now prefers pathname `/session/<id>` over hash routes when no search state is retained.
- `_setActiveSessionUrl()` clears stale `/session/<id>` hashes for plain session switches and uses `replaceState` for non-launch switches.
- `_sessionUrlForSid()` keeps search params but drops redundant self-referential hashes.

## Recovery
- If a tab gets stuck on the wrong session, refresh once.
- If it repeats, run the audit script and check if recent session mtimes/drafts are changing unexpectedly.

## Prevention
- Systemd timer `hermes-session-switch-audit.timer` records session list/draft snapshots every 2 minutes.

## 2026-10-23 Deleted-session recovery
- Confirm user deletion before diagnosing networking: `/api/session?session_id=<id>` may return `Session not found` while the HTML shell returns 200.
- WebUI deletion removes state.db rows/messages, sidecars, run/turn journals, request dumps and writes `webui/sessions/_deleted_webui_sessions.json`. Do not expect orphan recovery to undo intentional deletion.
- First preserve the current state.db plus WAL/SHM in a private, session-specific directory. Never restore a full old database over live sessions.
- Recovery sources: `~/备份/home-essentials-*.tar.zst` and newer `~/workspace/cold-backup/latest/cold-backup-*.tar.zst`; extract only `.hermes/state.db` and compare target message count/timestamps. These backups exclude WebUI sidecars.
- Restore only the requested session and its messages in a transaction; allocate fresh message IDs, preserve structured tool calls/reasoning, write its JSON sidecar without overwriting. Clear only that ID from the deletion tombstone.
- Publish the restored sidecar to the running service/index through `POST /api/session/rename` with its unchanged original title. This uses the application's locks and broadcasts the list change; no shared service restart needed.
- Verify target DB count, `/api/session`, sidebar `/api/sessions?sidebar_source=webui&exclude_hidden=1`, and browser render. Report backup cutoff explicitly; never claim a complete recovery if later messages are missing.
- Case: `e5a5671f6be1` restored 264 records through 2026-10-23 14:55:25 from the 14:55:40 cold backup. Pre-delete UI logs showed 368 records. Recovery artifacts: `~/.local/state/hermes-session-recovery/e5a5671f6be1-20261023-173935/`.
