# Runbook: Google Login State

Purpose: keep each browser/profile's Google login state durable and isolated.
Different Google accounts must not share or overwrite cookies across profiles.

## Files and Services

- Source profile: `~/.config/google-chrome`
- Desktop Chromium target: `~/.config/chromium`
- Mobile browser target: `~/.config/mobile-ai-chromium`
- Backup directory: `~/.local/state/chrome-backup`
- Target rollback snapshots: `~/.local/state/google-login-sync`
- Legacy sync script: `~/.local/bin/google-login-state-sync` (disabled by
  default; one-shot recovery requires `GOOGLE_LOGIN_ALLOW_CROSS_PROFILE_SYNC=1`)
- Independent backup script: `~/.local/bin/browser-login-state-backup`
- Isolated account launcher: `~/.local/bin/google-account-browser`
- Backup script: `~/.local/bin/chrome-login-backup.sh`
- Restore script: `~/.local/bin/chrome-login-restore.sh`
- Watchdog script: `~/.local/bin/chrome-login-watchdog.sh`
- Timers:
- `chrome-login-backup.timer`: hourly independent backup of Chromium-family
  and Firefox profiles; never copies state between profiles.
- `chrome-login-watchdog.timer`: keep disabled for multi-account setups; its
  historical single-profile auto-restore can restore the wrong account.
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

2. Run an independent backup:

   ```bash
   ~/.local/bin/browser-login-state-backup
   ```

3. Enable or restart the timers:

   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now chrome-login-backup.timer
   systemctl --user disable --now chrome-login-watchdog.timer
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
- If Google invalidates cookies, complete one normal login in that same
  browser/profile, then run the independent backup.
- Create additional isolated profiles with
  `google-account-browser chromium <label>` or
  `google-account-browser firefox <label>`.

## Android Passkey / Google Prompt Verification

- Open `https://g.co/passkeys` in Chrome. A device entry showing the phone
  model and `Last used: Just now` proves the platform passkey was actually
  exercised; do not create a duplicate when `Create a passkey` is disabled.
- Google Prompt readiness requires all of the following phone-side evidence:
  Google Play services notification permission allowed, GMS present in the
  device-idle allowlist, TCP `mtalk.google.com:5228` reachable, and an
  established `com.google.android.gms.persistent` connection on port 5228.
- Keep the phone Mihomo `Proxy` selector on one fixed node for Google login;
  do not leave it on an `Auto`/URL-test group that can change countries during
  an authentication flow. Confirm the selection survives a Mihomo restart.
- If two Mihomo PIDs split ownership of `7890/5354` and `7892`, run
  `~/.local/bin/phone-mihomo-clean-restart <serial>` and verify one PID owns
  all four listeners before testing Google Prompt.
