---
name: FRP 公网访问诊断 2026-05-21
description: 17699 端口映射修复 + DuckDNS 配置 + 公网访问方案
type: project
---

## 端口映射修复
- **17699** → 7699 (Caddy AI Launcher) — 原来错误映射到 7700(ttyd)
- **17700** → 7700 (ttyd Web终端) — 新增
- frpc.toml 已修复, NixOS allowPorts+防火墙 已更新并 rebuild

## DuckDNS
- 域名: `charlie1990.duckdns.org`
- Token: `1e66570c-983c-4c0d-b776-03d1ae3a9aa6`
- **修复**: service 加入 `--noproxy "*"` 防止 mihomo 拦截
- Timer: 已 enabled, 每小时更新

## dpdns.org
- 域名: `charlie1990.dpdns.org`
- Timer: 每月1日 09:00 续期

## 公网IP
- 真实ISP IP: `125.110.221.37` (DuckDNS 检测)
- 代理IP(mihomo): `185.37.253.247`
- IPv6: `2a04:6f00:1::ee:b:1025`

## 公网访问状态
- `charlie1990.duckdns.org:17699` → HTTP 000 (不通)
- 可能原因: 路由器未配置端口转发 / ISP CGNAT

## 路由器端口转发规则(需在 192.168.123.1 管理页配置)
| 外部端口 | 内部IP | 内部端口 | 服务 |
|---------|--------|---------|------|
| 17699 | 192.168.123.209 | 17699 | Caddy AI Launcher |
| 17700 | 192.168.123.209 | 17700 | ttyd Web终端 |
| 2223 | 192.168.123.209 | 2223 | SSH |
| 18090 | 192.168.123.209 | 18090 | OpenCode Sisy |
| 19890-19893 | 192.168.123.209 | 19890-19893 | OpenCode/Letta |

## 待办
- [ ] 从 Windows 登录路由器(192.168.123.1)配置端口转发
- [ ] 确认 ISP 是否 CGNAT (端口转发是否生效)
- [ ] 如 CGNAT → 考虑 Cloudflare Tunnel 或 Tailscale Funnel

**Why:** 2026-05-21 全面排查发现端口映射错误、DuckDNS 被代理拦截、公网不通
**How to apply:** 端口映射已修复，需用户在路由器配置转发规则才能公网访问
