---
name: 路由器 Padavan 配置备份 — 永久化
description: 断电恢复参考，包含端口转发/NVRAM/固件信息
verified: 2026-05-21
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
| 17699 | 192.168.123.209 | 17699 | TCP | nixos-ai (Caddy Launcher) |
| 17700 | 192.168.123.209 | 17700 | TCP | ttyd |
| 2223 | 192.168.123.209 | 2223 | TCP | SSH |
| 18090 | 192.168.123.209 | 18090 | TCP | OpenCode Sisy |
| 19890 | 192.168.123.209 | 19890 | TCP | OpenCode |
| 19891 | 192.168.123.209 | 19891 | TCP | OpenCode |
| 19892 | 192.168.123.209 | 19892 | TCP | OpenCode |
| 19893 | 192.168.123.209 | 19893 | TCP | Letta |
| 8080 | 192.168.123.209 | 8080 | TCP | OpenCode Web (2026-05-23新增) |

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