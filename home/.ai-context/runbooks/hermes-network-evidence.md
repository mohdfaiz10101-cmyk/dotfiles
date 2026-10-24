# Hermes 网络证据纠错（2026-10-23，d14ccbbd9ffe）

## 本轮证实的根因
- `wan-ip-monitor.sh` 被改为外部 IP 回显优先，透明代理出口 195.245.219.35 覆盖了光猫 WAN 125.110.234.23。`--noproxy` 不绕过 TUN、REDIRECT 或上游 OpenClash。
- 同一手机 Wi-Fi=0，错误域名目标 195.245.219.35 返回 000；`--resolve` 指向光猫 125.110.234.23 立即返回 HTTP 200，local=10.177.25.74。不能据前者断言运营商封锁。
- 已恢复 DDNS 从当前入口设备读取 WAN；读取失败保留 DNS，不使用代理出口。`zxhn-wan-ip` 是 OpenWrt 双 NAT 下默认来源。公共递归 DNS 不是权威 DNS。
- 手机旧 wrapper 只认识 192.168.123.0/24；现支持 OpenWrt 192.168.5.0/24 -> Fedora 192.168.5.144:7000。
- 手机独立回连路径为 DuckDNS:2228 -> 光猫:2228 -> OpenWrt:2228 -> Fedora:7000。服务端 bindPort=7000 不代表客户端外网也填7000。本轮补齐光猫和 OpenWrt 的2228映射。
- 原 USB forward 占用127.0.0.1:15555，阻止手机FRP注册同端口。已移到15655；USB桥15558只绑定loopback，转发15655。原15557为USB依赖备用入口，不能证明手机独立公网回连。

## 不再重复的误判
- 僵尸进程没有文件描述符，不能占监听端口；以ss/PID/unit核对归属，禁止按进程计数盲杀。
- 本机127.0.0.1端口200只证明本机后端；公网验收需蜂窝实际请求和浏览器截图。
- 代理路径200与直接公网200分别记录；curl退出码和HTTP状态都要检查，不能用最后一条grep的退出码代替整组成功。
- 不把旧会话推测沉淀为事实；本轮修复替代“光猫WANIP缓存、两个IP各有可用链路、运营商封锁”等未经证明的说法。

## 最小验证
1. `~/.local/bin/zxhn-wan-ip` 与公共DNS A一致；OpenWrt本地DNS允许域名映射192.168.5.144以绕过LAN发夹限制。
2. 用adb-record指定USB安全通道，记录wifi_on、蜂窝接口、local/remote IP、HTTP状态；root UID绕过规则需从MIHOMO链确认。
3. 原生FRP应出现phone-adb start proxy success；Fedora:15555监听者为frps，adb forward --list不得含tcp:15555。
4. `adb-record --tag verify -- -s 127.0.0.1:15555 shell 'su -c id'`证实root；该隧道不经过USB桥。
5. 手机恢复Wi-Fi后检查wrapper选择192.168.5.144:7000及同域名可用。

## 已更新规则的生效范围
SOUL.md用于新会话；不清空旧对话。现有会话每次pre-task调用hermes-memory-brief会优先命中本文件。用户若继续原对话，应先读取本文件并撤回原最终结论。

## 本轮验收与新的故障模式
- Android wrapper原 `trap cleanup EXIT INT TERM` 捕获TERM后不exit，旧8502仍存活，重启后与新实例互抢代理名。改为EXIT清理、INT/TERM执行exit；恢复脚本按精确wrapper/runtime进程清理并对未退出者补KILL。
- frps已确认来自蜂窝183.137.177.25的ARM64手机登录，原生phone-adb/phone-ssh/phone-haven-mcp注册成功。127.0.0.1:15555执行su -c id返回uid=0，USB forward列表仅15655。
- 5G手机Chrome已呈现DuckDNS:19976的Hermes页面，截图 `~/.local/state/hermes-network-review/phone-5g.png`；截图不能单独证明绕过代理，直连证据另以root curl local/peer确认。

