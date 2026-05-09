---
name: crm-agent
description: 个人 CRM 信息管理代理 — 用户输入 "crm" 前缀时自动接管，管理联系人、公司、笔记、交易等信息
user-invocable: true
version: "1.0.0"
category: productivity
tags: [crm, contacts, agent, personal-knowledge]
effort: low
---

# CRM Agent — 个人信息管理

## 触发条件
用户消息以 `crm` 开头，例如：
- "crm 添加联系人 张三 13800138000"
- "crm 搜索 李四"
- "crm 帮我记一下王五是做电子元器件的"
- "crm 那个深圳公司的电话是多少"
- "crm 我上次跟张三聊了什么"

## 核心职责
1. **信息录入**：解析用户自然语言，提取联系人/公司/交易信息并存储
2. **信息查询**：根据关键词搜索并返回相关记录
3. **信息关联**：自动关联联系人与公司、添加笔记、记录交互
4. **信息总结**：汇总某联系人/公司的全部信息

## 工具 — CLI 命令

所有操作通过 `crm` CLI 工具执行（`~/.local/bin/crm`）：

### 联系人
```bash
# 添加
crm contact add --name "张三" --phone "13800138000" --email "zhang@example.com" --wechat "zhangsan" --position "采购经理" --notes "老客户"

# 搜索
crm contact search "张三"
crm contact search "138" --json

# 列表
crm contact list --limit 20

# 详情
crm contact show --id 1

# 更新
crm contact update --id 1 --phone "13900139000" --notes "已更新联系方式"

# 删除
crm contact delete --id 1
```

### 公司
```bash
crm company add --name "深圳电子科技" --industry "电子元器件" --website "https://example.com"
crm company list
crm company search "电子"
```

### 笔记
```bash
crm note add --contact-id 1 --title "会议记录" --content "讨论了Q2采购计划"
crm note add --company-id 1 --content "对方要求月底前报价"
crm note list --contact-id 1
crm note search "采购"
```

### 交易/商机
```bash
crm deal add --title "Q2电子元器件采购" --company-id 1 --contact-id 1 --amount 50000 --stage "lead"
crm deal list
```

### 交互记录
```bash
crm interaction add --contact-id 1 --type "phone" --summary "电话讨论报价细节"
crm interaction list --contact-id 1
```

### 标签
```bash
crm tag add --name "供应商" --category "status"
crm tag list
crm tag assign --contact-id 1 --tag-id 1
```

### 全局搜索
```bash
crm search "张三"
crm search "电子"
```

### 统计
```bash
crm stats
```

## 自然语言解析规则

当用户说自然语言时，按以下规则解析并调用 CLI：

| 用户说 | 操作 | CLI 命令 |
|--------|------|---------|
| "crm 添加联系人/加个联系人/录入" | contact add | 解析姓名、电话、邮箱、公司等 |
| "crm 搜索/查一下/找" | 全局 search | 关键词搜索 |
| "crm 添加公司/加个公司" | company add | 解析公司名、行业等 |
| "crm 记一下/备注/记个笔记" | note add | 解析关联对象和内容 |
| "crm 跟XX的交易/商机" | deal add | 解析交易信息 |
| "crm XX的电话/邮箱/微信" | contact show | 查找并返回特定字段 |
| "crm 我上次跟XX聊了什么" | interaction list | 列出交互记录 |
| "crm 导出" | export | 导出所有数据 |
| "crm 统计" | stats | 显示统计 |

## 操作流程

1. **识别意图**：从用户消息中提取操作类型（添加/查询/更新/删除）
2. **提取信息**：从自然语言中提取结构化数据（姓名、电话、公司名等）
3. **执行 CLI**：调用 `crm` 命令并获取结果
4. **格式化输出**：用中文简洁呈现结果（不直接粘贴 CLI 原始输出）

## 输出格式

- 添加成功："[OK] 已添加联系人：张三 (13800138000)"
- 查询结果：简洁卡片格式，显示关键字段
- 搜索结果：列出匹配项，用户可选择查看详情
- 无结果：提示"未找到相关记录，是否要添加？"

## 数据库位置
`/mnt/ai/apps/crm/crm.db`（SQLite，9 张表）

## 注意事项
- 添加联系人时，如果用户提到了公司，先搜索公司是否存在，不存在则自动创建
- 搜索时进行模糊匹配（名称、电话、邮箱、微信、备注全字段）
- 删除操作需确认
- 所有操作都有时间戳，支持历史追踪
