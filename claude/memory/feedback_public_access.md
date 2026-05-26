---
name: 公网入口必须用 DuckDNS
description: 公网访问地址必须优先使用 charlie1990.duckdns.org，不是 Tailscale Funnel
type: feedback
---

## 规则
公网地址 MUST 使用 `charlie1990.duckdns.org`，禁止默认给 Tailscale Funnel 地址。

**Why:** Charlie 多次纠正，公网入口是 DuckDNS + FRP 链路，不是 Tailscale。Tailscale Funnel 是备用方案。

**How to apply:**
- 给手机/外部设备提供地址时，用 `charlie1990.duckdns.org:<端口>`
- SSH: `ssh -p 2223 charlie@charlie1990.duckdns.org`
- Launcher: `http://charlie1990.duckdns.org:17699/`
- OpenCode Web: `http://charlie1990.duckdns.org:19890/`
- Tailscale Funnel (`nixos-1.tail60cff7.ts.net`) 仅作为备用提及
