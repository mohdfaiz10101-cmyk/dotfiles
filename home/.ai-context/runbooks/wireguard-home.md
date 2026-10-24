# 家庭整网段远程访问：WireGuard（2026-10-24）

## 当前入口
- OpenWrt CR660x：LAN 192.168.5.1，WG wg_home=10.77.50.1/24；手机PKR110=10.77.50.2/32。
- 手机官方WireGuard 1.0.20260315，隧道 charlie-home，GoBackend用户态，Android VPN接口名可在tun0/tun1间变化，必须按地址识别。
- Endpoint wg.charlie1990.duckdns.org:51820，DuckDNS公开解析已确认该子域继承基域WAN地址。
- 光猫 WireGuard51820 UDP51820 ->192.168.1.4:51820，enable=1读回；OpenWrt WAN允许UDP51820到路由器自身，不是DNAT到Fedora。
- AllowedIPs：192.168.5.0/24、10.77.50.0/24、192.168.1.1/32。普通互联网沿手机本地网络和既有root Mihomo，不设默认路由，不覆盖系统DNS。
- Fedora http://192.168.5.144:19910/、:19976/、:8648/；路由器 http://192.168.5.1/；光猫 http://192.168.1.1/。

## 路由与防火墙
- UCI network.wg_home、network.wg_phone；firewall.wg_home、wg_home_in、wg_home_lan、wg_home_modem、wg_home_nat。
- wg_home区INPUT/OUTPUT接受，FORWARD拒绝；显式允许wg_home→LAN及仅192.168.1.1的WAN访问。无VPN全互联网出口放行。
- /etc/wg-home-nat.sh：仅WG源10.77.50.0/24→LAN192.168.5.0/24，SNAT为192.168.5.1，确保LAN返回路径。
- /etc/duckdns-hairpin.sh在原有TCP链增加“当前公网A:UDP51820 ->192.168.5.1”，由原WAN监控继续随公网IP更新。
- 不使用基域做WG Endpoint：它在家庭dnsmasq中专门解析为Fedora192.168.5.144。wg子域不受该精确domain记录影响；家里也用公网A配合UDP回环，避免切网缓存私网endpoint。
- 原ZeroTier与独立FRP保留；手机只能有一个用户0应用VPN。当前主通道WireGuard，ZT守护检测不到原目标VPN时保持disconnected，不抢占。

## 手机持久化与恢复
- Android用户0 always_on_vpn_app=com.wireguard.android，lockdown=0；已添加deviceidle白名单及后台appops allow。
- 实测单靠Always-on，强制进程退出后12秒仍未恢复。官方GoBackend源码确认：标准隐式Intent action android.net.VpnService + package com.wireguard.android触发Always-on恢复回调；显式component Intent不触发该回调。
- /data/adb/wg-home-guard.sh由/data/adb/service.d/98-zerotier-lan-shortcut.sh启动。维护源 ~/.local/share/phone-wireguard-home-guard.sh。
- 仅Always-on仍指向WireGuard且进程连续两轮不存在时触发标准恢复接口；至少120秒间隔、最多2次/小时。进程存在但隧道断开时标paused，尊重手动操作；切换Always-on到其他app后inactive，不启动WireGuard。
- 状态 /data/local/tmp/wg-home-guard.state，日志 /data/local/tmp/wg-home-guard.log。
- 若要切ZeroTier备用：手机设置→VPN→WireGuard，先关闭“始终开启”，再在ZeroTier连接目标network。恢复主通道时反向操作。保留Mihomo root服务，不启动另一个代理VPN。
- 不通过重启手机验证；仅做应用进程故障测试。

## 密钥与备份
- 路由器私钥 /etc/wireguard/home.key；UCI network配置含私钥。禁止uci show network全量打印或wg showconf。
- 手机配置 /data/user/0/com.wireguard.android/files/charlie-home.conf（owner为app，mode600，restorecon已执行）。官方FileConfigStore支持该私有目录。
- 主机私密备份 ~/.local/share/wireguard-private/（目录700，私钥和客户端配置600）；不导出到文档、日志、记忆。
- 配置变更前备份 /root/wg-home-backup/{network.before,firewall.before,duckdns-hairpin.before}，只恢复相关段，避免覆盖后续其他服务变更。

## 验收与复查
- 两轮Wi-Fi/5G往返均HTTP200，来源始终10.77.50.2；5G router302、modem200、Fedora19910/19976/8648均200，ICMP到Fedora成功。
- 通过隧道的UDP DNS：busybox nslookup charlie1990.duckdns.org 10.77.50.1返回答案；OpenWrt TCP22连接成功。openwrt.lan无记录不应当成UDP故障。
- 手机Mihomo Google204，普通百度200，证明原互联网路径可用。
- 默认复查命令 ~/.local/bin/home-vpn-check --serial ff3ef385；按手机真实接口强制出站，最新结果 ~/.local/state/wireguard-home/latest.json。source必须为10.77.50.2。
- 路由器只打印握手时间/transfer；不能把握手成功代替业务验收。

- 补充保活故障验收：单独kill WireGuard进程后，守护自动恢复新PID，30秒检查业务200/source10.77.50.2。5G最终home-vpn-check ok=true；Chrome截图已核对。

## FRP独立备用兼容修复
- 整网段VPN会让旧wrapper的“LAN route必须dev wlan0”不成立，旧基域在家又解析到Fedora，导致误连Fedora:2228而不是FRPS:7000。
- 已将维护源与部署的FRP WAN_HOST改为frp.charlie1990.duckdns.org（公开wildcard A）；WireGuard AllowedIPs不含这个公网目标，因此FRP走原生物理网络，不依赖WG隧道。
- 家庭回环链增加公网TCP2228→Fedora7000及仅原目标端口2228的SNAT。已有WAN映射不动。
- wrapper对UID2000目的TCP2228加入Mihomo RETURN，只旁路FRP控制连接。其他手机代理规则不变。
- Wi-Fi实测frpc连接源192.168.5.211→公网125.110.234.23:2228，frps恢复15555监听、phone-adb注册成功。

- FRP蜂窝最终源100.64.242.90→公网2228，native15555执行su -c id返回uid0；不是USB forward。
