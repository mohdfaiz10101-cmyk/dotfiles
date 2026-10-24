# iPhone Wi-Fi 自动备份（OpenWrt 无线 + libimobiledevice）

> 建立于 2026-10-24。让 iPhone 通过 OpenWrt Wi-Fi 被 Fedora 发现并自动备份，
> 等价于「iTunes/Finder 的 Wi-Fi 同步」，但走开源 libimobiledevice 全自动链路。

## 架构

```
iPhone (OpenWrt Wi-Fi, 192.168.5.x)
   │
   ├─ mDNS 5353 ──► avahi-daemon 广播 _apple-mobdev2._tcp  (让 iPhone "看见" 电脑)
   │
   └─ TCP 62078 ──► usbmuxd -S 0.0.0.0:62078  (usbmux 协议，替代 USB)
                        │
                        └─ idevicebackup2 -n backup /var/mnt/ai/backups/iphone/<UDID>/
```

关键点：**iPhone 的「无线同步」靠 mDNS 发现电脑**，不是靠 IP。电脑必须先广播
`_apple-mobdev2._tcp`，iPhone 才会把它列进 Finder/iTunes 的可选设备。

## 组件清单（均已验证生效）

| 组件 | 位置 | 状态 |
|---|---|---|
| avahi mDNS 广播 | `/etc/avahi/services/apple-mobdev2.service` | active |
| usbmuxd TCP 监听 | `/etc/systemd/system/usbmuxd.service.d/10-tcp-listen.conf` | listening 0.0.0.0:62078 |
| SELinux 策略模块 | `usbmuxd-tcp` v1.3（semodule -l 可见） | loaded |
| 开机自启 | `/etc/systemd/system/multi-user.target.wants/usbmuxd.service` | symlink |
| 备份脚本 | `~/.local/bin/iphone-wifi-backup` | executable |
| 定时器 | `~/.config/systemd/user/iphone-wifi-backup.timer` | 每天 03:30 + 15min 抖动 |
| 备份落点 | `/var/mnt/ai/backups/iphone/00008120-000904112160201E/` | POOL-D1 919G 数据盘 |

## 三个必须踩过的坑

### 1. SELinux 拒绝 bind 62078（最隐蔽）

Fedora 的 `usbmuxd.service` 默认只监听 Unix socket `/var/run/usbmuxd`。
改成 `-S 0.0.0.0:62078` 后被 SELinux 拦，报错信息有误导性：

- 先报 `Could not open lockfile` → 实际是写 `/run/usbmuxd-tcp.pid` 被拒
- 再报 `create_socket: bind() failed` → `unreserved_port_t:tcp_socket name_bind` 被拒
- 再报 `listen() failed` → `usbmuxd_t:self:tcp_socket listen` 被拒（tcontext 是自己，不是端口类型）

**三条规则都要**，少一条就换一个报错。策略源码：

```bash
sudo tee /tmp/usbmuxd-tcp.te <<'EOF'
module usbmuxd-tcp 1.3;
require {
    type usbmuxd_t;
    type unreserved_port_t;
    type usbmuxd_var_run_t;
    class tcp_socket { listen name_bind };
    class file write;
}
allow usbmuxd_t unreserved_port_t:tcp_socket name_bind;
allow usbmuxd_t self:tcp_socket listen;
allow usbmuxd_t usbmuxd_var_run_t:file write;
EOF
sudo checkmodule -M -m -o /tmp/usbmuxd-tcp.mod /tmp/usbmuxd-tcp.te
sudo semodule_package -o /tmp/usbmuxd-tcp.pp -m /tmp/usbmuxd-tcp.mod
sudo semodule -i /tmp/usbmuxd-tcp.pp
```

`/run/usbmuxd.*` 的 `usbmuxd_var_run_t` 标签系统策略已带，但 `-P` 指定的 pidfile
仍需 `semanage fcontext -a -t usbmuxd_var_run_t '/run/usbmuxd-tcp\.pid'` + `restorecon`。

诊断命令：`sudo ausearch -m AVC -ts recent | grep usbmuxd`
（`journalctl | grep avc` 有时漏，优先 ausearch）

### 2. usbmuxd 是 static，不会开机自启

`/usr/lib/udev/rules.d/39-usbmuxd.rules` 只在 **iPhone 插 USB** 时用
`ENV{SYSTEMD_WANTS}="usbmuxd.service"` 拉起它。纯无线场景开机后没人拉。

