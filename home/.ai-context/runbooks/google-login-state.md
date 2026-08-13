# Runbook: Google Login State

Purpose: keep the desktop Chrome Google login state reusable by desktop
Chromium and the Mobile AI Workbench controlled browser without storing Google
passwords in scripts.

## Files and Services

- Source profile: `~/.config/google-chrome`
- Desktop Chromium target: `~/.config/chromium`
- Mobile browser target: `~/.config/mobile-ai-chromium`
- Backup directory: `~/.local/state/chrome-backup`
- Target rollback snapshots: `~/.local/state/google-login-sync`
- Sync script: `~/.local/bin/google-login-state-sync`
- Backup script: `~/.local/bin/chrome-login-backup.sh`
- Restore script: `~/.local/bin/chrome-login-restore.sh`
- Watchdog script: `~/.local/bin/chrome-login-watchdog.sh`
- Timers:
  - `chrome-login-backup.timer`: hourly backup plus fan-out sync.
  - `chrome-login-watchdog.timer`: checks every 10 minutes and restores the
    desktop Chrome login marker from the latest backup when it disappears.
- `mobile-ai-browser.service` runs
  `ExecStartPre=%h/.local/bin/google-login-state-sync %h/.config/mobile-ai-chromium`
  before launching Chromium on CDP `127.0.0.1:9224`.

## Normal Repair

1. Confirm the source profile still has a Google account marker:

   ```bash
   python3 - <<'PY'
   import json, os
   state=json.load(open(os.path.expanduser('~/.config/google-chrome/Local State')))
   info=state.get('profile',{}).get('info_cache',{}).get('Default',{})
   print(bool(info.get('user_name') and info.get('gaia_name')))
   PY
   ```

2. Run a backup and sync:

   ```bash
   ~/.local/bin/chrome-login-backup.sh
   ~/.local/bin/google-login-state-sync
   ```

3. Enable or restart the timers:

   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now chrome-login-backup.timer chrome-login-watchdog.timer
   ```

4. Restart the mobile browser only when the phone browser panel needs a fresh
   process:

   ```bash
   systemctl --user restart mobile-ai-browser.service
   curl -fsS http://127.0.0.1:9224/json/version | jq -r .Browser
   ```

## Verification

Use counts and boolean markers only; do not print cookie values or tokens.

```bash
python3 - <<'PY'
import json, os, sqlite3
for root in ['~/.config/google-chrome','~/.config/chromium','~/.config/mobile-ai-chromium']:
    state=json.load(open(os.path.expanduser(root+'/Local State')))
    info=state.get('profile',{}).get('info_cache',{}).get('Default',{})
    db=os.path.expanduser(root+'/Default/Cookies')
    con=sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=2)
    count=con.execute("select count(*) from cookies where host_key like '%google.com' or host_key like '%accounts.google.%'").fetchone()[0]
    print(root, bool(info.get('user_name') and info.get('gaia_name')), count)
PY
```

## Notes

- Do not store Google account passwords in scripts or runbooks.
- If Google invalidates the copied cookies, complete a normal Google login once
  in desktop Chrome, then rerun the backup and sync commands.
- Avoid syncing into a target profile while that exact profile is running. The
  sync script skips targets whose `--user-data-dir` is currently active.
