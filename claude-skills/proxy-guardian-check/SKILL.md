---
name: proxy-guardian-check
description: "代理守护者巡检：检测FlClash代理状态（7890/7891端口）、出口IP、关键服务可达性（claude.ai/google/github）。用中文简洁输出。"
user-invocable: false
version: "1.0.0"
category: 系统运维
tags: [代理, FlClash, 巡检, 网络检测]
effort: medium
auto-generated: true
created: 2026-04-26
---

# Proxy Guardian Check

## 场景
# 代理守护者巡检

## 执行流程
1. 检查 FlClash 端口监听（7890/7891）
2. 检测出口 IP（curl https://api.ipify.org）
3. 检测关键服务可达性（claude.ai/google/github）
4. 输出简洁中文报告

## 输出格式
用表格展示状态（[OK]/[FAIL]），包含检测项、状态、详情三列

## 假阳性防护
systemctl --user show <svc> --property=Result 验证：Result=success → 正常完成，禁止误报失败

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
