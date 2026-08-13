# Runbook: NetBird Self-Hosted Tailnet

NetBird is the selected Tailscale replacement candidate. The Fedora client is
installed and enrolled in NetBird Cloud. The remaining migration work is
enrolling additional peers such as the Android phone and Windows.

## Current Fedora State

- Client package: `netbird 0.74.6`
- Service: `netbird.service` enabled and active
- Current status after 2026-08-01 check:
  `Management: Connected`, `Signal: Connected`, FQDN
  `fedora-171-39.netbird.cloud`, NetBird IPv4 `100.87.171.39/16`,
  interface `wt0`, kernel WireGuard port `38573`.
- firewalld must keep `wt0` in zone `trusted`; otherwise enrolled peers may
  reach the NetBird interface but not Fedora service ports.
- 2026-08-01 repair note: user reported phone could not reach
  `http://100.87.171.39:5000/`. Evidence showed Fedora `netbird status` was
  temporarily `Management: Disconnected` / `Signal: Disconnected`, while `wt0`
  still existed. `sudo -n systemctl restart netbird.service` restored
  Management/Signal and `wt0=100.87.171.39/16`; phone-side curl then returned
  HTTP 200 for `http://100.87.171.39:5000/`. If this recurs, verify both
  `netbird status` and a phone-side curl before changing DNS/DuckDNS.
- 2026-07-18: PKR110 is enrolled as `pkr110.netbird.cloud` /
  `100.87.37.3`. After unlocking the phone and tapping NetBird connect,
  Fedora showed `Peers count: 1/1 Connected`; `tun0` on Android had
  `100.87.37.3/16`, and app-UID tests verified Mattermost UID `10447` and
  Haven UID `10371` can reach Fedora NetBird IP `100.87.238.153`. Haven UID
  TCP probes succeeded for `2222`, `2223`, `2224`, `2225`, `2226`, `2227`,
  `2229`, `2230`, `5900`, and Mattermost `8065`.
  Mattermost Android and Haven NetBird entries use `100.87.238.153`, not
  `fedora.netbird.cloud`, because Android NetBird DNS can be unavailable when
  the VPN is down.

Verify:

```bash
systemctl is-enabled netbird.service
systemctl is-active netbird.service
netbird version
netbird status
ip addr show wt0
firewall-cmd --get-active-zones | sed -n '/trusted/,+2p'
```

After unlocking PKR110 and starting NetBird, verify from Fedora/ADB:

```bash
netbird status
adb -s 127.0.0.1:15555 shell \
  'curl -4 -m 8 http://100.87.238.153:8065/api/v4/system/ping'
adb -s 127.0.0.1:15555 shell \
  'toybox nc -z -w 5 100.87.238.153 2225; echo $?'
```

Expected Mattermost response includes `"status":"OK"` and SSH port probe
returns `0`. If `fedora.netbird.cloud` does not resolve on Android, use
`100.87.238.153`; NetBird DNS may be unavailable until Android VPN is active.
If raw `adb shell` UID `2000` behaves differently from root or app UIDs,
verify with the real app UID instead:

```bash
adb -s 127.0.0.1:15555 shell 'su -c "su 10447 -c \"curl -4 -m 8 -sS http://100.87.238.153:8065/api/v4/system/ping\""'  # Mattermost
adb -s 127.0.0.1:15555 shell 'su -c "su 10371 -c \"toybox nc -z -w 5 100.87.238.153 2225; echo $?\""'              # Haven
```

### Fedora Install Recovery Notes

On 2026-07-17 the booted Fedora deployment no longer had `/usr/bin/netbird`,
even though `netbird.service` remained enabled. `rpmi netbird` resolved
dependencies but failed while downloading
`https://pkgs.netbird.io/yum/amd64/netbird_0.74.6_linux_amd64.rpm` from inside
the rpm-ostree transaction. The reliable recovery was:

1. Download the RPM outside rpm-ostree, preferably with `aria2c`, to
   `~/.local/state/netbird-install/`.
2. Verify that the NetBird yum RPM and GitHub release RPM have the same
   SHA256. `rpm -Kv` may report `NOKEY` for NetBird key
   `DFFEAB2FD267A61F`; the payload/header digests should still be `OK`.
3. Run `rpmi ~/.local/state/netbird-install/netbird_0.74.6_linux_amd64.github.rpm`.
4. If `rpmi` stages the deployment but live apply fails with
   `packages would be changed: N, allow replacement to override`, run
   `sudo rpm-ostree apply-live --allow-replacement` and verify
   `command -v netbird`, `netbird version`, `systemctl is-active
   netbird.service`, and `netbird status`.

This path installed `netbird-0.74.6-1.x86_64` live without reboot. A reboot is
still appropriate later to boot the staged deployment cleanly.

For NetBird Cloud setup-key enrollment, avoid printing keys in terminal logs.
Store the key in `~/.local/state/netbird/setup-key` with mode `0600`, then run:

```bash
~/.local/bin/netbird-cloud-enroll
```

The helper reads the key file, runs
`sudo netbird up --management-url https://api.netbird.io:443 --setup-key-file
<file>`, and prints `netbird status`.

