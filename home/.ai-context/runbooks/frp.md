# Runbook: FRP Tunnel

FRP 客户端，连接本地 frps，暴露内网服务。

## Desired State

- `frps.service`（system level）— 本地 FRP 服务端
- `frpc.service`（user level）— FRP 客户端，配置 `~/.config/frpc/frpc.toml`
- `frpc` 连接 `frps` 后建立代理隧道（如 `fedora-console-18080`）

## Verify

```bash
systemctl --user is-active frpc
# frps 状态
curl -s 'http://admin:frp%40charlie2026@127.0.0.1:7500/api/proxy/tcp' | jq
```

### Public ntfy via DuckDNS

2026-07-13 desired state:

- Public ntfy URL: `http://charlie1990.duckdns.org:19867/`
- FRPC proxy: `fedora-ntfy`, local `127.0.0.1:2586`, remote `19867`
- Router DNAT: public `19867/TCP -> 192.168.123.71:19867`
- ntfy server config: `~/ai/ntfy/etc/server.yml`, `base-url: http://charlie1990.duckdns.org:19867`
- Main topic: `charlie-actions`

Padavan has a DMZ catch-all in the `vserver` NAT chain. If the `19867` DNAT rule
is appended after that catch-all, public ntfy fails even when DuckDNS and FRP are
healthy. The persistent fix is in router `/etc/storage/post_iptables_script.sh`;
it deletes any duplicate rule, then inserts `19867` before the DMZ catch-all.

Verify:

```bash
systemctl --user is-active container-ntfy.service frpc.service duckdns-update.timer
curl --noproxy '*' -sS -m 10 http://charlie1990.duckdns.org:19867/v1/health
/usr/bin/sshpass -p admin ssh -o StrictHostKeyChecking=no admin@192.168.123.1 \
  '/bin/iptables -t nat -L vserver --line-numbers -n | grep -E "19867|upnp|to:192.168.123.209" | tail -8'
```

### Phone FRPC Checks

When phone FRPC reports `EOF`, `session shutdown`, or `i/o timeout`, classify
the failure before changing FRPS:

```bash
# Fedora: manual frpc tests must not inherit proxy vars.
env | rg -i '^(http|https|all|no)_proxy='
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
  ~/.local/bin/frpc -c /path/to/test-frpc.toml

# FRPS and dashboard should be same-version with client.
/usr/local/bin/frps --version
~/.local/bin/frpc --version
systemctl is-active frps.service

# Phone: check DNS fake-ip, route, VPN UID, and runtime config.
adb shell 'su -c "nslookup charlie1990.duckdns.org 2>/dev/null || ping -c 1 charlie1990.duckdns.org"'
adb shell 'su -c "ip route show table all | head -120; ip rule show"'
adb shell 'su -c "ps -A -o PID,PPID,ARGS | grep -E '\''frpc_smart|frpc|toybox timeout'\'' || true"'
adb shell 'su -c "tail -80 /data/local/tmp/frpc.log; tail -40 /data/local/tmp/frpc_smart.log"'
adb shell 'su -c "grep -E '\''serverAddr|serverPort|loginFailExit'\'' /data/local/tmp/frpc.runtime.toml"'
```

Known 2026-07-08 phone state:

- `charlie1990.duckdns.org` resolved on phone to fake-ip `198.18.0.29`.
- Phone `wlan0` was down; active Internet was cellular `rmnet_data2` with CGNAT
  IPv4 `10.53.246.204`.
- Phone could ping public DNS, but could not reach home public `125.110.213.91:2228`.
- Tailscale VPN was online, but only selected app UIDs were routed; shell/root
  FRPC did not get `100.120.189.27:7000`.
- AidLux is `com.aidlux` UID `10510`, but it was not included in the Tailscale
  Android VPN UID list. Haven is `sh.haven.app` UID `10371` and was included.
  Running FRPC as UID `10371` fixed the tunnel.
- Router persistent DNAT exists: public `2228/TCP -> 192.168.123.71:7000`.
- `frps` and `frpc` are both `0.69.0`; old FRPS backup is
  `/usr/local/bin/frps.0.63.0.bak`.

Working 2026-07-08 phone FRPC state:

- `/data/adb/service.d/frpc.sh` starts
  `su 10371 -c "/system/bin/sh /data/local/tmp/frpc_smart.sh ..."` so FRPC uses
  the Haven/Tailscale UID.
