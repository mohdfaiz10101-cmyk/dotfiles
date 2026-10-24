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

## 2026-10-24 公网入口清单：桌面投屏 19986 + Muse WebTTY 19985 + 知伴 19984

### 桌面实时投屏（noVNC + wayvnc，19986，2026-10-24 新建并实测）
- **地址**：`https://charlie1990.duckdns.org:19986/vnc.html?autoconnect=1&resize=scale`
- **凭据**：`~/.local/share/credentials/wayvnc-desktop.env`（`charlie` / 12位hex）。
  这是**可实时操作的画面**（鼠标/键盘/触控回传），不是终端、不是截图。
- 链路：`https://charlie1990.duckdns.org:19986` → 光猫映射 `MuseDesktop19986`
  → OpenWrt `zone_wan_prerouting` DNAT `19986 -> 192.168.5.144:19986`
  → Caddy `wayvnc-desktop-https.service`（TLS 终止 + noVNC 静态文件）
  → `/websockify` → wayvnc `127.0.0.1:5900` → sway 输出 HDMI-A-1 1920x1080。
- 新增文件：
  - `~/.config/systemd/user/wayvnc-desktop.service`（`--websocket` 必须加）
  - `~/.config/systemd/user/wayvnc-desktop-https.service`
  - `~/.config/caddy/wayvnc-desktop.Caddyfile`
  - `~/.config/wayvnc/config`（`enable_auth=true`，`address=127.0.0.1`）
  - noVNC 客户端：`~/www/novnc/`（noVNC v1.5.0）
- wayvnc 只绑 `127.0.0.1:5900`，认证由 wayvnc 自己承担，Caddy 不接管。

#### 19986 验收证据（2026-10-24）
| 项 | 结果 |
|---|---|
| noVNC 页面 `/` `/vnc.html` `/core/rfb.js` | 200 / 200 / 200 |
| Caddy→wayvnc WebSocket `/websockify` | **101** |
| wayvnc 捕获 | `Capturing output HDMI-A-1` 1920x1080 |
| 手机蜂窝 `--resolve 125.110.234.23` | **200** |
| OpenWrt 经域名访问 | **200** |

- **坑1：wayvnc 必须加 `--websocket`**。不加时它讲裸 RFB，noVNC 连上后
  Caddy 转发返回 502。表现为「页面能开、画面黑屏」。
- **坑2：手机 DNS 污染会伪装成服务故障**。本轮 `--interface rmnet_data6`
  普通请求全 000，连此前实测 200 的 19984 也 000；`curl -v` 显示手机解析到
  `195.245.219.35`（mihomo 出口）和 OpenWrt IPv6。
  **加 `--resolve charlie1990.duckdns.org:19986:125.110.234.23` 后立刻 200。**
  判据：`nc -z` 到 WAN IP 端口 OK 而 HTTPS 000 ⇒ 是 DNS/路由，不是 DNAT。
- **坑3：`--noproxy '*'` 绕不过系统 tun 路由**。手机默认路由走 `vgate0`
  (172.30.221.70)，必须 `--interface rmnet_data6` 才走蜂窝。
- **坑4：直连 LAN IP `https://192.168.5.144:19986/` 返回 000**，而经域名 200。
  同 19985：Caddy 站点块按 SNI 匹配，不带 SNI 的 IP 请求落不到站点块。
- noVNC 静态资源用了 `@assets` 长缓存；根路径只 rewrite `/`，
  不要写 `rewrite *`（会把 `/core/*.js` 一起改掉）。
- **未完成项**：手机浏览器里的 noVNC 画面未截图——PKR110 反复锁屏，
  且按用户规则不解锁手机。HTTP 200 + WS 101 + wayvnc 捕获日志三层已证，
  首帧画面待用户自行打开确认。

### Muse WebTTY 公网 HTTPS 入口（19985，2026-10-24 新建并实测）
- **地址**：`https://charlie1990.duckdns.org:19985/muse/`
- **这是 shell 终端，不是浏览器界面**。用户明确反馈「进入后是 terminal，
  一点东西都没有我怎么用」——给地址时必须说明它给的是命令行。
