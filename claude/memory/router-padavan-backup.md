---
name: 路由器 Padavan 配置备份 — 永久化
description: 断电恢复参考，包含端口转发/NVRAM/固件信息
verified: 2026-05-24
priority: critical
---

## 设备信息
- 型号: RT-N56U_B1 (Padavan 固件)
- 管理地址: http://192.168.123.1
- 登录: admin / admin
- WAN类型: PPPoE (电信动态IP)

## 端口转发规则 (VSList)
在 `高级设置 → 外部网络(WAN) → 端口转发(UPnP)` 配置：

| 外部端口 | 内部IP | 内部端口 | 协议 | 描述 |
|---------|--------|---------|------|------|
| 7000 | 192.168.123.209 | 7000 | TCP | frps |
| 2222 | 192.168.123.209 | 22 | TCP | SSH |
| 2223 | 192.168.123.209 | 2223 | TCP | SSH-frp |
| 24801 | 192.168.123.209 | 24801 | TCP | RustDesk |
| 17698 | 192.168.123.209 | 17698 | TCP | Sunshine |
| 17699 | 192.168.123.209 | 17699 | TCP | nixos-ai |
| 7681 | 192.168.123.209 | 7681 | TCP | ttyd |
| 8080 | 192.168.123.209 | 8080 | TCP | OpenCode Web |
| 3456 | 192.168.123.209 | 9800 | TCP | Hub-API |
| 8283 | 192.168.123.209 | 8284 | TCP | Letta-MCP |
| 8888 | 192.168.123.209 | 18789 | TCP | OpenClaw-GW |
| 8700 | 192.168.123.209 | 8700 | TCP | OpenAgents-Web (2026-05-24新增) |
| 18090 | 192.168.123.209 | 18090 | TCP | Sisy-18090 |
| 18091 | 192.168.123.209 | 18091 | TCP | Sisy-18091 |
| 18300 | 192.168.123.209 | 18300 | TCP | Sisy-18300 |
| 18700 | 192.168.123.209 | 18700 | TCP | OpenAgents-Net |
| 19890 | 192.168.123.209 | 19890 | TCP | Sisy-19890 |
| 19891 | 192.168.123.209 | 19891 | TCP | Sisy-19891 |
| 19892 | 192.168.123.209 | 19892 | TCP | Sisy-19892 |
| 19893 | 192.168.123.209 | 19893 | TCP | Sisy-19893 |

## NVRAM CLI 命令 (SSH登录路由器后)
```bash
# SSH into router (if enabled)
ssh admin@192.168.123.1
# Show all VSList rules
nvram show | grep vts_rule
# Show general info
nvram show | grep wan_ipaddr
nvram show | grep lan_ipaddr
# Backup full NVRAM to file
nvram show > /tmp/nvram-backup-$(date +%Y%m%d).txt
```

## 灾难恢复步骤
1. 路由器断电重启后，检查 http://192.168.123.1
2. 进入 `高级设置 → 外部网络 → 端口转发`
3. 按上表逐条添加规则，点"应用本页面设置"
4. SSH登录路由器，`nvram commit` 确保持久化
5. 验证: `curl -I http://charlie1990.duckdns.org:17699` → 200

## NixOS侧 DDNS (自动恢复)
DuckDNS timer 每10分钟 + wan-ip-monitor 每60秒检测IP变更
自动触发DDNS更新，无需手动干预