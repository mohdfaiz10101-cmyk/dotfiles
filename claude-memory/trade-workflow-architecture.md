# 外贸工作流系统架构设计

## 系统目标
基于微信消息自动识别业务意图，为不同联系人分配对应工作流，实现业务流程自动化追踪。

## 核心概念

### 1. 工作流模板 (Workflow Template)
预定义的业务流程模板，每个模板包含多个步骤。

**示例模板：**

```json
{
  "id": "inquiry-to-order",
  "name": "询价到订单流程",
  "steps": [
    {"id": "step-1", "name": "确认产品需求", "required": true},
    {"id": "step-2", "name": "提供报价单", "required": true},
    {"id": "step-3", "name": "等待客户确认", "required": true},
    {"id": "step-4", "name": "确认付款方式", "required": true},
    {"id": "step-5", "name": "签订合同", "required": true},
    {"id": "step-6", "name": "安排生产", "required": false},
    {"id": "step-7", "name": "发货", "required": false}
  ]
}
```

**其他模板：**
- `sample-request`：样品请求流程
- `production-update`：生产进度更新
- `delivery-tracking`：物流追踪
- `payment-followup`：付款跟进

### 2. 联系人工作流分配 (Contact Workflow Assignment)
每个联系人可以同时分配多个工作流实例。

**数据结构：**
```json
{
  "contact_wxid": "wxid_xxx",
  "workflow_instance_id": "inst-20260421-001",
  "workflow_id": "inquiry-to-order",
  "current_step": 3,
  "assigned_at": "2026-04-21T10:00:00",
  "completed_steps": ["step-1", "step-2"],
  "status": "in_progress"
}
```

### 3. 微信意图识别 (Intent Recognition)
自动识别微信消息中的业务意图，触发工作流分配。

**意图类型：**
- `INQUIRY`：询价（关键词：价格、报价、cost、price）
- `SAMPLE_REQUEST`：索要样品（关键词：样品、sample、样品费）
- `ORDER_CONFIRM`：订单确认（关键词：订单、order、确认）
- `PAYMENT`：付款相关（关键词：付款、payment、转账、定金）
- `PRODUCTION`：生产进度（关键词：生产、交期、delivery）
- `SHIPPING`：物流发货（关键词：发货、shipping、物流）
- `COMPLAINT`：投诉问题（关键词：问题、complaint、质量）

**识别逻辑：**
```python
def classify_intent(message: str) -> str:
    """根据消息内容识别业务意图。"""
    intent_keywords = {
        "INQUIRY": ["价格", "报价", "cost", "price", "FOB", "CIF", "MOQ"],
        "SAMPLE_REQUEST": ["样品", "sample", "样品费", "寄样"],
        "ORDER_CONFIRM": ["订单", "order", "确认", "确认数量"],
        "PAYMENT": ["付款", "payment", "转账", "定金", "deposit"],
        "PRODUCTION": ["生产", "交期", "delivery", "生产进度"],
        "SHIPPING": ["发货", "shipping", "物流", "提单", "B/L"],
        "COMPLAINT": ["问题", "complaint", "质量", "退货", "返工"]
    }

    for intent, keywords in intent_keywords.items():
        if any(kw.lower() in message.lower() for kw in keywords):
            return intent
    return "GENERAL"
```

### 4. 工作流自动派发 (Auto-Dispatch Engine)
根据识别的意图，自动为联系人分配对应工作流。

**派发规则：**
```json
{
  "INQUIRY": {
    "workflow_id": "inquiry-to-order",
    "start_step": 1
  },
  "SAMPLE_REQUEST": {
    "workflow_id": "sample-request",
    "start_step": 1
  },
  "ORDER_CONFIRM": {
    "workflow_id": "inquiry-to-order",
    "jump_to_step": 5  // 跳到"签订合同"步骤
  },
  "PAYMENT": {
    "workflow_id": "inquiry-to-order",
    "jump_to_step": 5  // 跳到"签订合同"步骤
  }
}
```

## 数据库Schema

### workflows（工作流模板表）
```sql
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    steps_json TEXT NOT NULL,  -- JSON数组：步骤列表
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### contact_workflows（联系人工作流分配表）
```sql
CREATE TABLE contact_workflows (
    id TEXT PRIMARY KEY,
    contact_wxid TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    current_step INTEGER DEFAULT 1,
    completed_steps_json TEXT,  -- JSON数组：已完成的步骤ID
    status TEXT DEFAULT 'pending',  -- pending/in_progress/completed/cancelled
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
```

### step_progress（步骤进度表）
```sql
CREATE TABLE step_progress (
    id TEXT PRIMARY KEY,
    contact_workflow_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending/in_progress/completed
    completed_at TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (contact_workflow_id) REFERENCES contact_workflows(id)
);
```

### wechat_intents（微信意图历史表）
```sql
CREATE TABLE wechat_intents (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    contact_wxid TEXT NOT NULL,
    intent TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_workflow_id TEXT
);
```

## 系统架构

### 组件1：微信消息监听器
- 监听微信消息（复用wechat_agent.py）
- 调用意图识别服务
- 触发工作流派发引擎

### 组件2：意图识别服务
- 接收消息内容
- 返回意图类型和置信度
- 记录到wechat_intents表

### 组件3：工作流派发引擎
- 根据意图查找对应工作流
- 检查联系人是否已有该工作流
- 创建新工作流实例或更新现有实例

### 组件4：3000控制台管理界面
- 显示联系人列表及其工作流
- 查看工作流进度（打勾/未完成）
- 手动调整步骤状态
- 发送催促消息

### 组件5：微信自动回复集成
- 根据当前工作流步骤生成回复
- 提醒联系人完成下一步
- 询问进度信息

## 工作流状态机

```
pending → in_progress → completed
           ↓
         cancelled
```

**状态转换规则：**
- `pending` → `in_progress`：联系人开始第一个步骤
- `in_progress` → `completed`：所有必需步骤完成
- `in_progress` → `cancelled`：客户取消订单
- `in_progress` → `in_progress`：步骤推进（更新current_step）

## 示例业务流程

### 场景1：客户询价
1. 客户微信："这个产品多少钱？FOB价格多少？"
2. 意图识别：`INQUIRY`
3. 派发工作流：`inquiry-to-order`（从step-1开始）
4. 系统回复："您好，我们的FOB价格是$XX/件，MOQ是100件。需要我发详细报价单吗？"
5. 工作流状态：step-1完成，current_step=2

### 场景2：客户确认订单
1. 客户微信："好的，确认下单1000件"
2. 意图识别：`ORDER_CONFIRM`
3. 派发工作流：`inquiry-to-order`（跳到step-5"签订合同"）
4. 系统回复："好的，我会发送正式合同给您确认。请确认付款方式：T/T 30%定金，70%发货前付清。"
5. 工作流状态：completed_steps=[step-1,2,3,4], current_step=5

## 实施计划

1. **Phase 1**：数据库Schema实现
2. **Phase 2**：意图识别服务开发
3. **Phase 3**：工作流派发引擎开发
4. **Phase 4**：3000控制台界面开发
5. **Phase 5**：微信自动回复集成
6. **Phase 6**：测试和优化
