# CC→OP 委托模式必要性评估

## 数据分析（op-tasks.md）
- **CC→OP 任务**：5 条（0.8%）
- **CC 直接任务**：64 条（10.4%）
- **AGI→OP 任务**：9 条（全部 SKIP，假阳性告警）

## 结论：CC→OP 模式**不必要**

### 原因
1. **OpenCode 已接管任务分配**
   - `macg_macg_op_delegate` 内部通过 `task()` 工具自动选择合适 agent
   - 无需 CC 手动写任务标签

2. **现有任务分类已足够**
   - `[CC]` - CC 直接诊断生成的任务（64 条）
   - `[SELF-IMPROVE]` - 代码审查任务
   - 无需中间层 "CC→OP" 标记

3. **假阳性问题严重**
   - 9 条 AGI→OP 任务全部 SKIP
   - 自动生成的任务质量低（AGI 无系统上下文）

## 建议调整

### 方案 A：移除 CC→OP 模式（推荐）
- **CC 直接写 `[CC]` 任务**
- **OP 通过 `task()` 自动路由**
- **删除 `cc-decision-engine.py` 中 `delegate_to_op` 调用**

### 方案 B：保留但简化
- **CC→OP 仅用于"需要 OP 手动干预"的场景**
- **自动化任务直接写 `[CC]`**
- **区分度更高**

## 立即行动
1. 停用 `cc-decision-engine.timer`
2. 保留 `[CC]` 标签用于诊断任务
3. 移除 `CC→OP` 生成逻辑