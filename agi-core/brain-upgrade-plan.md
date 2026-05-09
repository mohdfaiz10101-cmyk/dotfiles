# AGI Brain 2026 Upgrade Plan
> 基于全量历史分析 | 2026-05-06

## 现状评估

### 优势
- Sense→Think→Act 主循环稳定运行，60s轮询+hash去重+RateGuard
- LiteLLM 19模型网关，模型路由分层合理
- Letta记忆+MCP+Telegram/Discord双通知
- 认知调制(Ne/Fe/Si) + 自动Flow触发(social_intelligence等)
- op-tasks.md 异步任务派发 + 黑名单/去重/冷却

### 瓶颈
- **Think层过薄**：155行，单次LLM调用无推理链，无工具调用能力
- **Sense层被轮询**：60s固定间隔，Hash Change才调LLM→仍有大量无效采集
- **Act层被限**：只能写op-tasks.md，不能自主执行多步任务
- **记忆单向**：写Letta但不读，LLM分析时无历史上下文
- **无学习闭环**：不追踪任务成败，不调整策略

## 升级路线（P0→P3）

### P0 — Think层升级：Tool-Aware Reasoning（本周）

**目标**：think.py从单次LLM调用升级为Agent式推理

**改动**：
1. 注入MCP工具到LLM上下文（letta_recall/search、claude-knowledge、wechat）
2. 推理链：`感知数据 → 查记忆(Letta recall) → 查知识库(knowledge search) → 生成决策`
3. 决策类型扩展：
   - `op_task`：写op-tasks.md（现状）
   - `direct_action`：直接调用工具执行（新）
   - `question`：向用户提问（新）
   - `delegate_cc`：复杂任务委托CC（新）

**技术**：GLM-5.1 function calling / tool use
**文件**：`agi/think.py` (+200行), `agi/think_tools.py` (新)

---

### P0 — 记忆闭环：从单向写入到双向感知

**目标**：LLM分析时自动注入相关历史上下文

**改动**：
1. think.py调用analyze前，先letta_search前3天的相关分析
2. SYSTEM_PROMPT追加：`## 最近3天类似场景的处理方式：{letta_results}`
3. 新增 `letta_letta_recall` 读取用户偏好/系统状态

**效果**：相同异常不重复告警，基于历史快速决策

---

### P1 — 事件驱动Sense：从轮询到订阅

**目标**：停止60s盲轮询，改为事件触发

**改动**：
1. systemd path units监听：
   - `/tmp/agi-brain-status.json` 变化 → 触发分析
   - `/tmp/chronos/*.json` 新文件 → 触发时间感知
   - Docker事件 (`docker events`) → 触发容器监控
2. brain.py主循环改为 `await asyncio.Event()` 等待而非sleep
3. 保留每5分钟心跳快照（写入Letta但跳过LLM分析）

**节省**：每天1440次采集 → ~50次有效触发，省token 95%+

---

### P1 — LangGraph状态机：线性→有状态工作流

**目标**：从线性管道升级为DAG工作流

**改动**：
1. 当前：`Sense → Think → Act`（永远是固定顺序）
2. 升级：`Event → Classify(urgent/routine) → Route → Execute → Verify → Learn`
   - urgent → 立即执行+通知
   - routine → 批量汇总分析
   - Verify: 执行后验证结果
   - Learn: 记录成功/失败反馈

**技术**：LangGraph StateGraph (pip install langgraph)
**优势**：支持分支、并行、重试、人工审批节点

---

### P2 — Autonomous Execution：从派任务到自主执行

**目标**：AGI Brain能自主完成多步操作（不仅是派发任务）

**改动**：
1. think.py新增 `execute_plan()` 函数：
   - 接过op_delegate职责，直接调用工具执行
   - 多步任务链：`查Letta→调API→写文件→发通知→验证`
2. 工具集扩展：
   - `systemctl restart <service>` — 服务自愈
   - `docker restart <container>` — 容器自愈
   - `curl health check` — 验证修复
   - `git commit/push` — 自动备份
3. 安全边界：高影响操作(rebuild/nixos)仍需CC审批

---

### P2 — Browser/Desktop Context Awareness

**目标**：AGI感知用户当前工作内容

**改动**：
1. `sensors/desktop_context.py`：`hyprctl clients -j` 获取当前窗口
2. `sensors/browser_context.py`：Playwright MCP 获取当前tab
3. think.py注入：`用户当前在{app}处理{file}，关联建议：{context}`

**已在规划**：op-tasks.md line 549 `Hyprland桌面感知接入AGI记忆`

---

### P3 — 学习反馈闭环

**目标**：追踪每次决策的结果，优化未来策略

**改动**：
1. 新表 `agi/feedback.db` (SQLite)：
   - task_id, decision, outcome, success, latency, model_used
2. 每周自动分析：哪些决策模式成功率高？哪些模型适合哪类任务？
3. 自动调整路由策略

---

### P3 — A2A协议标准化

**目标**：CC↔OP↔AGI Brain 正式Agent间协议

**技术**：Google A2A (Agent-to-Agent) 或自定义JSON-RPC
**改动**：
1. AGI Brain暴露 `/a2a/status` `/a2a/task` 端点
2. CC通过A2A协议委托AGI而非写op-tasks.md
3. 支持task生命周期：submitted→accepted→running→completed/failed

---

## 实施优先级

| 优先级 | 项目 | 收益 | 工作量 | 风险 |
|--------|------|------|--------|------|
| **P0** | Think层Tool-Aware | 决策质量↑300% | 2天 | 低 |
| **P0** | 记忆闭环 | 噪音↓80% | 1天 | 低 |
| **P1** | 事件驱动Sense | Token↓95% | 3天 | 中(sysd) |
| **P1** | LangGraph状态机 | 可维护性↑ | 3天 | 中(新依赖) |
| **P2** | 自主执行 | 自动化率↑ | 5天 | 高(安全) |
| **P2** | 桌面感知 | 个性化↑ | 2天 | 低 |
| **P3** | 学习闭环 | 长期优化 | 3天 | 低 |
| **P3** | A2A协议 | 标准化 | 2天 | 低 |

## 技术选型（2026最新）

| 技术 | 用途 | 替代 |
|------|------|------|
| **LangGraph** | Agent工作流引擎 | CrewAI/AutoGen(重量级) |
| **MCP Tools** | Agent工具调用 | Function Calling(已有) |
| **Instructor** | 结构化LLM输出 | response_format json(已有) |
| **A2A Protocol** | Agent间通信 | 自定义协议(可渐进) |
| **systemd path units** | 文件事件触发 | inotify(不稳定) |
| **Playwright MCP** | 浏览器自主操作 | CDP raw(已有) |
| **Hyprland IPC** | 桌面感知 | xdotool(不用) |
