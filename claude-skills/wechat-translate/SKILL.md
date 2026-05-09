---
name: wechat-translate
description: 微信实时翻译 — 中英互译、多语言支持、术语库
user-invocable: true
version: "1.0.0"
category: wechat-agent
tags: [wechat, translate, bilingual, communication]
effort: low
---

# 微信实时翻译

## 场景
为微信对话提供实时翻译能力，主要用于：
- 外籍客户沟通（中文 → 英文/日文）
- 进口供应商对接（英文 → 中文）
- 跨语言群聊辅助

## 工作流

### 自动翻译模式
1. 接收外文消息 → 自动检测语言
2. 翻译为中文 → 附在回复中发送
3. 生成外文回复 → 发送给对方

### 手动翻译模式
```
用户输入: "/translate 你好，请问交货期是多久？"
AI回复: 
  EN: "Hello, could you please tell me the delivery time?"
  JP: "こんにちは、納期はどのくらいですか？"
```

## 翻译规则
- **商务场景**：正式用语，避免口语化
- **技术术语**：使用行业通用翻译（维护术语库）
- **数字/日期**：保留原始格式，不转换
- **货币**：标注汇率（如 ¥299 ≈ $41）

## 术语库
路径：`/mnt/ai/apps/wechat-agent/data/glossary.json`
```json
{
  "产品A": "Product A",
  "交货期": "lead time",
  "起订量": "MOQ (Minimum Order Quantity)",
  "定制": "customized / ODM"
}
```

## 支持语言
| 语言 | 代码 | 方向 |
|------|------|------|
| 中文 | zh | 双向 |
| 英文 | en | 双向 |
| 日文 | ja | 双向 |
| 韩文 | ko | 接收翻译 |
| 西班牙文 | es | 接收翻译 |

## 质量控制
- 翻译后自检：语法正确性、术语一致性
- 长文本（>500字）分段翻译再合并
- 不确定时标注 `[待确认]`