- `/data/local/tmp/frpc.toml` exposes:
  - `phone-adb`: local `127.0.0.1:5555` -> remote `15555`
  - `phone-ssh`: AidLux SSH local `127.0.0.1:8022` -> remote `8022`
  - `phone-haven-mcp`: local `127.0.0.1:8730` -> remote `18700`
- 2026-07-13 修复方向：`adb-phone-keepalive.sh` 不得对 FRP ADB
  serial `127.0.0.1:15555` / `localhost:15555` 执行 `adb tcpip 5555`，
  这会把当前 FRP ADB 连接打成 `offline`。本机脚本已加入 skip。
- 2026-07-13 手机端待安装的稳定版 wrapper 保存在 Fedora
  `~/.local/share/phone-frpc-smart.sh`，并已推到手机
  `/sdcard/Download/frpc_smart.sh.new`。它把 runtime
  `loginFailExit` 写为 `false`，主用 `100.120.189.27:7000`，避免旧脚本
  因短暂 work-connection 超时就退出并关闭 `15555`/`18700`/`8022`。
  若 FRP/ADB 已断，只需在手机 root shell 执行：
  `cp /sdcard/Download/frpc_smart.sh.new /data/local/tmp/frpc_smart.sh; chmod 0755 /data/local/tmp/frpc_smart.sh; chown root:root /data/local/tmp/frpc_smart.sh; pkill -f /data/local/tmp/frpc; su 10371 -c "/system/bin/sh /data/local/tmp/frpc_smart.sh > /data/local/tmp/frpc.log 2>&1 &"`。
- Verify ADB over FRP:

```bash
adb connect 127.0.0.1:15555
adb devices
```

### PKR110 Wi-Fi / 5G FRPC

The current source wrapper is `~/.local/share/phone-frpc-smart.sh`, deployed
as `/data/local/tmp/frpc_smart.sh` and started at boot by
`/data/adb/service.d/frpc.sh`. It runs one FRPC instance as Android shell UID
`2000`, rather than the Tailscale-only Haven UID. Every 15 seconds it selects:

- Home Wi-Fi (`192.168.123.0/24`): `192.168.123.71:7000`.
- Other networks, including 5G: `charlie1990.duckdns.org:2228`.

Fedora firewall permanently allows `7000/tcp` for the LAN path. The phone
registers `phone-adb` at local Fedora `127.0.0.1:15555`; this is the stable
ADB target across Wi-Fi and 5G. Verified on 2026-07-15: LAN FRP login and
`adb connect 127.0.0.1:15555` succeeded; phone DuckDNS resolution and TCP
reachability to `:2228` also succeeded.

2026-07-18 repair/verification:

- Failure mode: USB ADB showed many stale `frpc_smart.sh` / `frpc -c
  /data/local/tmp/frpc.runtime.toml` processes. Logs contained
  `can't create /data/local/tmp/frpc.runtime.toml: Permission denied` and
  `proxy [phone-adb] already exists`. Treat this as duplicate phone FRPC
  wrappers fighting over the same remote ports.
- Durable wrapper fix: update `~/.local/share/phone-frpc-smart.sh` and deploy it
  to `/data/local/tmp/frpc_smart.sh`. The wrapper now must run as root, uses
  `/data/local/tmp/frpc_smart.lock`, writes `frpc.runtime.toml` as root,
  `chown shell:shell` for the runtime file, then starts `frpc` as UID `2000`
  with `su 2000 -c "exec ..."`; it also cleans stale client children.
- Phone config was reduced to control-plane proxies only:
  `phone-adb -> 15555`, `phone-ssh -> 8022`, and
  `phone-haven-mcp -> 18700`. The pre-change backup is
  `/data/local/tmp/frpc.toml.bak-20260718-control-only`. Moonlight proxy blocks
  were removed because local FRPS rejected those remote ports with
  `port not allowed`; do not re-add them without first allowing those ports on
  FRPS/router.
- On Wi-Fi-to-5G switching, the old FRPS remote proxy can remain registered for
  about 30-35 seconds. During that window the new client may log
  `proxy [phone-adb] already exists`; wait for the follow-up
  `start proxy success` before judging 5G ADB failed.
