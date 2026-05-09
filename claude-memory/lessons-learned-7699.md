---
name: 7699 手机访问经验
description: 手机通过 7699 访问 AI Launcher 的完整链路和踩坑
type: reference
---

# 7699 手机访问 — 根因与修复

## 最终方案：Windows 端口转发中转
手机(Tailscale) → Windows(100.91.93.99:7699) → netsh portproxy → NixOS(7699)

Windows portproxy 已配置：
```
netsh interface portproxy add v4tov4 listenport=7699 listenaddress=0.0.0.0 connectport=7699 connectaddress=100.119.174.25
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=100.119.174.25
```

手机浏览器访问：`http://100.91.93.99:7699`

## 为什么不直连
- **局域网不通**：路由器有 AP 隔离（客户端隔离），手机和主机同网段但不互通
- **路由器进不去**：无法关闭 AP 隔离
- **Tailscale relay 慢**：所有设备走 DERP(旧金山)，延迟 300ms-1s
- **手机到 Windows Tailscale 是直连**（`-`），Windows 到 NixOS 走 relay

## OpenCode 升级
- 旧版 1.2.27 web 模式有 socket closed bug
- 升级到 1.14.38 后 HTTP 200 正常
- npm 包名：`opencode-ai`（不是 `opencode`）
- 插件不兼容：`opencode-stt` 依赖 `@opencode-ai/plugin@^0.1.0` 不存在

## 排查优先级（下次直接用）
1. `curl localhost:7699/health` — 服务端 OK？
2. 手机 `curl 192.168.2.100:7699` — 局域网通？
3. `tailscale status` — relay 还是直连？
4. 不要花时间调 sshd/Caddy — 先确认网络通道
