---
name: agent-planner
slug: agent-planner
description: Agent 设计流程规划器 — 引导用户从需求到可执行方案，输出架构设计+文件清单+实施计划
category: agent-design
tags: agent,planner,architecture,workflow,design-pattern
created: 2026-04-25
---

# Agent 设计流程规划器

> 基于 Anthropic "Building Effective Agents" + OpenAI Agent SDK + LangGraph 最佳实践总结的可复用设计流程。

## 核心原则（死规则）

1. **简单优先**：从最简单方案开始，只在不够时加复杂度
2. **先分类后设计**：所有 agent 设计必须先过 Step1 分类
3. **输出可执行**：设计方案必须包含文件清单+代码骨架，不能只有文字描述
4. **与现有系统集成**：必须检查 memory/setup-plan.md 和已有 agents 避免重复

## 复杂度阶梯（L1→L3）

选择最简单够用的层级，禁止直接跳到 L3：

| 层级 | 模式 | 适用场景 | 例子 |
|------|------|---------|------|
| **L1** | 增强LLM调用 | 单次调用+检索/工具/记忆就能搞定 | 简单问答、格式转换 |
| **L2** | Workflow | 任务可拆成固定步骤，LLM在预定义路径上运行 | 文档处理管线、数据清洗 |
| **L3** | Agent | LLM需自主决策工具使用和步骤顺序 | 复杂编码、多文件重构 |

## 5种 Workflow 模式

根据需求选最简单够用的模式：

| 模式 | 一句话 | 选它当... | 例子 |
|------|--------|----------|------|
| **Prompt Chaining** | 上一步输出→下一步输入 | 任务有固定顺序的子步骤 | 大纲→检查→写正文 |
| **Routing** | 分类后分发到不同处理器 | 输入有明确类别需不同处理 | 客服分流、日志分析 |
| **Parallelization** | 多路并行→合并结果 | 子任务完全独立或需多视角 | 多维代码审查 |
| **Orchestrator-Workers** | 主控动态拆分→派发→合并 | 子任务不可预测 | 复杂编码agent |
| **Evaluator-Optimizer** | 生成→评价→循环优化 | 有明确质量标准需迭代 | 翻译、文案优化 |

## 设计流程（6步）

### Step1: 需求分类（Routing）

```
输入: 用户描述的需求
输出: agent类型 + 对应模板

分类维度:
├── 功能类型: 文档操作 / 系统运维 / 对话交互 / 数据处理 / 监控告警 / 网页操作
├── 交互模式: CLI脚本 / API服务 / 定时任务 / 交互对话 / 浏览器插件
├── 部署方式: Python脚本 / FastAPI服务 / systemd timer / Docker容器
└── 模型需求: 免费模型够用(巡检/格式化) / 需要付费模型(推理/编码)
```

检查清单:
- [ ] `grep -r "关键词" ~/.claude/skills/` — 有无现成 skill
- [ ] `grep -r "关键词" ~/.config/opencode/agents/` — 有无类似 agent
- [ ] 读 `memory/setup-plan.md` — 现有基础设施
- [ ] 读 `memory/MEMORY.md` — 用户偏好

### Step2: 复杂度评估

```
判断标准（满足任一就升一级）:

L1 → L2:
  - 需要多个步骤串行处理
  - 需要中间检查点验证
  - 需要程序化控制流程

L2 → L3:
  - 子任务数量/类型不可预测
  - 需要 LLM 自主选择工具
  - 需要从环境反馈中调整策略
  - 需要错误恢复和重试逻辑
```

### Step3: 接口设计（Agent-Computer Interface）

```
每个 agent 必须定义:

1. 输入接口: 用户怎么触发（CLI参数/API路由/自然语言）
2. 输出接口: 返回什么（JSON/文件/通知/前端面板）
3. 工具集:   需要哪些外部工具（文件操作/API调用/系统命令）
4. 错误处理: 失败怎么办（重试/降级/通知/标记[!]）

ACI 设计原则（Anthropic）:
- 给模型足够的"思考"空间再输出
- 格式贴近模型自然见过的文本格式
- 减少格式"开销"（避免需要维护行号/转义等）
- 像给初级开发者写文档一样写工具描述
```

### Step4: 架构输出

必须输出以下内容（不能只有文字描述）：

```markdown
## 架构设计

### 流程图（ASCII）
[用 ┌─┐ └─┘ │ ▼ → 组成]

### 文件清单
| 文件 | 用途 | 依赖 |
|------|------|------|

### 接口定义
[API路由 或 CLI参数 或 自然语言指令映射]

### 与现有系统集成
[复用哪些现有组件、需要新建哪些]

### 模型选择
[按 AGENT_FREE_ROUTE 选免费模型]
```

