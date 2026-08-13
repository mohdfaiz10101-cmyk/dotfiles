# Runbook: Network Scenario Monitor

Unified monitor for desktop network, phone network, proxy chain, system
performance, and phone-desktop communication.

## Desired State

- Script: `~/.local/bin/network-scenario-monitor`
- PKR110 repair orchestrator: `~/.local/bin/phone-network-stabilize`
  with `fix`, `check`, and `status` modes. It is the first command to run for
  combined NetBird/FRP/LAN ADB/mihomo/Play/DuckDNS/Kuma drift.
- PKR110 state lock timer: `phone-network-stabilize.timer`, every 5 minutes.
  It runs `status` mode to refresh evidence and keep the low-risk baseline
  locked without repeatedly restarting mihomo or other heavier components.
- Timer: `network-scenario-monitor.timer`
- Dashboard: `network-monitor-dashboard.service`, open
  `http://127.0.0.1:19979/`, LAN `http://192.168.123.71:19979/`, or
  Tailscale `http://100.120.189.27:19979/`.
- Interactive panel: `http://127.0.0.1:19979/actions`,
  `http://192.168.123.71:19979/actions`, or
  `http://100.120.189.27:19979/actions`. It supports only bounded actions:
  immediate capture, ntfy test notification, monitor restart, and Kuma restart.
- Latest machine state: `~/.local/state/network-scenario-monitor/latest.json`
- Latest AI-readable summary: `~/.local/state/network-scenario-monitor/latest.md`
- Latest PKR110 repair state:
  `~/.local/state/phone-network-stabilize/latest.json`
- Prometheus/Telegraf-compatible metrics:
  `~/.local/state/network-scenario-monitor/metrics.prom`
- Event log: `~/.local/state/network-scenario-monitor/events.jsonl`
- Phone inventory config:
  `~/.config/network-scenario-monitor/phones.json`. Each entry has
  `id`, `label`, `serials`, and optional `optional`. Optional phones are still
  measured when reachable, but being offline does not make the overall state
  degraded.
- Notification path: local ntfy topic `charlie-network`, only when the
  top-level classification changes, when a degraded state persists for 10
  minutes, or as a healthy heartbeat every 30 minutes. Use the dashboard action
  panel to send a manual test notification. Publishing uses
  `~/.local/bin/ntfy-send network` so ntfy authentication stays outside the
  monitor state and runbook. Network notifications set `NTFY_ACTIONS` with
  three Android-compatible buttons: dashboard view, quick recapture, and Hub
  `goose_aider` diagnosis. Keep it to three actions; ntfy rejects larger
  action sets.

## Scenarios

- `home_wifi_lan`: desktop or phone is on home `192.168.123.0/24`.
- `portable_or_other_wifi`: phone is on Wi-Fi but not home LAN. Current known
  examples include Tank phone hotspot `TANK3_5845` with PKR110 on
  `192.168.227.0/24`, and portable Wi-Fi such as `MIFI-C3BB`.
- `cellular_5g`: phone default network appears cellular.
- `non_lan_with_tailnet_available`: desktop is not on home LAN but Tailnet is
  present.

## Checks

- Desktop: default route, gateway ping, direct HTTPS, proxied HTTPS, DuckDNS DNS,
  DuckDNS SSH TCP, local proxy ports, core services, ntfy/Workbench/FRP ADB,
  CPU/load/memory/swap/disk/PSI.
- Phones: ADB reachability across FRP/LAN/Tailscale serials, network interface
  scenario, Android global HTTP proxy, ping excerpts, phone-to-desktop ntfy and
  clipboard ports, DuckDNS SSH reachability.
- Communication: ADB, ntfy LAN, clipboard receiver, FRP ADB, Workbench.

## Commands

```bash
network-scenario-monitor capture
network-scenario-monitor status | jq '.classification'
network-scenario-monitor metrics | head
cat ~/.local/state/network-scenario-monitor/latest.md
systemctl --user is-active network-scenario-monitor.timer
systemctl --user is-active network-monitor-dashboard.service uptime-kuma.service
~/.local/bin/ntfy-send network "网络测试" "network topic test"
curl -X POST http://100.120.189.27:19979/ntfy/recover?op=capture
```

## Dual-Stack Design

Use two monitoring layers together:

