---
name: cost-audit
description: "成本审计：追踪 LiteLLM 消耗、API 调用、本地模型使用率，超预算告警"
user-invocable: false
version: "1.0.0"
category: 运维
tags: [成本, 审计, LiteLLM, 预算]
effort: medium
auto-generated: true
created: 2026-04-24
---

# Cost Audit

## 场景
# 成本审计技能

## 功能
1. LiteLLM 调用统计（24h 模型分布）
2. API 余额检查（错误码 30001 检测）
3. 本地模型使用率（GPU 显存）
4. 预算告警（>70% 黄，>100% 红）

## 执行命令
```bash
# 模型调用统计
docker logs litellm-litellm --since 24h 2>&1 | grep -oP 'model=\S+' | sort | uniq -c | sort -rn

# 余额不足检查
docker logs litellm-litellm --since 24h 2>&1 | grep -c "30001"

# GPU 使用率
nvidia-smi --query-gpu=utilization.gpu,utilization.memory --format=csv,noheader,nounits
```

## 告警阈值
- 黄色：>70% 预算
- 红色：>100% 预算或余额不足


## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
