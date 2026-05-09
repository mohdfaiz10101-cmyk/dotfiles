---
name: docker-cleanup
description: "按需Docker清理（周度timer的按需版本）：(1) docker system df显示总用量 (2) 列出停止的容器/悬空镜像/未用卷 (3) 显示预估可回收空间 (4) --dry-r..."
user-invocable: false
version: "1.0.0"
category: system
tags: [docker, cleanup, disk, images, containers]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Docker Cleanup

## 场景
按需Docker清理（周度timer的按需版本）：(1) docker system df显示总用量 (2) 列出停止的容器/悬空镜像/未用卷 (3) 显示预估可回收空间 (4) --dry-run只预览不删除 (5) 默认docker system prune -f (6) --all模式docker system prune -a -f --volumes (7) 清理后验证df -h。NEVER删除运行中容器。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
