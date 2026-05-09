---
name: android-tailscale-keepalive
description: "Android Tailscale 后台保活：Doze白名单+Magisk service.d开机脚本+10分钟看门狗，防止OnePlus等激进省电手机杀死Tailscale"
user-invocable: false
version: "1.0.0"
category: android
tags: [tailscale, android, magisk, keepalive, background]
effort: medium
auto-generated: true
created: 2026-04-24
---

# Android Tailscale Keepalive

## 场景
1.dumpsys deviceidle whitelist +com.tailscale.ipn\n2.推送/data/adb/service.d/tailscale_keep.sh(开机自动执行)\n3.脚本内含10分钟看门狗循环\n通过ADB执行，需Magisk root

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
