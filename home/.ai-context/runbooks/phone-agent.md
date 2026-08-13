# Runbook: Phone Agent Control Plane

AidLux + ntfy based phone control loop. Use this when ADB, FRP, or Haven MCP is
unstable and Codex still needs to send short commands to the phone and read
results.

## Desired State

- Shared Codex phone-status MCP:
  - source: `~/.local/bin/phone-connect-mcp.py`
  - config source: `~/.config/mcp/servers.yaml` (`phone-connect`, core)
  - sync command: `~/.local/bin/mcp-sync.py --apply`
  - it is configured for Codex accounts 1–6.  Every phone-related task begins
    with the read-only `phone_status` tool; use its `healthy_for_phone_tasks`
    result before issuing controls.
  - default route is local FRP/USB (`127.0.0.1:15555`), then LAN Wi-Fi.
    Tailscale is explicit fallback only and is never required for normal phone
    control.
  - Tasker is detected as part of the status snapshot. Do not run
    `deploy-tasker-gateway.sh`: that legacy script overwrites Tasker's complete
    `autobackup.xml` rather than merging a profile.

- ntfy server:
  - local `http://127.0.0.1:2586`
  - LAN `http://192.168.123.71:2586` (fast path for the phone while home)
  - Tailscale `http://100.120.189.27:2586`
  - public `http://charlie1990.duckdns.org:19867`
  - Android ntfy app subscriptions should use the public base URL above, not
    the LAN URL, so notifications still arrive on 5G/portable Wi-Fi/non-LAN.
- Topics:
  - `charlie-actions`: user-facing notifications and copy links
  - `charlie-network`: network monitor alerts with recovery/Goose action buttons
  - `charlie-codex`: Codex completion notifications (restricted)
  - `charlie-system`: system alerts (restricted)
  - `phone-run`: Codex sends AidLux commands
  - `phone-status`: phone agent returns status/results
- Restricted ntfy mobile reader: `phone-channels`; its password is stored only
  in `~/.local/state/ntfy-phone-channels.password` (mode `0600`). It has
  read-only access to `charlie-actions`, `charlie-network`, `charlie-codex`,
  and `charlie-system`.
- Android ntfy database: `/data/user/0/io.heckel.ntfy/databases/AppDatabase`.
  Before direct DB edits, force-stop `io.heckel.ntfy`, copy a timestamped
  backup in the same directory, remove stale `AppDatabase-wal`/`-shm` after
  replacing the DB, and restore owner/mode/context to the app UID.
- File server:
  - `phone-agent-file-server.service`
  - serves `~/.local/share/phone-agent-web` at `http://100.120.189.27:9829`
- AidLux agent:
  - installer: `http://100.120.189.27:9829/install-aidlux-phone-agent.sh`
  - source: `~/.local/share/phone-agent.py`
  - runtime workdir on phone: `/home/aidlux/phone-agent-work`
- Root helper:
  - installer: `http://100.120.189.27:9829/install-root-helper.sh`
  - queue file: `/sdcard/Download/phone-root-queue.sh`
  - result log: `/sdcard/Download/phone-root-last.log`
  - persistent service when available: `/data/adb/service.d/97-phone-root-helper.sh`
  - root UID may not have working Tailscale/LAN/public networking; the helper
    must never depend on network posting for correctness. Read logs by USB/ADB
    when needed.

2026-08-10 current state:

- `phone-agent-file-server.service` has been recreated as a user service using
  `/usr/bin/python3 -m http.server 9829 --bind 0.0.0.0` from
  `~/.local/share/phone-agent-web`; it is enabled and active.
- `~/.local/share/phone-agent-web/frpc_smart.sh.new` is the latest PKR110
  FRPC wrapper source; `frpc-smart-update.sh` installs it to
  `/data/local/tmp/frpc_smart.sh` and restarts the phone wrapper.
- The old command wrappers `~/.local/bin/phone-run`,
  `~/.local/bin/phone-root-run`, `~/.local/bin/phone-status-read`, and
  `~/.local/bin/phone-command-push` are currently absent. Do not assume the
  AidLux ntfy command loop is usable until those wrappers or their replacement
  are restored.
- `phone-clipboard-receiver.service` and
  `~/.local/bin/phone-clipboard-receiver` are absent, and public/LAN port
  `19976` is now Hermes auth proxy. Do not recreate the old clipboard receiver
  on `19976` without assigning a new non-conflicting port.
- 2026-08-10 USB mode fix for PKR110: the phone was only presenting "charging"
  to the user. Over root ADB set `settings put global adb_enabled 1`,
  `settings put global development_settings_enabled 1`,
  `setprop persist.sys.usb.config mtp,adb`, and
  `svc usb setFunctions mtp,adb` / `setprop sys.usb.config mtp,adb`.
  Verified after state: `sys.usb.config=mtp,adb`,
  `sys.usb.state=mtp,adb`, `persist.sys.usb.config=mtp,adb`.
- Follow-up evidence the same night: `dumpsys usb` still reported
  `connected=false`, `kernel_state=DISCONNECTED`, and `data_role=no-data`
  while `usb_data_status=enabled`. That means Android's default USB function is
  correct, but the physical/data link was not enumerated. If the UI still only
  shows charging after replugging, check cable/USB port/connector first; the
  software-side MTP+ADB defaults have already been replayed by the FRPC Magisk
  boot service.

## Normal Commands

### ADB operation history

Use the recorder wrapper for repeatable phone diagnostics/configuration:

```sh
adb-record --tag mattermost -- -s ff3ef385 shell 'dumpsys window | grep -E "mCurrentFocus|mFocusedApp" | head'
adb-record --tag haven -- -s ff3ef385 shell 'su -c "dumpsys netpolicy | grep 10371 -A1 -B1"'
```

Log path:

```text
~/.local/state/adb-ops/history.jsonl
```

The wrapper runs `adb`, prints command output, and appends a JSONL record with
timestamp, cwd, serial, redacted command, return code, elapsed time, bounded
stdout/stderr tails, and output hashes. It is intentionally not a global `adb`
replacement. Do not put secrets in `--note` or command lines; common token and
password patterns are redacted, but full credentials, private keys, setup keys,
Mattermost tokens, and full app database dumps must still be avoided.

Send ordinary AidLux command:

```sh
phone-run "probe" "echo ok; id; pwd"
```

Read recent phone results:

```sh
phone-status-read
```

Queue a root command after root helper is installed:

```sh
phone-root-run "root probe" "id; getprop ro.product.model"
```

Push a short command/copy page to the phone:

```sh
phone-command-push "root helper 一键安装" \
  "curl -fsSL http://100.120.189.27:9829/install-root-helper.sh | sh"
```

## Bootstrap / Repair

If AidLux agent is missing or not consuming `phone-run`, push this short command
and run it inside AidLux:

```sh
curl -fsSL http://100.120.189.27:9829/install-aidlux-phone-agent.sh | sh
```

The installer must clean old pidfiles from both `~/phone-agent` and
`~/phone-agent-work`; if duplicate `phone-agent started` / `rc=0` messages appear
for the same ntfy id, rerun the installer from AidLux instead of sending more
`phone-run` commands.

If root access is needed, run this once in a Magisk/root shell:

```sh
curl -fsSL http://100.120.189.27:9829/install-root-helper.sh | sh
```

