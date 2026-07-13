# Runbook: DuckDNS DDNS

DuckDNS 动态域名更新，映射 `charlie1990.duckdns.org` 到路由器 WAN IP。

## Desired State

- `duckdns-update.timer` — 每 300s 触发 `wan-ip-monitor.sh`
- `wan-ip-monitor.sh` 读取路由器 `wan0_ipaddr` 并提交给 DuckDNS
- 域名 `charlie1990.duckdns.org` 解析到路由器真实 WAN IP

## Verify

```bash
systemctl --user is-active duckdns-update.timer
# 当前解析
dig +short charlie1990.duckdns.org
# 路由器 WAN IP
/usr/bin/sshpass -p admin ssh -o StrictHostKeyChecking=no admin@192.168.123.1 'nvram get wan0_ipaddr'
```

## Known Issues

- 不要从 Fedora 本机出口 IP 更新 DuckDNS（可能走代理/VPN）
- 必须读取路由器 `wan0_ipaddr` 提交，空 `ip=` 参数会清零 DNS 记录
- 60s 更新频率已被审计标记为资源浪费，已调整为 300s
