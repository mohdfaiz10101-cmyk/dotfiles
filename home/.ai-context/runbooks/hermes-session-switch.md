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