After that, Codex can use `phone-root-run` without asking the user to paste long
root commands.

## Verify

```sh
systemctl --user is-active container-ntfy.service phone-agent-file-server.service
curl --noproxy '*' -fsS http://100.120.189.27:2586/v1/health
curl -fsS http://127.0.0.1:9829/install-aidlux-phone-agent.sh | head
phone-run "agent probe" "echo PHONE_AGENT_OK; date; id; pwd"
sleep 5
phone-status-read | tail -n 40
```


## Token-Saving Smart Phone Operation Layer

Default path for future phone work:

1. Use `phone-smart "<task>"` as the first command router. It chooses the
   cheapest non-foreground path first:
   - visual/read-screen tasks -> `phone-see`
   - root/background/system tasks -> `phone-root-run`
   - ordinary shell tasks -> `phone-run`
   - tap/login/foreground tasks -> save a Step UI task file and stop unless the
     user explicitly asks to launch Step UI.
2. Use `phone-see "<question>"` when Codex needs to understand the phone
   screen. It captures a screenshot over ADB without foregrounding apps, sends
   it to a cheap vision model through local LiteLLM, and writes compact JSON to
   `~/.local/state/phone-vision/latest.json` and `latest.txt`. Codex should read
   those JSON/text summaries instead of loading screenshots into its own context.
3. Model policy: use Step models only, default `openai-compatible/step-3.7-flash`. Do not use GLM fallback. `step-3.5-flash-2603` does not support image input; use `step-3.7-flash` for screenshots. If Step vision returns empty/unsupported output, fail fast and save the screenshot path plus error so Codex does not waste more tokens.
4. Step UI/GELab-Zero is not the default executor because it touches the phone
   foreground and can interrupt the user. Use it only for tasks requiring visual
   clicking, login/permission dialogs, or app flows without backend APIs.


### ntfy Process Audit

`phone-see` and `phone-smart` now push best-effort process audit messages via
`~/.local/bin/phone-audit-ntfy` to ntfy channel `actions` / topic
`charlie-actions`. The same content is appended to
`~/.local/state/phone-smart/audit.log`. Audits include start/done/fail events,
selected route, tool/model, bounded token usage, compact summary, and local
screenshot path. Do not include API keys, OAuth tokens, passwords, private keys,
or full app databases. This is intended for user replay/review of intermediate
logic, not just final task result.

Verification:

```bash
phone-audit-ntfy test 'Phone audit test' 'ntfy audit pipeline ok'
phone-smart 'read current screen VPN status with Step only'
tail -n 40 ~/.local/state/phone-smart/audit.log
```

Commands:

```bash
phone-see "is VPN connected? return JSON"
cat ~/.local/state/phone-vision/latest.json | jq
phone-smart "fix Haven background permissions without opening UI"
phone-smart "read current screen and say what button is visible"
```

Verification note: `phone-see` is Step-only by policy. If the active Step model does not return visual content, it records `ok=false` in `~/.local/state/phone-vision/latest.json` and does not call GLM.

## Fast Clipboard Sync

KDE Connect is the clipboard transport. It keeps clipboard contents on the
LAN and must not be replaced with ntfy or Syncthing.

- Fedora service: `kdeconnectd.service`
- Fedora fast-send bridge: `kdeconnect-clipboard-bridge.service`
  - script: `~/.local/bin/kdeconnect-clipboard-bridge`
  - watches the Wayland clipboard every 0.5s and runs
    `kdeconnect-cli --device 75883083456a45978f45ca835c400474 --send-clipboard`
  - also refreshes the KDE Connect LAN link; as of 2026-07-18 it does **not**
    foreground the Android KDE Connect app by default, because repeatedly
    running `am start ... org.kde.kdeconnect_tp/.ui.MainActivity` made KDE
    Connect jump to the front page on the phone. Set `KDECONNECT_WAKE_PHONE=1`
    only for deliberate one-off repair.
  - log: `/tmp/kdeconnect-clipboard-bridge.log`; it records sizes/status, not
    clipboard contents
- Phone package: `org.kde.kdeconnect_tp`
- Phone-to-desktop fallback receiver:
  - Fedora service: `phone-clipboard-receiver.service`
  - script: `~/.local/bin/phone-clipboard-receiver`
  - listens on LAN port `19976/tcp`
  - token path: `~/.local/state/phone-clipboard/token` (mode `0600`; do not
    copy the value into runbooks or logs)
  - MacroDroid macro on the phone: `Phone to PC Clipboard Poll`
    (`m_GUID=-911976199760001`)
  - macro trigger/action chain: `RegularIntervalTrigger` every 2s →
    `UpdateClipboardAction` → `HttpRequestAction` POST body `{clipboard}` to
    the Fedora receiver
  - receiver writes POST body to Wayland via `wl-copy`, so desktop `Ctrl+V`
    pastes the phone clipboard after the macro fires
  - the receiver returns `204` for an empty POST body and does not write the
    desktop clipboard; this suppresses MacroDroid empty-clipboard polling noise
- Required firewall ports: `1714-1764/tcp` and `1714-1764/udp`
  for KDE Connect, plus `19976/tcp` for the MacroDroid phone-to-desktop
  fallback.
- The phone needs the KDE Connect foreground-notification permission and a
  battery-idle allowlist entry.
- On Android 16/ColorOS, KDE Connect also needs clipboard app-ops:
  `READ_CLIPBOARD=allow` and `WRITE_CLIPBOARD=allow`. Apply with root:

```sh
adb -s ff3ef385 shell 'su -c "appops set org.kde.kdeconnect_tp READ_CLIPBOARD allow; appops set org.kde.kdeconnect_tp WRITE_CLIPBOARD allow"'
```

`~/.local/bin/adb-phone-keepalive.sh` now replays the KDE Connect policy every
minute alongside Haven/Tailscale: package enable, Doze whitelist, clipboard app-ops,
background/foreground app-ops, wake lock, notification app-op, active standby
bucket, and netpolicy background whitelist. Use that script as the default
durable repair path rather than one-off appops commands.
It also tries the current KDE Connect LAN IP as `<ip>:5555`, so a phone DHCP
address change does not leave the keepalive script stuck on only the old static
`192.168.123.22:5555` address.
It also replays MacroDroid clipboard/background policy so the
`Phone to PC Clipboard` macro can keep monitoring Android clipboard changes.

If KDE Connect suddenly disappears from `kdeconnect-cli --list-available` while
ADB and Wi-Fi are healthy, check whether Android has disabled the package:

```sh
adb -s 192.168.123.22:5555 shell 'cmd package dump org.kde.kdeconnect_tp | grep -A3 "User 0:" | head'
```

If KDE Connect keeps jumping to the phone foreground, first check
`~/.local/bin/kdeconnect-clipboard-bridge` and
`/tmp/kdeconnect-clipboard-bridge.log`. The bridge must log
`kdeconnect phone foreground wake skipped` unless explicitly run with
`KDECONNECT_WAKE_PHONE=1`.

`enabled=3` means disabled-user state. Repair it and wake the app:

```sh
adb -s 192.168.123.22:5555 shell 'su -c "cmd package enable --user 0 org.kde.kdeconnect_tp; am start --user 0 -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n org.kde.kdeconnect_tp/org.kde.kdeconnect.ui.MainActivity"'
kdeconnect-cli --refresh --list-available
```

