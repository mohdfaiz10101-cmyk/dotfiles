---
name: wechat-dual-agent
description: "双微信实例(UOS+Wine)AES解密+AI自动回复守护进程，含多模态"
user-invocable: false
version: "1.0.0"
category: wechat-agent
tags: [wechat, auto-reply, decrypt, multimodal, daemon]
effort: medium
auto-generated: true
created: 2026-04-17
---

# Wechat Dual Agent

## 场景
场景：两个微信同时运行（WeChat UOS + Wine WeChat），需要自动AI回复。
步骤：
1. 先运行微信，再 wechat-finance --extract-keys 提取解密密钥
2. 守护进程：/home/charlie/agi/wechat_agent.py (893行)
3. DRY_RUN=1 测试，确认 /tmp/wechat-reply-queue.jsonl 有输出
4. systemctl --user start wechat-agent
注意：
- UOS DB路径：~/文档/xwechat_files/wxid_bjo2p0swoxm822_fe61/db_storage/message/
- Wine DB路径：/mnt/data/WeChat Files/{w422417869,wxid_gcyys3q9z3tk12}/Msg/ChatMsg.db
- 两个DB都是AES加密，需pycryptodome
- 图片→doubao-1-5-vision-pro-32k，语音→Whisper:8178，文字→GLM-4.7
- xdotool发送需要DISPLAY=:0环境变量

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
