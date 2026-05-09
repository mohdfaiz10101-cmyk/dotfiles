# 设备互联方案

## Android 手机（主力）
- 型号：OnePlus Ace 5 Pro (PKR110)，Android 16，Bootloader 已解锁
- **已 Root**：Magisk，通过 fastboot flash init_boot 完成（2026-04-19）
- **ADB WiFi 已连接**：`adb connect <手机IP>:5555`，可随时使用
- Termux 已安装，Tailscale 已配置
- 微信备份：需 `adb shell`→ `/data/data/com.tencent.mm/MicroMsg`（需 root）

## Android 手机（坏屏备用机 / STT 服务器）
- 型号：Xiaomi M2011K2G（Redmi K30 Pro），Android 13，**11GB RAM**，225GB 存储
- **ADB WiFi**：`192.168.2.29:5555`（已无线连接在线）
- ADB 序列号（USB）：`89f5ae98`
- 状态：屏幕损坏，充电正常，可 24h 常开作服务器
- 用途规划：sherpa-onnx + SenseVoice HTTP STT 服务器（:8178）→ 替代 Groq Whisper
- Termux/Tailscale：待安装（[op-tasks.md] pending）
- [2026-04-27] [Sonnet] 记录确认

## 连接方法
- SSH/ADB：手机 IP 通过 `adb devices` 确认
- wechat-backup.conf：配置 `ANDROID_IP=<手机IP>` 即可启用备份

## NixOS 小主机 (minipc)
- **主机名**: minipc | **IP**: `192.168.2.101` | **WiFi**: wlp0s20f0u4
- **CPU**: Intel N100 (4核4线程) | **内存**: 7.5GB | **磁盘**: 238GB NVMe (已用19G, 9%)
- **GPU**: Intel UHD Graphics (Alder Lake-N) | **无独显**
- **系统**: NixOS 26.05pre953160 (Yarara) | 内核 6.18.13
- **SSH**: `charlie@192.168.2.101`（密钥已配，直接登录）| root 也可登录
- **无 Docker** | **无 Tailscale** | **无 NVIDIA**
- **运行服务**: sshd, NetworkManager, display-manager, wpa_supplicant
- **外接设备**: sda(3.9M) + sdb(14.6G USB)
- **备注**: NixOS flake 配置中有 `nixosConfigurations.minipc`，由大主机统一管理

## Windows 主机 (WIN-S2D8GP89FU1)
- **SSH**: `G@192.168.2.36` 密码 `1` | Tailscale 组网
- **Python**: 3.12.10 (`C:\Users\G\AppData\Local\Programs\Python\Python312\`)
- **无 Docker** — 文件管理用 Python 脚本 + SMB 共享
- **角色**: 文件存档库、数据库备份、商业文档中心
- **共享路径**: `\\192.168.2.36\共享` 或 Tailscale IP 访问
- **同步**: Syncthing 双向同步 memory/ + documents/

## 双机记忆同步（DUAL_MACHINE_SYNC — 死规则）
- **NixOS (192.168.2.100)** = 主力机，所有 AI Agent 运行于此
- **Windows (192.168.2.36)** = 存档机，文档数据库 + 记忆副本
- **同步工具**: Syncthing（双向实时同步）
- **同步目录**:
  | 目录 | NixOS | Windows | 说明 |
  |------|-------|---------|------|
  | memory/ | `~/.claude/projects/-home-charlie/memory/` | `C:\Users\G\sync\memory\` | 所有 agent 记忆文件 |
  | documents/ | `/mnt/ai/documents/` | `C:\Users\G\sync\documents\` | 财务/CRM/合同文档 |
  | dotfiles/ | `~/dotfiles/` | `C:\Users\G\sync\dotfiles\` | agent 配置 + skills |
- **冲突策略**: NixOS 为主（服务端），Windows 为只读副本
- **验证**: 每次 agent 写入 memory 后，检查 Syncthing 同步状态

## 大主机有线网 (eno1 — Intel I219-V)
- MAC: 04:42:1a:21:3b:11 | WoL sysfs: enabled
- **已插网线**（carrier=1），但同子网配IP会抢占WiFi默认路由导致断网
- **需要 CC 在 NixOS 声明式配置**：eno1 仅配 IP 不配网关（never-default），WiFi 保持默认路由
- 目的：有线 WoL 唤醒大主机，WiFi 保持日常连接

## 网络
- 路由器: 192.168.2.1
- NixOS大主机: 192.168.2.100 (wlp0s20f0u5 WiFi) + eno1有线(待配置)
- NixOS小主机: 192.168.2.101 (wlp0s20f0u4 WiFi)
- Windows: 192.168.2.36
- Tailscale + Syncthing + mihomo 代理
- **minipc 有4个 I226-V 千兆口**（enp1s0~4s0），建议插网线稳定在线

## 小米平板5
- [2026-04-24] [Sonnet] 小米平板5已确认 Root (Magisk)，Tailscale IP 100.104.211.70，ADB WiFi 可用
