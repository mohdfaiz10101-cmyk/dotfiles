---
name: browser-cookie-sync
description: "多浏览器 Cookie 同步系统：Floorp→Chrome/Zen/BrowserOS，启动同步+实时推送"
user-invocable: false
version: "1.0.1"
category: system
tags: [cookies, browser, floorp, chrome, zen, browseros, sync]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Browser Cookie Sync

## 场景
多浏览器 Cookie 同步系统

## 架构
- 源浏览器：Floorp（cookies.sqlite）
- 目标：Chrome、Zen Browser、BrowserOS
- 同步服务器：localhost:9977（Python HTTP，SQLite 后端）

## 同步方式
1. 启动同步：browser-launch-with-cookies <browser> → 上传 Floorp cookies → 拉取写入目标浏览器
2. 实时推送：cookie-watcher.py（3s 轮询 Floorp cookies.sqlite mtime，10s 防抖）
3. 定时同步：sync-all-browser-cookies（5min cron，Firefox 系直推）

## 文件
- ~/.local/bin/upload-cookies-to-server — Floorp cookies POST :9977
- ~/.local/bin/sync-cookies-to-chrome — 多目标 Chromium DB 同步（自动发现 BrowserOS）
- ~/.local/bin/sync-all-browser-cookies — Firefox 系直接复制
- ~/.local/bin/cookie-watcher.py — 实时监控守护进程
- ~/.local/bin/browser-launch-with-cookies — 启动包装器
- ~/launcher/cookie-sync-server.py — 同步服务器（:9977）

## 注意事项
- Chrome/BrowserOS 使用加密 cookie（sync-cookies-to-chrome 写明文 value，encrypted_value 置空）
- BrowserOS 需首次启动创建 profile 后才能同步
- NixOS 运行 AppImage 需要 appimage-run 包装

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
