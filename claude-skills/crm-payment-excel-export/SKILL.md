---
name: crm-payment-excel-export
description: "CRM客户付款记录导出Excel到桌面：从crm.db查询contacts+notes中的付款信息，用openpyxl生成带格式的xlsx，含客户/金额/日期/事由/业务员/财务列，自动保存到~/Desktop/"
user-invocable: false
version: "1.0.0"
category: finance
tags: [crm, excel, payment, openpyxl, export, finance]
effort: medium
auto-generated: true
created: 2026-04-25
---

# Crm Payment Excel Export

## 场景
CRM付款记录Excel导出流程：
1. 从crm.db的contacts表查询目标客户（LIKE匹配nickname/remark/company）
2. 解析notes字段中的付款信息（金额、日期、事由、追踪号）
3. 用openpyxl生成xlsx：蓝色表头、居中对齐、边框、列宽22
4. 保存到~/Desktop/付款记录-{date}.xlsx
5. 同时更新crm.db的notes字段追加付款记录

表头模板：客户 | 付款金额(¥) | 付款日期 | 付款事由 | 归属 | 业务员 | 财务 | 追踪号 | 备注
依赖：pip install openpyxl
crm.db路径：/mnt/ai/apps/wechat-agent/data/crm.db
注意事项：检查是否已有记录避免重复、notes追加而非覆盖

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
