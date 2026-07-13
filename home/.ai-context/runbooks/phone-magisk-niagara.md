# Phone Magisk / Niagara Reboot Baseline

Last updated: 2026-06-28 18:09 CST

## Device / ADB

Use the stable local ADB endpoint first:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "id"'
```

Tailscale ADB may also exist, but for reboot comparisons prefer `127.0.0.1:15555` when available.

## Pre-Reboot Baseline

Captured after cleanup on 2026-06-28 18:03:12 CST:

```text
ROOT=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
SU=30.7:MAGISKSU
MAGISK=30.7:MAGISK:R
DENY=Denylist is enforced
HOME_U0_ROLE=bitpit.launcher,
HOME_U0=bitpit.launcher/.ui.HomeActivity
HOME_U10_ROLE=bitpit.launcher,
HOME_U10=com.android.launcher/.Launcher
QISHUI=versionCode=100198030 minSdk=21 targetSdk=30; versionName=19.8.0; lastUpdateTime=2026-06-26 20:38:16; installerPackageName=mark.via.gp; initiatingPackageName=com.android.shell;
MAGISK_PKGS:
  U=0 package:io.github.vvb2060.magisk
  U=10 no magisk manager package
  U=11 no magisk manager package
  U=999 no magisk manager package
SELFHEAL=/data/adb/service.d/95-phone-selfheal.sh
```

Expected post-reboot state:

- `su` works and context includes `u:r:magisk:s0`.
- `magisk -v` remains `30.7:MAGISK:R`.
- `magisk --denylist status` says `Denylist is enforced`.
- User 0 HOME resolves to `bitpit.launcher/.ui.HomeActivity`.
- `com.topjohnwu.magisk` should not be installed for users 0/10/11/999.
- `io.github.vvb2060.magisk` should remain installed for user 0.

Known ColorOS caveat:

- User 10 / `system_clone` may have role holder `bitpit.launcher` but still resolve HOME to `com.android.launcher/.Launcher`. Do not disable the system launcher globally without explicit approval.

## Compare Command

Run after reboot:

```sh
adb -s 127.0.0.1:15555 shell 'su -c '\''echo DATE=$(date "+%F %T %Z"); echo ROOT=$(id); echo SU=$(su -v); echo MAGISK=$(magisk -v); echo DENY=$(magisk --denylist status 2>&1); echo HOME_U0_ROLE=$(cmd role get-role-holders --user 0 android.app.role.HOME 2>/dev/null | tr "\n" ","); echo HOME_U0=$(cmd package resolve-activity --user 0 --brief -a android.intent.action.MAIN -c android.intent.category.HOME 2>/dev/null | tail -n 1); echo HOME_U10_ROLE=$(cmd role get-role-holders --user 10 android.app.role.HOME 2>/dev/null | tr "\n" ","); echo HOME_U10=$(cmd package resolve-activity --user 10 --brief -a android.intent.action.MAIN -c android.intent.category.HOME 2>/dev/null | tail -n 1); echo QISHUI=$(dumpsys package com.luna.music | grep -E "versionCode|versionName|installerPackageName|initiatingPackageName|lastUpdateTime" | tr "\n" ";"); echo MAGISK_PKGS_START; for u in 0 10 11 999; do echo U=$u; pm list packages --user $u 2>&1 | grep -E "com.topjohnwu.magisk|io.github.vvb2060.magisk" || true; done; echo MAGISK_PKGS_END; echo SELFHEAL=/data/adb/service.d/95-phone-selfheal.sh; echo SELFHEAL_LOG; tail -n 80 /data/adb/phone-selfheal.log 2>/dev/null || true'\'''
```

## Actions Already Applied

- Removed bad/stub `com.topjohnwu.magisk` from users 0 and 10.
- Kept real Magisk alpha/fork manager package `io.github.vvb2060.magisk`.
- Added Qishui Music `com.luna.music` processes to Magisk DenyList:
  - `com.luna.music`
  - `com.luna.music:push`
  - `com.luna.music:player`
- Installed `/data/adb/service.d/95-phone-selfheal.sh` to reapply DenyList and user 0 Niagara HOME after boot.
- Updated `/data/adb/service.d/95-phone-selfheal.sh` to remove boot-reinstalled `com.topjohnwu.magisk` stub for users 0/10/11/999 after Magisk has started.

## Post-Reboot Result

Observed after user reboot on 2026-06-28 18:07 CST:

```text
ADB: 127.0.0.1:15555 and 100.108.28.44:5555 both online
ROOT=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
SU=30.7:MAGISKSU
MAGISK=30.7:MAGISK:R
DENY=Denylist is enforced
HOME_U0_ROLE=bitpit.launcher,
HOME_U0=bitpit.launcher/.ui.HomeActivity
HOME_U10_ROLE=bitpit.launcher,
HOME_U10=com.android.launcher/.Launcher
QISHUI=versionCode=100198030 minSdk=21 targetSdk=30; versionName=19.8.0; lastUpdateTime=2026-06-26 20:38:16; installerPackageName=mark.via.gp; initiatingPackageName=com.android.shell;
```

One mismatch appeared after reboot:

- `com.topjohnwu.magisk` was reinstalled at `2026-06-28 18:05:34` from `/data/adb/magisk/stub.apk`.
- Its SHA256 matched `/data/adb/magisk/stub.apk`, so it was Magisk's built-in stub, not an unknown third-party installer.
- After updating and running selfheal, `com.topjohnwu.magisk` was removed again and only `io.github.vvb2060.magisk` remained for user 0.

## Failure Clues

- If `com.topjohnwu.magisk` returns, inspect immediately:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "pm path com.topjohnwu.magisk; dumpsys package com.topjohnwu.magisk | grep -E \"versionCode|versionName|firstInstallTime|lastUpdateTime|installerPackageName|initiatingPackageName|codePath|User [0-9]+:\"; tail -n 120 /cache/magisk.log | grep -E \"topjohnwu|signature|APK|pkg|stub|manager|cert\" || true"'
```

- If `su` fails after reboot, this is below `service.d`; check current slot / boot image / OTA patch state before editing service scripts.
- If user 0 HOME becomes resolver or system launcher, rerun:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "cmd role add-role-holder --user 0 android.app.role.HOME bitpit.launcher 0; cmd package set-home-activity --user 0 bitpit.launcher/.ui.HomeActivity"'
```