- Verified on 2026-07-18 with USB safety net:
  1. Wi-Fi on: runtime selected `192.168.123.71:7000` and
     `adb -s 127.0.0.1:15555 shell` returned `FINAL_FRP_ADB_OK`.
  2. Wi-Fi disabled: runtime selected `charlie1990.duckdns.org:2228`; after
     remote proxy release, `adb -s 127.0.0.1:15555 shell` returned
     `NON_WIFI_FRP_ADB_OK`.
  3. Wi-Fi restored: runtime switched back to `192.168.123.71:7000`.

2026-08-01 current control-plane rule:

- Root Android control must treat FRP as the primary fallback when NetBird is
  flapping. NetBird `100.87.37.3:5555` is useful only when the peer has a
  handshake; it is not the only management path.
- 2026-08-01 late diagnosis: do not classify the current PKR110 failure as
  "phone frpc killed" if these conditions hold:
  - `/data/adb/service.d/frpc.sh`, `/data/local/tmp/frpc_smart.sh`, and
    `/data/local/tmp/frpc` exist.
  - `ps` shows both `sh /data/local/tmp/frpc_smart.sh` and
    `frpc -c /data/local/tmp/frpc.runtime.toml`.
  - `/data/local/tmp/frpc.runtime.toml` selects
    `charlie1990.duckdns.org:2228`.
  - `/data/local/tmp/frpc_smart.log` repeatedly shows
    `connect to server error: i/o deadline reached`, `session shutdown`, or
    `EOF`.
  In that state the wrapper and client are alive; the active fault is FRP
  server reachability/handshake over the DuckDNS/router/public path, or a
  routing/proxy middlebox issue, and Fedora will not have `127.0.0.1:15555`
  listening until the client registers `phone-adb`.
- Desired phone fallback path remains:
  phone `frpc_smart.sh` -> Fedora/local `frps :7000` or DuckDNS `:2228` ->
  `phone-adb` remote `15555` -> Fedora `adb connect 127.0.0.1:15555`.
- Default diagnostic command:
  `~/.local/bin/phone-frp-fallback-status`. If NetBird or LAN ADB is currently
  reachable, use that path to inspect/restart phone frpc; do not claim USB is
  required.
- If Fedora has no ADB devices and `adb connect 100.87.37.3:5555` /
  `adb connect 192.168.123.22:5555` both fail with no route, Codex cannot
  remotely restart phone frpc yet. Use one USB/root-shell recovery to restart
  `/data/adb/service.d/frpc.sh` or `/data/local/tmp/frpc_smart.sh`, then switch
  back to `127.0.0.1:15555` for all root phone work.
- Do not let NetBird repair timers repeatedly force-stop or tap the NetBird app
  while FRP phone control is down; that creates reconnect/close loops and also
  prevents stable ADB recovery.

2026-08-10 clean retry result:

- Fedora-side prerequisites are healthy: `frps.service` is active and
  `127.0.0.1:7000` accepts TCP; router DNAT `2228 -> 192.168.123.71:7000`
  remains the non-NetBird phone fallback.
- Clean ADB retry after `adb kill-server` still produced no PKR110 device:
  `192.168.123.22:5555` returned no route/timed out,
  `100.87.37.3:5555` returned no route, and `127.0.0.1:15555` returned
  connection refused because phone FRPC is not registered.
- `phone-netbird-ensure` returned `reason=no-device`, so it cannot repair the
  phone while every ADB path is down.
- The Fedora source wrapper `~/.local/share/phone-frpc-smart.sh` now selects
  LAN only after both route and TCP probe to `192.168.123.71:7000` succeed;
  otherwise it probes `charlie1990.duckdns.org:2228` and falls back to retrying
  DuckDNS. This avoids fake/stale LAN routes and makes the fallback independent
  of NetBird.
- The latest deployable wrapper is also served as
  `http://192.168.123.71:9829/frpc_smart.sh.new`; updater:
  `http://192.168.123.71:9829/frpc-smart-update.sh`.
- One-time recovery still needs a phone-side root shell or USB ADB shell while
  all remote paths are down:
  `curl -fsSL http://192.168.123.71:9829/frpc-smart-update.sh | sh`
  on home Wi-Fi, or
  `curl -fsSL http://100.120.189.27:9829/frpc-smart-update.sh | sh`
  when the phone can reach the Tailnet file server.

2026-08-10 final recovery:

- PKR110 wireless debugging was paired through the router because Fedora could
  not ARP the phone directly while the router could. Working method:
  `sshpass -p admin ssh -N -L 127.0.0.1:<local>:192.168.123.22:<phone-port>
  admin@192.168.123.1`, then `adb pair/connect 127.0.0.1:<local>`.
