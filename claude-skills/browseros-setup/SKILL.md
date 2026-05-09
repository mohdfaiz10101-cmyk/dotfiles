---
name: browseros-setup
description: "BrowserOS AI 浏览器安装配置（NixOS AppImage 方式）"
user-invocable: false
version: "1.0.0"
category: system
tags: [browseros, appimage, nixos, browser, ai]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Browseros Setup

## 场景
BrowserOS — AI 原生浏览器（Chromium fork）

## 安装
- AppImage: ~/Apps/BrowserOS.AppImage（274MB）
- NixOS 启动需 appimage-run 包装
- 配置目录：~/.browseros/（SOUL.md、memory、sessions、skills）

## 启动
- 直接：appimage-run ~/Apps/BrowserOS.AppImage --no-sandbox
- Cookie 同步：browser-launch-with-cookies browseros
- 桌面菜单：BrowserOS (Cookie Sync)

## Cookie 同步
- Chromium cookie 格式，位于 ~/.config/BrowserOS/Default/Cookies
- sync-cookies-to-chrome 自动发现并写入
- 首次启动后才创建 cookie DB

## 网站
https://www.browseros.com/

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