修法（unit 是 static，`systemctl enable` 会报错说没有 [Install] 段）：

```bash
sudo ln -sfn /usr/lib/systemd/system/usbmuxd.service \
  /etc/systemd/system/multi-user.target.wants/usbmuxd.service
```

### 3. libimobiledevice 不广播 mDNS

Fedora 的 `libimobiledevice-glue-1.0.so.0` **没有链接 avahi/dns_sd**
（`ldd` + `nm -D` 均无符号）。所以即使 usbmuxd 在跑，iPhone 也看不到电脑。
必须由 avahi 补一个静态 service 文件：

`/etc/avahi/services/apple-mobdev2.service` → 端口 62078，`%h` 取主机名。
`sudo systemctl reload avahi-daemon` 后立即生效，`avahi-browse -t -r -p _apple-mobdev2._tcp` 可见。

**同时要限制广播接口**。avahi 默认在所有接口（含 podman/docker 的 veth/br-）广播，
会把 `fedora.local:62078` 泄露进容器网络。在 `/etc/avahi/avahi-daemon.conf` 的
**`[server]` 组内**加（不是文件末尾，INI 组会延续，追加到末尾会被归到 `[rlimits]`
导致 avahi 启动失败报 `Invalid configuration key "allow-interfaces" in group "rlimits"`）：

```ini
allow-interfaces=wlp0s20f0u6,wlp0s20f0u9u4
```

验证只剩两个 Wi-Fi 网卡：
`avahi-browse -t -r -p _apple-mobdev2._tcp | grep '^='` 应只有 4 行（2 网卡 × IPv4/IPv6）。
此项不影响 KDE Connect——它走自己的 UDP 1716 广播，不经 avahi。

## iPhone 侧一次性设置

1. 插一次 USB，在手机上点「信任」并输密码（建立配对记录 `/var/lib/lockdown/<UDID>.plist`）
2. 设置 → 通用 → 隔空播放与接力/ iTunes Wi-Fi 同步 → 打开「Wi-Fi 同步」
3. 之后手机连 OpenWrt Wi-Fi 就能被电脑发现，无需再插线

> 注意：iOS 的「无线同步」开关在 设置 → 通用 → 隔空播放与连续性 附近，
> 且需和电脑同一网段。iPhone 用「专用无线局域网地址」（MAC 本地位，如 c2:32:34:...），
> DHCP 里显示为随机主机名，别用 MAC 反查设备。

## 日常操作

```bash
# 手动跑一次
~/.local/bin/iphone-wifi-backup

# 看备份状态
cat ~/.local/state/iphone-backup/last.json

# 看日志
tail -30 ~/.local/state/iphone-backup/backup.log

# 强制全量
IPHONE_FULL=1 ~/.local/bin/iphone-wifi-backup   # 需配合 idevicebackup2 --full

# 改保留天数（默认 30 天）
IPHONE_BACKUP_RETAIN_DAYS=60 ~/.local/bin/iphone-wifi-backup

# 检查链路四件套
ss -tln | grep 62078                                   # usbmuxd TCP
avahi-browse -t -r -p _apple-mobdev2._tcp | grep IPv4  # mDNS 广播
idevice_id -n -l                                        # iPhone 是否在线
systemctl --user list-timers iphone-wifi-backup.timer   # 定时器
```

## 未验证项 / 待确认

- iPhone 当前不在线（`idevice_id -n -l` 空），**端到端备份未实测**。
  脚本在设备离线时静默退出 0，在线路径（配对校验 → backup → 清理 → 通知）代码已写但未跑过真实数据。
- 备份加密未开启。若需：`idevicebackup2 -n encryption on <PWD>`，
  之后脚本必须带 `BACKUP_PASSWORD` 环境变量，否则 lockdownd 会交互卡住。
- OpenWrt 侧无需改配置：LAN 区 `input/output/forward` 均 ACCEPT，未开 AP 隔离，
  mDNS 5353 与 TCP 62078 都是 LAN 内直通，已从防火墙配置核实。
- 另一台开 62078 的设备 192.168.5.146（MAC c2:32:34:2e:f9:2f，本地管理位）
  未确认身份；它拒绝 usbmux 握手，不影响本方案（脚本按 UDID 精确匹配）。
