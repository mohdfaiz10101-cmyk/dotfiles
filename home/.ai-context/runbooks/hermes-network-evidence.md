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