During Fedora SSO enrollment, `~/.local/bin/xdg-open` was broken because it
called stale `/run/current-system/sw/bin/xdg-open`. It now falls back to
`/usr/bin/xdg-open` or `/usr/bin/chromium-browser`. If SSO does not open a
browser, run `netbird up --no-browser`, open the printed URL in a Fedora-hosted
browser, and keep the `localhost:53000` callback on Fedora.

## Interactive SSO Login

For Fedora enrollment, run `netbird up` and complete the URL in a browser on
that same Fedora host. The initiating NetBird client starts a temporary
listener at `http://localhost:53000/`, and the Auth0 login URL contains a
one-time PKCE/state transaction. Do not move a Fedora-generated URL to another
device; its final callback would target that other device's localhost instead.
The Android NetBird app has its own corresponding local callback flow. Do not
reuse an old URL: start the login again from the client that is being enrolled.

If a mobile Firefox page fails before authentication while another browser
opens it, use a desktop Fedora browser for this enrollment. Firefox tracking
protection or HTTPS-only handling can interfere with the Auth0 cross-site
cookies or its final HTTP localhost redirect.

## PKR110 NetBird Monitor Guard

2026-07-19 check: `io.netbird.client` is a system/privileged updated system
app (`pkgFlags=[ SYSTEM ... UPDATED_SYSTEM_APP ]`) and Android global
`always_on_vpn_app` is `io.netbird.client`, but after boot the app can still sit
at `Disconnected` / `0 of 0 Peers connected` until its main connect button is
pressed. The durable host-side guard is:

- Script: `~/.local/bin/phone-netbird-ensure`
- Timer: `phone-netbird-ensure.timer` every 5 minutes
- State: `~/.local/state/phone-netbird-ensure/latest.json`
- Foreground safety: `phone-netbird-ensure` must not open/tap the NetBird app
  from timers unless both `PHONE_NETBIRD_AUTO_REPAIR=1` and
  `PHONE_NETBIRD_ALLOW_FOREGROUND=1` are set for an explicit short repair
  window. Routine timers are monitor-only so NetBird does not steal the phone
  foreground while the user is using another app.

It verifies phone-side route to the current Fedora NetBird host for Haven UID
`10371` goes via `tun0`. As of 2026-08-01, it defaults to monitor-only mode:
no device / backoff / disconnected states exit successfully for systemd and do
not force-stop NetBird or blindly tap the connect button. This avoids a
reconnect/close loop when Android NetBird, ADB, and Mihomo are already unstable.
Only set `PHONE_NETBIRD_AUTO_REPAIR=1` for an explicit short repair window.

2026-08-10 same-account recovery:

- Do not clear `io.netbird.client` data or re-enroll PKR110 with a setup key
  when the user wants the same NetBird account/profile. The active Android
  profile is `charlie`, user `android`, peer `pkr110.netbird.cloud` /
  `100.87.37.3`.
- The failure mode was not account loss: the Android app could keep the
  correct profile but sit at `Connecting` with no `tun0`. Phone-side config had
  mismatched Rosenpass/DisableDNS values between `profiles/charlie.json` and
  `netbird.cfg`. Back up those files before editing; do not print secrets.
- Current verified state after repair: Fedora sees
  `pkr110.netbird.cloud` as `Connected`, Android has
  `tun0 100.87.37.3/16`, and `ip route get 100.87.171.39` on the phone routes
  via `tun0`.
- Remaining quality risk: the current peer path is `Relayed` via NetBird relay,
  not direct ICE, and phone-to-Fedora ping showed high latency. Treat NetBird as
  available but not the only control path; keep FRP ADB `127.0.0.1:15555` and
  LAN ADB `192.168.123.22:5555` as primary operational fallbacks.
- Android Wi-Fi evidence during this repair showed good RSSI/link speed but
  `isUsable: false`; if NetBird falls back to relay again, verify Android Wi-Fi
  validation and router/UDP reachability before changing accounts.
- Later 2026-08-10 regression: after Play Store/mihomo repair and NetBird app
  restarts, the same `charlie` profile remained present but Android NetBird
  returned to `0 of 0 Peers connected` / `Connecting` with no `tun0`.
  Fedora still had Management/Signal connected and saw `pkr110.netbird.cloud`
  as `Connecting`, so the remaining fault is Android NetBird client management
  map/peer fetch or account-side policy state, not FRP/LAN/ADB. Do not claim
  NetBird as the primary fallback until Android has `tun0` and Fedora sees a
  fresh handshake again. Current stable control plane is FRP ADB
  `127.0.0.1:15555` plus LAN ADB `192.168.123.22:5555`.
- Play Store risk: setting NetBird `DisableDNS=false` can publish NetBird DNS
  `100.87.255.254` into Android VPN DNS. If Google Play/GMS fails while NetBird
  is active, compare Play UID DNS with and without NetBird DNS before changing
  the account. Historical backups include files named
  `charlie.json.pre-20260731-disable-dns*`.
- 2026-08-10 final stabilization: `~/.local/bin/phone-network-stabilize status`
  verified FRP ADB, LAN ADB, NetBird ADB, mihomo proxy, Play proxy probe, and
  DuckDNS `19976` all healthy. Android has `tun0 100.87.37.3/16`; Fedora sees
  `pkr110.netbird.cloud` connected. Android global HTTP proxy is intentionally
  cleared by default, and normal app UID route probes go through Wi-Fi
  `192.168.123.1`, not NetBird. Keep NetBird as overlay-only; do not re-enable
  a system-wide proxy or full-tunnel VPN unless the user explicitly asks.

