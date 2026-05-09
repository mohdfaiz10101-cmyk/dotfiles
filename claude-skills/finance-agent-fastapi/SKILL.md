---
name: finance-agent-fastapi
description: "FastAPI财务Agent模板：银行卡CRUD+OCR账单识别+JSON文件存储+systemd服务+React三栏面板"
user-invocable: false
version: "1.0.0"
category: finance
tags: [fastapi, finance, ocr, litellm, react, systemd]
effort: medium
auto-generated: true
created: 2026-04-23
---

# Finance Agent Fastapi

## 场景
后端: FastAPI+uvicorn，JSON文件存储(600权限)，LiteLLM视觉OCR(doubao主+claude备用)，还款提醒计算。前端: 三栏布局(卡片列表/详情/OCR+交易)，Catppuccin Mocha风格，拖拽上传图片OCR。服务: systemd user service，venv路径/home/charlie/agi/.venv。端口检查: 先检查占用再选择备用端口。

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
