# Phone Error Log Watch

Purpose: keep a periodic Android crash/error summary for PKR110 so phone app
failures such as Niagara, Haven, NetBird, input method, and game/network issues
are not lost from volatile `logcat`.

## Service

- Script: `~/.local/bin/phone-error-log-watch`
- Timer: `phone-error-log-watch.timer`
- Interval: every 10 minutes
- Primary serial order: `100.87.37.3:5555`, `127.0.0.1:15555`, `192.168.123.241:5555`, then legacy `192.168.123.22:5555`
- Uses `~/.local/bin/adb-record --tag phone-error-log-watch` for ADB evidence.

## State

- Summary: `~/.local/state/phone-error-log-watch/latest.md`
- JSON: `~/.local/state/phone-error-log-watch/latest.json`
- History: `~/.local/state/phone-error-log-watch/history.jsonl`

## Manual commands

```bash
systemctl --user status phone-error-log-watch.timer phone-error-log-watch.service
systemctl --user start phone-error-log-watch.service
sed -n '1,160p' ~/.local/state/phone-error-log-watch/latest.md
jq '.dropbox_recent[-8:]' ~/.local/state/phone-error-log-watch/latest.json
```

## Niagara launcher notes

- Package: `bitpit.launcher`
- Main activity: `bitpit.launcher/.ui.HomeActivity`
- Check default home:

```bash
~/.local/bin/adb-record --tag niagara-check -- -s 127.0.0.1:15555 shell \
  'cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME'
```

2026-07-19 investigation: the recent Dropbox crash at `06:13:23` was not
Niagara; it was `com.accessibilitymanager` failing before user unlock with
`SharedPreferences in credential encrypted storage are not available until after user (id 0) is unlocked`.
Niagara `bitpit.launcher` v`1.16.14` was installed, not suspended, and a
controlled launch produced a running PID without `AndroidRuntime`/`FATAL
EXCEPTION` in the captured logcat. Default home later resolved to
`bitpit.launcher/.ui.HomeActivity`.


## Alipay / Luckin mini-app notes

2026-07-19: `phone-error-log-watch` also matches `com.eg.android.AlipayGphone`, `Alipay`, `luckin`, and `瑞幸`. For Luckin mini-app login no-response, first verify Alipay UID network/DNS through root Mihomo before treating it as a mini-app UI issue. The known bad state is a live `mihomo` process with missing listeners for `7890/7892/9000/5354`; see `mihomo-control.md`.

## Common current signals

- `com.accessibilitymanager`: boot-before-unlock receiver crash; usually not a
  Niagara failure.
- `com.iflytek.inputmethod.oem`: repeated `StringIndexOutOfBoundsException` in
  iFlytek IME background thread.
- `sh.haven.app`: if `SQLiteDatabaseCorruptException` appears, inspect Haven DB
  backups before editing `/data/user/0/sh.haven.app/databases/haven.db`.

## Rotation / NetBird guards

- `phone-netbird-ensure.timer`: every 5 minutes, monitor-only by default. It
  checks whether the Fedora NetBird host for Haven UID routes via `tun0`; state
  `~/.local/state/phone-netbird-ensure/latest.json`.
- `phone-rotation-guard.timer`: every 5 minutes, keeps Android
  `accelerometer_rotation=0` and `user_rotation=0` for users `0/10/11/999`;
  state `~/.local/state/phone-rotation-guard/latest.json`.

2026-07-19 rotation investigation: the rotation state was already off for user
`0` but on for users `10/11/999`. `org.crape.rotationcontrol` was the most
suspicious app because it has `WRITE_SETTINGS`, overlay permission, and
`BOOT_COMPLETED`; its `WRITE_SETTINGS` appop was set to `ignore` and the guard
keeps all users locked to portrait. `MacroDroid` also has `WRITE_SETTINGS` and
accessibility enabled, so if rotation still flips, inspect MacroDroid macros
next rather than blaming the system UI.

## Game / browser foreground guard

2026-07-19: League of Legends: Wild Rift packages on PKR110 are
`com.tencent.lolm` and `com.tencent.lolmtyf`. NetBird Android does not expose a
safe per-app exclusion config, and its VPN DNS can break public DNS for game and
browser foreground use. As of 2026-08-01, `phone-netbird-ensure.timer` runs
every 5 minutes and must not blindly reconnect/tap NetBird by default; enable
`PHONE_NETBIRD_AUTO_REPAIR=1` only for an explicit short repair window. Browsers
are not a pause trigger because WebTTY/Workbench should keep using NetBird when
public/DuckDNS is degraded. Haven should prefer numeric NetBird IP profiles,
not DNS names.
