---
name: wechat-windows-lock
description: "Windows微信版本锁定+降级部署：将微信4.x降级到3.9.12.51，锁定版本，部署wcferry bridge"
user-invocable: false
version: "1.0.0"
category: wechat
tags: [wechat, windows, wcferry, version-lock]
effort: medium
auto-generated: true
created: 2026-04-23
---

# Wechat Windows Lock

## 场景
# WeChat Windows版本锁定+降级部署

## 触发场景
- 需要wcferry bridge（只支持3.9.x）
- 微信4.x升级后bridge失效
- 首次部署Windows微信自动化

## 前提
- Windows SSH: `ssh G@192.168.2.36`（密码`1`）
- NixOS代理: `http://192.168.2.100:7890`

## Step 1 — 下载安装包

```bash
# NixOS下载（走代理）
curl -L --proxy http://192.168.2.100:7890 \
  'https://github.com/lich0821/WeChatFerry/releases/download/v39.5.2/WeChatSetup-3.9.12.51.exe' \
  -o /tmp/WeChatSetup-3.9.12.51.exe

# 传输到Windows
scp /tmp/WeChatSetup-3.9.12.51.exe G@192.168.2.36:'C:/ai-node/WeChatSetup-3.9.12.51.exe'
```

## Step 2 — 安装3.9.12.51

```powershell
# SSH到Windows执行（需要WeChat 4.x关闭，手动关或杀进程）
Stop-Process -Name WeChatAppEx -Force -ErrorAction SilentlyContinue
Start-Sleep 3
Start-Process -FilePath 'C:\ai-node\WeChatSetup-3.9.12.51.exe' -ArgumentList '/S' -Wait
```

安装路径: `C:\Program Files\Tencent\WeChat\[3.9.12.51]\WeChat.exe`

## Step 3 — 版本锁定

```cmd
# 注册表禁用自动更新
reg add HKCU\Software\Tencent\WeChat /v EnableAutoUpgrade /t REG_DWORD /d 0 /f

# 锁定WeChatUpdate.exe（禁止执行）
icacls "C:\Program Files\Tencent\WeChat\[3.9.12.51]\WeChatUpdate.exe" /deny Everyone:X
```

## Step 4 — 部署wcferry bridge

```bash
# C:\wxdump\wcf_server.py 已有，端口改为18888
# 注册开机自启任务
ssh G@192.168.2.36 'powershell -NoProfile -Command "
$action = New-ScheduledTaskAction -Execute python.exe -Argument C:\wxdump\wcf_server.py -WorkingDirectory C:\wxdump
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName WeChatFerryBridge -Action $action -Trigger $trigger -Force
"'
```

## Step 5 — 版本自动检测（NixOS端）

```bash
# wechat-version-guard.timer 已部署，每日10:00检测
# 若Windows微信升级到4.x → 发出桌面通知 + op-live-feed告警
systemctl --user status wechat-version-guard.timer
```

## 验证

```bash
# 1. Windows微信版本
ssh G@192.168.2.36 "powershell -c '(Get-Item C:\\Program\\Files\\Tencent\\WeChat\\[3.9.12.51]\\WeChat.exe).VersionInfo.FileVersion'"

# 2. wcferry bridge可达性（WeChat 3.9.x必须登录后）
curl http://192.168.2.36:18888/status

# 3. 版本守护timer
systemctl --user is-active wechat-version-guard.timer
```

## 注意事项
- WeChat 4.x和3.9.x无法共存，切换前需关闭4.x
- 切换后需手动扫码重新登录WeChat 3.9.x
- 若微信强制更新弹窗 → WeChatUpdate.exe权限已被拒绝，直接关闭即可
- 完整脚本: C:\ai-node\wechat-lock.ps1 (-Lock/-Status/-Install)


## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