Manual verification:

```bash
systemctl --user start phone-netbird-ensure.service
adb -s 127.0.0.1:15555 shell 'su -c "ip route get 100.87.238.153 uid 10371"'
adb -s 127.0.0.1:15555 shell 'su -c "su 10371 -c "toybox nc -z -w 5 100.87.238.153 2225; echo $?""'
```

### Fedora peer login expiry

2026-07-19 C5 investigation found a separate Fedora-side failure mode:
Android `phone-netbird-ensure` can report `ok=true` / `already-connected`
while the Fedora NetBird daemon itself has expired login state. Verify both
sides before calling NetBird healthy:

```bash
netbird status
ip link show wt0
sudo tail -n 120 /var/log/netbird/client.log | rg 'peer login has expired|NeedsLogin|interface wt0 has been removed'
adb -s 127.0.0.1:15555 shell 'su -c "ip route get 100.87.238.153 uid 10371"'
adb -s 127.0.0.1:15555 shell 'su -c "su 10371 -c \"toybox nc -z -w 5 100.87.238.153 19904; echo rc=$?\""'
```

Symptoms/evidence from 2026-07-19:

- `netbird status` returned `Daemon status: NeedsLogin`.
- `ip link show wt0` returned `Device "wt0" does not exist`.
- `/var/log/netbird/client.log` showed
  `peer login has expired, please log in once more` and `interface wt0 has been removed`.
- Running `~/.local/bin/netbird-cloud-enroll` with the stored setup-key failed
  with the same `peer login has expired` error, so the helper is not enough to
  renew this state in-place.

Do **not** immediately run `netbird deregister` as a shortcut: Haven/WebTTY
profiles hard-code Fedora NetBird IP `100.87.238.153`, and deregister/re-enroll
may allocate a different peer/IP. Preferred recovery is an interactive Fedora
SSO relogin or NetBird admin-side repair that preserves the Fedora peer/IP, then
restore `wt0` to firewalld trusted:

```bash
netbird up --no-browser
sudo firewall-cmd --zone=trusted --add-interface=wt0
sudo firewall-cmd --permanent --zone=trusted --add-interface=wt0
netbird status
```

## Android and Mihomo

NetBird's Android app uses Android's single `VpnService` slot, as do Mihomo
and Clash when run in VPN mode. They cannot be active together. Root access
does not add a second `VpnService`; it only permits a different design:
Mihomo in root/transparent-proxy mode with iptables policy routing, while
NetBird remains the sole Android VPN app. Prefer the existing Mihomo client's
root mode when it provides one; do not install an unverified Magisk module
just to create a second VPN tunnel.

Running Mihomo inside AidLux affects AidLux processes only. It cannot proxy
the Android browser or Google OAuth unless a separate root-level host routing
rule forwards Android traffic to that proxy.

### PKR110 Root Transparent Proxy

On phone `PKR110`, the deployed solution is the Magisk service
`/data/adb/service.d/97-mihomo.sh`. It runs `/data/adb/mihomo` against
`/data/adb/mihomo_netbird`, redirects device TCP traffic to `redir-port 7892`,
and DNS traffic to `5354`, while `io.netbird.client` owns Android's VPN slot.
NetBird UID `10573` is not bypassed on this phone: direct root/mobile routing
times out for Google/NetBird control traffic, so login and control-plane HTTPS
must traverse root Mihomo. The source subscription remains the active Clash
Meta processing configuration, copied to the independent root directory; do
not edit the Clash Meta app's private configuration in place.

Backups retained on the phone:

- `/data/adb/service.d/97-mihomo.sh.bak-20260715`
- `/data/adb/service.d/97-mihomo.sh.before-netbird-config`
- `/data/adb/mihomo_data` (the pre-NetBird root configuration)

Use Clash Meta only to edit rules or refresh its subscription.
Leave its connection state stopped: starting it activates its Android VPN and
conflicts with NetBird. After a subscription refresh, synchronize its active
configuration into the root daemon with:

## iPhone Peer Connecting / No Handshake

2026-08-01 check: iPhone peer `iphone-w422417869.netbird.cloud` had NetBird
IP `100.87.23.147`, but Fedora `netbird status -d` showed `Status:
Connecting`, no WireGuard handshake, and `ping -c 3 100.87.23.147` returned
destination host unreachable. Fedora itself was healthy:

- `netbird.service`: active/running
- Fedora NetBird IP: `100.87.171.39/16`
- `ip route get 100.87.23.147`: routes via `wt0`
- `firewall-cmd --get-active-zones`: `wt0` in `trusted`
- Services such as `8648`, `8787`, and `5000` listen on `0.0.0.0`

Do not use the iPhone's own `100.87.23.147` as a Hermes/WebTTY server URL.
Phone browsers should open Fedora/Hermes through:

```text
http://100.87.171.39:8648
http://100.87.171.39:8787
```

