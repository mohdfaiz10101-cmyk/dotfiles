---
name: nixos-rebuild-guard
description: "NixOS rebuild 前置安全检查+rebuild后冒烟测试：循环依赖检测+/mnt挂载依赖检测"
user-invocable: false
version: "1.0.0"
category: nixos
tags: [nixos, systemd, safety, rebuild]
effort: medium
auto-generated: true
created: 2026-04-24
---

# Nixos Rebuild Guard

## 场景
preflight检查A:PartOf+After同target循环依赖 检查B:/mnt符号链接缺After；smoketest检查xdg-portal符号链接+home-manager After=mnt-ai.mount+无循环依赖

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