- After recovery, stable ADB fallbacks were verified:
  `127.0.0.1:15555` via phone FRPC and `192.168.123.22:5555` via LAN ADB.
- Duplicate phone FRPC wrappers caused `proxy [phone-adb] already exists`.
  Use `/sdcard/Download/frpc-hard-restart.sh` to kill all stale
  `frpc_smart.sh` / `frpc.runtime.toml` processes, remove the lock, and start
  exactly one wrapper. Final verified process state: one
  `/data/local/tmp/frpc_smart.sh` and one `frpc.runtime.toml` child.
- The Magisk boot service `/data/adb/service.d/frpc.sh` is now durable and
  idempotent. It restores `/data/local/tmp/{frpc,frpc.toml,frpc_smart.sh}` from
  `/data/adb/phone-frpc/`, replays USB/ADB/NetBird baseline settings, and only
  starts FRPC when no wrapper is already running. This reduces phone reboot and
  `/data/local/tmp` cleanup risk.

2026-08-02 PKR110 wrapper fix:

- Root cause: `/data/local/tmp/frpc_smart.sh` selected LAN only from the
  presence of a `192.168.123.x` address on `wlan0`. During Wi-Fi/5G/VPN route
  transitions the phone could keep selecting `192.168.123.71:7000` while
  logging `dial tcp 192.168.123.71:7000: connect: no route to host`; FRP was
  not killed, it was alive but pointed at a temporarily invalid route.
- Fedora-side FRPS, token, and router DNAT were verified independently: a
  temporary local frpc login succeeded against both `127.0.0.1:7000` and
  `charlie1990.duckdns.org:2228`.
- Durable wrapper source is `~/.local/share/phone-frpc-smart.sh`; deployed to
  phone `/data/local/tmp/frpc_smart.sh`. It now writes
  `/data/local/tmp/frpc_smart.heartbeat` and selects LAN only when
  `ip route get 192.168.123.71` actually returns `dev wlan0`; otherwise it
  falls back to `charlie1990.duckdns.org:2228`.
- Reusable precise restart helper: `~/.local/share/phone-frpc-restart.sh`.
  Push it to `/sdcard/Download/phone-frpc-restart.sh` and run with root if
  duplicate wrappers appear. Avoid broad `pkill -f frpc_smart.sh` from inline
  ADB commands because it can terminate the current ADB shell before cleanup.
- Verified final state: exactly one wrapper and one frpc child, heartbeat
  present, and `~/.local/bin/phone-frp-fallback-status` reports
  `state=available` with `127.0.0.1:15555` listening.

One-time phone root-shell recovery command, when USB ADB or local terminal is
available:

```bash
cp /sdcard/Download/frpc_smart.sh.new /data/local/tmp/frpc_smart.sh 2>/dev/null || true
chmod 0755 /data/local/tmp/frpc_smart.sh
chown root:root /data/local/tmp/frpc_smart.sh
pkill -f /data/local/tmp/frpc 2>/dev/null || true
pkill -f /data/local/tmp/frpc_smart.sh 2>/dev/null || true
/system/bin/sh /data/local/tmp/frpc_smart.sh >/data/local/tmp/frpc.log 2>&1 &
```

Verify from Fedora:

```bash
adb connect 127.0.0.1:15555
adb -s 127.0.0.1:15555 shell 'su -c "id; ps -A -o PID,ARGS | grep -E '\''frpc|frpc_smart'\'' | grep -v grep"'
```

## Restart

```bash
# 客户端
systemctl --user restart frpc

# 服务端（需 sudo）
sudo systemctl restart frps
```

## Known Issues

- FRP 代理注册成功不保证 Windows 本地转发正常
- `frpc.toml` 中 `fedora-console-18080` 必须指向本地 ttyd `127.0.0.1:8080`，不是 `19092`（桌面 PiP）
- 优先用 Tailscale 直连绕过 FRP
- 2026-08-10 resolved phone fallback risk: wireless-debug recovery restored
  durable phone FRPC. Current verified ADB paths are FRP
  `127.0.0.1:15555`, LAN `192.168.123.22:5555`, and NetBird
  `100.87.37.3:5555` when NetBird is connected. If this regresses after a
  phone reboot, first inspect duplicate `frpc_smart.sh` wrappers and the Magisk
  boot service `/data/adb/service.d/frpc.sh`; do not assume router CPU or
  conntrack exhaustion.