If the iPhone peer stays `Connecting`, this is an iPhone-side tunnel/handshake
problem, not a Fedora service-port problem. User-side recovery order:

1. Open the iPhone NetBird app and confirm it says connected.
2. Toggle NetBird/VPN off and on once; keep the app foreground for 20-30s.
3. In iOS Settings -> VPN, confirm NetBird is the active VPN.
4. Temporarily disable Low Power Mode, Low Data Mode, iCloud Private Relay,
   and any other VPN/proxy profile while testing.
5. Test Safari with `http://100.87.171.39:8648`, not `100.87.23.147`.
6. Recheck from Fedora with `netbird status -d` and `ping -c 3 100.87.23.147`.

Do not restart Fedora NetBird just because an iPhone peer is `Connecting`;
Android `pkr110.netbird.cloud` can be connected at the same time, proving the
host control plane and relay path are generally working.

```bash
adb shell 'su -c /data/adb/mihomo-sync-netbird.sh'
```

The sync script validates the staged configuration, retains the previous root
directory at `/data/adb/mihomo_netbird.previous`, atomically replaces the
root copy, and restarts Mihomo. Clash Meta's per-app VPN selection is not
transferred; neither is its UI-only manual node selection. The root profile
uses its configuration's `Auto` strategy group. Root transparent-proxy
bypasses require explicit UID rules in `97-mihomo.sh`.

PKR110 fake-DNS failure mode found on 2026-07-16:

- Do not put public DNS destination returns before DNS hijack. Non-root app
  DNS must hit Mihomo first:
  `owner uid 0 RETURN`, then `udp/tcp dport 53 REDIRECT --to-ports 5354`,
  then public DNS destination returns for root/Mihomo's own upstream DNS.
- Do not keep `/data/adb/mihomo_netbird/config.yaml` globally pinned to
  `interface-name: wlan0` on PKR110. That breaks 5G when the active default
  route is cellular `rmnet_data*`. Keep `sniffer.enable: true`; redir traffic
  otherwise arrives as bare IPs and domain rules for Google/NetBird do not
  apply.
- Add proxy server domains such as `+.tr202601.com`, `+.liangxin1.xyz`, and
  `+.lxy1015.top` to `fake-ip-filter`. If these resolve to `198.18.x.x`, all
  proxy health checks fail and Google Play/NetBird appear broken.
- Chrome/Google Play/GMS may run under multiple Android user IDs. Reject
  UDP/443 for user-0, user-10, user-11 and user-999 Chrome/GMS/Play UIDs so
  QUIC falls back to TCP and can pass through the transparent proxy.
- Route `login.netbird.io`, `netbird.io`, and `auth0.com` through the root
  Mihomo proxy group used for NetBird login. On the 2026-07-16 PKR110 repair,
  `login.netbird.io` as `DIRECT` and `auth0.com` as the OpenAI route made
  NetBird/Google OAuth appear intermittently stuck even though raw Google
  reachability was healthy.

Verify from Fedora when ADB is available:

```bash
adb shell 'su -c "ps -A -o PID,ARGS | grep -E \"[s]h /data/adb/service.d/97-mihomo.sh|[/]data/adb/mihomo\""'
adb shell 'su -c "curl -sS http://127.0.0.1:9000/proxies"'
adb shell 'su -c "iptables -t nat -S MIHOMO"'
adb shell 'curl -I --connect-timeout 6 --max-time 12 https://play.googleapis.com'
adb shell 'curl -I --connect-timeout 6 --max-time 12 https://accounts.google.com'
```

### PKR110: NetBird login and Android VPN slot repair (2026-07-16)

The Android device has only one `VpnService` slot.  Before asking NetBird to
connect, ensure Tailscale is neither always-on nor enabled.  Stopping its app
alone is insufficient when Android retains its old VPN session.

```bash
adb shell 'settings delete global always_on_vpn_app'
adb shell 'settings put global always_on_vpn_lockdown 0'
adb shell 'pm disable-user --user 0 com.tailscale.ipn'
adb reboot
```

This preserves Tailscale data and is reversible with:

```bash
adb shell 'pm enable com.tailscale.ipn'
```

After boot, verify `settings get global always_on_vpn_app` returns `null`, then
open NetBird.  The correct login test is the app reaching `login.netbird.io`;
the user must complete their own Google/NetBird authentication. Never enter or
request account credentials through an automation agent.

On this mobile network the NetBird app can reach its control endpoints only
through the root Mihomo TCP redirect. Do **not** add a NetBird UID direct-bypass
rule while login/control traffic needs the proxy; its WireGuard UDP transport is
not covered by the TCP redirect.

Chrome Custom Tabs initially prefer QUIC (`UDP/443`), which bypasses the TCP
redirect and leaves NetBird's **Continue with Google** button spinning. The
current `97-mihomo.sh` therefore rejects UDP/443 only for Chrome UID `10336`,
forcing safe HTTPS/TCP fallback. Verify after boot:

```bash
adb shell 'su -c "iptables -t filter -S OUTPUT | grep 10336"'
```

If NetBird opens the Auth0 page but tapping Google switches to another Android
app instead of Google, check web intent hijackers before changing proxy rules.
Known PKR110 hijackers found on 2026-07-16:

```bash
adb shell 'cmd package query-activities -a android.intent.action.VIEW -d https://accounts.google.com'
adb shell 'cmd package query-activities -a android.intent.action.VIEW -d https://login.netbird.io'
```

Disable only the interfering user package, and record the package name because
this is a user-visible change:

```bash
adb shell 'su -c "pm disable-user --user 0 any.shortcut"'
adb shell 'su -c "pm disable-user --user 0 org.kde.kdeconnect_tp"'
```

Re-enable if needed:

```bash
adb shell 'su -c "pm enable --user 0 any.shortcut"'
adb shell 'su -c "pm enable --user 0 org.kde.kdeconnect_tp"'
```

On the same repair, Chrome DevTools over ADB worked only when the websocket was
opened with `suppress_origin=True`. Do not write a persistent
`/data/local/tmp/chrome-command-line` just to bypass origin checks; if such a
file was staged during debugging, delete it after the test.

The Auth0 page can render two Google buttons. The visible remembered-flow
button is `btn-remembered`; `btn-google` may have a zero-size rect and clicking
it in DevTools proves nothing. A valid network-chain verification is:

1. Start NetBird from the app and tap the connect button.
2. Attach Chrome DevTools to the `login.netbird.io` page.
3. Trigger `document.getElementById("btn-remembered").click()`.
4. Confirm requests progress through:
   `login.netbird.io/authorize` →
   `accounts.google.com/o/oauth2/auth` →
   `login.netbird.io/login/callback` →
   `http://localhost:53000/?code=...`.

If that final localhost callback is reached but NetBird remains disconnected,
`netbird.cfg` is not updated, and `ss -ntp | grep 53000` shows Chrome stuck in
an established connection to NetBird's local listener, stop changing Google,
Mihomo, DuckDNS, or router settings. The network path and OAuth provider are
working; the Android NetBird client is failing to consume its local callback.
Use setup-key enrollment if available, capture NetBird trace logs, or replace
the Android client build.

PKR110 repeat confirmation on 2026-07-17 with NetBird Android `v0.5.0`:

- After selecting the first Google account, Chrome opened a loopback callback
  to NetBird, but NetBird did not accept/read it:
  `LISTEN 1 *:53000 users:((".netbird.client",pid=...,fd=...))` plus
  `ESTAB [::1]:53000 [::1]:<chrome-port>` with about 800 bytes in `Recv-Q`.
- `netbird.cfg` still had empty `Token`, empty `SetupKey`, empty `Peers`,
  `Signal`, and `Relay`; `ip link show wt0` returned `no_wt0`.
- Device idle whitelist, app-ops for background/foreground/VPN, and
  `cmd activity unfreeze <pid>` did not drain the callback queue. Do not keep
  repeating the Google OAuth path for this state; use setup-key enrollment or
  update/replace the Android client.

Android setup-key enrollment path verified on 2026-07-17:

1. Open NetBird.
2. Drawer → `Profiles` → floating `Add Profile`; create a temporary profile
   so the `default` OAuth profile is not overwritten.
3. Switch to that profile.
4. Drawer → `Change Server` → confirm `Yes`.
5. Tap `Add this device with a setup key`.
6. Fill `Server` with `https://api.netbird.io` for NetBird Cloud, or use the
   deployment's management API URL for self-hosting.
7. Replace the example setup-key UUID with a real dashboard-generated setup
   key, then tap `Change`.
8. Return to the main screen and tap connect; on Android verify the app shows
   `Connected` and `tun0` has the NetBird address. The app should no longer
   open Chrome OAuth.

The example UUID shown by the Android UI is not a real key. If it is left in
place, `Change Server` can still report success because only the server
setting changed; connecting then falls back to the broken OAuth flow.

PKR110 setup-key completion and 5G/Wi-Fi verification on 2026-07-17:

- The working Android profile is `charlie`; the app shows
  `pkr110.netbird.cloud`, NetBird IPv4 `100.87.37.3/16`, and `Connected`.
- Android NetBird uses Android `VpnService`, so the live interface is `tun0`,
  not `wt0`. Do not fail verification just because `wt0` is absent on
  Android. Require `tun0` with the NetBird address and a route such as:

  ```bash
  adb -s 127.0.0.1:15555 shell 'ip -br addr | grep -E "tun0|wlan|rmnet"'
  adb -s 127.0.0.1:15555 shell 'ip route get 100.87.238.153'
  ```

- For automated setup-key entry, switch to CodeBoard, quote the remote
  `input text` payload, and verify the field shape without printing the key.
  An unquoted or partially cleared `input text` can truncate at the first
  hyphen or leave one extra trailing character. After exact entry, press
  `KEYCODE_BACK` once to hide the IME before tapping `Change`; otherwise the
  tap can hit the keyboard instead of the button and the page appears stuck.
- After `Change` returns to the main screen, tap the large connect button. A
  successful setup-key profile does not need the broken OAuth browser flow.
- Verified 5G/cellular path: with Wi-Fi disabled, Android reported active
  default network `101` over `rmnet_data3`; phone-to-Fedora NetBird ping
  `100.87.238.153` succeeded and Fedora `netbird status` showed
  `Peers count: 1/1 Connected`.
