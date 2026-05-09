---
name: timer-schedule-manager
description: "systemd timer调度管理，强制白天规则：所有OnCalendar timer必须在08:00-22:00之间执行。--audit扫描所有timer定义文件(timers.nix/ser..."
user-invocable: false
version: "1.0.0"
category: system
tags: [timer, schedule, maintenance, daytime-only]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Timer Schedule Manager

## 场景
systemd timer调度管理，强制白天规则：所有OnCalendar timer必须在08:00-22:00之间执行。--audit扫描所有timer定义文件(timers.nix/services.nix/disk-pool.nix/auto-services.nix)检查违规。--fix自动将违规timer移至白天。时间槽建议：08-09健康检查、09-12同步任务、12-15重型任务(prune/backup)、15-18报告通知、18-22提交非关键。22:00-08:00 FORBIDDEN。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
