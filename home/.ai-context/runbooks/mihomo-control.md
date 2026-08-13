# Runbook: Unified Mihomo Control

## Architecture

- Control plane: `sub-store.service`, Podman image
  `docker.1ms.run/xream/sub-store:latest`.
- Dashboard: `http://127.0.0.1:19887/` only. It must not be exposed to LAN or
  public Internet because it holds subscription addresses.
- Persistent data: `~/.local/share/sub-store/`.
- Versioned policy: `~/dotfiles/mihomo/`; it contains no subscription URLs or
  node credentials.
- Phone root runtime: `/data/adb/mihomo_netbird`; Magisk service
  `/data/adb/service.d/97-mihomo.sh`.

## Policy

The default is CN direct, foreign proxy:

1. Private/LAN traffic: `DIRECT`.
2. Advertising domains: `REJECT`.
3. `GEOSITE,cn` and `GEOIP,cn`: `DIRECT`.
4. `MATCH,PROXY`.

Do not use a GFW-list-only default. A CN-direct policy proxies new foreign
domains before any GFW list categorizes them.

## Subscription Refresh

1. Update the upstream subscription in Sub-Store.
2. Generate/update the Clash Meta/Mihomo profile with the shared rules in
   `~/dotfiles/mihomo/rules/common.yaml`.
3. On Android, keep Clash Meta stopped and run:

```bash
~/dotfiles/mihomo/scripts/sync-android-root
```

The command invokes `/data/adb/mihomo-sync-netbird.sh`, validates the staged
profile, retains `/data/adb/mihomo_netbird.previous`, then restarts root
Mihomo.

## AI Super Button

The AI Super Button and its Workbench action bus expose three phone-safe
network actions under the `网络` group:

- `订阅面板`: opens Workbench `/sub-store/`, a device-code-protected reverse
  proxy to loopback-only Sub-Store.
- `代理状态`: reports Sub-Store service state and ADB availability.
- `同步手机代理`: runs the validated Android root sync script; it does not
  start Clash Meta VPN.
- `NetBird`: opens the installed official NetBird Android app locally, without
  sending the launch through Workbench or a proxy.

Android source: `~/.local/share/mobile-ai-super-button/`; rebuild and queue
installation with `~/.local/bin/mobile-ai-super-button-build-install`.

## 2026-07-16 Phone DNS / Tailscale Repair

- Only `/data/adb/service.d/97-mihomo.sh` may be executable. A historical
  `97-mihomo.sh.bak-*` was executable and launched a second
  `/data/adb/mihomo_data` instance alongside `/data/adb/mihomo_netbird`.
- The transparent-proxy script must bypass Tailscale user-0 UID `10352`, as
  Tailscale owns Android's VPN slot. Do not bypass NetBird UID `10573` while
  it is signing in: its Chrome Custom Tab OAuth flow needs the proxy path.
- Because the root script redirects DNS to `5354`, the active profile needs
  `dns.listen: 0.0.0.0:5354`. The durable insertion is in
  `/data/adb/mihomo-sync-netbird.sh`; verify after profile sync.
- `/data/adb/service.d/99-network-watch.sh` writes passive five-minute
  evidence to `/data/adb/phone-network-watch.log` without restarting VPN,
  Mihomo, or Haven. Healthy: `mihomo=1 old_mihomo=0 dns5354=1` and
  `duckdns_2225_rc=0`.

## Android VPN Boundary

Clash Meta VPN, NetBird, and Tailscale all use Android's single `VpnService`
slot. Do not start Clash Meta while Tailscale/NetBird is active. On PKR110,
Tailscale user-0 UID `10352` owns the current VPN slot and must bypass the
root transparent proxy; add other per-app bypasses as explicit iptables
owner-UID rules to `/data/adb/service.d/97-mihomo.sh`.

## Verify

```bash
systemctl --user is-active sub-store.service
curl --noproxy '*' -fsSI http://127.0.0.1:19887/
adb shell 'su -c "ps -A -o PID,ARGS | grep -E \"[s]h /data/adb/service.d/97-mihomo.sh|[/]data/adb/mihomo\""'
adb shell 'su -c "curl -sS http://127.0.0.1:9000/proxies"'
```

