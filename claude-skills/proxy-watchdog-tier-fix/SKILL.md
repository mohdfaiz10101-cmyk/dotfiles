---
name: proxy-watchdog-tier-fix
description: "修复 proxy-watchdog 主从配置倒置：默认 tier 与恢复逻辑不一致导致主力代理被周期性停掉"
user-invocable: false
version: "1.0.0"
category: proxy
tags: [proxy, mihomo, watchdog, nixos, tier]
effort: medium
auto-generated: true
created: 2026-04-24
---

# Proxy Watchdog Tier Fix

## 场景
症状：mihomo 运行不到5分钟被停，watchdog 日志出现 'Recovered to xray (tier 1)'\n根因：proxy.nix proxyWatchdog 脚本 CURRENT 默认 echo "xray"，if CURRENT != "xray" 触发恢复到 xray\n修复：\n1. echo "xray" → echo "mihomo" (默认状态)\n2. if [ "$CURRENT" != "xray" ] → if [ "$CURRENT" != "mihomo" ]\n3. 恢复目标从 xray → mihomo\n4. 故障转移顺序：stop xray + restart mihomo → xray → free\n5. 立即生效：sudo sh -c 'echo mihomo > /run/proxy-watchdog-state'\n6. 然后 nixos-rebuild（restartIfChanged=false 保护代理不断）

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