Verify the paired link:

```sh
kdeconnect-cli --refresh --list-available
```

If a paired phone is on the LAN but does not reappear after a firewall or
network change, restart the desktop daemon once, then refresh:

```sh
systemctl --user restart kdeconnectd.service
kdeconnect-cli --refresh --list-available
```

The device must report `paired and reachable` before testing clipboard sync.

Verify desktop-to-phone clipboard:

```sh
token="KDE_PC_TO_PHONE_$(date +%s)"
printf '%s' "$token" | WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 wl-copy
sleep 3
tail -n 20 /tmp/kdeconnect-clipboard-bridge.log
```

For strict proof, paste into a focused Android text field and inspect the UI
dump for the token. `dumpsys clipboard` may redact or omit clipboard payloads on
this phone.

Verify phone-to-desktop receiver path without exposing the token:

```sh
token="$(cat ~/.local/state/phone-clipboard/token)"
text="PHONE_TO_PC_$(date +%s)"
adb -s 192.168.123.22:5555 shell \
  "printf '%s' '$text' | curl --noproxy '*' -m 5 -fsS -X POST --data-binary @- 'http://192.168.123.71:19976/clipboard/$token' -o /dev/null -w '%{http_code}'"
wl-paste --no-newline
```

Expected HTTP status is `202`; `wl-paste` should equal `$text`. This verifies
the LAN receiver and desktop paste path. For true end-to-end verification, copy
new text in any Android app and confirm `~/.local/state/phone-clipboard/receiver.log`
records a new accepted hash and `wl-paste --no-newline` returns the copied text.
On Android 16/ColorOS, MacroDroid may run successfully but read an empty
clipboard after a real app copy; if logs show repeated HTTP `204` with no
accepted hash, do not keep changing the Fedora receiver. The blocker is Android
background clipboard access on the phone.

For root helper:

```sh
phone-root-run "root probe" "echo ROOT_HELPER_OK; id; date"
sleep 5
phone-status-read | tail -n 80
```

## APK install fallback when ADB is down

For Android APK tasks, KDE Connect can be used only as a file-delivery fallback,
not as a silent installer. If `adb devices` is empty and both the FRP
`127.0.0.1:15555` and LAN `:5555` paths fail, this is the safe fallback:

```sh
kdeconnect-cli --refresh --list-available
kdeconnect-cli --device 75883083456a45978f45ca835c400474 --share /path/to/app-debug.apk
```

The phone user must still tap the received APK and approve installation, or ADB
must be restored before running `pm install` / `ime enable` / `ime set`.
Do not report an APK as installed merely because KDE Connect accepted the file.

If root network cannot post to ntfy, verify via USB ADB:

```sh
tmp="$(mktemp)"
printf '%s\n' 'echo ROOT_QUEUE_OK; id; date' > "$tmp"
adb push "$tmp" /sdcard/Download/phone-root-queue.sh
rm -f "$tmp"
sleep 12
adb shell 'su -c "tail -n 120 /sdcard/Download/phone-root-last.log"'
```

## Known Issues

- 2026-07-18 observed state: `adb devices` / `adb get-state` can still report
  `device` while `adb shell echo ...` times out and the phone-status MCP returns
  `probe_ok=false`. Treat this as an unavailable ADB control plane, not as a
  healthy phone. Prefer `phone_status`/bounded `adb shell` probes before issuing
  commands; restore control through FRP `127.0.0.1:15555`, USB ADB, or a
  phone-local Tasker/AidLux/root-helper rescue action.
- AidLux `/bin/su` is Linux `su`, not Magisk root. It prompts for a password and
  fails. Do not expect AidLux agent to run root commands directly.
- On this phone, Magisk/root UID network requests to ntfy can time out even when
  AidLux can reach ntfy. Keep root helper network posts short-timeout and use
  USB ADB log reads as the reliable verification path.
- Use the root helper queue for privileged commands: AidLux writes to
  `/sdcard/Download/phone-root-queue.sh`; the Magisk/root helper executes it.
- Keep ntfy notifications short. For long commands, use `phone-command-push` so
  the phone notification points to the copy page.
- A paired KDE Connect phone can remain undiscoverable after a firewall reload
  even while its Android foreground service is healthy. Restarting only
  `kdeconnectd.service` restores its LAN discovery socket; do not re-pair or
  reset phone data first.
- The custom `kdeconnectd.service` can show `inactive` while the real daemon is
  running as a D-Bus activated unit under `dbus-:*-org.kde.kdeconnect@*.service`.
  Check `kdeconnect-cli --refresh --list-available` and `busctl --user tree
  org.kde.kdeconnect` before treating `systemctl --user is-active
  kdeconnectd.service` as authoritative.
- Desktop-to-phone clipboard was verified on 2026-07-16 after setting
  `WRITE_CLIPBOARD=allow` and enabling `kdeconnect-clipboard-bridge.service`.
  Later the same day KDE Connect became unreachable because Android reported
  `org.kde.kdeconnect_tp` as `enabled=3` (disabled-user state). Re-enabling the
  package, waking `org.kde.kdeconnect.ui.MainActivity`, and refreshing KDE
  Connect restored `paired and reachable`; the bridge immediately logged a new
  desktop clipboard send. The keepalive script now replays the KDE Connect
  app/background policy durably.
  Phone-to-desktop automatic sync was not proven in that session. Failed paths:
  the phone MCP clipboard helper returned `无法读取剪贴板`/`剪贴板设置失败`;
  installing the Termux `termux-api` userspace package created
  `termux-clipboard-get/set`, but direct calls via root/ADB timed out; a
  temporary MacroDroid `ClipboardChangeTrigger` file was not verified and was
  removed. Do not claim reverse sync works until a real Android copy updates
  `wl-paste` on Fedora.
- Later on 2026-07-16, a durable Fedora `phone-clipboard-receiver.service` and
  MacroDroid macro `Phone to PC Clipboard` were installed as the phone-to-PC
  fallback. The receiver path was verified by posting from the phone with curl:
  phone HTTP returned `202` and Fedora `wl-paste` matched the posted text. A
  fully automated UI copy test with QuickEdit did not produce an Android copy
  event, so if troubleshooting continues, verify with a manual phone copy before
  changing the receiver.
- Later again on 2026-07-16, a manual WeChat copy still did not reach Fedora.
  MacroDroid database logs showed the polling macro running (`Regular interval
  trigger wakeup`, `剪贴板刷新`, `HTTP 请求 (POST)`), but the receiver got empty
  request bodies. Direct phone curl POST to
  `http://192.168.123.71:19976/clipboard/<token>` returned `202` and updated
  `wl-paste`, proving the LAN receiver and desktop paste path are healthy.
  MacroDroid and KDE Connect both had clipboard/background app-ops set to
  `allow`; Android 16/ColorOS still returned an empty clipboard to background
  readers. The likely next repair is an LSPosed clipboard whitelist module
  scoped to `system`, with `com.arlosoft.macrodroid` and
  `org.kde.kdeconnect_tp` in its app whitelist, followed by a phone reboot.
  Candidate source inspected: `fei-ke/ClipboardWhitelist` release
  `1.1.0` (`ClipboardWhitelist-v1.1.0-13-release.apk`, sha256
  `c844b2981c59c76660da3e5b37aff59466c3796d34e5968ff53c4dd61ced134e`).
  Do not install or reboot without explicit user consent, because this changes
  framework clipboard policy through LSPosed.