## Wi-Fi/5G切换补全
- 5G重建蜂窝连接后，域名直连19976=200，local10.132.151.42 -> peer125.110.234.23；Google Play经既有mihomo返回302。
- Wi-Fi下缓存公网A会触发光猫发夹失败。OpenWrt已增加专用DUCKDNS_HAIRPIN链，仅LAN的19976/8648/18300/18094转向Fedora .144，并做对应SNAT；持久include `/etc/duckdns-hairpin.sh`。WAN IP保存在 `/etc/duckdns-public-ip`，wan-ip-monitor.sh随光猫WAN变化同步，不重载整个防火墙。
- Wi-Fi最终19976=200，local192.168.5.211 -> peer125.110.234.23；同域名切换可用。
- 旧tcp_ok用nc不带-z，连接成功后等待协议数据直至timeout，误把可达LAN判为失败。已改toybox nc -z -w，实测rc0；wrapper最终current/wanted192.168.5.144:7000。
- ZeroTier由另一Hermes任务配置，路由器当前ONLINE/OK、10.68.142.60；这不等于手机已入网或全网段路由已验收。不要与并发ZeroTier任务互相覆盖配置。
- Fedora Tailscale当前Running，但手机peer均Offline；不能作为已恢复的手机备用通道交付。

## ZeroTier后台只读核查（2026-10-23续）
- Fedora19910绑定0.0.0.0，LAN HTTP200；只有监听LAN/全接口且防火墙允许的服务才能经子网路由访问，localhost-only需要额外代理。
- 路由器ZT运行network b9a18a606ff8b427、dev zt3hhhfvci、10.68.142.60；防火墙zerotier zone却引用不存在的network ztmjfmfyq5。
- UCI zerotier.sample_config.join仍8056c2e21c000001，与runtime不一致；init脚本stop会删除networks.d/*.conf，因此重启后有加入错误网络风险。
- 当前手机未观察到ZT地址/到家庭LAN的ZT路由；不能交付5G整网段访问已完成。以上只读观察，未覆盖并发Hermes正在配置的ZeroTier。

## c016a43ccbca复核修复（2026-10-23）
- Via留空、路由器本机绑定ZT源curl当端到端、HTTP407推出redir的FCM407均为错误推断。402确实发生，但GET network.config.routes为空，不能编造默认路由占满1条或Android手动路由已可用。
- OpenWrt firewall zone原network=zt3hhhfvci错误（该字段需逻辑接口）；已改device=zt3hhhfvci。保留标准procd+list join，禁用无start函数的zerotier-autologin。
- 移除了/etc/firewall.user里无条件FORWARD到br-lan所有TCP的放行，使用正常ZT zone->LAN转发。
- 手机和Fedora的OpenClash黑名单旁路曾被会话清空；已恢复两MAC和.211/.144，runtime ipset及RETURN均确认，手机Google204。
- 免费电脑服务入口：`/etc/zt-fedora-gateway.sh`，只接受ZT接口到10.68.142.60的TCP1024-65535，DNAT到Fedora192.168.5.144同端口；SNAT到192.168.5.1确保回程。fw3 include持久加载，不涉及WAN公开入口。
- 手机2e8201bf45已加入并经Central授权，分配10.68.142.114。手机ZeroTier Android1.16.0有移动数据开关，已确认开启；无手工LAN路由输入项。
- 实测WiFi经ZT19910=200；切到5G后旧路径失效，断开/重连目标ZeroTier网络后，5gZT19910=200，local10.68.142.114 peer10.68.142.60；路由器peer DIRECT到手机蜂窝IPv6。不能承诺切网无缝，遇旧路径需重连。
- 这是电脑高位TCP服务入口，不是全LAN/全协议路由。完整LAN方案仍需可用的managed route或其他独立VPN。

## 统一地址与切网试验最终状态（2026-10-24）
- `/data/adb/zt-lan-shortcut.sh`及Magisk service.d启动脚本已部署。家里Wi-Fi安装仅10.68.142.60/32经192.168.5.1的优先路由，离开家移除；路由器服务网关也接受LAN输入并SNAT，家庭统一地址实测200，source192.168.5.211。
- 维护源`~/.local/share/phone-zerotier-lan-shortcut.sh`和`~/.local/share/openwrt-zerotier-fedora-gateway.sh`。脚本保留ZeroTier UID的Mihomo旁路，不改默认互联网路由。
- 自动stop/start ZeroTier服务的切网试验未通过，已从部署脚本撤回。当前脚本不启动/停止VPN；不要宣称全自动重连已完成。
- 调查确认Android onStartCommand需要long extra `com.zerotier.one.network_id`，但仅补参数仍不足以保证完整VPN生命周期，不把该试验当默认恢复步骤。
- 默认恢复用ZeroTier App的目标网络开关；手机原生FRP独立可用时可远程操作该界面。Wi-Fi保留LAN快捷入口，5G需应用保持已连接。

## 2026-10-24 ZeroTier后续已完成修复
旧结论“完整自动恢复未完成”由本次验收更新：新增手机本地限次数漫游守护，执行完整app重建+临时deviceidle白名单+带long extra的普通startservice，替代旧失败的服务stop/start方案。故障注入自动修复、两轮实际往返切网、5G19910/19976/8648均通过，手机Chrome已截图。详见 `~/.ai-context/runbooks/zerotier-roaming.md`。这是自动恢复，不保证既有长连接不断。

## Muse 云端虚拟机访问 PKR110 root 的可用路径（2026-10-24 实证）

- Muse VM `100.118.209.71` 已在同一 tailnet，且已能用公钥 SSH 到 Fedora `100.120.189.27:22`；journal 记录 `Accepted publickey for charlie from 100.118.209.71 ... SHA256:k7RqcEt9lyRSqrY0t000qvOpCUix6516LYcESkZFRX8`（对应 authorized_keys 注释 `hatch`，该行无 `command=`/`no-port-forwarding` 限制）。
- 结论：Muse **不需要直连手机**，走 Fedora 跳板即可拿到 root ADB。实测（从 Fedora 经 SSH 模拟 Muse 路径）：
  `ssh 100.120.189.27 'adb connect 127.0.0.1:15555; adb -s 127.0.0.1:15555 shell "su -c id; getprop ro.product.model"'`
  → `uid=0(root) ... context=u:r:magisk:s0` / `PKR110` / Android `16`。
- 直连前提不可行：手机 `/data/misc/adb/adb_keys` 只有 2 条公钥，其中一条是 Fedora `~/.android/adbkey.pub`。Muse VM 若自带 adb 直连 `100.120.189.27:15555` 会因客户端密钥未授权而 unauthorized；除非改用 Fedora 的 adb server。
- 手机侧真实拓扑：Wi-Fi 已关、走蜂窝（CHN-CT 100.70.15.51），手机 root  wrapper `/data/local/tmp/frpc_smart.sh` 以 shell(2000) 跑 `frpc -c /data/local/tmp/frpc.runtime.toml`，注册 `phone-adb`(本地5555→远端15555)、`phone-ssh`(本地8022→远端8022)、`phone-haven-mcp`(本地8730→远端18700)，服务端 `frp.charlie1990.duckdns.org:2228`。
- 三个远端口在 Fedora 均为 frps 监听且经 tailscale IP 实测 OPEN：15555(ADB)、8022(手机 root shell)、18700(Haven MCP)。`100.120.189.27:2228` 不通（frps 的 control/bindPort 是 7000，2228 是光猫/OpenWrt 映射入口，非 frps 监听口）。
- **安全隐患（待 Charlie 决策）**：`8022` 由手机 `/data/adb/service.d/shell-8022.sh` 用 `toybox nc -l -p 8022` + fifo 提供 **无认证 root shell**，单连接循环、一次只服务一个连接；frps 绑 `0.0.0.0`，Fedora `tailscale0` 在 firewalld `trusted` zone，网络层任何 tailnet peer 均可访问。Tailscale ACL 是否已限制未验证。
- 已验证可用的 Muse 侧最小命令序列（TCP only，不受 UDP 受限影响）：
  `ssh charlie@100.120.189.27` → `~/.local/bin/adb connect 127.0.0.1:15555` → `~/.local/bin/adb -s 127.0.0.1:15555 shell su -c '<cmd>'`

## OpenWrt 替换光猫后 DDNS 污染与手机 19976 超时（2026-10-24）

### 根因（非 WAN IP 漂移）
- A 记录 `125.110.234.23` 始终正确，WAN IP 未变。坏的是 **AAAA**：被写成代理出口 `195.245.219.35`。
- 机制：`openclash.config.router_self_proxy='1'` 让 OpenWrt **自身出站也走代理**；ddns `ip_source='web'` 让 DuckDNS 自动探测 IP，探测到的是代理出口，写进 AAAA。`duckdns_v6` 为此重试 1436 次。
- 手机按 RFC 6724 优先 IPv6，连到幽灵 AAAA → 黑洞 → `Request timed out. Please try again.`（前端 `static/workspace.js` 的 30s api() 超时文案）。强制 `-4` 立即 200。
- 二级 NAT：OpenWrt WAN=`192.168.1.4`（光猫下私网），故 `ip_source=interface` 报 `No or private IP`。19976 是**光猫直映射到 Fedora**，OpenWrt `dstnat` 无此规则、不在这条路径上。

### 修复
1. `ddns.duckdns_v6.enabled=0`。
2. 部署 `/usr/bin/wan-modem-ip.sh`：直登光猫 LuCI `192.168.1.1/cgi-bin/luci` → `admin/settings/gwinfo` 读 `WANIP`，校验公网、拒绝私网。凭据 `/etc/config/wan-modem-ip.cred`(600)。
3. `ddns.duckdns_v4.ip_source='script'`、`ip_script='/usr/bin/wan-modem-ip.sh'`、`use_ipv6=0`。
4. openclash rules 段**最前**插 `DOMAIN-SUFFIX,duckdns.org,DIRECT` + `DOMAIN-KEYWORD,duckdns,DIRECT`（原有 `DOMAIN-SUFFIX,charlie1990.duckdns.org,ROUTER-PROXY` 是污染源；Clash 规则自上而下首个匹配生效）。
5. `openclash.config.lan_ac_mode='1'` + `router_self_proxy='0'`，并把 br-lan(`8c:de:f9:57:69:35`)/eth1(`8c:de:f9:57:69:34`) MAC 加入 `lan_ac_black_macs`。

### 验收证据
- `/usr/bin/wan-modem-ip.sh` → `125.110.234.23`；DuckDNS 不带 ip 自动探测 → `125.110.234.23`。
- 路由器直连出口 → 真实 IPv6 `240e:...6934`；代理端口 7890 仍 `195.245.219.35`（代理功能未破坏）。
- 端到端 `http://charlie1990.duckdns.org:19976/` = 200, 0.45s。
- 手机 FRP 端口 15555/8022/18700 全部仍监听，frpc 未重启，隧道未中断。

### 操作坑
- MAC 旁路**单独加无效**，必须同时 `lan_ac_mode=1`。
- OpenWrt 是光猫下二级 NAT，`ip_source=interface` 必失败。
- `/etc/init.d/openclash restart` 会长时间不返回，须后台执行 + 40s 以上 sleep。
- OpenWrt 无 `/usr/libexec/sftp-server`，scp 不可用；用 `ssh host 'cat > /path' < file`。
- 公共 DNS(119.29.29.29/114) AAAA 缓存仍会残留旧幽灵值，属 TTL，非配置问题。

## 2026-10-24 续：只查公共DNS会漏判，权威NS才是真相

### 第一轮修复不彻底的原因
- 只查 `223.5.5.5` 看到 A=`125.110.234.23` 就宣布修好，**错误**。公共 DNS 是缓存（TTL 60s），权威记录仍是脏值。
- 必须 `dig +short charlie1990.duckdns.org @ns2.duckdns.org`（ns1/ns2/ns3 都查）。当时权威值是 **A=`195.245.219.35`**、AAAA=`240e:...687d`，两条都被污染。
- 污染源在 **Fedora 本机**，不在 OpenWrt：`duckdns-full-monitor.timer`（每 1–5 分钟）和 `duckdns-update.timer`（5 分钟）用 `api.ipify.org`/`ipinfo.io` 取 IP，`--noproxy '*'` 绕不过本机 mihomo 透明 TUN，于是每隔几分钟就把代理出口写回 A。

### 最终修复
1. `systemctl --user disable --now duckdns-full-monitor.{timer,service} duckdns-update.{timer,service} wan-ip-monitor.{timer,service}`，并对 service `mask`。
2. OpenWrt ddns 独家维护：`ip_source=script` + `/usr/bin/wan-modem-ip.sh`（读光猫 LuCI）+ `use_https=1` + `dns_server=223.5.5.5`。
3. 手动纠正权威记录后交由 OpenWrt 周期维护。

### 验收标准（缺一不可）
- `@ns1/ns2/ns3.duckdns.org` 的 A **和** AAAA 都正确。
- `curl -4` **和** `curl -6` 访问 `:19976` 都返回 200（手机按 RFC 6724 优先 IPv6，只测 IPv4 会漏掉真正的故障面）。
- OpenWrt ddns 日志出现 `Update successful - IP '125.110.234.23' send`。
- `systemctl --user list-timers | grep -ciE 'duckdns|wan-ip'` = 0。

### 已知无害噪声
- OpenWrt ddns 日志 `Registered IP '192.168.5.144' detected`：本地 DNS 被 DUCKDNS_HAIRPIN 劫持所致，不影响 `Update successful`，不必追。
- `duckdns-update.sh` 脚本文件不存在，timer 指向空路径，属历史残留。

## 2026-10-24 终局：4 个写入源全清，IPv6 弃用

### 为什么要排查"所有"写入者
- 第一轮只修 OpenWrt 就宣布完成 → 用户继续超时。原因：Fedora 本机有 **4 个** DuckDNS 写入源，`duckdns-full-monitor`（每 1–5 分钟）持续把代理出口写回 A。
- `network-resilience-guard`、`phone-network-stabilize` 经核查**只探测不写入**，属误判排除项；真正写入者是 `duckdns-full-monitor` / `duckdns-update` / `wan-ip-monitor`。
- 排查顺序：①`dig @ns1/ns2/ns3.duckdns.org` 查权威记录（公共 DNS 是缓存，必误判）→ ②`systemctl --user list-timers --all | grep -iE 'duckdns|wan-ip'` 列全部 timer → ③`ps` + journalctl 按时间戳定位真凶。

### mask 必须用文件级
- `systemctl --user disable` 会被其它任务重新拉起（本次 `duckdns-full-monitor.timer` disable 后仍显示 enabled）。
- 有效做法：`ln -sf /dev/null ~/.config/systemd/user/<unit>.{timer,service}` + `systemctl --user daemon-reload`，确认 `is-enabled` = `masked`。
- 已 mask：`duckdns-full-monitor`、`duckdns-update`、`wan-ip-monitor`。

### DuckDNS 清空 AAAA 的正确姿势（含一个踩坑）
- `ipv6=`（空值）→ 无效；`ipv6=EMPTY` → `KO`。**正确是 `ipv6=::`**。
- **必须同时显式传 `ip=<正确IP>`**：本次只传 `ipv6=` 时，DuckDNS 用请求来源 IP 把 A 记录自动覆盖成 `195.245.219.35`，造成一次自伤。
- 单条命令同时设定：`...&ip=125.110.234.23&ipv6=::&verbose=true`。

### IPv6 为什么弃用
- OpenWrt `FED_V6_DNAT` 规则 `0 pkts` 从未命中：IPv6 流量到达 OpenWrt 自身地址时走 `dev lo` 本地回环，**不经过 PREROUTING**，DNAT 被绕过。`--interface eth1` 也无效。
- 直连 Fedora IPv6 `[240e:393:342e:efb2::6c8]:19976` = 200（DNAT 目标和后端都没问题），问题纯在入口侧 IPv6 NAT。
- 服务全部在 IPv4（frps / Caddy / frpc），保留连不通的 AAAA 只会让手机按 RFC 6724 优先选错路 → 清空 AAAA 为 `::`，手机立即失败并快速回退 IPv4。
- OpenWrt 侧 `uci delete ddns.duckdns_v6` 整段删除，防止将来误开启写回脏 AAAA。

### 终态（2026-10-24 19:03）
- ns1/ns2/ns3：`A=125.110.234.23`、`AAAA=::`。
- IPv4 端到端 `:19976` = 200。
- OpenWrt ddns v4 存活（`ip_source=script` + `/usr/bin/wan-modem-ip.sh` + `use_https=1` + `dns_server=223.5.5.5`）。
- Fedora 侧 `duckdns|wan-ip` timer 数 = 0。

### 未解决（需手机侧配合，非本轮引入）
- `127.0.0.1:15557` / `15558` ADB 显示 `offline`：frps 侧持续收到 `fedora-phone-adb-15557` 新连接（手机 frpc 活着），TCP 层通，但 ADB 协议握手无响应。frps 曾在 18:18/18:20 被外部重启两次，日志有 `proxy already exists` 重复注册。需在手机上确认 wrapper `/data/local/tmp/frpc_smart.sh` 与 adbd 状态。