- **凭据**：`~/.local/share/credentials/muse-ttyd.env`（`MUSE_TTYD_USER` /
  `MUSE_TTYD_PASS`）。密码已于 2026-10-24 按用户要求改为用户自选值，
  旧值备份 `muse-ttyd.env.bak-before-passwd-20261024`。Realm 显示 `ttyd`。
- 链路：`https://charlie1990.duckdns.org:19985` → 光猫 WAN `125.110.234.23`
  → 光猫端口映射 `MuseWebTTY19985`（`exPort=inPort=19985` → `192.168.1.4`）
  → OpenWrt `zone_wan_prerouting` DNAT `19985 -> 192.168.5.144:19985`
  → Caddy `muse-ttyd-https.service`（`:19985`，TLS 终止）
  → ttyd `127.0.0.1:7790`（base path `/muse`，原生 Basic Auth）。
- 新增文件：
  - `/var/home/charlie/.config/caddy/muse-ttyd.Caddyfile`（0600）
  - `/var/home/charlie/.config/systemd/user/muse-ttyd-https.service`（0600，enabled）
  - 备份 `Caddyfile.bak-before-muse-19985-20261024`、
    `charlie-assistant-https.service.bak-before-muse-19985-20261024`、
    OpenWrt `/etc/config/firewall.bak-before-muse-19985-20261024`
- Fedora firewalld 已 `--add-port=19985/tcp`（permanent + reload）。
- **ttyd 仍只绑 `127.0.0.1:7790`**：公网暴露的只有 Caddy 的 TLS 层，
  shell 本身不直接对 WAN/LAN 监听。认证由 ttyd 原生 `-c` 承担，
  Caddy 不解码、不接管认证。
- Caddy 用 `read_timeout 0 / write_timeout 0`，避免长终端会话被读超时切断。
- 无明文 HTTP 监听，cleartext 无法触达 root-capable shell。

### 19985 验收证据（2026-10-24）
| 项 | 结果 |
|---|---|
| 无凭据 HTTPS | `401` |
| 带凭据 HTTPS | `200` |
| WebSocket upgrade `/muse/ws` | `101 Switching Protocols` |
| ttyd 监听地址 | `127.0.0.1:7790`（未变） |
| shell 身份（本地 entry） | `charlie@hermes-fedora` |
| OpenWrt DNAT 计数器 | 3 包 / 180 字节（真实流量） |
| 手机 5G Chrome（PKR110 Wi-Fi=0） | 弹出 ttyd 登录框，URL 与 realm 正确 |

- 手机蜂窝 root curl：`https_19985=401`、对照 `https_19984=200`，对端 `125.110.234.23`。
- 截图：`~/.local/state/muse-public-entry/phone-5g-muse-webtty-19985.png`（登录框）、
  `phone-5g-muse-webtty-19985-terminal.png`（登录后，TLS 盾标已出现）。
- **未完成项**：终端渲染出提示符的画面未取到——PKR110 在验证中途没电，
  WebSocket 建连后的首帧未截图。HTTP/101/TLS 三层已证，终端首帧仍待补一张图。
- **直连 WAN IP 不通是预期**：`https://125.110.234.23:19985/` 返回 000，
  光猫要求 SNI 匹配域名（19984 同样行为）。验证一律带 `--resolve` 或域名。

#### 故障：手机报 `Client sent an HTTP request to an HTTPS server.`（2026-10-24）

- **不是服务故障**：手机发的是**明文 HTTP**，TLS 层的 Caddy 直接回了这句。
  同期本地 HTTPS 三项全过（401 / 200 / WS 101）。
- **根因是 scheme 丢失**：给用户的地址若不带 `https://` 前缀，聊天软件/复制粘贴
  会把它当纯文本，手机浏览器默认按 `http://` 打开。
- **修不掉的部分**：该错误在 TLS 握手期产生，`handle_errors` / `{tls_error}`
  接不到（实测 `handle_errors` 无效果），也不能在 19985 上同端口挂明文
  跳转（Caddy 报 `cannot natively multiplex HTTP and HTTPS`），80 端口已被
  主 Caddy 占用。**只能在给地址时始终带 `https://`。**