- Verified Wi-Fi path: after `svc wifi enable`, the phone connected to
  `PDCN_5G` on `wlan0` (`192.168.123.229/24`), kept `tun0`
  `100.87.37.3/16`, and both directions pinged over NetBird with 0% packet
  loss in the final 5-packet test.
- P2P optimization verified on 2026-07-17:
  - Android NetBird `Advanced` → `Force relay connection` must be off
    (`checked="false"`). If it is on, NetBird intentionally uses relay and
    there is no P2P advantage.
  - Fedora firewall must allow the local WireGuard/NetBird port:
    `firewall-cmd --list-ports` includes `51820/udp`.
  - Padavan router must DNAT public UDP `51820` to Fedora
    `192.168.123.71:51820`. Persistent rule lives in
    `/etc/storage/post_iptables_script.sh` under
    `# NetBird UDP P2P 51820 -> Fedora (2026-07-17)`.
  - With phone on 5G (`wlan0 DOWN`, cellular `rmnet_data3`, NetBird `tun0`
    `100.87.37.3/16`), Fedora `netbird status --detail` showed real P2P,
    not relay: `Connection type: P2P`, candidates `srflx/prflx`, endpoints
    `125.110.209.185:51820/36.21.8.26:49002`, and
    `Last WireGuard handshake: 2 seconds ago`. Short bidirectional ping passed
    with `0% packet loss`, around `81 ms` average.
  - With phone on home Wi-Fi `PDCN_5G` (`wlan0 192.168.123.229/24`), Fedora
    `netbird status --detail` showed `Connection type: P2P`, candidates
    `host/prflx`, endpoints `192.168.2.201:51820/192.168.123.229:51820`;
    short bidirectional ping passed with `0% packet loss`, around `5–11 ms`
    average.
  - `Relay server address` may still be listed as available in status output;
    judge the active path by `Connection type`, ICE candidates, recent
    `Last WireGuard handshake`, transfer counters, and bidirectional ping.

Final dual-mode verification commands:

```bash
netbird status
ping -c 5 -W 3 100.87.37.3
adb -s 127.0.0.1:15555 shell 'ping -c 5 -W 2 100.87.238.153'
adb -s 127.0.0.1:15555 shell 'cmd wifi status | head -20'
adb -s 127.0.0.1:15555 shell 'dumpsys connectivity | grep "Active default network" | head -1'
```

PKR110 input failure mode found on 2026-07-17:

- Do not tap `Use NetBird server` after expanding setup-key mode. In NetBird
  Android `v0.5.0` that button immediately submits a server-only change and
  bypasses the setup-key field.
- ADB `input text` is not reliable with the phone's normal Chinese IMEs for
  URLs or setup keys; it can rewrite `/`, `.`, and `:` into Chinese
  punctuation. Switch to CodeBoard before automated field entry:

  ```bash
  adb shell 'ime set com.gazlaws.codeboard/.CodeBoardIME'
  ```

- Even with CodeBoard, `input keyevent KEYCODE_0`, `KEYCODE_C`, and
  `KEYCODE_Z` were observed not to enter NetBird's setup-key `EditText`.
  Plain `input text` can also drop hyphens or truncate long strings. If exact
  setup-key text must be automated, use an input method that supports direct
  text broadcast or UiAutomator `setText()`, and verify the field before
  submitting.
- Installing a helper IME (`ADBKeyBoard`) through `adb install`, `pm install`,
  or `cmd package install` hung on this Android 16 PKR110 build while
  `com.android.packageinstaller`/Play verifier were active. Do not block on
  repeated install attempts; stop and use manual paste or a preinstalled input
  helper.

Field verification before pressing `Change`:

```bash
adb shell 'uiautomator dump /sdcard/window.xml >/dev/null; grep -E "edit_text_server|edit_text_setup_key|btn_change_server" /sdcard/window.xml'
```

The server field must be exactly `https://api.netbird.io:443` for NetBird
Cloud. The setup-key field must contain the real dashboard setup key, not the
example UUID, and must preserve all required characters.

If Google OAuth completes but Chrome reaches
`http://localhost:53000/?code=...` with `ERR_CONNECTION_REFUSED`, the network
path is healthy: the Android NetBird client has failed to start its required
local OAuth callback listener. Confirm with:

```bash
adb shell 'su -c "ss -lntp | grep 53000 || true"'
```

Do not change Mihomo or Google routing further for that symptom. Capture a
NetBird trace log from its Advanced menu and repair/update the Play-installed
NetBird client; the official Android flow requires that local listener.

On PKR110, clearing NetBird app data on 2026-07-16 did not restore the listener
(`ss` remained empty after a fresh login attempt). Treat a repeated
`ERR_CONNECTION_REFUSED` on port 53000 as a client-side defect, not an account,
Google, DuckDNS, or router issue. A server-side setup key enrollment is the
safe workaround when available because it avoids browser OAuth.

Magisk executes every executable file in `/data/adb/service.d`, regardless of
backup-looking suffixes. All historical `97-mihomo.sh.*` files must be mode
`0600`; only `/data/adb/service.d/97-mihomo.sh` may be executable. If boot
creates more than one `mihomo -d` process, fix permissions, stop the duplicate
processes, and start only the current script before testing NetBird.