1. Primary AI layer: `network-scenario-monitor`
   - Purpose: scenario-aware diagnosis for this machine and phones.
   - Strengths: knows 5G vs portable Wi-Fi vs home LAN, ADB/FRP/Tailscale,
     phone-to-desktop ports, proxy ports, Workbench, ntfy, and system pressure.
   - Outputs: compact JSON, Markdown, JSONL event history, and `metrics.prom`.
   - Notification: ntfy only on top-level classification change, to reduce
     noise.

2. Standards fallback layer: Uptime Kuma / Prometheus Blackbox / Telegraf
   - Purpose: independent blackbox availability and time-series history.
   - Uptime Kuma service exists as `uptime-kuma.service` and listens on
     `0.0.0.0:3002` when started. Use local `http://127.0.0.1:3002/`, LAN
     `http://192.168.123.71:3002/`, or Tailscale
     `http://100.120.189.27:3002/` for visual status pages and simple
     webhook/ntfy notifications.
   - Prometheus Blackbox Exporter pattern: probe HTTP, DNS, TCP, ICMP endpoints
     externally; it should monitor `charlie1990.duckdns.org` ports, LAN ports,
     and public service URLs without trusting local app internals.
   - Telegraf pattern: collect ping latency/loss and optionally use `exec` to
     read `network-scenario-monitor metrics`.

The fallback layer should not replace the AI layer. It should confirm whether
the AI layer itself, local scripts, or local ADB assumptions are wrong.

## Phone / Windows / Fedora Closed Loop

Windows is a valid LAN-side monitor and repair node, but it should be treated
as a peer observer rather than the final external truth source. The intended
closed loop is:

- Phone probes Windows and Fedora from the user's real network path.
- Windows probes Fedora over LAN/Tailnet and can run bounded repair actions
  when Fedora is reachable from LAN but a Fedora service is down.
- Fedora probes phone and Windows, owns local service repair, and publishes the
  unified network state.

Repair actions must use quorum and cooldowns:

- If Phone can reach Windows but not Fedora, and Windows also cannot reach
  Fedora service ports, repair Fedora service/network first.
- If Phone cannot reach Windows or Fedora but Windows can reach Fedora, treat
  the phone network/VPN/proxy path as suspect; do not restart Fedora.
- If Fedora and Windows can reach each other but public/DuckDNS probes fail,
  repair router/DuckDNS/FRP public ingress, not app services.
- If all three lose each other, assume home LAN/router/power/network outage and
  notify; do not start a restart loop.
- Use at least a 5-15 minute cooldown for disruptive actions such as restarting
  NetBird, FRP, router NAT, or heavy web services.

This LAN closed loop improves self-healing inside the home network. It does not
replace an external VPS/blackbox monitor, because Windows and Fedora share the
same router, ISP, and power/network failure domain.

Interop entrypoints:

- Fedora state/action hub: `network-monitor-dashboard.service`
  `http://127.0.0.1:19979/mesh`
- Shared machine state: `GET /mesh/state`
- Bounded repair bus: `POST /mesh/action`

Every node should expose or consume the same three capability classes:

- `probe`: check the other two nodes from the current node's real route.
- `report`: publish result back to ntfy `charlie-network` and/or the mesh hub.
- `repair`: call only whitelisted actions; never accept arbitrary shell
  commands over HTTP/ntfy.

Initial Fedora mesh action whitelist:

- `target=fedora action=capture`: run `network-scenario-monitor capture`.
- `target=fedora action=restart_monitor`: restart the monitor service only.
- `target=fedora action=restart_kuma`: restart the standards fallback UI.
- `target=fedora action=goose_repair`: create a bounded Hub diagnosis task.
- `target=phone action=frp_status`: run `phone-frp-fallback-status`.
- `target=phone action=netbird_ensure`: run `phone-netbird-ensure`.
- `target=windows action=probe`: placeholder until the Windows peer agent is
  installed; no remote Windows repair is enabled before that.

Windows peer agent design:

- Start with PowerShell + Task Scheduler, not a heavy new platform.
- Probe Fedora LAN/Tailnet/DuckDNS ports, phone-facing routes, Windows
  OpenSSH, and NetBird/Tailscale state.
- Report compact JSON to the Fedora mesh hub or ntfy.
- Repair only bounded local Windows actions such as restarting OpenSSH,
  reconnecting its overlay client, or calling Fedora `/mesh/action` when quorum
  says Fedora service repair is appropriate.
- Installer generated on Fedora:
  `~/.local/share/network-scenario-monitor/windows-peer-agent/install-windows-peer-agent.ps1`.
