# 设备互联方案

## Android 手机
- 型号：OnePlus Ace 5 Pro (PKR110)，Android 16，Bootloader 已解锁
- **已 Root**：Magisk，通过 fastboot flash init_boot 完成（2026-04-19）
- **ADB WiFi 已连接**：`adb connect <手机IP>:5555`，可随时使用
- Termux 已安装，Tailscale 已配置
- 微信备份：需 `adb shell`→ `/data/data/com.tencent.mm/MicroMsg`（需 root）

## 连接方法
- SSH/ADB：手机 IP 通过 `adb devices` 确认
- wechat-backup.conf：配置 `ANDROID_IP=<手机IP>` 即可启用备份

## Windows
- SSH：`G@192.168.2.36`，密码 `1`
- Tailscale 组网

## 网络
- Tailscale + Syncthing + mihomo 代理

## 小米平板5
- [2026-04-24] [Sonnet] 小米平板5已确认 Root (Magisk)，Tailscale IP 100.104.211.70，ADB WiFi 可用