## Recommended Topology

Use a small public VPS for the NetBird management/relay control plane. Do not
use the home Fedora host as the long-term control plane unless there is no VPS:
home-hosted control depends on the same router, WAN, DuckDNS, and power path
that NetBird is meant to bypass.

Default self-host profile:

- Official NetBird `getting-started.sh`
- Embedded IdP/Dex
- Built-in Traefik with Let's Encrypt
- Public DNS name such as `netbird.example.com`
- Setup key enrollment for Fedora, phone, Windows, and other fixed devices

Required public inbound ports on the VPS:

- `80/tcp` for HTTP challenge and redirect
- `443/tcp` for dashboard, management, signal, relay, and gRPC
- `3478/udp` for STUN/NAT traversal
- `51820/udp` only if NetBird Proxy is enabled

## VPS Deploy Path

Prerequisites:

- A VPS with Docker Engine or Docker-compatible Compose.
- DNS `A` record for the NetBird domain points to the VPS public IPv4.
- Firewall/security group opens `80/tcp`, `443/tcp`, and `3478/udp`.

Use the local helper:

```bash
netbird-selfhost-kit preflight netbird.example.com user@vps
netbird-selfhost-kit deploy netbird.example.com user@vps admin@example.com
```

The helper runs the official release script on the VPS with:

```bash
NETBIRD_DOMAIN=<domain>
NETBIRD_LETSENCRYPT_EMAIL=<email>
NETBIRD_AGENT_NETWORK=true
```

After deploy, open:

```text
https://<domain>
```

Finish onboarding in the dashboard, create a setup key, then enroll Fedora:

```bash
sudo netbird down || true
sudo netbird up --management-url https://<domain> --setup-key <SETUP_KEY>
netbird status
```

Do not store the setup key in this runbook or in final answers.

## Migration Order

1. Enroll Fedora and confirm it gets a NetBird IP.
2. Enroll one secondary device, preferably Windows or phone.
3. Verify peer-to-peer SSH to Fedora service ports:
   - Codex Smart `2230`
   - Codex 1 `2225`
   - Codex 2 `2226`
   - Codex 3 `2229`
   - OpenCode SSH `2224`
4. Add NetBird copies of Haven/SSH profiles. Keep existing Tailscale and
   DuckDNS profiles until NetBird has been stable for several days.
5. Only after that, update primary profile labels or automation.

## Verification

### Android (PKR110) OAuth and tunnel boundary — 2026-07-16

- Google OAuth completes when Chrome QUIC is rejected for Chrome's UID only and
  NetBird's temporary `localhost:53000` callback listener is live. Do not reuse
  an old Auth0 URL: its state is single-use and produces a misleading 400/error
  page.
- Keep `login.netbird.io` on the phone's native route. The stale Auth0 return
  path through the transparent proxy produced `ERR_CONNECTION_CLOSED`.
- Android's `ACTIVATE_VPN` permission and a running
  `io.netbird.client/.tool.VPNService` do not prove a tunnel is up. Require a
  `wt0` interface and an Android VPN network before declaring success.
- Current unresolved state after a clean Mihomo restart: OAuth/profile is
  present, but NetBird remains `Connecting`, shows `0 of 0 Peers`, and creates
  no `wt0`. Diagnose its control-plane/tunnel traffic next; do not repeat the
  OAuth reset or claim it is connected.

Fedora:

```bash
netbird status
ip addr show wt0 2>/dev/null || ip addr | rg -n 'netbird|wt'
```

From another NetBird peer:

```bash
ssh -p 2230 charlie@<fedora-netbird-ip>
ssh -p 2225 charlie@<fedora-netbird-ip>
```

Dashboard:

- Fedora peer is online.
- Setup key is limited or expires after enrollment.
- Peer names are readable: `fedora`, `phone`, `windows`, etc.

## Rollback

On Fedora, disconnect from the self-hosted NetBird network without uninstalling:

```bash
sudo netbird down
```

To reset local NetBird state only if needed:

```bash
sudo systemctl stop netbird.service
sudo rm -rf /var/lib/netbird
sudo systemctl start netbird.service
```

Keep Tailscale and DuckDNS entries intact during rollback.

### Fedora peer `NeedsLogin` impact on Android Mattermost (2026-07-18)

If Android Mattermost reports `Server unreachable` for
`http://100.87.238.153:8065`, check Fedora NetBird before changing Mattermost:

```bash
netbird status
mattermost-phone-repair status
```

On 2026-07-18 Fedora NetBird reported `Daemon status: NeedsLogin`; the Android
phone had `tun0` but could not reach Fedora. Setup-key re-enroll failed with
`peer login has expired, please log in once more`, so the correct repair was
interactive SSO on Fedora. After login, `netbird status` showed
`Peers count: 1/1 Connected` and the Mattermost Android UID `10447` returned
`HTTP:200` from `/api/v4/system/ping`.

### 2026-07-19 PKR110 Android foreground conflicts