- Default install command on Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows-peer-agent.ps1 -HubUrl http://192.168.123.71:19979
```

- The installed task is `CharlieMeshWindowsPeerAgent`; it runs every 2 minutes,
  writes `C:\ProgramData\CharlieMesh\latest.json`, and reports to
  `POST /mesh/report`.
- Current SSH status on 2026-08-02: Fedora could not deploy automatically:
  `100.91.93.99:22` timed out, `127.0.0.1:2222` timed out during banner
  exchange, and `192.168.123.136:22` reset the connection. Treat Windows as
  report-only/missing-agent until OpenSSH login is stable or the installer is
  run locally on Windows.

Phone peer design:

- Use existing logged wrappers first: `adb-record`, `phone-webtty-route-probe`,
  `phone-frp-fallback-status`, and `phone-netbird-ensure`.
- For broad phone network instability, run
  `~/.local/bin/phone-network-stabilize fix` before bespoke repairs. It
  normalizes always-on NetBird with lockdown off, keeps Android global HTTP
  proxy cleared by default, repairs mihomo if needed, checks DuckDNS public
  ingress, disables stale Kuma monitors, and writes a compact state file.
  Use `PHONE_FORCE_GLOBAL_PROXY=1` only for a temporary Play/GMS emergency
  recovery when direct Play UID probes fail but explicit proxy probes succeed.
- ADB repair channel priority is FRP `127.0.0.1:15555`, then LAN
  `192.168.123.22:5555`, then NetBird `100.87.37.3:5555`. NetBird must never
  be the primary channel when repairing NetBird itself.
- In `portable_or_other_wifi` / Tank hotspot mode, `lan_adb=false` is expected
  because the phone is not on `192.168.123.0/24`. Health should be judged from
  FRP ADB, NetBird ADB, mihomo/Play probes, and DuckDNS public ingress.
- Current NetBird policy is overlay-only. Domestic games and ordinary Android
  apps should direct-route over the default network/mihomo DIRECT rules.
  Stock PKR110 NetBird v0.5.0 does not expose a reliable config-backed
  arbitrary per-app exclusion list; do not claim that Hermes can guarantee
  app-by-app NetBird selection without NetBird admin policy or an APK rebuild.
- The phone is the real user-path judge for mobile browser/WebTTY/Workbench
  usability. Do not declare mobile health from Fedora curl alone.
- Phone-triggered repair should go through ntfy action buttons or
  `/mesh/action`, so actions remain visible and bounded.

Recommended fallback monitors:

- Desktop public ingress: `charlie1990.duckdns.org:2225`,
  `:19888`, `:19899`, `:19900`, `:19902`, `:19903`, `:19904`, `:19906`.
- Desktop local services: `127.0.0.1:19888/buttons`,
  `127.0.0.1:19000/status`, `127.0.0.1:2586/v1/health`.
- Phone communication: `127.0.0.1:15555` TCP,
  `http://charlie1990.duckdns.org:19976/` as the Hermes 8787 auth-proxy
  public entry, and `192.168.123.71:2586` from phone-side probe.
- Network quality: ping `192.168.123.1`, `1.1.1.1`, and Tailnet peers; track
  average RTT and packet loss.

2026-08-10 correction:

- `19976` is Hermes WebUI auth proxy (`FRPS/FRPC -> 18999 -> 8787`), not the
  phone clipboard receiver. Monitor labels should use `hermes_auth_19976`.
- FRPS dashboard `127.0.0.1:7500` is not configured; use the `:7000` listener
  and `frpc.service` as FRP local liveness evidence.

Fallback enablement:

```bash
systemctl --user enable --now uptime-kuma.service
# open http://100.120.189.27:3002 from Tailnet and add monitors/ntfy notification manually
# open http://127.0.0.1:19979/standard for the local standards plan
```

Do not expose Uptime Kuma directly to the public Internet unless it is placed
behind the existing authenticated Hub/Workbench path.

## Uptime Kuma `:3002` Overlay Comparison

On 2026-07-17 the `:3002` Kuma instance was populated with a public local
status page:

- URL: `http://127.0.0.1:3002/status/network`

2026-08-10 cleanup:

- Disabled stale Kuma monitors `Tailscale · PKR110 legacy ping`
  (`100.108.28.44`) and `Public · Kuma 3002`. The former is a retired phone
  overlay address; the latter should not be publicly exposed. Leaving them
  active caused false red status unrelated to current DuckDNS/FRP health.
- Restarted `uptime-kuma.service` after DB update so the disabled monitors take
  effect immediately.
