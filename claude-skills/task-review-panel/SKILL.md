---
name: task-review-panel
description: "任务审查系统部署：解析 op-tasks.md → 分类(自动化/流程化/归档/待处理) → Hub API 端点 → 前端看板面板三列布局"
user-invocable: false
version: "1.0.0"
category: ops
tags: [task-review, op-tasks, kanban, hub-api, nextjs]
effort: medium
auto-generated: true
created: 2026-04-25
---

# Task Review Panel

## 场景
1. 分析脚本 ~/bin/task-review.py：parse_tasks→compute_frequency→classify_tasks→写 task-review.json\n2. Hub API 追加 /task-review GET + /task-review/feedback POST + /task-review/run POST\n3. 前端 TaskReviewPanel.tsx：stats卡片+三列看板+待处理列表+历史时间轴，30s轮询\n4. page.tsx 注册 PANEL_MAP task-review\n5. Sidebar.tsx 追加 ClipboardList tab 到 monitor 组

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
