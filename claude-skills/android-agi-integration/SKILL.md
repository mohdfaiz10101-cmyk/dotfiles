---
name: android-agi-integration
description: "Android 手机通过 ADB 接入 AGI Brain：sense_android() 采集传感器 + brain.py 集成 + P0/P1 任务体系"
user-invocable: false
version: "1.0.0"
category: agi
tags: [android, adb, sensor, brain, agi]
effort: medium
auto-generated: true
created: 2026-04-18
---

# Android Agi Integration

## 场景
## 场景\n手机 USB 连接 NixOS 主机，作为 AGI 感知节点注入 brain.py Sense 阶段。\n\n## 步骤\n1. 确认 adb devices 识别设备：adb devices | grep device\n2. 创建 ~/agi/android_sensor.py，核心函数 sense_android() 通过 adb shell dumpsys 采集：battery_pct, charging, screen_on, wifi_ssid, mem_avail_mb, foreground_app\n3. brain.py sense() 末尾追加（try/except 容错，断连返回 offline）：\n   from android_sensor import sense_android\n   android_data = sense_android()\n   android_data['status'] = 'online'\n   return {..., 'android': android_data}\n4. 测试：cd ~/agi && source .venv/bin/activate && python3 android_sensor.py\n\n## 踩坑\n- foreground_app 用 mResumedActivity 正则匹配，Android 13 部分版本位置不同\n- wifi SSID 含引号需 strip()，如 '"PDCN - 客厅"' → 需二次处理\n- ADB 命令用 adb -s {DEVICE_ID} shell 指定设备，多设备时必须\n\n## P0/P1 后续任务\n- P0: device-registry.json (设备能力注册), sensor-bridge.py (5min定时采集), decision-log.db (决策轨迹)\n- P1: Termux 安装 (adb install), SSH server 配置, Tailscale 组网

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
