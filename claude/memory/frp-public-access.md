---
name: DuckDNS + FRP + 路由器 公网穿透 — 已验证2026-05-21
description: 三态连通性全链路配置 (DDNS→NAT→FRP), 已通过端到端验证
type: permanent-reference
verified: 2026-05-21
---

## DuckDNS
- 域名: `charlie1990.duckdns.org` (非 charlie-nixos)
- WAN IP: `125.110.221.37` (PPPoE 动态)
- Token: `1e66570c-983c-4c0d-b776-03d1ae3a9aa6`
- 更新: duckdns.timer 每10分钟 (curl --noproxy "*")
- ✅ 已验证: curl charlie1990.duckdns.org:17699 → 200 OK

## 路由器 (Padavan RT-N56U_B1, 192.168.123.1)
- 管理员: admin/admin, UI: http://192.168.123.1
- 端口转发 (VSList): **17699 → 192.168.123.209:17699 TCP** (已存在, 描述"nixos-ai")
- ✅ 已验证: 规则正常运行, NVRAM持久化

## FRPS (服务端, NixOS)
- 配置: `~/ai-deploy/frps.toml`, bindPort=7000, dashboard:7500
- 认证: token=frp-token-charlie-2026, dashboard user=admin pass=frp@charlie2026
- 暴露端口: 17699/2223/60000-60005/19890-19893
- 系统管理: NixOS rebuild (frps Nix store路径)

## FRPC (客户端, NixOS)
- 配置: `~/.config/frpc/frpc.toml`, 连接本地FRPS 192.168.123.209:7000
- 13条隧道含: nixos-tty(17699→7699 Caddy), nixos-ssh(2223→22), opencode等
- systemd: frpc.service (Restart=always, RestartSec=15)

## 外网访问链路 (已验证)
```
charlie1990.duckdns.org:17699 → 路由器NAT → 192.168.123.209:17699
  → NixOS FRPS → frpc隧道(nixos-tty) → localhost:7699 → Caddy Launcher
```

## 监控体系 (三层防御)
1. **duckdns.timer** → 每10分钟主动DDNS更新
2. **connectivity-chain-watchdog.timer** → 每5分钟 L1 DNS/L2 NAT/L3 FRP/L3b E2E
3. **frp-watchdog.timer** → 每5分钟 frps+frpc自愈
- 脚本: `~/.local/bin/connectivity-chain-watchdog.sh`

## 过去误判 (已修正)
- 2026-05-21 早期: 以为DuckDNS不通 (HTTP 000), 实际是mihomo代理拦截了DNS
- 修复: DuckDNS service + watchdog 均使用 `--noproxy '*'`