### Step5: 用户确认（Evaluator-Optimizer 循环）

```
输出方案 → 用户反馈 → 修正 → 再确认 → 最终方案

常见反馈:
- "太复杂了" → 降一级复杂度
- "加上XXX功能" → 补充到接口设计
- "能不能用YYY" → 替换技术选型
- "跟现有ZZZ冲突" → 调整集成方案
```

### Step6: 写入 op-tasks

最终方案确认后：
1. 拆分为具体实施任务
2. 标注 [CC] 或 [OP]
3. 写入 op-tasks.md
4. 通知 CC/OP 执行

## Agent 模板库

### 模板A: CLI工具型（L2 Prompt Chaining）
```
适用: 文档处理、格式转换、数据提取
结构: Python脚本 → main入口 → 解析参数 → 执行步骤链 → 输出结果
部署: ~/bin/xxx.py + 可选 systemd timer
模型: 免费（Qwen3-235B）或无LLM
```

### 模板B: API服务型（L2 Routing）
```
适用: 需要前端面板/多客户端调用的服务
结构: FastAPI → 路由分发 → 业务逻辑 → 返回JSON
部署: systemd user service + 前端面板组件
端口: 从 9800-9899 分配
模型: 按复杂度选（简单用免费，复杂用付费）
```

### 模板C: 监控巡检型（L1 增强调用）
```
适用: 定时健康检查、资源监控
结构: Bash/Python脚本 → 检查项 → 结果格式化 → 通知
部署: systemd timer（白天规则）
模型: 免费（Qwen3-235B/Cerebras Llama-8B）
```

### 模板D: 对话交互型（L3 Agent）
```
适用: 需要多轮对话+工具调用的场景
结构: LLM loop → 意图识别 → 工具调用 → 结果反馈 → 继续循环
部署: OpenCode agent + systemd 服务
模型: 按任务复杂度（GLM-5-turbo / Sonnet）
```

### 模板E: 编码构建型（L2 Orchestrator-Workers）
```
适用: 代码生成、多文件修改
结构: 主控拆分任务 → Worker执行 → 合并结果 → 验证
部署: 直接集成到 CC/Sisyphus
模型: GLM-Z-Air / Sonnet
```

## 端口分配规则

新 API 服务端口从以下范围分配（先 grep 确认未被占用）：
- 9800-9899: 业务API
- 9900-9999: 系统服务

## 主动推荐模式（PROACTIVE_RECOMMEND — 定时触发）

### 触发条件
memory-curator 或 CC 每周扫描时，执行以下推荐分析：

### Step0: 历史模式分析

```bash
# 1. 扫描 op-tasks + lessons-learned 的任务模式
grep -oP '\[OP\] \[.*?\]' op-tasks*.md | sort | uniq -c | sort -rn | head -10
grep -oP '\- \[.*?\] .*?：' lessons-learned.md | sort | uniq -c | sort -rn | head -10

# 2. 扫描 CC 对话中的重复主题
grep -i "每次\|重复\|又.*了\|总是" memory/*.md | head -20

# 3. 检查哪些任务类型没有专职 agent
# 已有agents: ls ~/.config/opencode/agents/
# 高频任务类型 vs agents覆盖 → 差集 = 推荐列表
```

### 推荐输出格式

```
[AGENT_RECOMMEND] 基于历史分析（{日期范围}，{N}个任务样本）

| 推荐Agent | 原因（历史频率） | 模型 | 类型 |
|-----------|-----------------|------|------|
| {slug} | "{场景}"出现{N}次，无专职agent | {免费模型} | {类型} |

是否创建？（自动写入 op-tasks / 用户确认）
```

### 决策阈值
- 同类任务 ≥3次/周 且 无对应 agent → **推荐创建**
- 同类任务 ≥5次/周 且 有对应 skill 但无 agent → **推荐升级 skill→agent**
- 同类任务 <3次 → **跳过**，维持 skill 级别

## 使用方式

### 被动模式（收到设计需求时）
Sisyphus 收到"设计一个xxx agent"任务时：
1. 调用此 skill
2. 按6步流程执行
3. 输出可执行方案
4. 用户确认后写入 op-tasks

### 主动模式（定时/会话启动时）
CC 每周或会话启动时：
1. 运行 Step0 历史模式分析
2. 按阈值筛选推荐
3. 输出推荐列表
4. 用户确认 → 走 Step1-6 设计流程