- LAN: `http://192.168.123.71:3002/status/network`
- Tailnet: `http://100.120.189.27:3002/status/network`
- Database backup before direct edits:
  `~/.local/share/uptime-kuma/kuma.db.bak-netbird-compare-*`

Monitor set:

- `NetBird · PKR110 overlay ping`: ping `100.87.37.3` from Fedora/Kuma; this
  checks Fedora → phone NetBird overlay reachability.
- `Tailscale · PKR110 legacy ping`: ping `100.108.28.44`; expected DOWN while
  the Android Tailscale client is disabled/not owning the VPN slot.
- `FRP · phone ADB tunnel 15555`: TCP port check
  `host.containers.internal:15555`. Use `host.containers.internal`, not
  `127.0.0.1`, because Kuma runs in a Podman container and container loopback is
  not the Fedora host loopback.

Read current evidence without opening the UI:

```bash
curl --noproxy '*' -fsS http://127.0.0.1:3002/api/status-page/network
curl --noproxy '*' -fsS http://127.0.0.1:3002/api/status-page/heartbeat/network
```

Important interpretation:

- Kuma can compare host-observed reachability over time, but a few minutes of
  heartbeats is not enough to prove long-term stability.
- NetBird is a full overlay check. FRP `15555` is only a control tunnel/TCP
  reachability check, not a general device overlay replacement.
- The FRP monitor may show historical DOWN entries before
  `host.containers.internal` was configured; judge current and post-fix
  heartbeats separately.

## Rules

- Do not store raw large logs or secrets in the monitor state.
- Keep probes bounded and low impact. The timer runs every two minutes at idle
  I/O priority.
- Live monitor state is evidence. Runbooks explain topology; they do not prove
  current health.

## Unified Notification Center / AI Handling Plan

The monitor stack should be treated as one observability pipeline, not separate
ad-hoc scripts:

1. `network-scenario-monitor` is the primary state collector. It classifies the
   current desktop scenario and every configured phone (`home_wifi_lan`,
   `portable_or_other_wifi`, `cellular_5g`,
   `non_lan_with_tailnet_available`) and writes JSON/Markdown/Prometheus state.
2. Phone perceived route quality comes from `phone-webtty-route-probe`, because
   server-side probes can misjudge LAN/NetBird/DuckDNS from the phone's actual
   network.
3. WebTTY perceived page load comes from `codex-webtty-perf-summary`, because
   service `/status` can be fast while real mobile page load is slow.
4. `mobile-ai-route-prewarm` keeps Workbench/WebTTY routes warm and provides
   current best-route advice for LAN, NetBird, DuckDNS, and phone-host paths.
5. `network-monitor-dashboard` is the unified notification/action center:
   `/` for summary, `/ai` for AI-readable state, `/metrics` for Prometheus,
   `/actions` for bounded recovery actions, and ntfy action buttons for
   dashboard, recapture, and Goose diagnosis.
6. Uptime Kuma on `:3002` remains the standards/blackbox comparison layer. It
   should confirm public/LAN/Tailnet reachability independently, but should not
   replace the AI scenario monitor.

Notification policy:

- Topic: `charlie-network` through `~/.local/bin/ntfy-send network`.
- Send only on top-level state change, degraded repeat after 10 minutes, or
  healthy heartbeat after 30 minutes.
- Also send when the failure signature changes while the top-level state stays
  the same, for example `tablet ADB offline` becoming
  `root disk full + tablet ADB offline`. Otherwise a new root cause can be
  hidden behind an unchanged `degraded` label.
- Keep Android ntfy actions to three buttons: dashboard, recapture, AI
  diagnosis.
- AI diagnosis entry is the dashboard Goose action; it receives
  `latest.md` and bounded `latest.json` rather than raw logs.

Coverage matrix:

| Layer | Home Wi-Fi/LAN | Portable Wi-Fi | 5G | Non-LAN with overlay |
| --- | --- | --- | --- | --- |
| Desktop network | gateway, direct/proxy HTTPS, DuckDNS, FRP, proxy ports | default route, direct/proxy HTTPS, DuckDNS | same via current route | Tailnet/NetBird reachability |
| Phone network | ADB LAN/FRP, `wlan0`, LAN ntfy/clipboard | ADB fallback, non-home Wi-Fi, public/overlay route | FRP/DuckDNS or overlay, `rmnet*`, latency to desktop/public DNS | NetBird/Tailscale/FRP fallback |
| Proxy | Fedora Mihomo ports `7890,7892-7897`, env proxy | same | same plus phone proxy/vpn state | same plus overlay route |
| Communication | ADB, ntfy, clipboard receiver, Workbench, WebTTY | public/overlay ntfy and WebTTY | FRP ADB, public ntfy, DuckDNS WebTTY | Tailnet/NetBird routes first |
| Performance | load, memory, swap, disk, PSI | same | same | same |

