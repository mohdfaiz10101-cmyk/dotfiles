# Anchored Summary — 2026-05-24 ADB/Tailscale Session

## 设备状态
- **OnePlus Ace 5 Pro (PKR110)**: USB ADB 连接 (serial `ff3ef385`)
- **WiFi IP**: `192.168.123.229/24` (wlan0 UP)
- **Xiaomi Pad 5**: WiFi ADB `192.168.123.241:5555` (稳定)

## 本次修复
1. **Tailscale 禁用**: `pm disable com.tailscale.ipn` + `setprop persist.tailscale.enabled 0`
2. **默认路由缺失**: `ip route show default` 返回空 → 添加 `default via 192.168.123.1 dev wlan0`
3. **互联网恢复**: `ping 8.8.8.8` 成功 (198ms avg, 0% loss)

## 关键发现
- 手机 WiFi 有 IP 但无默认路由 → 无法访问外网
- Tailscale `persist.tailscale.enabled=0` 已设置，但 app 可能通过其他机制自启
- 路由器 DHCP 可能未正确推送默认路由给此设备

## 待跟进
- [ ] 调查 Tailscale 自启机制 (Magisk? service.d? app 自启动?)
- [ ] 检查路由器 DHCP 配置为何此设备缺默认路由
- [ ] 验证 `phone-clip-sync` 在当前 ADB 配置下正常工作

## 环境
- NixOS: `192.168.123.209`
- Windows 跳板: `192.168.123.136` (SSH user G, pass 1)
- ADB wrapper: `/home/charlie/.local/bin/adb-windows.sh`
