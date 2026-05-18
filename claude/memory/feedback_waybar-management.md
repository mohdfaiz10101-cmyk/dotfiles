---
name: Waybar 管理方式
description: Waybar 必须通过 systemd 管理，禁止手动启动
type: feedback
---

Waybar 由 home-manager 的 `programs.waybar.enable = true` 管理，自动创建 `waybar.service`。

**规则：只通过 systemctl --user 管理，禁止手动启动。**
- 重启：`systemctl --user restart waybar.service`
- 查看状态：`systemctl --user status waybar.service`
- 配置文件是 nix store 符号链接（只读），修改需走 nix rebuild 或临时替换为可写副本

**Why:** 手动 `waybar &` 会产生第二个实例，导致屏幕显示两条 bar。NixOS wrapper 产生 2 个进程（.waybar-wrapped + waybar）是正常的父子关系，只渲染 1 个 UI。

**How to apply:** 需要重载 waybar 配置时，一律用 `systemctl --user restart waybar.service`。