## Robustness changes (2026-07-18)

- Phone inventory is now config-driven via
  `~/.config/network-scenario-monitor/phones.json`; add future phones there
  instead of editing the script. Mark devices such as a rarely-used tablet with
  `"optional": true` so their absence is visible but not treated as a blocking
  failure.
- `network-scenario-monitor` Workbench communication probe must include
  `X-Device-Code: w19900422`; otherwise `/buttons` returns `401` and creates a
  false communication warning.
- Android global HTTP proxy is now promoted into the phone network object as
  `network.global_http_proxy`; do not leave it hidden only in raw ADB output.
- Classification now includes desktop communication probe failures and hard
  system-performance failures: writable data filesystem usage `>=95%` and
  memory available `<1024MB`. On Fedora Silverblue/composefs, `/` is an
  immutable image and can normally show `100%` full (`composefs 59M/59M`);
  do not alert on `/`. Monitor the writable Btrfs path
  `/var/home/charlie` / `/var` instead, and expose `/` only as
  `disk_root_image.ignored_for_alerts=true`.
- Notification dedupe now tracks the sorted failure signature in addition to
  the top-level level, so new or resolved root causes can notify immediately
  even if the level remains `degraded`.
- Current verification command:

```bash
python3 -m py_compile ~/.local/bin/network-scenario-monitor
network-scenario-monitor capture --no-notify | jq '{classification,desktop:{comms:.desktop.comms,performance:.desktop.performance},phones:[.phones[]|{id,reachable,classification,proxy:(.network.global_http_proxy? // ""),paths}]}'
```

## Failure History: Google direct probe false degradation (2026-07-18)

Symptom: `network-scenario-monitor` repeatedly classified the host as
`upstream_direct_degraded` because direct HTTPS to
`https://www.google.com/generate_204` timed out, while direct HTTPS to
`https://www.gstatic.com/generate_204` and
`https://connectivitycheck.gstatic.com/generate_204` succeeded and proxy HTTPS
also succeeded.

Fix applied: changed `~/.local/bin/network-scenario-monitor` direct HTTPS probe
from `https://www.google.com/generate_204` to
`https://connectivitycheck.gstatic.com/generate_204`.

Verification:

```bash
python3 -m py_compile ~/.local/bin/network-scenario-monitor
network-scenario-monitor capture
cat ~/.local/state/network-scenario-monitor/latest.md
```

Expected post-fix evidence: `direct HTTPS` is `ok: True` with `204`; if only
`phone:tablet:adb` remains and the tablet is intentionally offline, desktop and
PKR110 networking are healthy.

## Mobile AI route prewarm / channel scoring (2026-07-18)

- Script: `~/.local/bin/mobile-ai-route-prewarm`
- Timer: `mobile-ai-route-prewarm.timer`, every 2 minutes
- State: `~/.local/state/mobile-ai-route-prewarm/latest.json`
- Workbench API: `http://127.0.0.1:19888/api/route-best`

Purpose: keep Workbench/WebTTY HTTP paths warm and maintain a recent best-route
snapshot across local, LAN, NetBird, DuckDNS, and current phone-host paths. It
uses bounded HTTP probes only; it does not open terminal WebSockets or create
tmux clients.

Verification:

```bash
systemctl --user is-active mobile-ai-route-prewarm.timer mobile-ai-workbench.service
curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/route-best |
  jq '{ok,generated_at,speed_summary,advice}'
```

## WebTTY real browser load performance (2026-07-18)

Service health and `/status` latency are not enough to prove phone perceived
page speed. Codex WebTTY pages now include `codex_web_perf_beacon`, which posts
browser Navigation Timing once after page load:

- Raw logs: `~/.local/state/codex-webtty-perf/account-N.jsonl`
- Summary timer: `codex-webtty-perf-summary.timer` every 5 minutes
- Summary: `~/.local/state/codex-webtty-perf/summary.json`

Use P95 and slow-count from this summary when deciding whether WebTTY loading is
actually improving. Treat repeated `load_p95_ms >= 2500` as an optimization
candidate for UI script reduction, route selection, or cache/preload changes.