- 2026-07-17 clipboard follow-up: the active phone network was off-LAN, so the
  MacroDroid receiver URL was moved to DuckDNS `:19976`; router DNAT
  `19976/TCP -> 192.168.123.71:19976` is required. Direct phone curl POST to
  the DuckDNS receiver returned `202` and updated Fedora `wl-paste`, proving
  public routing, token validation, and Wayland paste are healthy. Empty macro
  posts return `204` by design.
- 2026-07-17 LSPosed/Vector state: old `one.yufz.clipboard` was disabled after
  inspection showed a likely hook bug in its ClipboardService class string.
  `io.github.tehcneko.clipboardwhitelist` v1.0.0 is installed, enabled in
  `/data/adb/lspd/config/modules_config.db`, and scoped to `system`; Vector
  v2.0 is the active Zygisk/Xposed framework and the old LSPosed module has a
  `disable` marker. The module's preferences file is misspelled
  `clipboad_whitelist.xml`; it currently lists `com.arlosoft.macrodroid`,
  `org.kde.kdeconnect_tp`, and `app.octoclip.v1`. Read LSPosed DB with WAL/SHM
  copies; the main DB alone can be stale.
- 2026-07-17 MacroDroid remains the blocker: `READ_CLIPBOARD` and
  `WRITE_CLIPBOARD` app-ops are `allow`, the polling macro runs every 2s, and
  receiver logs show continued HTTP `204` empty bodies. Do not change the
  Fedora receiver or router for this symptom. A temporary edit of
  `contentBodyText` in the macro file is not enough to validate behavior while
  MacroDroid has the macro loaded in memory; restore it to `{clipboard}` unless
  saving through the MacroDroid UI or rebooting/reloading the app state.
- ntfy Android subscriptions are in
  `/data/user/0/io.heckel.ntfy/databases/AppDatabase`. If direct database
  repair is unavoidable, stop the app first and restore the database with the
  ntfy package UID returned by `cmd package list packages -U io.heckel.ntfy`,
  mode `0600`, and `restorecon`. Do not reuse another app's UID: ntfy will
  crash with `SQLITE_CANTOPEN` when its database is unreadable.
- Avoid `ps -ef` in AidLux commands; it previously hung and timed out. Prefer
  bounded checks like `pgrep`, `id`, `pwd`, `ls`, `command -v`, or short logs.
- Duplicate AidLux agents can race on ntfy and hide newer commands. If that
  happens, run `curl -fsSL http://100.120.189.27:9829/install-aidlux-phone-agent.sh | sh`
  in AidLux to converge to one process.
- Do not rely on Haven MCP or phone FRP as the control plane while they are
  unstable. Use this agent first, then repair FRP/Haven from the root helper.

## Safe focused-field text entry from a local file

When Android `adb shell input text` would expose or corrupt a secret containing
shell-special characters, use the recorded helper instead of placing the secret
on the command line:

```bash
adb-input-file-text --serial 127.0.0.1:15555 --tag <tag> --file /path/to/private-file
```

The helper uses `adb-record` for push/type operations, prints only byte count,
types into the currently focused input field one character at a time, and removes
the phone temporary file. It is suitable for ASCII passwords/tokens. Do not use
full UI dumps that may include visible password fields unless the pulled XML is
parsed locally and `login_form.password.input` or equivalent password nodes are
redacted before output.

## Magisk Keepalive Module: NetBird Primary + Haven/ntfy

Installed module:

```text
/data/adb/modules/netbird-primary-haven-ntfy-userapp-keepalive-no-apk-overlay/
```

Purpose: keep NetBird as the primary VPN path and keep Haven/ntfy/KDE Connect
background policies alive without systemizing or overlaying APKs. Apps remain
normal user apps under `/data/app/...`, so Google Play/F-Droid/APK updates keep
working. The module applies Doze whitelist, AppOps background/foreground/wakelock
permissions, active standby bucket, netpolicy background whitelist, and sets
Android `always_on_vpn_app=io.netbird.client` with lockdown off. It does not
start Tailscale; Tailscale remains manual fallback because Android has one VPN
slot.

Files:

```text
module.prop
service.sh
apply-now-netbird-primary-haven-ntfy-userapp-keepalive.sh
uninstall.sh
```

Immediate replay:

```sh
su -c 'sh /data/adb/modules/netbird-primary-haven-ntfy-userapp-keepalive-no-apk-overlay/apply-now-netbird-primary-haven-ntfy-userapp-keepalive.sh'
```

Verification from 2026-07-19:

- Module files installed with root ownership.
- `pm path io.netbird.client`, `sh.haven.app`, `io.heckel.ntfy`,
  `org.kde.kdeconnect_tp`, and `com.tailscale.ipn` all returned `/data/app/...`.
- Deviceidle whitelist included all five packages.
- Netpolicy whitelist included NetBird UID `10573`, Haven UID `10371`, ntfy UID
  `10367`, and KDE Connect UID `10429`.
- NetBird AppOps showed `POST_NOTIFICATION`, `WAKE_LOCK`, `RUN_IN_BACKGROUND`,
  `RUN_ANY_IN_BACKGROUND`, and `START_FOREGROUND` allowed.
- `settings get global always_on_vpn_app` returned `io.netbird.client`.

If NetBird probes still fail while policies are correct, check whether the
NetBird app has actually connected/authorized the VPN. The module can keep
permissions and always-on preference, but cannot bypass Android's user VPN
authorization dialog.


## Magisk Priv-App Systemize: NetBird Primary + Haven + ntfy

Date: 2026-07-19

User reported ordinary keepalive was not enough and requested system-level app
protection. Installed a reversible Magisk overlay module:

```text
/data/adb/modules/systemize-netbird-primary-haven-ntfy-privapp-keepalive-store-update-risk-reversible/
```

Purpose:

- Make these packages system/priv-app candidates without deleting user data:
  - `io.netbird.client` → `/system/priv-app/NetBirdPrimaryPrivSystemApp`
  - `sh.haven.app` → `/system/priv-app/HavenPrivSystemApp`
  - `io.heckel.ntfy` → `/system/priv-app/NtfyPrivSystemApp`
- Keep NetBird as primary always-on VPN:
  - `settings put global always_on_vpn_app io.netbird.client`
  - `settings put global always_on_vpn_lockdown 0`
- Replay background policy at boot via module `service.sh`:
  - Doze whitelist
  - `RUN_IN_BACKGROUND`, `RUN_ANY_IN_BACKGROUND`, `START_FOREGROUND`,
    `WAKE_LOCK`, `POST_NOTIFICATION`
  - standby bucket `active`
  - netpolicy restrict-background whitelist by UID

