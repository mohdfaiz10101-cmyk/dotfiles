# 2026-08-01 Moonlight / Sunshine / Waydroid 续借交接

## 当前目标

手机通过 Moonlight 连接 Fedora Sunshine，只显示/启动 Waydroid，并适配随身 Wi-Fi、5G、公网访问。

## 当前最终状态

- Sunshine 服务：`sunshine.service` 已重启，状态 `active`。
- Sunshine serverinfo：`SUNSHINE_SERVER_FREE`，`currentgame=0`。
- Sunshine 监听端口：
  - `47984/tcp`
  - `47989/tcp`
  - `48010/tcp`
  - `60000/udp`
- 路由器 DNAT 已确认：
  - `47984/tcp -> 192.168.123.71`
  - `47989/tcp -> 192.168.123.71`
  - `48010/tcp -> 192.168.123.71`
  - `47998-48010/udp -> 192.168.123.71`
- 不暴露 Sunshine Web UI `47990/tcp` 到公网。

## 手机网络路径结论

手机当前随身 Wi-Fi：

- SSID：`MIFI-C3BB`
- 手机 IP：`192.168.100.100/24`
- 不是家里 LAN `192.168.123.0/24`

随身 Wi-Fi 实测：

- `http://charlie1990.duckdns.org:47989/serverinfo` 可达，返回 `HTTP 200`。
- `192.168.123.71:47989` timeout。
- `100.87.171.39:47989` timeout。

因此随身 Wi-Fi / 5G / 公网场景下，Moonlight 应优先使用：

```text
charlie1990.duckdns.org:47989
```

不要优先使用：

```text
192.168.123.71:47989
100.87.171.39:47989
```

## Moonlight DB 当前配置

手机 Moonlight 包：

```text
com.limelight
UID 10537
```

数据库：

```text
/data/data/com.limelight/databases/computers4.db
```

`fedora` host 当前应为：

```json
{"local":{"address":"charlie1990.duckdns.org","port":47989},"manual":{"address":"charlie1990.duckdns.org","port":47989}}
```

已保留备份：

```text
/data/data/com.limelight/databases/computers4.db.bak_codex
/data/data/com.limelight/databases/computers4.db.bak_portable_wifi
```

重要：此手机普通 `su -c` 可能无法访问/写入 `/data/data`，需要：

```sh
su -mm -c '<command>'
```

## “fedora 离线”的处理

出现 `fedora` 离线时先检查手机侧：

```sh
curl -m 6 http://charlie1990.duckdns.org:47989/serverinfo
```

本次发现过 Sunshine 返回：

```text
SUNSHINE_SERVER_BUSY
currentgame != 0
```

处理方式：

```sh
systemctl --user restart sunshine.service
```

重启后确认：

```text
SUNSHINE_SERVER_FREE
currentgame=0
```

然后清理 Moonlight app list 缓存并重开 Moonlight：

```sh
su -mm -c 'rm -f /data/data/com.limelight/cache/applist/1379115E-D133-0E2A-499E-6E2D8CD9ECCF'
am force-stop com.limelight
am start -n com.limelight/.PcView
```

验证标准：

- 手机侧 serverinfo `HTTP 200`
- Moonlight activity 从 `.PcView` 进入 `.AppView`
- 表示 host 在线且应用列表已打开

## Sunshine 菜单当前标准

配置文件：

```text
/var/home/charlie/.config/sunshine/apps.json
```

当前菜单顺序：

1. `Waydroid 手机`
2. `电脑浏览器`
3. `电脑终端`
4. `电脑文件`
5. `电脑监控`
6. `Steam 大屏幕`
7. `缺氧：安装或登录`
8. `缺氧：启动`
9. `电脑桌面`
10. `平板：搜索App`
11. `平板：浏览器`
12. `平板：终端`

禁止回退到：

```text
Waydroid 手机 自动
重复的 Waydroid 手机
平板搜索App
```

改菜单后必须：

```sh
jq empty /var/home/charlie/.config/sunshine/apps.json
systemctl --user restart sunshine.service
```

并清理手机 Moonlight app list 缓存。

## Waydroid 专用入口

入口脚本：

```text
/var/home/charlie/.local/bin/moonlight-waydroid-only
/var/home/charlie/.local/bin/moonlight-launch
/var/home/charlie/.local/bin/moonlight-display-mode
```

Sunshine 第一个 app 必须执行：

```text
/var/home/charlie/.local/bin/moonlight-launch waydroid
```

成功日志：

```text
/run/user/1000/moonlight-waydroid-only.log
ready workspace=8
```

Sway 验证目标：

```text
workspace 8
Waydroid visible=true
focused=true
fullscreen_mode=1
```

## 已更新的持久知识

已更新：

```text
/var/home/charlie/.ai-context/runbooks/waydroid-control-plane.md
```

已记录 preference：

- Moonlight/Sunshine 在随身 Wi-Fi 下优先 DuckDNS。
- Moonlight 离线时先查 phone-side serverinfo / Sunshine busy / Moonlight applist cache。
- 菜单名必须短、唯一、手机可读，第一个入口为 `Waydroid 手机`。

## 权限说明

不能绕过 Codex 权限模型，不能让新窗口 bypass all permission。任何新会话仍应按当前审批/沙箱规则执行。