## 2026-07-19 LOL/WebTTY Shared Phone Network Repair

If League of Legends: Wild Rift cannot connect while Haven remains stable,
first check for duplicate root Mihomo startup scripts and duplicate daemons. A
2026-07-19 failure had `/data/adb/service.d/97-mihomo.sh.pre-bytedance-quic-20260718`
still executable, so Android launched two `97-mihomo` loops and two
`mihomo -d /data/adb/mihomo_netbird` processes. Fix by making every
`97-mihomo.sh.*` backup non-executable, then run the deterministic clean
restart:

```bash
adb -s 127.0.0.1:15555 shell 'su -c "chmod 0644 /data/adb/service.d/97-mihomo.sh.* 2>/dev/null || true"'
~/.local/bin/phone-mihomo-clean-restart 127.0.0.1:15555
```

Expected: exactly one `sh /data/adb/service.d/97-mihomo.sh`, exactly one
`mihomo -d /data/adb/mihomo_netbird`, LOL direct UID returns for `10343` and
`10491`, and the game can enter a match. On this phone, disabling NetBird DNS
(`DisableDNS=true`) in NetBird's local profile reduced DNS interference while
Haven/WebTTY continue to use numeric `100.87.238.153`; do not rely on
`fedora.netbird.cloud` if DNS is disabled.

## PKR110 5G / Game Proxy Repair

If 5G has partial proxy failures while Wi-Fi was previously healthy, check the
active interface and the Mihomo profile before changing nodes. A bad state
found on 2026-07-17 was `/data/adb/mihomo_netbird/config.yaml` pinning
`interface-name: wlan0` while the active default route was cellular
`rmnet_data3`; Mihomo outbound traffic then used the wrong interface.

For the root profile, do not keep a fixed `interface-name: wlan0` when the
phone must work across home Wi-Fi, portable Wi-Fi, and 5G. Remove the fixed
interface, validate, and restart:

```bash
adb -s ff3ef385 shell 'su -c "/data/adb/mihomo -t -d /data/adb/mihomo_netbird"'
~/.local/bin/phone-mihomo-clean-restart ff3ef385
```

League of Legends: Wild Rift is UDP-heavy. The current root transparent path
only redirects TCP and DNS, not general UDP, so keep both installed variants on
the carrier path. The durable rule in `/data/adb/service.d/97-mihomo.sh` is:

- `LOL_DIRECT_UIDS="10343 10491 1010343 1010491 1110343 1110491 99910343 99910491"`
- Add those owner-UID `RETURN` rules near the top of `MIHOMO`, before DNS/TCP
  redirects.

Verify after restart:

```bash
adb -s ff3ef385 shell 'su -c "iptables -t nat -S MIHOMO | grep -E \"10343|10491\"; pgrep -c mihomo"'
adb -s ff3ef385 shell 'curl -o /dev/null -sS -w "%{http_code} %{time_total}\n" --connect-timeout 5 --max-time 15 https://www.google.com/generate_204'
```

## Phone Play Store / Duplicate Mihomo Repair

If the phone is on home Wi-Fi and ADB works but Play Store or ordinary app
traffic times out, first check for duplicate root Mihomo instances. A common
bad state is one old `mihomo` still owning `7890/7892/9000/5354` while one or
more newer `/data/adb/service.d/97-mihomo.sh` loops have started and logged
`bind: address already in use`.

Do not declare Play Store fixed from proxy/controller checks alone. The required
closure is: launch `com.android.vending`, wait for load, capture a phone
screenshot, and verify the UI is no longer stuck on `请重试`.

Use the deterministic clean restart instead of hand-killing partial PIDs:

```bash
~/.local/bin/phone-mihomo-clean-restart 192.168.123.22:5555
```

Expected post-repair state:

- exactly one `sh /data/adb/service.d/97-mihomo.sh`
- exactly one `mihomo -d /data/adb/mihomo_netbird`
- `curl http://127.0.0.1:9000/proxies` returns JSON
- `curl -I https://play.google.com/store/games` returns HTTP headers

Then force-stop and relaunch Play Store if its UI kept stale failed
connections:

