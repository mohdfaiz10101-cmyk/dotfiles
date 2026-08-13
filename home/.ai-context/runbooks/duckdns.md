# Runbook: DuckDNS DDNS

DuckDNS 动态域名更新，映射 `charlie1990.duckdns.org` 到路由器 WAN IP。

## Desired State

- `duckdns-update.timer` — 每 300s 触发 `wan-ip-monitor.sh`
- `wan-ip-monitor.sh` 读取路由器 `wan0_ipaddr` 并提交给 DuckDNS
- 域名 `charlie1990.duckdns.org` 解析到路由器真实 WAN IP

## Verify

```bash
systemctl --user is-active duckdns-update.timer
# 当前解析
dig +short charlie1990.duckdns.org
# 路由器 WAN IP
/usr/bin/sshpass -p admin ssh -o StrictHostKeyChecking=no admin@192.168.123.1 'nvram get wan0_ipaddr'
```

## Layered Resilience Monitor

`network-resilience-guard.timer` runs every minute and writes the latest
classification to `~/.local/state/network-resilience/latest.json` plus a
time-series at `~/.local/state/network-resilience/events.jsonl`. It checks the
Wi-Fi gateway, router WAN IP, DuckDNS DNS, direct HTTPS, HTTPS through Mihomo,
local FRPC/FRPS, Workbench and Codex C1/C6 gates. It sends a local ntfy notice
only when the failure layer changes.

```bash
systemctl --user is-active network-resilience-guard.timer
cat ~/.local/state/network-resilience/latest.json | jq
tail -n 20 ~/.local/state/network-resilience/events.jsonl | jq
```

Interpretation: `upstream-direct-degraded` means LAN/router/DuckDNS/FRP are
healthy but direct Internet HTTPS fails while Mihomo succeeds. This points to
the ISP/5G upstream path, not Mihomo or inbound DuckDNS forwarding. Prefer the
Tailscale Haven profiles during this state; DuckDNS remains a WAN fallback.

`network-resilience-maintenance.timer` runs every 15 minutes. It is deliberately
conservative: DNS faults trigger the existing WAN-based DuckDNS updater;
FRP-local faults can restart `frpc.service` at most once per 15 minutes; local
service faults invoke the WebTTY guard. It never reboots the Padavan router or
reconnects Wi-Fi automatically. The PDCN Wi-Fi profile has power save disabled
to reduce client-side latency spikes.

```bash
systemctl --user is-active network-resilience-maintenance.timer
nmcli -g 802-11-wireless.powersave connection show PDCN  # expected: disable
```

## Known Issues

- 不要从 Fedora 本机出口 IP 更新 DuckDNS（可能走代理/VPN）
- 必须读取路由器 `wan0_ipaddr` 提交，空 `ip=` 参数会清零 DNS 记录
- 60s 更新频率已被审计标记为资源浪费，已调整为 300s
- 2026-08-10: DuckDNS DNS itself was consistent across `8.8.8.8`,
  `223.5.5.5`, `1.1.1.1`, and `119.29.29.29`, all resolving to router WAN
  `125.110.209.185`. The failures were port-layer faults: `19867` had router
  DNAT to Fedora `:19867` but Fedora lacked a listener; fixed with
  `ntfy-public-19867.socket` proxying to `127.0.0.1:2586`. `18094` lacked
  router DNAT/hairpin; fixed with `18094 -> 192.168.123.71:5000` plus LAN
  MASQUERADE for `:5000`. Verified DuckDNS `8648`, `19976`, `19867`, and
  `18094` all returned HTTP 200.
