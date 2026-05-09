---
name: proxy-diagnose
description: "3层代理系统诊断：Tier1 Xray Inbound(检查xray服务+7890/7891端口+本地代理curl测试)、Tier2 Mihomo Outbound(检查mihomo服务+909..."
user-invocable: false
version: "1.0.0"
category: system
tags: [proxy, network, xray, mihomo, diagnose]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Proxy Diagnose

## 场景
3层代理系统诊断：Tier1 Xray Inbound(检查xray服务+7890/7891端口+本地代理curl测试)、Tier2 Mihomo Outbound(检查mihomo服务+9090 API+活跃代理组)、Tier3 Watchdog(检查watchdog timer+最近日志+自动恢复)。支持--full全量延迟测试、--fix自动修复（重启失败服务/切换备用组/重新生成xray config）。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