```bash
adb -s 192.168.123.22:5555 shell \
  'su -c "am force-stop com.android.vending; am force-stop com.google.android.gms; monkey -p com.android.vending -c android.intent.category.LAUNCHER 1"'
```

2026-08-10 repair note:

- The helper `~/.local/bin/phone-mihomo-clean-restart` was restored because the
  runbook referenced it but it was missing from the host. It validates
  `/data/adb/mihomo_netbird`, disables executable backup scripts, starts exactly
  one `/data/adb/service.d/97-mihomo.sh` loop and one `mihomo -d
  /data/adb/mihomo_netbird`, then checks `7890/7892/9000/5354`.
- Verified after restart: `127.0.0.1:7890` returned Google
  `generate_204`, and Play Store UI loaded real content instead of a retry
  screen. Final 2026-08-10 stabilization verified Play UID direct and explicit
  proxy probes both return HTTP 200. Keep Android global HTTP proxy cleared by
  default so domestic games and ordinary apps are not forced through a system
  proxy; use `PHONE_FORCE_GLOBAL_PROXY=1 ~/.local/bin/phone-network-stabilize fix`
  only as a temporary emergency recovery.

2026-08-01 Play Store real-app repair notes:

- Do not add global `ip6tables -P OUTPUT DROP` to block IPv6 fallback. It can
  make Android/Play report no usable network. If present, remove it from
  `/data/adb/service.d/97-mihomo.sh` and run `ip6tables -P OUTPUT ACCEPT`.
- If `su 10261 -c 'curl https://play.google.com/store/games'` fails but
  `su 10261 -c 'curl -x http://127.0.0.1:7890 https://play.google.com/store/games'`
  returns HTTP 200, the subscription/node is usable and the failure is in the
  transparent redir path or Android VPN policy.
- If `iptables -t nat -vnL MIHOMO` counters show the Play UID traffic reaching
  `REDIRECT --to-ports 7892` but the app still fails, a user-visible temporary
  emergency recovery is Android global proxy:
  ```bash
  PHONE_FORCE_GLOBAL_PROXY=1 ~/.local/bin/phone-network-stabilize fix
  ```
  Roll back with:
  ```bash
  ~/.local/bin/phone-network-stabilize fix
  ```
- After the proxy or redir fix, force-stop Play/GMS, relaunch Play Store, and
  screenshot the real UI before reporting success.

## Phone Browser Google Login Slow

If phone browser Google login is slow while CLI checks such as
`curl https://accounts.google.com` are fast, check whether the browser is using
QUIC UDP/443. The root transparent proxy handles TCP and DNS, but app QUIC can
bypass the TCP redir path and stall before falling back.

The durable rule lives in `/data/adb/service.d/97-mihomo.sh`:

- `GOOGLE_QUIC_UIDS` includes Google Play Services, Play Store, Chrome, and
  installed browsers such as Via (`mark.via.gp`, UID `10641`), Quark (`10436`),
  Edge/Sesame (`10623`), Yandex (`10607`), Chrome beta (`10628`), mbrowser
  (`10465`), and HeyTap Browser (`10157`), plus user-10/user-11/user-999 UID
  variants.
- `setup_iptables()` rejects only those UIDs' UDP/443 traffic so browsers fall
  back quickly to HTTPS/TCP. This is not global proxying and does not change
  domestic traffic policy.

After editing the UID list, apply with:

```bash
~/.local/bin/phone-mihomo-clean-restart 192.168.123.22:5555
adb -s 192.168.123.22:5555 shell \
  'su -c "iptables -t filter -S OUTPUT | grep -- \"--uid-owner 10641\""'
```

Verify the login endpoint:

```bash
adb -s 192.168.123.22:5555 shell \
  'curl -o /dev/null -sS -w "total=%{time_total} code=%{http_code}\n" --connect-timeout 5 --max-time 15 https://accounts.google.com/signin/v2/identifier'
```

## Douyin/TikTok Comments or Some Videos Cannot Load