Verification after reboot:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "pm path io.netbird.client; dumpsys package io.netbird.client | grep -Ei \"pkgFlags|privateFlags|codePath|resourcePath\" | head -n 12; settings get global always_on_vpn_app; dumpsys deviceidle whitelist | grep -E \"io.netbird.client|sh.haven.app|io.heckel.ntfy\""'
```

Expected decisive flags include both `SYSTEM` and `PRIVILEGED`. Because the
packages remain installed in `/data/app` as updates over the Magisk system copy,
`pm path` can still show `/data/app`; confirm with `dumpsys package`, which
should show `pkgFlags=[ SYSTEM ... UPDATED_SYSTEM_APP ]` and
`privateFlags=[ ... PRIVILEGED ... ]`.

Update risk:

- App store updates may still install as `UPDATED_SYSTEM_APP`, but if updates
  fail or the app breaks, disable the module, reboot, update/reinstall normally,
  then rebuild the module from the new APKs.
- NetBird uses split APKs; the module copies all `pm path` APKs into the same
  priv-app directory. Do not copy only `base.apk` for NetBird.

Rollback:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "touch /data/adb/modules/systemize-netbird-primary-haven-ntfy-privapp-keepalive-store-update-risk-reversible/disable; reboot"'
```

Re-apply boot policy immediately without reboot:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "sh /data/adb/modules/systemize-netbird-primary-haven-ntfy-privapp-keepalive-store-update-risk-reversible/apply-now-systemize-netbird-primary-haven-ntfy-privapp-keepalive-store-update-risk-reversible.sh"'
```

## Phone Home Launcher Recovery: Niagara/bitpit blank screen

Date: 2026-07-19

Symptom: pressing Home shows a blank/black launcher screen. A stale Toast may say
`target已更新`; that Toast came from Haven target switching and is not the Home
launcher error.

Detected default Home:

```text
bitpit.launcher/.ui.HomeActivity
```

Immediate recovery: switch Android HOME role/default activity back to the system
Oplus launcher without clearing user app data:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "cmd role add-role-holder android.app.role.HOME com.android.launcher 0 2>&1 || true; cmd package set-home-activity com.android.launcher/.Launcher 2>&1 || true; am force-stop bitpit.launcher; input keyevent HOME"'
```

Verify:

```sh
adb -s 127.0.0.1:15555 shell 'su -c "cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME; dumpsys window | grep -E \"mCurrentFocus|mFocusedApp\" | head"'
```

Expected:

```text
com.android.launcher/.Launcher
mCurrentFocus=... com.android.launcher/com.android.launcher.Launcher
```

Do not clear `bitpit.launcher` data unless the user explicitly accepts losing
Niagara launcher layout/preferences. Prefer system launcher as the stable phone
fallback during remote operations.

## Haven local Desktop tab: system app does not fix missing window target

Date: 2026-07-19

Symptom: Haven bottom `桌面` tab shows `连接到窗口以显示内容` or later `Connecting / 0 of 0 Peers connected`.

Finding:

- `sh.haven.app` is already Magisk systemized and verified with `SYSTEM` +
  `PRIVILEGED`; the foreground SSH service is alive.
- The symptom is not an Android LMK/Doze kill. It is Haven's local desktop
  module lacking a managed desktop/window peer/session.
- The `桌面` tab is Haven's local PRoot Linux desktop installer/launcher, not
  the remote Fedora VNC profile list.
- Openbox packages can be installed manually in the Haven Alpine rootfs when
  the UI package install fails:

```sh
adb -s 127.0.0.1:15555 shell 'su -c '\''ROOT=/data/user/0/sh.haven.app/files/proot/rootfs/alpine-3.21; chroot "$ROOT" /bin/sh -lc "apk update && apk add --no-cache openbox tigervnc xterm font-dejavu dbus-x11 xauth xinit xsetroot"'\'''
```

Manual VNC start for diagnostics only:

```sh
adb -s 127.0.0.1:15555 shell 'su -c '\''ROOT=/data/user/0/sh.haven.app/files/proot/rootfs/alpine-3.21; chroot "$ROOT" /bin/sh -lc "mkdir -p /root/.vnc; printf haven\\n | vncpasswd -f > /root/.vnc/passwd; chmod 600 /root/.vnc/passwd; pkill Xvnc 2>/dev/null || true; pkill openbox 2>/dev/null || true; Xvnc :1 -rfbauth /root/.vnc/passwd -rfbport 5901 -geometry 1080x1800 -depth 24 -localhost=0 >/tmp/haven-xvnc.log 2>&1 & sleep 3; DISPLAY=:1 openbox-session >/tmp/haven-openbox.log 2>&1 &"'\'''
```

This starts `Xvnc` and `openbox`, but Haven may still show `Connecting / 0 of 0
Peers connected` because manually started Xvnc is not registered as a Haven
managed desktop peer. Do not confuse this with process killing.

A wrong experiment added the NetBird VNC profile to `workspace_item`, causing
`终端 × 2`; it was removed. Keep workspace items terminal-only unless the exact
Haven workspace item kind/protocol semantics are known.

## Phone Flow Recorder / Smart Ordering

For foreground mobile GUI flows such as Alipay/Luckin ordering, use `phone-flow` instead of raw `adb input tap` so every operation becomes reusable evidence:

```bash
phone-luckin-flow '支付宝瑞幸智能点单：记录商品/规格/门店偏好；到授权、提交订单、付款确认前停止'
phone-flow ui --label 'read current Luckin screen'
phone-flow tap 540 1230 --label '支付宝一键登录'   # sensitive labels are blocked unless explicitly allowed
phone-flow stop --status completed --summary 'reached confirmation screen; user completed sensitive step manually'
phone-flow recall '支付宝 瑞幸 点单'
```

Important limits:

- Android/Alipay cannot be clicked in true background by ADB; taps affect the phone's current foreground UI.
- Do not let agents confirm payment, phone authorization, SMS codes, privacy agreement, or final order submission. Stop there unless the user explicitly confirms the specific sensitive action.
- `phone-flow` records compact UI summaries, focus, screenshot path/SHA, coordinates, labels, and status to `~/memory/workflows/phone-events.jsonl`, appends a `workflow-event-v1` event to `~/memory/workflows/events.jsonl`, and POSTs to n8n `http://127.0.0.1:5678/webhook/phone-flow-event`.
- The n8n workflow is `Phone Flow Event Intake` (`phone-flow-event-intake`), active local webhook path `phone-flow-event`.
- `phone-flow` also writes `~/.local/state/mobile-ai-super/phone-flow-progress.json`; Workbench `/api/super/notice` prioritizes it so the Android AI Super Button floating strip shows the live phone flow. While `~/.local/state/phone-flow/current.json` matches the same `flow_id`, the notice must not expire back to generic service status. Keep `n8n✓` near the start of the `line` because the capsule truncates long text on phone screens.
- `uiautomator dump` can fail with `could not get idle state` when a keyboard/terminal is active; keep screenshot-path evidence as the fallback and rerun `phone-flow ui` after closing the IME if screen text is needed.

Default Luckin bootstrap helper: `~/.local/bin/phone-luckin-flow`.
Recorder script: `~/.local/bin/phone-flow`.

## Shadow Android / Cloud Phone Migration Policy

Date: 2026-07-19

User preference: minimize disturbance on the real phone. Use Step models for
phone UI understanding and shadow/cloud Android rehearsal whenever possible,
then push only the shortest verified path or a confirmation card to the real
phone.

Durable policy file:

```text
~/.local/state/phone-flow/preferences/shadow-android-policy.json
```

Default command entry:

```bash
phone-shadow status
phone-shadow classify '支付宝瑞幸点单 豆沙 小黄油拿铁 少甜'
phone-shadow plan 'B站搜索视频：影子机优先，Step读屏，不打扰真机'
phone-shadow start '支付宝瑞幸点单：先在影子机演练，真机只做最终确认'
phone-shadow ui '读取影子机当前屏幕，不要操作'
phone-shadow step-task '支付宝瑞幸点单：豆沙 + 小黄油拿铁，少甜'
```

`phone-shadow` writes:

- `~/.local/state/phone-shadow/current.json`
- `~/.local/state/mobile-ai-super/shadow-android-progress.json`
- `~/memory/workflows/phone-shadow-events.jsonl`
- `~/memory/workflows/events.jsonl` with source `phone-shadow`
- n8n webhook `POST http://127.0.0.1:5678/webhook/phone-flow-event`

It also pushes the latest progress line to the real phone AI Super Button via
ADB `com.charlie.mobileaisuperbutton.SET_NOTICE`, so the phone floating strip
does not depend only on polling.

Default model policy:

- Use Step for visual/UI reasoning by default, preferably
  `openai-compatible/step-3.7-flash`.
- If Step vision/UI reasoning is unavailable or returns empty, fail fast and
  notify; do not silently switch to non-Step models for phone UI decisions.
- Deterministic shell/ADB actions are allowed after Step/UI evidence, but
  sensitive actions remain blocked.

Execution split:

1. Real phone: final shortest path only, plus user-only confirmation for
   payment, SMS/OTP, biometric, phone authorization, privacy agreement, final
   order submit, bank card, deletion, transfer, or similar sensitive steps.
2. Shadow Android / spare phone: app flow discovery, menu browsing, cart
   rehearsal, UI coordinate/path learning, and non-sensitive repeated tasks.
3. Cloud phone: gradually migrate low-risk apps/workflows. Never assume cloud
   login/session/location/IP is equivalent to the real phone; verify before
   relying on it.

Current shadow device:

- `192.168.123.241:5555`, model `24117RK2CC`, Android 13, Redmi/nabu.
- Current real phone routes may include both `100.87.37.3:5555` and
  `127.0.0.1:15555`; prefer the already-online route and avoid hanging on
  `adb connect` when a route is already listed.

App classes from the current PKR110 package set:

- Good shadow-first candidates: browsers, media/content, notes, cloud-drive and
  read/search workflows such as `org.mozilla.fenix`, `com.android.chrome`,
  `com.bilibili.app.in`, `com.reddit.frontpage`, `com.netease.cloudmusic`,
  `com.baidu.netdisk`, `app.alextran.immich`, `com.google.android.keep`.
- Rehearse on shadow, confirm on real phone: shopping/ordering flows such as
  `com.eg.android.AlipayGphone`, `hk.alipay.wallet`, `com.sankuai.meituan`,
  `com.taobao.taobao`, `com.taobao.idlefish`, `com.alibaba.wireless`.
- Privacy/identity-limited: messaging and work communications such as
  `com.tencent.mm`, `com.tencent.mobileqq`, `com.tencent.wework`,
  `com.tencent.androidqqmail`, `org.telegram.*`, `com.whatsapp.w4b`,
  `com.mattermost.rn`. Use shadow/cloud only for low-risk UI rehearsal or
  explicit user-approved account sessions.
- Real-phone/manual only: banking, payment finalization, games with device or
  anti-cheat binding, and identity flows such as `cn.com.spdb.mobilebank.per`,
  `com.unionpay`, `com.unionpay.tsmservice`, `com.tencent.lolm`,
  `com.tencent.lolmtyf`.
- Keep on real phone as device infrastructure: VPN/proxy/automation/terminal
  bridge apps such as NetBird, Tailscale, Mihomo/Clash, Haven, Termux, AidLux,
  Tasker, MacroDroid, KDE Connect, and `com.charlie.mobileaisuperbutton`.

Prompt the user when an app is unsuitable for shadow/cloud migration, when
cloud state differs from the real phone, when device/location/IP risk can alter
results, or when a workflow has become reusable/stale and should be promoted or
refreshed.

## Universal Ordering Router / Mini-App Ordering Policy

Date: 2026-07-19

Default entry for future shopping, food, coffee, mini-program, and app ordering tasks:

```bash
phone-order-router plan '支付宝小程序购买西瓜冷萃，自提，用户参与选择，支付前停止'
```

State and evidence:

- Script: `~/.local/bin/phone-order-router`
- Events: `~/memory/workflows/phone-order-events.jsonl`
- Shared workflow bus: `~/memory/workflows/events.jsonl` with source `phone-order-router`
- Floating progress: `~/.local/state/mobile-ai-super/phone-order-progress.json`
- n8n webhook: `POST http://127.0.0.1:5678/webhook/phone-flow-event`

Routing order:

1. **Official API/MCP first** when a vendor provides a user-authorized ordering interface. Example: Luckin official `my-coffee` MCP at `https://gwmcp.lkcoffee.com/order/user/mcp`, token from `LUCKIN_MCP_TOKEN` or `~/.my-coffee/LUCKIN_MCP_TOKEN`.
2. **User-provided or official partner API second**. Do not invent or scrape private APIs. Only use documented endpoints or tokens explicitly provided/approved by the user.
3. **Shadow Android / cloud phone Step UI rehearsal** for mini-programs and ordinary app ordering when no API is available. Learn search/spec/cart path off the real phone where possible.
4. **Real phone Step UI final path** only for the shortest verified path and user-visible confirmation. Use `phone-flow` for taps/swipes so all steps are logged to n8n and workflow memory.
5. **Manual-only boundary** for final payment, biometric, OTP/SMS, bank card, transfer, identity, and any action that submits or commits an order without user confirmation.

Sensitive confirmation gates that must stop or ask the user:

- Login, phone-number authorization, SMS/OTP, privacy/agreement confirmation.
- `提交订单`, `确认订单`, `立即购买`, `下单`, `支付`, `付款`, `免密支付`.
- Fingerprint/face confirmation, bank card, transfer, deletion/cancellation that has irreversible cost.

Mini-program rule:

- Android root is allowed for diagnostics, screenshots, app state, logs, and stable routing, but do **not** automatically extract/reuse Alipay/WeChat mini-program private tokens, payment cookies, or hidden internal request signatures.
- Root-based packet/log inspection may be used only to diagnose stability or discover whether an official documented API exists; it is not the default ordering data plane.

Confirmation UX:

- The phone floating AI Super Button should show progress like `n8n✓ 下单路由 · <route> · <app>`.
- For choices, present a concise confirmation card: store, item, spec, quantity, estimated price, coupon/discount status, and next action.
- If multiple viable choices exist, ask one question only and offer a recommended default.
- Payment remains user-owned; after payment the agent may query order status/取餐码 only through official API/MCP or visible app UI.

Verification:

```bash
python3 -m py_compile ~/.local/bin/phone-order-router
phone-order-router plan '支付宝小程序购买西瓜冷萃，自提，用户参与选择，支付前停止'
tail -n 3 ~/memory/workflows/phone-order-events.jsonl | jq -c '{ts,kind,goal,route:.plan.route,app:.plan.app,n8n}'
```

### Luckin Fast Order via Super Button

Date: 2026-07-19

Default fast path for user voice/super-button Luckin orders:

```bash
luckin-quick-order preview
luckin-quick-order create --confirm-create   # only after explicit user confirmation
```

Current remembered default:

- Store: `瑞安云霞家园店`, `deptId=610152`
- Item: `大西瓜生椰冷萃`, `productId=5524`, `skuCode=SP3944-00005`
- Spec: `大杯/冰/不另外加糖`
- Safety: preview is allowed after user intent; `createOrder` requires explicit confirmation; payment remains user-manual.

Workbench / AI Super Button actions:

- `luckin-preview`: calls official MCP preview only, no order created.
- `luckin-create-last`: returns `409 confirm_required` unless called with `confirm=1`; then creates a real pending-pay order QR. Never pays automatically.

Tasker/voice trigger URLs while Workbench is reachable:

```text
/api/super/run?action=luckin-preview&device=w19900422
/api/super/run?action=luckin-create-last&confirm=1&device=w19900422
```

State:

- Token: `~/.my-coffee/LUCKIN_MCP_TOKEN` (`0600`, do not print)
- Helper: `~/.local/bin/luckin-quick-order`
- Preferences: `~/.local/state/phone-order-router/preferences.json`
- Last preview: `~/.local/state/phone-order-router/luckin-last-preview.json`
- Last order: `~/.local/state/phone-order-router/luckin-last-order.json`

Verification:

```bash
node --check ~/.local/bin/mobile-ai-workbench
systemctl --user is-active mobile-ai-workbench.service
curl --noproxy '*' -fsS 'http://127.0.0.1:19888/api/super/actions?device=w19900422' | jq -c '.[] | select(.id|test("luckin"))'
curl --noproxy '*' -fsS -X POST -H 'content-type: application/json' -H 'x-device-code: w19900422' 'http://127.0.0.1:19888/api/super/run?action=luckin-preview'
```

### API / MCP / CLI / Skill Selection Matrix

Date: 2026-07-19

For future voice/super-button/order/workflow tasks, classify integration layers in this order:

1. **Official MCP / API = execution data plane**
   - Best for structured actions: search, quote/preview, create pending order, query status, cancel.
   - Use when there is user-authorized token and tool schema.
   - Record every call/result summary to n8n and `~/memory/workflows/*events.jsonl`.
2. **Official CLI = local trigger/bootstrap/debug wrapper**
   - Best for local installs, login callback, token bootstrap, one-command fast actions, Tasker/voice/super-button shell hooks.
   - Do not use CLI as the only source of business truth if MCP/API schema exists; wrap MCP calls instead.
3. **Official Skill = agent policy/instruction layer**
   - Best for teaching agents tool order, parameter rules, safety gates, and output format.
   - Skill is not the execution layer; pair it with MCP/API or a verified CLI wrapper.
4. **Step UI / shadow Android = visual fallback**
   - Use when no safe official API/MCP exists, for mini-programs, private app flows, or UX rehearsal.
   - Prefer shadow/cloud rehearsal; real phone only for shortest path and user confirmations.

Current Luckin decision:

- Official source: `https://open.lkcoffee.com/`
- Skill package: `my-coffee` tells the agent ordering rules and safety sequence.
- MCP endpoint: `https://gwmcp.lkcoffee.com/order/user/mcp` is the authoritative execution path.
- Local CLI wrapper: `~/.local/bin/luckin-quick-order` is only a fast trigger around MCP, used by Super Button/Tasker/voice.
- Step UI is fallback only when MCP is unavailable or when checking the visible app state.

Default router verification:

```bash
phone-order-router plan '瑞幸 MCP CLI Skill 选择最合适方案并记录' | jq '{route:.plan.route, policy:.plan.api_capability.integration_policy.priority, stack:.plan.api_capability.recommended_stack}'
```

### Super Button Fluid Order Panel

Date: 2026-07-19

The AI Super Button `/super` panel must expose ordering as a live card, not just raw notifications.

Current Luckin panel behavior:

- Top card: `瑞幸快下单`
- Live fields: order status, amount, and pickup code.
- Buttons: preview, create pending-pay QR, open pay page, refresh pickup code.
- `/api/super/notice` prioritizes recent Luckin order status and shows `瑞幸取餐码 <code> · <status>` when available.
- `luckin-create-last` in the panel uses browser confirmation and server-side `confirm=1`; payment is still user-manual.

Verification:

```bash
curl --noproxy '*' -fsS 'http://127.0.0.1:19888/api/super/notice?device=w19900422' | jq '{line,luckin_line,notice_source}'
curl --noproxy '*' -fsS -X POST -H 'content-type: application/json' -H 'x-device-code: w19900422' 'http://127.0.0.1:19888/api/super/run?action=luckin-query'
```

### 2026-07-19 AI Super Button Luckin media/file panel

The AI Super Button order surface is now a live media/file card, not just a text notification.

Implemented paths:

- Workbench `:19888` serves order artifacts through the same device-code protected origin:
  - `GET /api/super/media?device=w19900422`
  - `GET /files/luckin/pickup-code-qr.png?device=w19900422`
  - `GET /files/luckin/pickup-token-qr.png?device=w19900422`
  - `GET /files/luckin/pay.html?device=w19900422`
  - `GET /files/luckin/pickup.html?device=w19900422`
- `/super` renders a Fluid-Island style card with:
  - large pickup QR preview and take-meal code,
  - file-manager grid for pickup/payment images and HTML pages,
  - dynamic Luckin status refresh,
  - phone music status plus previous/play-pause/next controls.
- Native Android APK `com.charlie.mobileaisuperbutton` expanded panel now includes Luckin/media quick actions and opens the same `/super` or pickup/pay pages. Keep complex preview logic in Workbench; APK should remain a thin overlay shell.

Verification commands:

```bash
node --check ~/.local/bin/mobile-ai-workbench
systemctl --user restart mobile-ai-workbench.service
curl --noproxy '*' -fsS 'http://127.0.0.1:19888/api/super/media?device=w19900422' \
  | jq -c '{music:.music,luckin:{code:.luckin.takeMealCode,status:.luckin.status,files:(.luckin.files|map(.id))}}'
curl --noproxy '*' -fsSI 'http://127.0.0.1:19888/files/luckin/pickup-code-qr.png?device=w19900422'
~/.local/bin/mobile-ai-super-button-build-install
~/.local/bin/adb-record --tag super-button-verify -- -s 127.0.0.1:15555 shell \
  'dumpsys activity services com.charlie.mobileaisuperbutton/.OverlayService | grep -E "isForeground|ServiceRecord" -A3'
```

Luckin account note: official MCP currently exposes only shop/product/preview/create/query/cancel order tools. It does not expose an order transfer/sync-to-other-mobile-account API. A created order belongs to the Luckin account behind `~/.my-coffee/LUCKIN_MCP_TOKEN`; if the phone-number account differs, log in/authorize that account and rotate the token rather than trying to sync an existing order across accounts.

### 2026-07-19 Luckin Super Button consolidation and small quick-pay policy

User preference: Luckin must appear as one integrated card, not many loose buttons.

Implemented:

- `/super` Luckin card primary controls are now:
  - `🎙 语音点单` — browser speech recognition; dispatch text is prefixed with `瑞幸` and routed through `/api/super/dispatch`.
  - `小额快付≤20` — if no active Luckin order exists, preview first, then only when amount is `<= 20` CNY auto-creates the official payment QR. It does **not** bypass Alipay/WeChat/OS payment confirmation; it only opens the official payment page/QR. If an active order already exists, it opens pickup/pay page instead of creating a duplicate.
