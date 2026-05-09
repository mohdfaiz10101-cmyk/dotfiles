---
name: cloudflare-tunnel-phone
description: "Cloudflare Quick Tunnel 外网穿透：无路由器/VPS，穿透NAT，URL发Telegram，开机自启"
user-invocable: false
version: "1.0.0"
category: networking
tags: [cloudflare, tunnel, phone, remote, nat]
effort: medium
auto-generated: true
created: 2026-04-24
---

# Cloudflare Tunnel Phone

## 场景
1. 创建 ~/.local/bin/cloudflared-ttyd 脚本（nix-shell -p cloudflared，HTTPS_PROXY=mihomo:7890，启动后捕获*.trycloudflare.com URL → tg-push）\n2. 创建 ~/.config/systemd/user/cloudflared-ttyd.service（After=ttyd-opencode，Restart=on-failure）\n3. systemctl --user enable && start\n4. 等20秒验证：cat /tmp/cloudflare-ttyd-url → curl测试200\n固定URL升级：注册cloudflare.com → 创建named tunnel → 配置自定义域名

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
