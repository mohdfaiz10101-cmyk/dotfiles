# Runbook: DuckDNS DDNS

DuckDNS 动态域名更新，映射 `charlie1990.duckdns.org` 到路由器 WAN IP。

## Desired State

- `duckdns-update.timer` — 每 300s 触发 `wan-ip-monitor.sh`
- `wan-ip-monitor.sh` 读取路由器 `wan0_ipaddr` 并提交给 DuckDNS
- 域名 `charlie1990.duckdns.org` 解析到路由器真实 WAN IP
- On PDCN/home Wi-Fi, `wan-ip-monitor.sh` also keeps the Fedora compatibility
  alias `192.168.123.71/24` present on the active PDCN device because router
  DNAT rules for public services still target `.71`.
- Public endpoint checks include Hermes `:8648` and Hermes WebUI `:19976`.

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
- 2026-09-07: `19976` failed because Fedora's PDCN interface had only
  `192.168.123.209/24` while router DNAT still targeted `192.168.123.71`.
  Added persistent `192.168.123.71/24` to NetworkManager connection `PDCN`,
  updated `wan-ip-monitor.sh` to reapply that alias automatically, and added
  `charlie1990.duckdns.org:19976` to endpoint checks.

## 2026-10-22 OpenWrt / ZXHN public Hermes repair

- Working IPv4 path: `charlie1990.duckdns.org:19976` -> ZXHN F650
  WAN `125.110.234.23` -> modem port mapping `Hermes19976` TCP
  `19976 -> 192.168.1.4:19976` -> OpenWrt redirect `Hermes-19976`
  `19976 -> 192.168.5.144:19976` -> Fedora Hermes entry.
- Modem LuCI `http://192.168.1.1/cgi-bin/luci` is reachable through OpenWrt.
  Login POST uses `username` and `psd`; authenticated menu JS is
  `/luci-static/resources/js/main.js`. The user account DOES expose port mapping;
  do not infer restricted permissions merely from the landing page.
- Supported APIs: GET `/admin/settings/gwinfo?get=all` (`WANIP`), GET
  `/admin/settings/pmDisplay`, POST `/admin/settings/pmSetSingle` with page CSRF
  `token`, `op=add`, `srvname`, `client`, `protocol=TCP`, `exPort`, `inPort`.
  Read back `pmDisplay`: `enable=1`, `retVal=0` from add is not enough by itself.
- Credentials: private file `~/.local/share/credentials/zxhn-f650.json` (0600).
  Default WAN-reader: `~/.local/bin/zxhn-wan-ip` (no credential output).
  Both `wan-ip-monitor.sh` and `duckdns-full-monitor.sh` use it when an active
  NetworkManager profile starts with `OpenWrt`; keep prior DNS if reading fails.
- Disabled `duckdns-aaaa-follow.timer`: its published ChinaNet-side IPv6 was not
  verified from cellular. Cleared DNS records and immediately restored the verified
  A record; authoritative/public resolver confirms no AAAA. Do not republish AAAA
  until tested from a genuinely external IPv6 client.
- Do NOT equate a delegated global LAN prefix with non-routable IPv6, or cross-LAN
  failure with definitive ISP filtering. Prior Hermes conclusions overreached.
- Verified physical PKR110 via ADB `192.168.2.11:5555`, Wi-Fi disabled: curl -4
  to the DuckDNS hostname returned HTTP 200, cellular local `100.72.90.26`, peer
  `125.110.234.23`. Earlier interface-bound cellular `100.104.152.176` also
  returned HTTP 200. LAN hairpin to the public IPv4 still times out; this is
  separate from the working external path.
- OpenWrt DHCP reservation `dhcp.hermes_fedora`: MAC `ea:cd:2a:97:28:c2`,
  fixed `192.168.5.144`; backup `/etc/config/dhcp.before-hermes-public-20261022`.
- Phone probes must rediscover active rmnet interface each run: Android changes
  `rmnet_data5` to `rmnet_data4`; a vanished interface gives immediate
  `Network is unreachable` and does not establish a service outage.

- Final browser verification: PKR110 Wi-Fi state `0` at both probe and screenshot;
  `DuckDNS_5G http=200 local=100.87.230.179 peer=125.110.234.23`.
  Screenshot shows 5G/4G status (no Wi-Fi) and the rendered Hermes chat UI.
  Evidence: `~/.local/state/openwrt-public/phone-5g-hermes.png`.
- After Wi-Fi re-enable, phone joined OpenWrt at `192.168.5.211:5555` (ADB).
  Added dnsmasq `dhcp.hermes_duckdns` domain record:
  `charlie1990.duckdns.org -> 192.168.5.144` on OpenWrt only. Phone Wi-Fi
  curl to the same hostname returned HTTP 200 with peer `192.168.5.144`.
  Public resolver `1.1.1.1` still returns A `125.110.234.23`, no AAAA.

## 2026-10-23 DDNS与LAN回环纠错
默认读取光猫WAN，禁止透明代理出口回显覆盖。OpenWrt专用hairpin规则支持
19976/8648/18300/18094，跟随wan-ip-monitor.sh从光猫读取的WAN IPv4。
本次蜂窝与Wi-Fi同域名19976均实测200；原生phone FRP支持两网络。
详细根因、脚本及证据：`hermes-network-evidence.md`。