- `io.netbird.client` remains a system/privileged updated system app and `always_on_vpn_app=io.netbird.client` can be reasserted by `phone-netbird-ensure.timer`.
- Android NetBird v0.5.0 hardcodes only a few `VpnService.Builder.addDisallowedApplication(...)` packages in `IFace.java`; there is no exposed config-backed per-app exclusion list in the installed app. Do not assume League of Legends / browser packages can be excluded from NetBird without patching/rebuilding the app.
- With NetBird active, the VPN may publish DNS `100.87.255.254` for domain `netbird.cloud`; public names such as `charlie1990.duckdns.org` and Tencent game names can fail from app-like UIDs. Haven NetBird entries remain safe because they use numeric `100.87.238.153`.
- As of 2026-08-01, `~/.local/bin/phone-netbird-ensure` no longer acts as a
  foreground repair guard by default. It must not force-stop NetBird or blindly
  tap the connect button unless `PHONE_NETBIRD_AUTO_REPAIR=1` is explicitly set
  for a short repair window. Do not include browsers in any pause/reconnect
  loop: browser foreground pausing made Codex WebTTY over NetBird unstable.
- If NetBird UI remains `Disconnected` / `0 of 0 Peers connected`, do not keep
  foregrounding it every few minutes. Re-check app auth/profile state, Android
  VPN slot ownership, Mihomo mode, and NetBird management reachability before
  changing rules again.


### 2026-07-19 PKR110 NetBird ADB/ensure false negative

- Failure mode: PKR110 was reachable over NetBird ADB as `100.87.37.3:5555`, but local USB/old LAN serials (`127.0.0.1:15555`, `192.168.123.22:5555`) were stale. `phone-netbird-ensure.timer` kept reporting `connecting-stuck` even while Android VPN was connected.
- Durable fix: `~/.local/bin/phone-netbird-ensure` defaults to `100.87.37.3:5555 192.168.123.22:5555 127.0.0.1:15555`, runs `adb connect` for TCP serials, and treats no-device/backoff states as successful systemd exits so timers do not create a failure storm.
- Verification:

```bash
systemctl --user restart phone-netbird-ensure.service
cat ~/.local/state/phone-netbird-ensure/latest.json
# expect: serial=100.87.37.3:5555, ok=true, reason=already-connected
```

- Android package state on PKR110: `io.netbird.client` is a privileged updated system app (`pkgFlags=[ SYSTEM ... UPDATED_SYSTEM_APP ]`, `privateFlags=[ ... PRIVILEGED ... ]`), `always_on_vpn_app=io.netbird.client`, `tun0` routes `100.87.238.153` for app UIDs.

### 2026-08-01 Fedora NetBird self-flapping from health timers

- Failure mode: phone access to `http://100.87.171.39:5000/` was intermittent
  even though the Fedora service on `0.0.0.0:5000` and LAN access were healthy.
  `netbird status` alternated between connected and disconnected.
- Root cause: two user timers treated an unreachable phone peer
  (`100.87.37.3`) as proof that Fedora NetBird was broken:
  `netbird-healthcheck.timer` ran every 60s and restarted `netbird.service`
  when `ping 100.87.37.3` failed; `netbird-phone-monitor.timer` restarted the
  host after three failed phone pings. This caused minute-level daemon flapping.
- Durable fix:
  - `~/.local/bin/netbird-healthcheck.sh` now checks only Fedora host
    Management/Signal state, requires consecutive failures, and has a
    15-minute restart cooldown.
  - `~/.local/bin/netbird-phone-monitor.sh` no longer restarts Fedora NetBird
    from phone peer reachability; it records/notifies and points to DuckDNS
    fallback paths.
- Verification on 2026-08-01:
  - After one timer cycle, `journalctl --user -u netbird-healthcheck.service -u
    netbird-phone-monitor.service --since '3 min ago'` showed services finished
    without new `systemctl restart netbird.service`.
  - `netbird status`: Management connected, Signal connected,
    `NetBird IP: 100.87.171.39/16`.
  - PKR110 phone route to Fedora NetBird IP used `tun0`:
    `100.87.171.39 dev tun0 table 1032 src 100.87.37.3`.
  - PKR110 phone probe returned HTTP 200 for:
    `http://100.87.171.39:5000/`,
    `http://charlie1990.duckdns.org:19910/`, and
    `http://charlie1990.duckdns.org:8648/`.

Do not reintroduce host daemon restarts based only on a lazy/offline peer ping.
For phone usability, classify the active phone path first: NetBird `tun0`, 5G,

### 2026-08-10 PKR110 NetBird Remaining Risk

- During phone fallback recovery, `settings get global always_on_vpn_app`
  returned `io.netbird.client`, NetBird process was running, and background
  permissions were replayed.
- However Android had no `tun0`, route to Fedora NetBird IP
  `100.87.171.39` still used `wlan0`, and Fedora `netbird status` showed
  `Peers count: 0/3 Connected`.
- Screenshot evidence from the phone NetBird app showed:
  "It looks like there are no machines that you can connect to..." on the
  Peers tab. Treat this as account/policy/enrollment state, not a local ADB or
  FRP failure.
- Do not depend on NetBird as the only phone control plane until the NetBird
  app account/policy is fixed and `tun0` with `100.87.37.3/16` is verified.
  Current stable fallbacks are FRP ADB `127.0.0.1:15555` and LAN ADB
  `192.168.123.22:5555`.
LAN, USB reverse, or DuckDNS/FRP.
