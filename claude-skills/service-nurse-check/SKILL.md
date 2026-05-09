---
name: service-nurse-check
description: "Service-Nurse巡检：Docker容器状态+systemd服务+磁盘空间+关键端口可达性"
user-invocable: false
version: "1.0.0"
category: 运维
tags: [巡检, systemd, docker, 健康检查]
effort: medium
auto-generated: true
created: 2026-04-26
---

# Service Nurse Check

## 场景
执行systemctl --user list-unions --type=service --state=running,failed和docker ps检查，验证Letta/LiteLLM API连通性，输出简洁中文状态报告

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
