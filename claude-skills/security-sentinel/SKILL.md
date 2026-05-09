---
name: security-sentinel
description: "安全哨兵巡检：检查SSH异常登录、端口异常、密钥泄露、高CPU/内存进程、防火墙状态"
user-invocable: false
version: "1.0.2"
category: 安全
tags: [ssh, 端口, 进程, 防火墙, 巡检]
effort: medium
auto-generated: true
created: 2026-04-26
---

# Security Sentinel

## 场景
# 安全哨兵巡检

## 功能
检查系统安全状态：
1. SSH异常登录（last -n 20）
2. 端口扫描（ss -tuln）
3. 密钥泄露（~/.ssh/authorized_keys）
4. 高CPU/内存进程（ps aux --sort=-%cpu | head -10）
5. 防火墙状态（systemctl status nftables）

## 执行
```bash
# SSH登录检查
last -n 20 | grep -v "reboot"

# 端口扫描
ss -tuln | grep LISTEN

# 密钥检查
cat ~/.ssh/authorized_keys 2>/dev/null

# 高CPU/内存进程
ps aux --sort=-%cpu | head -10
ps aux --sort=-%mem | head -10

# 防火墙状态
systemctl status nftables --no-pager
```

## 输出格式
```
[ok] SSH登录检查 → 结果
[ok] 端口扫描 → 结果
[ok] 密钥检查 → 结果
[ok] 高CPU进程 → 结果
[ok] 高内存进程 → 结果
[ok] 防火墙状态 → 结果
[完成] 安全哨兵巡检 — [OK/FAIL]风险等级
```

## 注意
- FALSE_POSITIVE_GUARD：systemctl is-active返回inactive不等于失败
- 必须用systemctl --user show <svc> --property=Result验证
- Result=success为正常完成（oneshot/timer），禁止升级为失败任务

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
