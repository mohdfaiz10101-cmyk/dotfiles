---
name: phone-tailscale-guard
description: "手机 Tailscale VPN 保活：ADB 检测 VPN 冲突，自动杀抢 VPN 的应用，恢复 Tailscale 连接"
user-invocable: false
version: "1.0.0"
category: system
tags: [android, tailscale, vpn, adb, guard]
effort: medium
auto-generated: true
created: 2026-05-03
---

# Phone Tailscale Guard

## 场景
## 手机 Tailscale VPN 保活\n\n### 问题\nAndroid 同一时间只能有一个 VPN。Clash Meta / NekoBox 等代理开 VPN 模式会踢掉 Tailscale。\n\n### 方案\nsystemd timer 每10分钟执行保活脚本：\n1. ADB 检查手机当前 VPN 持有者\n2. 不是 Tailscale → am force-stop 杀掉占用应用\n3. 启动 Tailscale\n\n### 文件\n- 脚本: ~/.local/bin/phone-tailscale-guard\n- Timer: ~/.config/systemd/user/phone-tailscale-guard.timer\n- ADB 设备: 100.64.206.110:5555 (Tailscale IP)\n\n### 手动执行\nbash ~/.local/bin/phone-tailscale-guard\n\n### 检查状态\nsystemctl --user status phone-tailscale-guard.timer

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
