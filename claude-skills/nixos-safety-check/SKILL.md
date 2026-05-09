---
name: nixos-safety-check
description: "nixos-rebuild/flake-update前的安全预检：(1) grep memory/检索历史故障 (2) nix flake check干跑 (3) 根分区<85% (4) 记录当..."
user-invocable: false
version: "1.0.0"
category: system
tags: [nixos, safety, pre-flight, rebuild]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Nixos Safety Check

## 场景
nixos-rebuild/flake-update前的安全预检：(1) grep memory/检索历史故障 (2) nix flake check干跑 (3) 根分区<85% (4) 记录当前generation用于回滚 (5) 列出当前失败服务作为基线。支持rebuild/update/restart三种操作模式。NEVER自动执行rebuild。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
