---
name: wechat-reply-customer
description: 微信客户私聊自动回复 — 识别客户意图、生成专业回复、通过 MCP 发送
user-invocable: true
version: "1.0.0"
category: wechat-agent
tags: [wechat, customer-service, auto-reply, mcp]
effort: medium
---

# 微信客户自动回复

## 场景
客户通过微信私聊发送消息时，AI 自动识别意图并生成专业回复。支持：询价、技术支持、售后、物流查询、投诉处理。

## 前置条件
- 微信 MCP Server 已注册到 opencode.json
- Windows Bridge (WeChatFerry) 运行中
- 环境变量 `WECHAT_BRIDGE_URL` 已配置

## 工作流

### 1. 获取未读消息
```
使用 MCP 工具: get_recent_messages
参数: limit=20, chat_type="private"
```

### 2. 意图分类
对每条消息进行意图识别：
- **询价** → 提取产品关键词，查询价格表，生成报价
- **技术支持** → 匹配 FAQ 库，给出解决方案
- **物流查询** → 调用物流 API 或查询 ERP 系统
- **投诉** → 安抚话术 + 升级标记
- **闲聊** → 礼貌简短回复

### 3. 生成回复
规则：
- 语气：专业、礼貌、简洁
- 长度：≤ 200 字
- 禁止：发送链接（除非用户主动要）、推销、承诺具体折扣
- 包含：称呼 + 核心回复 + 结束语

### 4. 发送消息
```
使用 MCP 工具: send_text_message
参数: wxid="目标wxid", content="回复内容"
```

### 5. 记录 CRM
调用 `wechat-crm-sync` skill 更新客户档案。

## 封号防护
- 同一联系人 5 秒内不重复发送
- 单日发送上限 200 条
- 凌晨 2:00-8:00 静默（不自动发送，仅记录待回复）

## 示例
```
用户消息: "你好，请问你们的产品A多少钱？"
AI回复: "您好！感谢咨询。产品A 目前零售价 ¥299/件，批量采购（≥50件）可享 8.5 折优惠。需要我发详细规格给您吗？"
```