- **已修掉的真实隐患**：Caddy 默认广告 `alt-svc: h3=":19985"`，而 **UDP/19985
  没做任何映射**（只开了 TCP），手机走 QUIC 必然失败。已加
  `servers { protocols h1 h2 }` 全局块去掉 h3 广告，复验 alt-svc 计数 = 0。
- 坑：`protocols` 在 Caddy 2.8 **只能放全局 `servers` 块**，写在站点块里
  validate 报 `unrecognized directive: protocols`。

### 19984 知伴 HTTPS 入口（原有，2026-10-24 复核仍有效）
- 链路：`https://charlie1990.duckdns.org:19984` → 光猫 WAN `125.110.234.23`
  → OpenWrt `zone_wan_prerouting` DNAT `19984 -> 192.168.5.144:19984`
  → Caddy `charlie-assistant-https.service`（`:19984`，h1/h2/h3）→ `127.0.0.1:18446`。
- 系统服务名：`charlie-assistant.service`（后端，环境变量
  `ASSISTANT_ORIGIN=https://charlie1990.duckdns.org:19984`）与
  `charlie-assistant-https.service`（Caddy，systemd --user，`assistant.Caddyfile`）。
- 证书为 `charlie1990.duckdns.org` 自有证书，非 Let’s Encrypt 自动签发。
- HTTP 明文 80 端口访问 19984 会得到 `400`（Caddy `auto_https off`），不是故障；
  手机/外网必须用 `https://`。
- 蜂窝实测（PKR110 Wi-Fi=0，root curl `--noproxy *`）：
  `https_19984=200`，同域名 `http_19976=200`，对端 `125.110.234.23`。
- LAN 回环已有 `Charlie-Assistant-HTTPS (reflection)` SNAT/DNAT，与 19976
  同套 hairpin 逻辑；FRP 侧 `frps.allowPorts` 也含 19180–19982 与 19976–19977。
- 注意：`frps.allowPorts` 含该段不等于已注册映射；19984 走的是路由器 DNAT，
  frpc.toml 里没有 19984 代理，两条路径不要混记。

### Muse WebTTY 公网入口（实测证据，2026-10-24 起已有）
- **已开通**：`https://charlie1990.duckdns.org:19985/muse/`，见上一节。
- `muse-ttyd.service` 仍只绑 `127.0.0.1:7790`；`openwrt-ttyd.service` 仍只绑 `127.0.0.1:7792`。
- `frpc.toml` 无 7790/7792 映射；`frps.allowPorts` 无这两个端口——**7792 至今没有公网入口**。
- 19985 走的是「光猫 DNAT + OpenWrt DNAT + 独立 Caddy」这条路由器路径，
  **不走 FRP**；不要把两者混记。
- Muse 的另一条路径是 tailnet（`100.118.209.71`）经 Fedora 跳板拿 root ADB，
  细节见 `hermes-network-evidence.md` 末尾「Muse 云端虚拟机访问 PKR110 root」。
- 不要为 `openwrt-ttyd`(7792) 新增 WAN 端口映射，除非用户明确要求；
  17990/17890 是 Muse 代理监听，不是公网服务。

### IPv6 / AAAA 现状
- 公网解析：A `125.110.234.23`，AAAA `240e:393:342e:efb0:8ede:f9ff:fe57:6934`（OpenWrt WAN 侧）。
- OpenWrt ip6tables 只对 `19976` 有 DNAT，**没有 19984**。若手机走 IPv6 或 HTTP/3，
  19984 不通属预期，未验证前不要宣称 19984 支持 IPv6。

### 2026-10-24 自愈通知降噪
- 单次UDP @8.8.8.8曾返回195.245.219.35，而公网WAN及HTTPS DNS为125.110.234.23；此现象不能直接判定域名记录真的被改。
- wan-ip-monitor.sh 改用Google DNS-over-HTTPS（先直连，失败走本机7890代理）；核验失败保留记录，不按空结果触发漂移修复。
- 保留DDNS更新timer和真实WAN变化通知；常规“DuckDNS 自愈”成功只写journal，不弹窗。
- 验证：bash -n通过，duckdns-update.service Result=success；加密DNS与光猫WAN一致。
