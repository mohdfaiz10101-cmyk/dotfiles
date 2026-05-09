---
name: wechat-crm-sync
description: 微信联系人 CRM 同步 — 客户标签、沟通记录、关系图谱
user-invocable: true
version: "1.0.0"
category: wechat-agent
tags: [wechat, crm, contacts, sync, tags]
effort: medium
---

# 微信 CRM 同步

## 场景
将微信联系人信息同步到本地 CRM 数据库，维护客户标签、沟通历史、关系图谱。支持：
- 新联系人自动建档
- 标签分类（客户/供应商/同事/朋友）
- 沟通频率统计
- 最后联系时间追踪

## 前置条件
- 微信 MCP Server 运行中
- CRM 数据库路径：`/mnt/ai/apps/wechat-agent/data/crm.db`

## 数据库 Schema

### contacts 表
```sql
CREATE TABLE IF NOT EXISTS contacts (
  wxid TEXT PRIMARY KEY,
  nickname TEXT,
  remark TEXT,
  tags TEXT,  -- JSON array: ["客户","VIP"]
  company TEXT,
  phone TEXT,
  email TEXT,
  first_seen DATETIME,
  last_contact DATETIME,
  message_count INTEGER DEFAULT 0,
  notes TEXT
);
```

### conversations 表
```sql
CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  wxid TEXT,
  direction TEXT,  -- 'in' or 'out'
  content TEXT,
  timestamp DATETIME,
  summary TEXT,
  FOREIGN KEY (wxid) REFERENCES contacts(wxid)
);
```

## 工作流

### 1. 拉取联系人列表
```
使用 MCP 工具: list_contacts
```

### 2. 对比本地 CRM
- 新联系人 → 自动建档
- 已有联系人 → 更新昵称/备注变更

### 3. 自动标签建议
基于对话内容分析：
- 频繁询价 → 标记 "潜在客户"
- 技术讨论 → 标记 "技术对接"
- 付款记录 → 标记 "VIP"
- 超过 30 天未联系 → 标记 "待跟进"

### 4. 更新沟通统计
- 递增 message_count
- 更新 last_contact 时间戳
- 记录对话摘要到 conversations 表

## 查询接口
```
# 查找待跟进客户（30天未联系）
SELECT wxid, nickname, last_contact FROM contacts 
WHERE tags LIKE '%客户%' AND last_contact < datetime('now', '-30 days')
ORDER BY last_contact ASC;

# 高频联系人 Top 10
SELECT wxid, nickname, message_count FROM contacts 
ORDER BY message_count DESC LIMIT 10;
```

## 同步频率
- 全量同步：每日 08:00
- 增量同步：每次对话后自动更新
- 手动触发：`/wechat-crm-sync`
