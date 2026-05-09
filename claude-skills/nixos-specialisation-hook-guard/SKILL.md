---
name: nixos-specialisation-hook-guard
description: "NixOS specialisation(noGUI/Recovery)启动时自动跳过危险Stop hook，防止配置被误改"
user-invocable: false
version: "1.0.0"
category: nixos
tags: [nixos, specialisation, hook, guard, recovery]
effort: medium
auto-generated: true
created: 2026-04-24
---

# Nixos Specialisation Hook Guard

## 场景
在 Stop hook 脚本顶部（shebang后第一行）加入检测：grep -qE 'nixos-system-(noGUI|recovery|Recovery|F3)' /proc/cmdline 2>/dev/null && exit 0 | 适用脚本：cc-rule-extractor.sh / opencode-config-guard.sh / cc-autoskill-hook.sh / cc-decision-learner.sh / nixos-full-sync | 原理：NixOS specialisation boot时 /proc/cmdline 的init=路径包含specialisation名称

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