If Douyin/TikTok opens but comments fail or only some videos play, check
whether the app is trying QUIC/HTTP3 over UDP/443 while root Mihomo only
redirects TCP and DNS. With fake-ip DNS, UDP/443 can bypass Mihomo and go to a
fake address, causing partial app failures.

2026-07-18 PKR110 repair:

- Installed Douyin package: `com.ss.android.ugc.aweme.mobile`, UID `10791`.
- TikTok package was not present under users `0/10/11/999` during this repair.
- Durable script: `/data/adb/service.d/97-mihomo.sh`
  - Added `BYTEDANCE_QUIC_UIDS="10791 1010791 1110791 99910791"`.
  - `setup_iptables()` and `cleanup_iptables()` now handle
    `$GOOGLE_QUIC_UIDS $BYTEDANCE_QUIC_UIDS`.
  - Backup before change:
    `/data/adb/service.d/97-mihomo.sh.pre-bytedance-quic-20260718`.
- Verification after `~/.local/bin/phone-mihomo-clean-restart ff3ef385`:
  exactly one `/data/adb/service.d/97-mihomo.sh`, exactly one
  `mihomo -d /data/adb/mihomo_netbird`, `/proxies` responds, and filter
  OUTPUT contains UDP/443 `REJECT` owner rules for `10791`, `1010791`,
  `1110791`, and `99910791`.

Commands:

```bash
adb -s ff3ef385 shell 'su -c "cmd package list packages --user 0 -U | grep -Ei '\''douyin|aweme|tiktok|musically|bytedance|ies'\''"'
adb -s ff3ef385 shell 'su -c "iptables -t filter -vnL OUTPUT | grep -E '\''10791|1010791|1110791|99910791'\''"'
adb -s ff3ef385 shell 'su -c "am force-stop com.ss.android.ugc.aweme.mobile; monkey -p com.ss.android.ugc.aweme.mobile -c android.intent.category.LAUNCHER 1"'
```

If TikTok is later installed, add its real app UID and user-10/user-11/user-999
variants to `BYTEDANCE_QUIC_UIDS`, then run:

```bash
~/.local/bin/phone-mihomo-clean-restart ff3ef385
```

## Image Refresh

Docker Hub timed out on 2026-07-15 from this host, including with proxy
variables cleared. Use the working mirror:

```bash
podman pull docker.1ms.run/xream/sub-store:latest
systemctl --user restart sub-store.service
```

## 2026-07-19 Alipay/Luckin Mini-App Login No Response

If Alipay opens the Luckin Coffee mini-app but tapping `支付宝一键登录` appears to do nothing, verify the real app UID path before blaming Alipay or the mini-app UI. On PKR110 the Alipay UID was `10342`; root and shell could differ from the app because root Mihomo redirects non-root DNS to `5354`.

Failure found: one `mihomo -d /data/adb/mihomo_netbird` process was alive but its listeners were missing (`7890/7891/7892/9000/5354` absent). Alipay UID then failed DNS:

```bash
adb -s 100.87.37.3:5555 shell 'su -c "su 10342 -c '\''curl -I --connect-timeout 6 --max-time 12 -sS https://m.luckincoffee.com'\''"'
```

Durable repair applied to `/data/adb/service.d/97-mihomo.sh`:

- single-instance lock: `/data/adb/mihomo-service.lock`
- `start_mihomo()` kills stale `mihomo_netbird` processes before starting
- `mihomo_healthy()` requires listeners for TCP `7890/7892/9000` and UDP DNS `5354`
- the loop restarts Mihomo when the process exists but listeners are missing

Verification after repair:

```bash
adb -s 100.87.37.3:5555 shell 'su -c "cat /proc/net/tcp /proc/net/tcp6 /proc/net/udp /proc/net/udp6 | grep -E '\'':14EA|:1ED2|:1ED3|:1ED4|:2328'\'' | head"'
adb -s 100.87.37.3:5555 shell 'su -c "su 10342 -c '\''curl -I --connect-timeout 6 --max-time 12 -sS https://m.luckincoffee.com'\''"'
```

Expected Alipay UID result: HTTP headers from `m.luckincoffee.com`, not `Could not resolve host`. Do not click user agreements, phone-number authorization, payment, or privacy consent on behalf of the user; stop on those screens.
