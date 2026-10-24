# ZeroTier Android 切网恢复（2026-10-24）

## 当前拓扑
- OpenWrt 192.168.5.1 / ZeroTier 10.68.142.60，network b9a18a606ff8b427；手机 PKR110 10.68.142.114，com.zerotier.one 1.16.0-1。
- 服务入口 http://10.68.142.60:19910/；TCP1024-65535同端口转发Fedora192.168.5.144，不代表全LAN或UDP。
- 家庭Wi-Fi由既有 /data/adb/zt-lan-shortcut.sh 提供目的/32快捷路由。5G需使用真实tun0路径验收。

## 证据和修复边界
- 冷启动于Wi-Fi后切蜂窝可复现tun0地址保留而请求000；单纯stopservice/startservice的旧试验无效。
- 已实测替代流程：am force-stop app，cmd deviceidle tempwhitelist -d 60000 app，再 am startservice --user 0 带long extra com.zerotier.one.network_id。临时白名单避免后台startservice被Android拒绝。
- 本机目标network的Java signed long为 -5070619558642404313。不能遗漏参数或将十六进制ID误作字符串extra。
- 普通startservice直接在后台执行会报 app is in background；不要把Starting service打印当恢复成功。必须先停止整个旧app，并重新核对真实网关。
- Disable connectivity check 已开启并从shared_prefs读回；单独设置不能消除切网故障。临时OUTPUT ACCEPT并非已证实根因，诊断规则已移除。

## 手机端守护
- 维护源 ~/.local/share/phone-zerotier-roaming-guard.sh，部署 /data/adb/zt-roaming-guard.sh。
- Magisk /data/adb/service.d/98-zerotier-lan-shortcut.sh 启动LAN辅助和漫游守护。
- 守护仅处理已存在的本网络tun0和活着的ZeroTier app，尊重手动断开；家庭Wi-Fi跳过。
- 非家庭网络变化等待12秒，先ping -I tun0网关，失败再HTTP探测；连续两轮失败才完整重建这个app，不打开界面。
- 重建后等待18秒；两次重建至少120秒；每个底层路由最多两次尝试。禁止自动重启手机、system_server、代理或其他VPN。
- 状态 /data/local/tmp/zt-roaming-guard.state；日志 /data/local/tmp/zt-roaming-guard.log。
- 仅启动了服务不代表正常。状态healthy以及手机端19910/19976/8648的实际响应才是验收。

## 定向抓包
手机原生 /system/bin/tcpdump 可用，不要假定缺失：
`adb-record --tag zt-capture -- -s SERIAL shell 'su -c "timeout 20 tcpdump -ni any -c 40 -s 100 udp port 9994"'`
OpenWrt已安装tcpdump-mini与libpcap1；指定eth1避免mini解码any的LINUX_SLL2输出UNSUPPORTED。
抓包已观察蜂窝rmnet接口双向IPv4/IPv6 UDP，随后网关HTTP200。不能据ONLINE单独判断可用。

## 最终验收
- 故障注入：仅阻断手机ZeroTier UID的UDP9994，守护连续失败后自动替换app PID，解除故障后19910=200、source10.68.142.114。
- 两轮 Wi-Fi→5G→Wi-Fi验证：家庭入口200/source192.168.5.211，蜂窝入口200/source10.68.142.114；最终守护healthy。
- 5G实际19910、19976、8648均200；手机Chrome显示19910的Hermes设备验证页，带唯一验证query。
- 证据 ~/.local/state/zerotier-roaming/{recovery-test.txt,roundtrip-test.txt,phone-5g-browser.png}。诊断阻断/放行规则及抓包进程均已清理。
- 自动重建有探测和等待时间，约30–60秒，不承诺原有TCP/WebSocket连接不断；重新请求会使用恢复后的隧道。

## 长期架构核查（2026-10-24 02:51）
- CR660x MT7621，约256MB RAM，已有OpenClash、ZeroTier、FRPC；WireGuard内核模块、tools、LuCI协议及界面均已安装，wg show interfaces为空，尚未配置WG隧道。
- 公网入口现有光猫WAN125.110.234.23，OpenWrt WAN192.168.1.4，双NAT；WireGuard需先验证对应UDP双层映射和手机5G握手，不能从已有TCP入口推断UDP可用。
- 最新官方 https://www.zerotier.com/pricing.md 的Personal明确不含custom routes且无API access。402本身不能区分具体套餐限制；现由官方政策核实自定义路由需要更高套餐，不能外推ZeroTier协议不支持完整LAN/TCP/UDP。
- 针对此用户建议：全LAN远程主通道优先评估现成OpenWrt原生WireGuard；保留现有ZeroTier及独立FRP恢复路径。手机只选一个应用VPN活动，Mihomo root代理保持独立。只路由家庭网段，后续按需求单独配置出口代理、发现协议和DNS。
- 未来新增多个家庭/异地网段或公网不可达时再评估Tailscale/NetBird等控制层；不要在256MB路由器上同时堆叠多种VPN和自建控制平台。未部署WG，仅完成选型核查。