- Low-level Luckin actions (`preview/create/query/pay/pickup`) and media key actions remain API-callable but are hidden from the generic `/super` action grid to avoid UI clutter.
- Native APK expanded list is consolidated to `🎙 瑞幸语音点单` and `小额快付≤20`; the media card quick buttons are `语音` and `取餐`.
- `luckin-quick-order create` now regenerates pay QR artifacts (`LuckinPay-WeChatDirect.png`, `LuckinPay-OfficialQR.png`, `pay.html`) whenever a new payment QR is created.
- `luckin-quick-order latest_order_id()` prefers the latest non-cancelled query order so a cancelled/unpaid duplicate does not hide the real pickup order.

Safety/verification:

```bash
curl --noproxy '*' -fsS 'http://127.0.0.1:19888/api/super/actions?device=w19900422' \
  | jq '[.[]|select(.id|test("luckin|music"))|{id,label,hidden}]'
curl --noproxy '*' -sS -X POST -H 'content-type: application/json' -H 'x-device-code: w19900422' \
  'http://127.0.0.1:19888/api/super/run?action=luckin-auto-small' -d '{}' \
  | jq '{ok,existing,orderId,status,takeMealCode,open_url}'
```

Do not test `luckin-auto-small` with default limit when there is no active order unless the user actually wants a real payment QR created. For safe smoke tests use `limit=1`, which blocks after preview before `createOrder`.

### 2026-07-19 AI Super Button notification/context click routing

Fix: tapping the floating capsule body or Android foreground notification should open the context page, not just expand the overlay or APK main page.

Routing rule in `OverlayService.contextUrl()`:

- Luckin `待支付` / `支付码` -> `/files/luckin/pay.html?device=w19900422`
- Luckin `取餐码` / `等待取餐` / `luckin_order` -> `/files/luckin/pickup.html?device=w19900422`
- Luckin/search/order keywords -> `/super?device=w19900422&focus=luckin`
- fallback -> `/super?device=w19900422`

The foreground notification is dynamically refreshed with the same context URL via `NotificationManager.notify(19888, notification())` when notice/Luckin/media state changes. The floating capsule text area uses `openContextPanel()`; the dropdown item is `打开对应界面`.

Verify:

```bash
~/.local/bin/mobile-ai-super-button-build-install
adb-record --tag super-dynamic-notify-verify -- -s 127.0.0.1:15555 shell \
  'dumpsys activity services com.charlie.mobileaisuperbutton/.OverlayService | grep -E "isForeground|foregroundNoti" -A2 -B2'
```

### 2026-07-19 AI Super Button smart-hide sizing

User reported the always-open capsule blocked app UI. Current policy:

- Meaningful notice is prominent for only `8s` (`NOTICE_PROMINENT_MS=8000L`).
- Repeated identical `/api/super/notice` polling must not refresh the prominent timer.
- Codex routine active lines must not keep the large capsule alive.
- Idle compact state is a single `AI` / `AI•` pill: `46dp` window width, measured on PKR110 as about `138px` at current density.
- Left pill toggles expanded panel; content area in prominent mode opens context; right/menu only appears in prominent or expanded states.

Verification evidence after 12s idle:

```text
mAttrs={(18,220)(138xwrap) ... package=com.charlie.mobileaisuperbutton ... ty=APPLICATION_OVERLAY}
```

## AI Super Button Codex Task Board (2026-07-19)

User-visible Codex execution visibility is a three-layer contract:

1. Idle overlay stays compact (`AI` / `AI•`) so it does not block phone apps.
2. New meaningful activity may expand briefly, then auto-shrinks after about 8s.
3. Full task visibility lives in the Codex board, not the tiny overlay:
   - native overlay expanded card: `Codex 任务全貌`, C1-C8 rows, each row opens `/go/cN`.
   - web panel: `http://charlie1990.duckdns.org:19888/super?device=w19900422&focus=codex`.
   - overlay menu button: `任务全貌` opens the same focused panel.

Implementation files:

```text
~/.local/share/mobile-ai-super-button/src/com/charlie/mobileaisuperbutton/OverlayService.java
~/.local/bin/mobile-ai-super-button-build-install
~/.local/bin/mobile-ai-workbench
```

Verification:

```bash
curl --noproxy '*' -fsS 'http://127.0.0.1:19888/api/super/notice?device=w19900422' \
  | jq -c '{codex_line,codex_active_count,codex_accounts:(.codex_accounts|length)}'
curl --noproxy '*' -fsSL -H 'x-device-code: w19900422' \
  'http://127.0.0.1:19888/super?focus=codex&device=w19900422' \
  | rg 'Codex 任务全貌|refreshCodexBoard'
~/.local/bin/mobile-ai-super-button-build-install
~/.local/bin/adb-record --tag super-codex-board -- -s 127.0.0.1:15555 shell \
  'dumpsys activity services com.charlie.mobileaisuperbutton/.OverlayService | grep -E "isForeground|ServiceRecord" -A3'
```

If the user says they cannot see the whole Codex task, do not add more global launcher buttons. First ensure the overlay has only top-level actions (`任务全貌`, `瑞幸小程序`, `语音`, `搜索`, `收起`) and that any Codex-context tap opens `/super?focus=codex`.

Update 2026-07-19: `Codex 任务全貌` must be a backend-pulled board, not a WebTTY shortcut list.

- Backend endpoint: `/api/codex/board?device=w19900422`
- Source: `tasksPayload()` plus each account `/history.txt`, returned as `source=backend-pulled:/api/tasks + /history.txt`.
- `/super?focus=codex` now calls `/api/codex/board`, shows `后台拉取 <time>`, and C1-C8 rows link to `/tasks?account=N`, not `/go/cN`.
- Native overlay C1-C8 rows also link to `/tasks?account=N`. Terminal entry remains only in the task detail page via the explicit `终端` button.

Verification:

```bash
node --check ~/.local/bin/mobile-ai-workbench
systemctl --user restart mobile-ai-workbench.service
curl --noproxy '*' -fsS 'http://127.0.0.1:19888/api/codex/board?device=w19900422' \
  | jq -c '{source,active_count,line,accounts:(.accounts|length),first:.accounts[0].urls.detail}'
```

## 2026-07-20 Global Agent Comms Layer

For phone foreground interaction, do not call raw ADB/ntfy/phone-run first. Use:

```bash
agent-comms snapshot
agent-comms open-url '<url>'
agent-comms manual-action --id '<id>' --title '<title>' --message '<message>' --url '<url>' --open-url
```

This records one compact current view in `~/.local/state/agent-comms/latest.json` and prevents future agents from missing key facts such as LAN ADB being available while FRP ADB is down, or Fedora NetBird requiring login while the phone NetBird app is connected.

MCP wrappers should call `agent-comms`; they must not bypass `adb-record` or duplicate ADB serial ordering.

As of 2026-07-20 the MCP wrapper is installed:

- server file: `~/.local/bin/agent-comms-mcp.py`
- config source: `~/.config/mcp/servers.yaml` entry `agent-comms`
- synced into OpenCode and Codex by `~/.local/bin/mcp-sync.py --apply`
- tools: `agent_comms_snapshot`, `agent_comms_open_url`, `agent_comms_manual_action`, `agent_comms_manual_done`