## Phone-side WebTTY route probe (2026-07-18)

Server-side probes can misjudge phone routes: `19000-19007` are loopback-only
Codex gates, and local Python/urllib can accidentally honor `HTTP_PROXY`. Use
phone-side evidence for phone perceived route quality:

- Script: `~/.local/bin/phone-webtty-route-probe`
- Timer: `phone-webtty-route-probe.timer`, every 2 minutes
- State: `~/.local/state/phone-webtty-route-probe/latest.json`
- It uses `~/.local/bin/adb-record --tag phone-webtty-route-probe -- ...` and
  Android `/system/bin/curl` to test LAN, NetBird, and DuckDNS WebTTY external
  ports.

Verification:

```bash
systemctl --user is-active phone-webtty-route-probe.timer
cat ~/.local/state/phone-webtty-route-probe/latest.json | jq '{generated_at,items}'
```

## WebTTY USB reverse fallback (2026-07-18)

When the phone is USB-connected, use adb reverse as the strongest local fallback
for Workbench/Codex WebTTY. It avoids router hairpin, DuckDNS, FRP, Wi-Fi client
isolation, and NetBird/VPN routing quirks.

- Script: `~/.local/bin/webtty-usb-reverse-ensure`
- Timer: `webtty-usb-reverse-ensure.timer`, every 1 minute
- State: `~/.local/state/webtty-usb-reverse/latest.json`
- Ports reversed: `19888`, `19899`, `19900`, `19902`, `19903`, `19904`,
  `19905`, `19906`, `19907`

Phone URLs over USB reverse:

- Workbench: `http://127.0.0.1:19888/?device=w19900422`
- C1: `http://127.0.0.1:19899/?device=w19900422`
- C2: `http://127.0.0.1:19900/?device=w19900422`
- C3-C8: matching external ports `19902` through `19907`.

Verification:

```bash
systemctl --user is-active webtty-usb-reverse-ensure.timer
cat ~/.local/state/webtty-usb-reverse/latest.json | jq '{ok,serial,ports}'
adb -s <usb-serial> shell "curl -m 8 -s -o /dev/null -w 'code=%{http_code} total=%{time_total}\n' http://127.0.0.1:19899/status?device=w19900422"
```

## Failure History: WebTTY smart route pointed phones to loopback/internal ports (2026-07-18)

Symptom: phone could not open account pages from 5G/other networks after a recovery flow because links used `127.0.0.1` or internal `19000-19007` gate ports.

Rules now enforced:

- `127.0.0.1:<external-port>` is USB `adb reverse` only. It is not a 5G/public URL.
- `19000-19007` are Fedora loopback-only gates and must never be used by phone LAN/NetBird/DuckDNS links or Workbench iframes.
- Phone-visible account ports are `19899`, `19900`, `19902`, `19903`, `19904`, `19905`, `19906`, `19907`.
- Workbench `/go/cN?mode=smart` should prefer DuckDNS for universal 5G/off-LAN reachability. LAN is valid only on home Wi-Fi; NetBird is valid only when Android NetBird is actually connected.
- Workbench embedded account frames should use the external account ports even when Workbench itself was opened through USB `127.0.0.1:19888`.

Verification from the real phone, not only Fedora curl:

```bash
# 5G/off-LAN universal route
~/.local/bin/adb-record --tag webtty-5g-public-all -- -s ff3ef385 shell '
for p in 19899 19900 19902 19903 19904 19905 19906 19907; do
  printf "$p "
  curl -L -m 8 -s -o /dev/null -w "code=%{http_code} total=%{time_total}
"     "http://charlie1990.duckdns.org:$p/status?device=w19900422"
done'

# Smart redirect must not point to 127 or 19000-19007.
for k in c1 c2 c3 c4 c5 c6 c7 c8; do
  curl -sI -H 'X-Device-Code: w19900422' "http://127.0.0.1:19888/go/$k?mode=smart" | rg -i '^location:'
done
```

On 2026-07-18, phone 5G public DuckDNS checks returned HTTP 200 for all C1-C8 in about 160-345ms. Android Chrome screenshot confirmed `http://charlie1990.duckdns.org:19899/` loaded the C1 terminal on 5G. Wi-Fi hairpin via DuckDNS may show Chrome `ERR_CONNECTION_RESET`; in that scenario use LAN `192.168.123.71:<external-port>` while on home Wi-Fi, or 5G DuckDNS when off-LAN.
