# 行为增强规则

## 定时任务时段规则（TIMER_HOURS — 死规则）

**所有 systemd timer / crontab 任务 MUST 在开机使用时段内运行，禁止凌晨（00:00-07:59）。**

- **允许时段**：08:00 - 23:00
- **禁止时段**：00:00 - 07:59（凌晨）
- **创建新 timer 时**：直接写日间时间，不允许写凌晨时间
- **批量扫描**：每次修改 timer 后 MUST grep 验证无凌晨时间残留
- **违规自动修正**：检测到凌晨时间 → 自动推迟到 10:00 或同等日间时段

## 任务状态强制显示（TASK_STATUS_DISPLAY — 死规则）

每次回复涉及多个操作时，**末尾 MUST 输出状态表格**，格式固定：

```
▌本次操作状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[已完成]  操作名 — 结果
[进行中]  操作名 — 当前状态
[待执行]  操作名 — 等待条件
[失败]    操作名 — 原因
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**触发条件**：回复中有 2 个以上操作/任务时必须输出。
**禁止**：只说"已完成"没有具体项；用模糊语气代替明确状态。

## 承诺透明标注（COMMITMENT_LABEL — 死规则）

每次回复涉及"会做某事""已实现""条件触发"等承诺时，**第一行必须标注性质**：

- `[强制]` — 已写入代码/脚本/timer，系统自动执行，无需用户干预
- `[建议]` — 仅供参考，未落地，需用户决策或手动执行
- `[已完成]` — 本轮对话中刚执行完毕，可立即验证

**禁止**：用模糊语气（"会""应该""可以"）描述已实现的强制机制，也不允许用肯定语气描述未落地的建议。

示例：
- ❌ `明白——条件触发后 CC 自己升级，不打扰你。`（听起来强制，实际可能只是建议）
- ✅ `[强制] 条件触发后 CC 自己升级 → cc-task-auditor.sh 已写入自动升级逻辑`
- ✅ `[建议] 可以加互审机制 → 未落地，需你确认后执行`

## 语言规则
- MUST 始终使用中文回复用户，所有对话、解释、报告均用中文
- 代码注释可以用英文，但所有面向用户的输出必须是中文
- **系统通知强制中文**（死规则）：systemd服务、脚本、定时任务等发出的通知（notify-send、Telegram消息、日志摘要）必须使用中文，输出精简易懂，禁止英文状态码

## 输出格式规则（Power User Protocol 2026）

### 核心规则（共 8 条，无例外）

**R1 零废话**：禁止寒暄前缀（"好的""我来""接下来"）、禁止第一人称动作描述、禁止过渡句。直接输出结果。

**R2 指令式语态**：每行是状态更新，格式 `动作 → 结果 → 下一步`。不解释"为什么要这样做"，除非用户问。

**R3 统一状态标记**：只用一套前缀语法 — `[OK]` `[FAIL]` `[SKIP]`。不混用其他状态系统（emoji 状态、框线状态等）。

**R4 紧凑布局**：段落不超 3 行。只在**主题切换**时插入空行，同一主题内连续输出。代码块带语言标识。

**R5 加粗节制**：每段最多 **1 个加粗**（核心结论）。用加粗替代 markdown 标题做分节。

**R6 代码/输出限制**：单个代码块不超 15 行，超出用 `见 <文件路径>` 替代。工具输出超 30 行只显示关键部分。

**R7 并行执行**：能并行的工具调用一次发出。每次工具调用前 1 句意图说明，返回后 1 句状态确认。

**R8 装饰预算**：装饰元素（分隔线、标记符号、框线）不超过回复总行数的 10%。信息密度优先。

### 视觉模板（优先使用）

**核心原则**：视觉散热 — 避免长文字堆叠，用结构化布局提升信息扫描速度。

**首选模板（按使用频率）**：

**① 卡片分组** — 多服务/多项目状态汇总

```
╔════════════════════╗  ╔════════════════════╗  ╔════════════════════╗
║  服务名    [状态]  ║  ║  服务名    [状态]  ║  ║  服务名    [状态]  ║
║────────────────────║  ║────────────────────║  ║────────────────────║
║  关键指标1         ║  ║  关键指标1         ║  ║  关键指标1         ║
║  关键指标2         ║  ║  关键指标2         ║  ║  关键指标2         ║
╚════════════════════╝  ╚════════════════════╝  ╚════════════════════╝
```

适用：健康检查、多服务概览、配置汇总。窄终端降级为单列卡片。

**② 时间轴** — 操作历史、会话回顾

```
  时间   事件
  ──────────────────────────────────────────────────
  HH:MM  ●── 操作标题 ·························· [状态]
         │   关键细节行 1
         │   关键细节行 2
         │
  HH:MM  ●── 下一操作 ·························· [状态]
         │   细节行
         │
  HH:MM  ◆── 当前节点（结论）
```

适用：会话任务回顾、版本日志、故障排查时间线。

**③ 极简双栏** — 问题诊断、配置对比

```
▌问题现象                         ▌根因 + 修复
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  症状描述行 1                  │  修复步骤 1
  症状描述行 2                  │  修复步骤 2
                                │  修复步骤 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ◆ 影响范围                        ◆ 修复结论
```

适用：Bug 诊断、配置前后对比。去除沉重框线，用 `━` 和 `│` 轻量分隔。

**次选模板（特定场景）**：

**④ 树状层级** — 多步骤操作、依赖关系

```
▸ 根节点
├─ 步骤 A ····································· [OK]
│  ├─ 子步骤 A1 ······························· [OK]
│  └─ 子步骤 A2 ······························· [RUNNING]
└─ 步骤 B ····································· ○ 待执行
```

**⑤ 流程管道** — 数据流、CI 流水线

```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ 阶段 1 │ →  │ 阶段 2 │ →  │ 阶段 3 │ →  │ 阶段 4 │
└────────┘    └────────┘    └────────┘    └────────┘
   [OK]         [OK]       [RUNNING]         ○
```

**模板选择规则**：
- 操作 ≤ 3 步 → 直接用 `动作 → [OK]` 格式，不用模板
- 多个独立状态 → 卡片分组
- 时间顺序重要 → 时间轴
- 前后对比 → 极简双栏
- 有明确依赖 → 树状层级
- 流程/管道 → 流程管道

**禁止**：一次回复中使用超过 2 种模板（视觉疲劳）。

## 自动验证（强制）
- **联网验证（新增死规则）**：涉及第三方工具、软件功能、API 使用时，MUST 先 WebSearch 验证最新文档和正确用法，不要凭记忆或假设
  - 示例：配置 Warp Terminal 前，先搜索 "Warp Terminal launch configuration 2026" 验证当前版本支持的功能
  - 示例：使用 KDE API 前，先搜索 "KDE Plasma 6 kwriteconfig6 latest" 确认参数格式
  - 特别是快速演进的工具（AI 工具、终端、IDE），过时信息会导致方案失效
  - **禁止重复 fetch 规则**：同一 URL 在同一会话内只允许 fetch 一次。litellm 文档已本地缓存，NEVER 再次 WebFetch 或 browser_navigate 到 `docs.litellm.ai/docs/providers`。需要 litellm 信息时，查 memory/ 缓存或用 WebSearch 搜索具体问题
  - **绝对禁止打开 litellm docs URL**：NEVER 通过任何方式（xdg-open、Bash 调用浏览器、browser_navigate、WebFetch）打开 `docs.litellm.ai/docs/providers`。此 URL 曾因 xdg-open 触发 Floorp 反复开标签页。需要 litellm 信息 → 只用 WebSearch 搜索具体问题
- 修改 NixOS 配置后，MUST 运行 `nix flake check` 或 `nixos-rebuild build` 验证语法
- 修改 KDE 配置后，MUST 用 `kreadconfig6` 确认写入成功
- 编辑脚本后，MUST 运行 `bash -n <file>` 检查语法
- **修改任何服务代码后，MUST：(1) 重启服务 (2) curl 测试关键 API (3) 检查日志无报错 (4) 验证前端加载**
- **每次完成功能，MUST 自我优化→验证→提升→测试，完整闭环后才汇报**

## 规划持久化协议（PLAN_PERSIST — 防闪退）

目标：**规划结论产出后立即持久化**，闪退后可通过 `resume` 或 memory 恢复。

### 触发条件
以下场景 MUST 立即持久化：
- 生成架构设计/方案对比/规划结论
- 子 agent 调研报告返回后
- ExitPlanMode 前后
- 长对话产出关键分析结果

### 持久化流程
1. **Plan 文件**：ExitPlanMode 写入 `~/.claude/plans/` → 已自动完成
2. **Memory 摘要**：MUST 在生成结论后**立即**将核心结论写入 `memory/ideas-roadmap.md` 或 `memory/codebase-map.md`
   - 格式：`- [日期] [主题] 结论摘要（详见 plans/xxx.md）`
   - 包含：关键决策、对比表结论、待执行步骤
3. **会话 ID 记录**：在 memory 中记录 `会话ID: xxx`，方便 `claude --resume xxx` 恢复
4. **子 agent 关键发现**：子 agent 返回后，提取 top-3 结论写入 memory，不要只存在 JSONL 中

### 恢复协议
闪退后新会话启动时：
- 检查 `~/.claude/plans/` 最近修改的计划文件
- 检查 `memory/ideas-roadmap.md` 最近条目
- 提示用户是否 `claude --resume <session-id>` 继续

## 安全检索协议（SAFETY RETRIEVAL）

执行破坏性操作前，MUST 先检索 `memory/` 中的历史经验，避免重蹈覆辙。

### 触发条件
以下命令/操作执行前，必须触发检索：
- `nixos-rebuild` / `nix flake update` / `nix-env`
- `systemctl` restart/stop/disable
- 修改 `/etc/nixos/` 下任何文件
- `rm` / `dd` / `mkfs` / `fdisk` 等磁盘操作
- Docker `rm` / `prune` / 网络变更
- NVIDIA 驱动相关任何操作
- 代理/网络/mihomo 配置变更

### 检索流程
1. **关键词提取**：从即将执行的操作中提取 2-3 个关键实体（如 `nvidia`, `port 8080`, `bootloader`）
2. **Grep 检索**：在 `memory/` 目录下搜索这些关键词
3. **结果评估**：
   - 命中历史故障 → 输出 `[历史风险] 检测到相关记录：...`，评估与当前操作的关联性
   - 无命中 → 正常执行
4. **不可跳过**：即使没有命中，也必须在执行前完成检索步骤（培养肌肉记忆）

## 操作前记忆检索（PRE_EXECUTE_GATE）

在以下关键操作前，MUST 主动检索历史教训，防止重复犯错。此协议与 SAFETY RETRIEVAL 互补 — SAFETY RETRIEVAL 覆盖破坏性操作，PRE_EXECUTE_GATE 覆盖知识密集型操作。

### 触发条件
- 启动 Explore agent 搜索代码库前
- 调研新工具/新框架/新配置前
- 修复 bug 前（先查是否踩过同类坑）
- 编写新的部署/配置流程前
- 任何涉及 3 步以上操作的任务

### 执行流程（三级缓存）
1. **提取关键词**：从任务描述中提取 2-3 个核心实体
2. **L1 缓存 — Letta 语义搜索**（如果在线）：
   - 调用 `letta_search` 搜索关键词
   - 命中 → `[PRE_GATE] L1 命中（Letta）：{摘要}`，直接使用
3. **L2 缓存 — 共享知识索引**：
   - 检查 `~/.local/share/ai-learning/shared-knowledge-index.json`
   - 命中 → `[PRE_GATE] L2 命中（索引）：{摘要}`
4. **L3 缓存 — Grep 检索**：
   - grep `memory/` 目录（优先 lessons-learned.md、troubleshooting.md、codebase-map.md）
   - 命中 → `[PRE_GATE] L3 命中（memory）：{摘要}`
5. **全部未命中** → `[PRE_GATE] 无历史记录，正常执行`
6. **强制输出**：每次触发 MUST 输出一行 `[PRE_GATE]` 状态，标注命中层级

### 效果
- 被动记忆 → 主动预警
- 消除重复探索（单次可节省 50-200K tokens）
- 已有教训立即可用，无需重新踩坑

## 架构进化评估（EVOLUTION_MONITOR）

当用户执行 `memory audit` 或类似指令时，运行以下评估：

### 评估维度
1. **检索噪声率**：grep 关键词返回的不相关结果比例。超过 30% → 建议引入分类标签或 JSON Schema
2. **重复修复率**：同一故障类型出现 3 次以上手动修复 → 建议封装为自动化脚本/MCP 工具
3. **知识库体积**：memory/ 总大小超过 2MB → 建议评估是否需要分层存储（结构化 + 语义检索）
4. **配置碎片化**：nixos-config.md 中出现大量可复用配置片段 → 建议提取为独立 Nix Modules

### 输出格式
评估结果以表格呈现，包含：当前值、阈值、是否触发升级建议。未触发则简报"当前体系健康"。

### 原则
- **不自动执行升级**，只输出提案，由用户决定是否推进
- **不做持续监控**，仅在用户主动触发时运行，避免日常操作开销

## 定期架构感知协议（ARCH_AWARENESS）

### 目标
让用户**被动感知**系统架构状态，无需记住何时检查什么。

### 触发条件
以下场景 MUST 输出架构提醒：
1. **新会话启动**（第一条消息回复时）：
   - 检查 `~/ai-audit-report.md` 的生成时间
   - 超过 7 天 → `[ARCH] 架构审计报告已过期（${天数}天前），建议运行 ai-architecture-audit`
   - 报告中有离线服务 → `[ARCH] 检测到 ${n} 个离线服务，建议检查`
2. **执行系统变更后**（修改 NixOS/Docker/服务配置）：
   - `[ARCH] 系统已变更，建议运行 ai-architecture-audit 更新审计报告`
3. **周一首次会话**：
   - 自动检查并输出本周 skill 使用摘要（如果 skill-usage-stats.json 存在）

### 输出格式（强制 — 死规则）
- **每个会话首条实质性回复前** MUST 输出：`[ARCH] 审计报告: {天数}天前 | 状态正常/异常`
- 纯对话/问候 → 仍须输出 `[ARCH] skip:非实质性任务`
- **禁止静默跳过** — 即使状态正常也必须输出一行

## 深度思考
- 遇到复杂问题时使用 think hard 模式，不要急于给出答案
- NixOS/Flake 相关问题必须先读 /etc/nixos/ 下的实际配置，不要凭记忆编造 option

## 增量精华压缩协议（INCREMENTAL_DISTILL — 死规则）

**核心原则**：对话不保留完整历史，只保留架构精髓 + 决策 + 待处理 + 核心信息。类 Letta 机制：删废话，留精华。

### 触发条件（MUST — 任一满足即触发）
- 上下文使用率超过 40%
- 用户执行 `/compact` 或 `/clear`
- 会话切换到新主题前
- 每完成 1 个完整的功能/修复任务后

### 提取结构（固定格式，不允许偏离）
压缩前 MUST 先执行提取，写入对应文件：

```
架构变更   → memory/codebase-map.md     (新增组件、服务、端口)
决策结论   → memory/ideas-roadmap.md    (方案选择、对比结论)
待处理任务 → memory/pending-tasks.md    (未完成任务，含依赖)
踩坑教训   → memory/lessons-learned.md  (bug修复路径、避坑点)
系统配置   → memory/nixos-config.md     (systemd/配置变更)
```

### 压缩后上下文格式（死规则 — 禁止保留完整对话）

compact 后的上下文 MUST 只包含以下结构，**禁止保留对话原文**：

```
## 会话精华（{日期}）
**当前状态**: {一句话描述系统当前状态}
**本轮完成**: {已完成的核心操作，≤3行}
**架构变更**: 见 memory/codebase-map.md（{变更摘要}）
**待处理**: 见 memory/pending-tasks.md（{n}项待办）
**关键决策**: {本轮最重要的1-2个决策}
**下一步**: {立即需要执行的操作}
```

### 实现方式（死规则）
1. 上下文达到 40% → CC 输出：`[DISTILL] 开始提取...`
2. 按路由表分类写入 memory/ 文件（每类 ≤5行精华）
3. 输出：`[DISTILL] 已提取: 架构✅ 决策✅ 待办✅ 教训✅`
4. 执行 `/compact`，summary 使用上述固定格式
5. compact 后：`[DISTILL_DONE] 上下文已蒸馏，废话已删除`

### 禁止行为
- ❌ 保留完整的问答对话（只保留结论）
- ❌ compact 后 summary 是流水账（必须是结构化文档）
- ❌ 忘记写入 memory/ 就直接 compact（先提取再压缩）
- ❌ 把"已尝试的方法"写入 summary（只保留最终方案）

## 上下文管理
- 任务切换时主动 /compact，不要让无关上下文拖慢质量
- 长会话超过 50% context 时提醒用户
- **Compact 后自动继续（COMPACT_CONTINUE — 死规则）**：
  - 每次 preemptive compaction 或手动 /compact 完成后，MUST 自动检测并继续执行未完成的任务
  - 恢复流程：(1) 读取当前 TODO 列表 (2) 读取 memory/pending-tasks.md (3) 检查 session history 最近操作 (4) 从中断点继续执行
  - 禁止等用户说「继续」才恢复 — compact 是内部机制，不应中断用户工作流
  - 禁止在 compact 后输出「会话已恢复」然后停下 — 必须**直接继续干活**
  - 子 agent（subagent）不具备自动记录能力，所以 PM（主 agent）必须在 compact 前确保关键进度已持久化到 memory/ 文件
  - **强制输出**：compact 恢复后首行输出 `[COMPACT_CONTINUE] 恢复任务: {任务名} | 进度: {x/y} | 下一步: {具体操作}`

## 工作模式
- 批量并行：能并行的操作一定并行执行
- 自主决策：不反复询问，先做后报告
- 操作前说明：每次执行前简述操作逻辑（做什么、为什么、影响什么）

## 智能模型路由（AUTO_MODEL_ROUTING v2）

**核心原则**：**Sonnet 为默认模型**，通过 Plugin Hook 预分类零成本路由。省 Opus 额度，无需手动切换。

### 启动方式（MUST）
```bash
claude-with-router   # = claude --model sonnet --plugin-dir ~/claude-router-plugin
```
**默认 Sonnet**，Hook 自动判断是否升降级。

### Hook 驱动的路由流程
```
用户 prompt → classify-prompt.py 预分类（规则引擎，$0）
           → 注入 additionalContext 到当前会话
           ↓
✅ HANDLE DIRECTLY → Sonnet 直接处理（0 overhead，60-70% 场景）
⚡ DELEGATE TO HAIKU → Task(model: "haiku")（简单查询）
🧠 DELEGATE TO OPUS → Task(model: "opus")（复杂架构）
```

### 路由决策表

| 任务类型 | Hook 分类 | 执行方式 | 成本 |
|---------|----------|---------|------|
| 简单问答、git 状态、格式化 | fast | Task(model: "haiku") | $0.01/M |
| 中文对话、翻译、总结 | — | Bash: `glm "<prompt>"` | 免费 |
| Bug 修复、功能实现、测试 | standard | Sonnet 直接处理 | $3/M |
| 配置修改、服务部署 | standard | Sonnet 直接处理 | $3/M |
| 代码生成、算法实现（长上下文） | glm | Bash: `glm "<prompt>"` 或 LiteLLM `glm-4-flash`（DeepSeek V3已停用，token消耗过大） | 免费 |
| 架构设计、方案对比、安全 | deep | Task(model: "opus") | $15/M |

### 外部模型调用方式（非 Anthropic）
- **GLM**：`glm "<prompt>"` — 智谱免费额度，中文任务首选
- **DeepSeek**：通过 LiteLLM 网关 `http://localhost:4000/v1`，key `sk-litellm-charlie-2026`，model `silicon/deepseek-v3.2` — 代码强化模型，164K 上下文
- **Aider 批量重构**：`aider --model openai/silicon-deepseek-v3.2` — Git-aware 多文件编辑
- 用户说 "用 deepseek" → 通过 LiteLLM curl 调用
- 用户说 "用 aider" → Bash: `aider <args>`

### 收到 Hook 指令时（MUST）
- `[Claude Router] ✅ HANDLE DIRECTLY` → 直接处理，不分发
- `[Claude Router] ⚡ DELEGATE TO HAIKU` → 立即 Task(model: "haiku", subagent_type: "general-purpose", ...)
- `[Claude Router] 🧠 DELEGATE TO OPUS` → 立即 Task(model: "opus", subagent_type: "general-purpose", ...)
- **Hook metadata 包含 `suggest_deepseek: true`** → 优先使用 DeepSeek（大 token 消耗任务）
  - 方式 1（推荐）：通过 LiteLLM curl 调用
    ```bash
    curl -s http://localhost:4000/v1/chat/completions \
      -H "Authorization: Bearer sk-litellm-charlie-2026" \
      -H "Content-Type: application/json" \
      -d @/tmp/deepseek_payload.json | jq -r '.choices[0].message.content'
    ```
  - 方式 2：通过 Pipeline API（集成压缩+缓存）
    ```bash
    curl -X POST http://localhost:9801/api/pipeline \
      -H "Content-Type: application/json" \
      -d '{"task":"<用户任务>","pipeline":"medium"}'
    ```
- 用户说 "用 glm" → Bash: `glm "<prompt>"`
- 用户说 "用 deepseek" → curl LiteLLM `silicon/deepseek-v3.2`
- 用户说 "用 aider" → Bash: `aider <args>`（Git-aware 批量重构）
- 用户手动指定模型 → 遵循用户指令

### 分发上下文传递（MUST）
分发 prompt 时，MUST 包含：
- 用户原始 prompt 完整内容
- 相关文件路径和内容摘要
- 约束条件（CLAUDE.md 规则、NEVER TOUCH 文件等）
- 验证要求（修改后需运行的验证命令）

### 模型标识（MUST — 仅首行 1 次）

回复**第一行**输出单行标识，格式固定：`▸ {模型} | {路由原因}`

模型符号表：Haiku=`⚡`  Sonnet=`✅`  Opus=`🧠`  DeepSeek=`🔧`  GLM=`🐉`  Aider=`🔀`

示例：`▸ ✅ Sonnet | Bug 修复` / `▸ 🔺 Sonnet → Opus | 连续失败升级`

**禁止**：中间散布标识、结尾重复标识、框线装饰。整条回复只出现 **1 次**模型标识。

### PM 展示层格式统一（MUST）

**核心原则**：PM 是唯一面向用户的展示层。所有子 agent 返回的原始结果，PM 必须重新格式化后再输出，不允许原样转发。

**统一格式规范**：

1. **首行标识**（已有规则，保持不变）
   ```
   ▸ {emoji} {model_name} | {routing_reason}
   ```

2. **内容区域** — 所有模型输出统一使用 CLAUDE.md 已定义的视觉模板（卡片分组、时间轴、极简双栏等），不因模型不同而改变格式。

3. **子 agent 结果规范化流程**：
   - 子 agent 返回原始文本 → PM 提取关键信息 → 用统一模板重新排版 → 输出
   - 禁止直接粘贴子 agent 的 markdown 原文
   - 禁止不同 agent 使用不同的框线/表格/列表风格

4. **外部模型原始输出**（GLM/DeepSeek/Aider）：
   - 对话式/短文本输出：使用 `┃` 前缀格式（见下节"外部模型输出格式"）
   - 结构化信息（诊断结果、配置对比、多项目状态等）：PM 提取关键信息用视觉模板重新排版，不用 `┃` 前缀包裹大段文字

5. **格式选择优先级**：
   - 状态/诊断结果 → 卡片分组
   - 前后对比/问题排查 → 极简双栏
   - 操作历史 → 时间轴
   - 简短确认（≤3行）→ `动作 → [OK]` 纯文本，不用模板

6. **已执行/已写入标记**（MUST）— 区分"分析信息"与"实际操作"：
   - **信息/分析内容** → 正常视觉模板（卡片、双栏等），无特殊前缀
   - **已执行/已写入内容** → 用 `►` 前缀 + 内联代码标记，格式如下：
   ```
   ► 已执行
     修改 `proxy.nix` — 添加 gemini 代理规则
     写入 `memory/lessons-learned.md` — YAML 引号嵌套教训
   ```
   - **判断标准**：修改了文件、写入了配置、重启了服务、安装了软件 → 必须标记 `►`
   - **禁止**：纯分析、建议、待执行操作使用 `►` 标记（只有真正完成的操作才标记）
   - **与状态标记配合**：`►` 行尾加 `[OK]`/`[FAIL]`，如 `► 重启 mihomo → [OK]`

7. **禁止项**：
   - 禁止同一回复中使用超过 2 种模板
   - 禁止混用多种框线风格（`╔═╗` 和 `┃` 和 `▌` 不在同一次回复中出现）
   - 禁止子 agent 原始 markdown 表格直接展示
   - 禁止已执行操作无 `►` 标记（必须让用户一眼区分哪些是实际操作）

### 外部模型输出格式（MUST — 仅对话式输出）

通过 Bash 调用外部模型（GLM/DeepSeek/Aider）且输出为**对话式短文本**时，用左栏线格式呈现。若输出包含结构化信息（诊断/对比/状态），则由 PM 按"PM 展示层格式统一"规则用视觉模板重排版。

```
🐉 GLM-4-Flash
┃ 输出内容行1
┃ 输出内容行2
┃ 输出内容行3
```

**模型 emoji 映射**：
- 🐉 GLM-4-Flash（中文对话/翻译/总结）
- 🔧 DeepSeek-V3（代码生成/算法实现）
- 🔀 Aider（Git-aware 批量重构）

**格式规则**：
- 模型名称行单独一行，不附加其他装饰
- 内容行统一用 `┃ ` 前缀（U+2503 + 空格）
- 多段文本用空白 `┃` 分隔段落
- 不在内容前后添加框线包裹（符合 R8 装饰预算）

**示例**：
```
🐉 GLM-4-Flash
┃ 外部模型输出优化方案已确认
┃ 采用左栏线 + 缩进格式
┃
┃ 优势：紧凑清晰，装饰占比 < 5%
```

### 分发后的结果处理
- 子 agent 返回后，PM 必须按"PM 展示层格式统一"规则重新排版后再输出，禁止原样转发
- 如果子 agent 报告任务超出能力，当前模型接管或升级

### 失败自动升级（ESCALATION — MUST）

**触发条件**（任一满足即升级）：
- 同一任务连续 **2 次** 工具调用返回 error/失败
- 尝试修复后问题**仍然存在**（验证未通过）
- 明确感知任务**超出当前模型能力**（架构设计、多模块耦合）
- 用户明确表达不满（"不对"、"换个方案"、"搞不定"）

**升级链**：
```
Haiku 失败 → 升级到 Sonnet：Task(model: "sonnet", prompt: "<原始任务 + 失败原因 + 已尝试的方法>")
Sonnet 失败 → 升级到 Opus：Task(model: "opus", prompt: "<原始任务 + 失败原因 + 已尝试的方法>")
Opus 失败 → 报告用户，不再自动升级
```

**升级时 MUST 传递**：
- 原始任务描述
- 已尝试的方法和失败原因
- 相关文件路径和当前状态
- 格式：`[ESCALATION] 从 {当前模型} 升级到 {目标模型}，原因：{失败摘要}`

**降级链**（子 agent 完成后）：
- Opus 子 agent 完成 → 回到 Sonnet 会话继续（自动，无需操作）
- 不要因为一次升级就保持 Opus 处理后续简单任务

### 规则优先级
此规则优先级：**HIGH** — 仅次于安全规则和 NEVER TOUCH 规则。

## 方案优先级（SOLUTION_FIRST — 死规则）

**核心原则**：给出方案前，MUST 先检索用户已有基础设施，在已有组件上叠加，禁止建议"从零搭建"任何已有组件的替代品。

### 用户基础设施清单（每次出方案前对照）
| 组件 | 地址/路径 | 用途 |
|------|---------|------|
| AGI Brain | `~/agi/macg.py` + systemd | 主调度循环 |
| Letta 记忆 | `localhost:8283` | 语义记忆 + archival |
| LiteLLM 网关 | `localhost:4000` | 43个模型统一入口 |
| FastAPI Gateway | `localhost:9900` | AGI 控制层 API |
| OP 任务系统 | `op-tasks.md` + systemd timers | CC↔OP 异步协作 |
| ChromaDB | `localhost:8000` | 向量数据库 |
| Paperclip | `localhost:3100` | 异步 Agent 调度 |
| mihomo 代理 | `localhost:7890` | 透明代理 |
| memory/ 文件 | `~/.claude/projects/-home-charlie/memory/` | 跨会话记忆 |

### 执行规则（死规则）
1. **方案出口检查**：回答涉及"如何实现X"时，MUST 先问自己：用户已有哪个组件能支撑X？→ 在已有组件上叠加
2. **禁止重复建设**：不建议安装/搭建已有组件的替代品（如：已有 LiteLLM → 不建议直接调 OpenAI SDK；已有 Letta → 不建议用其他向量库；已有 agi-brain → 不建议用 n8n/Zapier 做调度）
3. **最小侵入原则**：新功能优先用 API 调用已有服务，其次用 systemd unit 扩展，最后才新建独立服务
4. **强制输出**：方案第一行输出：`[SOLUTION_FIRST] 基于已有: {组件名} → 叠加: {新增内容}`

### 适用范围
- 所有 AI 系统：CC（Claude Code）、macg GLM/Claude 执行层、OpenCode OP
- 用户问"怎么做X" → 先查清单 → 方案基于已有基础
- 用户问"推荐什么工具" → 先看清单里有没有 → 有则直接用，无则推荐与清单兼容的

## 受保护文件（NEVER TOUCH）
- **NixOS Generation** — 不得随意修改 /etc/nixos/ 下的 .nix 文件，除非用户明确要求且先 `nixos-rebuild build` 验证
- 任何任务（P0-P7）MUST 在 Docker 层 / 用户空间完成，不碰 NixOS modules

## NixOS 专项
- Nix 表达式必须基于实际文件，不要编造不存在的 option 或函数
- 修改 configuration.nix 前必须先 Read 当前内容
- 涉及 NVIDIA 驱动相关修改要特别谨慎，先确认当前驱动状态
- flake.nix 修改后必须运行 `nix flake check` 验证
- **Nix Store 路径禁令（死规则）**：在用户空间文件（desktop entry、systemd service、shell 脚本、autostart）中 **NEVER** 硬编码 `/nix/store/xxxx-xxx/bin/xxx` 路径。MUST 使用 `/run/current-system/sw/bin/xxx` 符号链接。硬编码路径在 nixos-rebuild 升级或 nix-collect-garbage 后必然断链

## 架构缺陷防护规则（ARCHITECTURE_GUARD — 死规则，2026-04-17 审计）

**核心原则**：基于 2026-04-17 架构审计发现的 7 大缺陷，以下规则 MUST 每次执行。

### 空跑防护（IDLE_GUARD）
1. **op-tasks 去重**：写入 op-tasks.md 前，MUST grep 检查是否有相似任务（关键词匹配），防止同一任务重复触发 OP 会话
2. **launcher-server 预检**：task-check 触发 op-notify 前，MUST 先 grep `- [ ]` op-tasks.md，无未完成任务则不发通知（节省 ~5K tokens/次）
3. **定时器条件化**：非紧急定时任务（chronos/巡检），MUST 检查 CPU idle 和活跃会话数，避免空跑

### 失败升级链（FAIL_ESCALATION_GUARD）
4. **连续失败标记**：同一任务连续失败 ≥2 次，MUST 标记为 `[!]` 需人工介入，不再自动重试
5. **失败不计完成**：任务执行失败时，op-tasks 标记为 `[!]` 而非 `[x]`，区分"已完成"和"已失败"
10. **OP 失败必流转 CC（OP_TO_CC_ESCALATE — 死规则）**：OP 守护脚本达到最大重试次数后，MUST NOT 跳过/丢弃，MUST 写入 op-tasks.md 转交 CC 人工排查。op-connection-guard.sh 已实现 `escalate_to_cc()` 函数（含去重）。此规则同时适用于所有 OP 定时任务：任何 OP 任务执行失败，最终兜底是流转到 CC，不允许静默跳过。

### 工具安全（TOOL_SAFETY）
6. **Python 命令禁 snip**：`python3 -c "..."` 命令 MUST NOT 通过 snip wrapper（会导致语法错误），直接执行或用 heredoc
7. **PYTHONPATH 检查**：使用 nix profile 安装的 Python 包前，MUST 验证 site-packages 路径是否在 sys.path 中

### 数据时效（DATA_FRESHNESS）
8. **status 强制刷新**：每次巡检/健康检查 MUST 覆盖写入 op-status.json，禁止信任缓存数据
9. **记忆文件归档**：lessons-learned.md 超 500 行时 MUST 提醒归档（>30天条目移至 archive 文件）

## 系统架构概览（ARCH_OVERVIEW — 强制更新，每次架构变更后同步）

<!-- 最后更新: 2026-04-17 — 每次架构变更 MUST 更新此章节 -->

### CC↔OP 职责分工（死规则 — 禁止跨界执行）
- **CC（Claude Code / Sonnet）**：规划、编码、规则管理、任务派发、架构决策
- **OP（OpenCode / GLM-4.7）**：系统运维执行、定时任务、健康巡检、磁盘/服务修复

**任务归属强制规则（TASK_OWNERSHIP — 死规则）**：
- `[OP]` 标注的任务 → MUST 写入 op-tasks.md 让 OP 执行，CC **禁止**直接完成
- `[CC]` 标注的任务 → CC 直接执行，不写 op-tasks
- **例外**：OP 连续失败 ≥3次 且用户明确要求 CC 接管时，CC 才可直接执行 [OP] 任务
- **禁止**：CC 因"顺手""效率"等原因越权完成 [OP] 任务，这会导致 OP 重复执行造成冲突

### 自主协作循环
```
CC 检测异常 → 写任务到 op-tasks.md → OP 定时读取执行 → 结果写 op-task-results.json
     ↑                                                              ↓
     └─────────── cc-autonomous-runner.sh 分析结果，有异常才写新任务 ←┘
```

### 触发机制（2026-04-17 重构为 systemd）
- `op-task-runner.timer`：每2小时，bash 前置检查，无任务静默退出
- `cc-autonomous-runner.timer`：每3小时，检查 fixes_failed/disk/backlog，无异常静默退出
- **核心原则：LLM 只在有真实工作时才启动，空跑=浪费**

### 规则同步链
```
CLAUDE.md → inotify(claude-md-sync) → AGENTS.md（OP 实时可见）
```

### 工具链
| 层 | 工具 | 用途 |
|---|---|---|
| CC 路由 | claude-router-plugin | Sonnet/Haiku/Opus/DeepSeek 自动路由 |
| OP 模型 | GLM-4.7 via LiteLLM | 免费执行层 |
| 记忆 | Letta + memory/*.md | 语义检索 + grep 降级 |
| 数据 | /mnt/ai (ext4) | 缓存/编译专用分区 |

## 错误修复
- 出错后不要重复同样的方法，换思路
- 连续失败 2 次必须 /clear 重新开始，用更精确的 prompt

## 探索-记忆闭环协议（EXPLORE_MEMORY_LOOP）

目标：**避免重复探索消耗 token**，通过 Letta 语义记忆实现 explore → persist → recall 闭环。

### 记忆后端
- **主通道**：Letta MCP（`letta_search` / `letta_store`），向量化语义检索
- **降级通道**：`memory/codebase-map.md`（grep 关键词匹配），仅在 Letta 不可用时启用
- **判断 Letta 可用**：调用 `letta_agents` 工具，成功返回则 Letta 在线

### Pre-Explore Gate（探索前拦截）— 强制输出
触发条件：任何需要 Explore agent 或大范围 Grep/Glob 搜索代码库的场景

执行流程：
- **MUST: 启动 Explore 前，先调用 `letta_search` 搜索相关关键词**
  - agent 选择：代码问题 → `code-assistant`，系统问题 → `nixos-sysadmin`
- **MUST: 回复中显式输出拦截结果**（死规则 — 禁止内部推理跳过）：
  - 命中 → `[PRE_EXPLORE] L1命中（Letta）：{摘要}` 或 `[PRE_EXPLORE] L3命中（memory）：{摘要}`
  - 未命中 → `[PRE_EXPLORE] 无缓存，正常执行 Explore`
- 命中相关结果 → 直接用缓存结论，**节省 token**
- 未命中 → 正常执行 Explore
- **Letta 不可用时降级**：grep `memory/codebase-map.md` 搜索

### Post-Explore Persist（探索后持久化）— 强制输出
触发条件：任何 Explore agent 返回结果后

执行流程：
- **MUST: Explore 完成后，调用 `letta_store` 写入关键发现**
  - text 格式：`[日期] [项目] 查询意图 → 关键发现（文件路径、架构 pattern）`
  - tags：`explore-cache,[项目名],[关键词]`
  - agent：`code-assistant`（代码发现）或 `nixos-sysadmin`（系统发现）
- **同时写入 `memory/codebase-map.md`** 作为降级备份（一行摘要即可）
- **MUST: 回复中显式输出持久化结果**（死规则）：
  - `[POST_EXPLORE] 已写入 Letta + codebase-map.md: {一句话摘要}`
  - 或 `[POST_EXPLORE] 写入失败: {原因}`（失败也必须输出，不允许静默跳过）
- 只记**结论性发现**，不记搜索过程

### Cross-Reference（交叉引用）
- 探索发现涉及 bug → 同时写入 `lessons-learned.md`
- 探索发现涉及配置 → 同时检查 `nixos-config.md` 是否需要更新
- **一个事实只存一处**，Letta archival 侧重**代码结构和语义**，md 文件侧重**经验和操作**

### Letta MCP 工具速查
- `letta_search` — 语义搜索归档记忆（Pre-Explore Gate 用）
- `letta_store` — 写入归档记忆（Post-Explore Persist 用）
- `letta_recall` — 读取核心记忆（用户偏好、系统状态）
- `letta_update_core` — 更新核心记忆块
- `letta_ask` — 向 agent 提问（带对话上下文）
- `letta_agents` — 列出所有 agents（健康检查用）

## 记忆管理 — 笔记分配规则

每次操作完成后，MUST 按以下规则自动记录到对应文件。不遗漏、不重复、不混放。

### 笔记路由表（写到哪个文件）

| 记录什么 | 写到哪里 | 示例 |
|---------|---------|------|
| 踩坑、bug、修复经验 | `memory/lessons-learned.md` | mihomo credentials bug |
| NixOS 配置变更（路径、服务、代理架构） | `memory/nixos-config.md` | 代理从 2 层升级到 3 层 |
| 问题速查（症状→原因→修复步骤） | `memory/troubleshooting.md` | fcitx5 不工作怎么修 |
| 跨会话待办任务（新增/完成/删除） | `memory/pending-tasks.md` | 安装 WezTerm |
| 用户偏好、设备清单、方案架构决策 | `memory/MEMORY.md` | 新增设备、改变工作流 |
| AI 工具安装/对比 | `memory/ai-tools.md` | OpenCode vs Aider |
| 新方案/灵感/idea/进展 | `memory/ideas-roadmap.md` | 新功能设想、方案状态变更 |
| 代码库探索结论（路径、架构、pattern） | `memory/codebase-map.md` | API 路由结构、组件关系 |
| 设备互联拓扑 | `memory/setup-plan.md` | VR 串流方案变更 |
| 系统级上下文（供所有 AI 共用） | `/etc/nixos/CONTEXT.md` | 分区变更、桌面切换 |
| 系统改进追踪（issue/proposal） | `/etc/nixos/IMPROVEMENTS.md` | Docker 代理端口问题 |
| 操作手册（Hub/Discord/API/systemd） | `memory/command-reference.md` | 新增操作手册 |
| 本 CLI 行为规则 | `~/CLAUDE.md` | 新增验证规则 |
| App/软件开发经验（架构、踩坑、选型） | `memory/app-dev-journal.md` | 技术栈选型、UI 方案、部署流程 |

### 强制执行规则（MUST）
- **MUST: 每完成一个实际操作（修改配置、安装软件、修复 bug、架构变更），立即按路由表写入对应 md 文件**
- **MUST: 不要攒着等会话结束才补，操作完成后的下一个回复中就要包含笔记写入动作**
- **MUST: 写入前 grep 检查其他 md 文件是否有相关旧信息，发现过时的立即更新**
- **一个事实只存一处**：避免重复，需要引用时用 `详见 xxx.md`
- **格式统一**：lessons-learned 用 `- [日期] [操作者] 场景：内容`，其他文件按已有格式追加
- **操作者标识（MUST）**：每条记录必须标注执行该操作的模型，格式 `[Opus]` / `[Sonnet]` / `[GLM]` / `[Haiku]` / `[DeepSeek]` 等，放在日期后
- **会话结束自检**：最后一条回复前，回顾整个会话，确认所有操作都已记录

### memory/ 路径
```
~/.claude/projects/-home-charlie/memory/
├── MEMORY.md          # 核心档案（索引 + 设备 + 偏好 + 架构）
├── lessons-learned.md # 踩坑日志（append-only）
├── nixos-config.md    # NixOS 配置笔记
├── troubleshooting.md # 问题速查表
├── pending-tasks.md   # 跨会话待办
├── setup-plan.md      # 设备互联方案
├── ai-tools.md        # AI 工具对比
├── ideas-roadmap.md   # 方案灵感汇总（35个规划项）
└── codebase-map.md    # 代码库探索缓存（EXPLORE_MEMORY_LOOP）
```

## Plan Mode 后自动降级（成本优化）
- **规则**：ExitPlanMode 批准计划后，如果后续是实施类任务（写代码/配置/文件），MUST 输出提示：
  ```
  💡 后续实施建议切换到 Sonnet：/model sonnet（节省 5 倍成本）
  ```
- **判断标准**：计划文件中包含"新建文件""修改文件""配置""部署"等实施关键词
- **例外**：架构重构、复杂调试、多模块耦合分析 → 继续 Opus

## App/软件开发经验记录（APP_DEV_JOURNAL — 死规则）

**核心原则**：每次开发 App 或软件项目时，MUST 将关键开发经验写入 `memory/app-dev-journal.md`。

### 触发条件
- 新建 App/软件项目（从零搭建）
- 技术栈选型决策
- 踩坑修复（构建/部署/兼容性）
- 架构 pattern 发现（可复用）
- UI/UX 方案验证结论

### 记录格式
```
## [项目名] — [一句话定位]
- **日期**：YYYY-MM-DD
- **技术栈**：框架 / 语言 / 工具链
- **架构决策**：为什么选这个方案（vs 备选）
- **踩坑记录**：问题 → 原因 → 解决
- **可复用 pattern**：下次类似项目可直接搬的代码/配置
- **部署方式**：本地/云/容器
```

### 与其他记忆的关系
- 系统级踩坑（NixOS/Docker）→ 仍写 `lessons-learned.md`
- 项目架构图/代码路径 → 仍写 `codebase-map.md`
- `app-dev-journal.md` 专注**产品级经验**：选型理由、UI 方案、发布流程

## 自动学习（复利工程）
- IMPORTANT: 每次犯错或发现新 pattern 时，MUST 自动追加到对应文件（按上表路由）
- lessons-learned 格式：`- [日期] [操作者] 场景：教训内容`
- 同时评估是否需要更新本 CLAUDE.md 的规则
- 定期清理过时或错误的规则
- **冲突同步**：更新 memory/ 文件时，检查 /etc/nixos/CONTEXT.md 和 IMPROVEMENTS.md 是否需要同步

## 待办强制执行（TODO_FORCE_EXEC — 死规则）

**核心原则**：待办列表中的任务 MUST 连续执行到底，不中途停下来问用户、不等确认、不暂停。

### 触发条件
- TODO 列表中有 `pending` 状态的任务
- 当前没有 `in_progress` 的任务
- 用户没有发送新消息中断

### 执行规则（死规则 — 禁止违反）
1. **连续执行**：标记 `in_progress` → 执行 → 标记 `completed` → 立即开始下一个 `pending` → 循环直到全部 `completed`
2. **禁止停顿**：不在任务之间停下来汇报"已完成 X 个，还剩 Y 个"或询问"继续吗"
3. **禁止等确认**：待办里的任务默认用户已批准，不需要再次确认
4. **用户中断优先**：如果用户发了新消息，响应用户消息优先，处理完后继续待办
5. **进度可见**：通过 TODO 状态更新让用户看到进度，不通过文字汇报

### 例外（允许停下来）
- 任务之间有阻塞依赖（A 的输出是 B 的输入，A 失败了）
- 需要用户提供信息（如密码、URL、选择项）
- 安全敏感操作（删除数据、修改 NixOS 配置）

### 失败处理
- 单个任务失败 → 标记 `cancelled`，继续下一个，不在中间停下来汇报
- 连续 3 个任务失败 → 停下来报告问题
- 全部完成后 → 输出最终汇总

## 意图→规则强制转化（INTENT_TO_RULE — 死规则）

**核心原则**：用户的任何持续性工作流要求、行为偏好、流程规范，MUST **第一次就识别**并立即写入规则文件，不等到用户说第2次。

### 识别信号（满足任一即触发）
1. **绝对化关键词**：「每次」「都要」「强制」「死规则」「永远」「一直」「必须」「不要忘记」「记住」
2. **工作流要求**：用户描述了一个多步骤流程且期望每次都这样执行（如"每次compact完你要继续执行"）
3. **纠正性反馈**：用户指出 agent 做错了或漏做了某个步骤
4. **重复要求**：用户对同一要求说了第 2 次 — 说明第 1 次 INTENT_TO_RULE 没触发，这是**失败信号**
5. **元指令**：用户直接命令「写进规则里」「这些要求都要强制记录」「你每次都要xxx」
6. **隐性意图**：用户描述一个期望的长期行为模式（如"sisyphus不要只跟我对话，要理解我意图并且强制执行记录"）

### 执行流程（死规则 — 禁止跳过）
1. **识别意图**：从用户消息中提取「他希望我永远自动做什么」— 一句话概括
2. **写入 CLAUDE.md**：在对应章节添加新规则，格式为 `## [规则名]（[标签] — 死规则）` + 具体行为要求
3. **同步 AGENTS.md**：将精简版写入 `~/.config/opencode/AGENTS.md` 对应章节
4. **强制输出**：`[INTENT_TO_RULE] 新规则已写入: {规则名} → CLAUDE.md + AGENTS.md`
5. **验证**：写入后 grep 确认两个文件都包含该规则

### 已转化的规则清单（索引）
| 规则 | 写入日期 | 触发原因 |
|------|---------|---------|
| COMPACT_CONTINUE | 2026-04-16 | 用户要求 compact 后自动继续执行 |
| INTENT_TO_RULE | 2026-04-16 | 用户要求重复要求强制记录为规则 |
| 单次识别扩展 | 2026-04-16 | 用户质疑"只说一次怎么识别"，修正为第一次就识别 |
| APP_DEV_JOURNAL | 2026-04-17 | 用户要求"每次做app或软件时记录开发经验" |
| OUTPUT_DESKTOP_PERSIST | 2026-04-17 | 用户要求"以后op输入结果全部放桌面" |
| PLAYWRIGHT_MUST_EXECUTE | 2026-04-17 | 用户要求"涉及网页操作必须用 Playwright 自己执行，不要只写指南" |
| AUTO_COST_OPTIMIZE | 2026-04-19 | 用户要求"以后agent自动执行成本优化操作" |

### 禁止行为
- ❌ 只回复「好的」「我记住了」「下次会注意」但**不修改文件**
- ❌ 在对话中承认问题但**推迟到「下次」再改**
- ❌ 认为规则「已经隐含理解」— 不写入文件 = 不存在
- ❌ 写入 CLAUDE.md 但**不同步 AGENTS.md**（subagent 读 AGENTS.md）
- ❌ 等「用户说第2次」才触发 — 第一次就要识别

## Agent 自动成本优化（AUTO_COST_OPTIMIZE — 死规则）

**核心原则**：Agent 发现成本优化机会时，MUST 自动执行，不等用户确认。

### 触发条件（任一满足即执行）
1. 发现 OP 定时任务使用高成本模型处理简单巡检 → 自动降级为 glm-4.7 或 bash 脚本
2. 发现 Router 规则过于宽松导致误路由 → 自动收紧正则
3. 发现 opencode 进程执行可 bash 替代的任务 → 自动创建 bash 替代脚本
4. 发现服务 timeout 配置不合理（频繁 ALRM 被杀） → 自动调整 timeout
5. 发现 fast 路由比例低于 40% → 检查是否有本该走 fast 的查询被误分类

### 执行规则
1. **自动执行**：检测到优化机会 → 直接修改配置/脚本 → 验证 → 报告结果
2. **禁止询问**：不需要问"是否优化"，成本优化默认用户授权
3. **验证闭环**：修改后 MUST 运行验证（bash -n / systemctl daemon-reload / 测试运行）
4. **结果输出**：`[COST_OPT] 操作 → 节省预估`

### 检查周期
- 每次用户提到"成本""额度""消耗""token"时，主动运行全面成本审计
- 修改 OP 定时任务配置时，顺便检查其他任务的模型/timeout 是否合理
- 月度自动检查 router-stats.json，分析 fast/standard/deep 比例变化

**核心原则**：涉及网页操作（登录、配置、数据提取）时，MUST 用 Playwright 自己执行，不要只写指南让用户手动操作。

### 触发条件
- 用户提到"操作网页""打开xxx网站""在网页上配置"
- 任务涉及 Web 界面交互（OAuth 配置、Cloud Console、管理后台）
- 需要浏览器已登录的 session（Cookie 复用）

### 执行规则
1. **MUST 调用 Playwright MCP 工具**（browser_navigate/browser_click/browser_type 等）直接操作
2. **禁止只写文字指南**："去 xxx 网站点 yyy 按钮" 这种回复 = 失败
3. **禁止让用户手动操作网页** — 用户说"你操作"就是要你自己做
4. **Cookie 复用**：如果用户浏览器已登录，MUST 复用其 profile/cookie
5. **失败回退**：Playwright 失败 → 先排查工具可用性 → 仍失败才报告用户

### 禁止行为
- ❌ 输出"请按照以下步骤在浏览器中操作..."
- ❌ 生成配置指南但不在网页上实际执行
- ❌ 说"我无法直接操作浏览器"而不尝试 Playwright

## Skill 匹配提醒协议（SKILL_REMINDER）— 强制输出

### Skill→Agent 智能路由映射（死规则 — 派发时自动匹配）

**派发任务时 MUST 按目标 agent 领域自动注入对应 skills，禁止空 load_skills=[]**

| 目标领域 | 自动注入的 Skills |
|---------|------------------|
| **系统运维** (nixos-sysadmin/deep/诊断) | `nixos-safety-check` `system-health-check` `proxy-diagnose` `security-audit` `docker-cleanup` `docker-network-troubleshooting` `timer-schedule-manager` `taskboard` `age-key-backup` |
| **代码开发** (code-assistant/quick/deep) | `api-design-principles` `architecture-patterns` `python-testing-patterns` `typescript-advanced-types` `git-advanced-workflows` `tool-calling-patterns` `skill-create` + 按语言匹配 |
| **前端/UI** (visual-engineering) | `frontend-ui-ux`(builtin) + 按需 `e2e-testing-patterns` `javascript-testing-patterns` |
| **DevOps/K8s** | `k8s-manifest-generator` `helm-chart-scaffolding` `gitops-workflow` `github-actions-templates` `deployment-pipeline-design` `terraform-module-library` |
| **PM/编排** (主 agent 自用) | `mpm*` `pm-*` `paperclip*` `memory-maintenance` `proactive-maintenance-planner` |

**匹配逻辑**：从任务描述提取关键词 → 上表匹配 → 注入对应 skills。跨领域任务合并注入。

### 触发条件
每个会话的**第一个实质性任务**开始前自动触发（纯对话/问候不触发）。

### 执行流程（死规则 — 必须显式输出）
1. **关键词提取**：从用户任务描述中提取 2-3 个核心实体
2. **Skill 匹配**：按上表路由映射 + `~/.claude/skills/` 目录名匹配
3. **结果处理（MUST 输出一行标签）**：
   - 命中 → `[SKILL] {agent/领域}: {name1}, {name2}...`
   - 未命中 → `[SKILL] 无匹配`（**禁止静默跳过**）
4. **派发时 MUST 将匹配到的 skills 传入 load_skills=[]**

### 周度 Skill 审计（整合到 ai-architecture-audit）
- 每周审计报告中包含 "Skills 使用率" 维度
- 从未使用的 skills → 建议删除或合并
- 高频操作无对应 skill → 建议创建

## Skill 自动封装协议（AUTO_SKILL）— 强制输出

### 触发条件（MUST 自检 — 死规则）
完成以下操作后，MUST 评估是否值得封装为 Skill：
- 新配置/部署流程（≥3 步）
- 非平凡 bug 修复（有排查过程）
- 可复用代码 pattern 或工作流
- 发现了有价值的系统优化方案

### 评估标准（满足 ≥2 条即值得封装）
- **可复用性**：未来可能再次遇到相同场景
- **复杂度**：不是简单的一行命令（涉及多步操作或排查）
- **知识密度**：包含非显而易见的信息或经验
- **缺失性**：现有 skills 未覆盖（可用 `ls ~/.claude/skills/` 确认）

### 强制输出（死规则）
每次完成实际操作后，MUST 输出一行评估标签：
- 值得封装 → `[AUTO_SKILL] 可封装: {一句话摘要}（满足 {n}/4 条标准）`
- 不值得 → `[AUTO_SKILL] 跳过: {原因}（满足 {n}/4 条标准）`
- **禁止静默跳过** — 即使明显不值得也必须输出标签

### 封装流程（死规则 — 一步直达，禁止任何中间停顿）

**输出 `[AUTO_SKILL] 可封装` 后，下一个动作必须是 Bash 调用 create-skill.py，无例外。**

```bash
python3 ~/.claude/skills/create-skill.py \
  --name "{slug-name}" \
  --description "{一句话描述}" \
  --content "{步骤+踩坑+命令}" \
  --category "{分类}" \
  --tags "{tag1},{tag2}"
```

验证 → `ls ~/.claude/skills/{name}/SKILL.md` → 输出 `[AUTO_SKILL] 已创建 → {路径}`

**兜底机制**：Stop hook 扫描 session JSONL，检测 `[AUTO_SKILL] 可封装` 但无 create-skill.py 调用 → 写入 lessons-learned 计数 → 连续 3 次自动触发审计。

**禁止**：
- ❌ 输出标签后不调用 Bash — 标签 + 无 Bash = 失败
- ❌ 把 pending 文件步骤当借口拖延
- ❌ `💡 检测到可封装知识...建议创建（y/n）` — 永久禁用
- ✅ **标签后立即 Bash，一步完成**

### Skill 内容格式
```yaml
---
name: skill-name
description: 一句话描述
user-invocable: false
version: "1.0.0"
category: 分类名
tags: [tag1, tag2, tag3]
effort: low|medium|high
---
# Skill 标题
## 场景
什么情况下使用
## 步骤
具体操作步骤
## 注意事项
踩坑经验
```

## 回复前自检协议（SELF_CHECK_PROTOCOL）

每次回复发送前，MUST 逐项检查。这不是"建议"而是"拦截器" — 任何一项未通过都必须先处理再回复。

### 自检清单
- [ ] **记忆写入**：本次会话有实际操作（修改配置/安装软件/修复 bug/架构变更）→ 是否已按记忆路由表写入对应 memory/ 文件？
- [ ] **PRE_GATE**：启动了 Explore agent → 是否先执行了 PRE_EXECUTE_GATE 检索？
- [ ] **SAFETY RETRIEVAL**：执行了破坏性操作 → 是否先检索了 memory/ 历史教训？
- [ ] **NixOS 验证**：修改了 .nix 文件 → 是否运行了 `nix flake check`？
- [ ] **服务验证**：修改了服务代码 → 是否重启 + curl 测试 + 检查日志？
- [ ] **脚本语法**：编辑了脚本 → 是否运行了 `bash -n` 检查？

### 执行方式（强制输出 — 死规则）
- **MUST 在回复末尾显式输出自检结果**，格式：`[自检] 记忆:✅ PRE_GATE:✅ 安全:✅ 验证:✅`
- **禁止"内部推理时确认"** — 事实证明内部推理 = 跳过（已连续多次失败）
- **任何未通过项立即补执行**，不允许"下条回复补"
- **未通过项超过 2 个** → 先处理未通过项再继续当前任务
- **自检结果必须在实际输出之前完成** — 先执行自检动作，再输出正文

### 失败计数（通用机制 — 跨所有强制输出协议）
- **计数规则**：同一检查项/标签连续 3 次未输出 → 自动写入 lessons-learned.md 作为待改进项
- **适用范围**：`[PRE_GATE]` `[PRE_EXPLORE]` `[POST_EXPLORE]` `[SKILL]` `[AUTO_SKILL]` `[自检]` `[ARCH]` 尾注 `📎`
- **计数方式**：无法机器计数，靠自检协议中的 `[自检]` 行逐项核对
- **触发写入**：自检发现某项连续跳过 → 立即追加到 `memory/lessons-learned.md`，格式：`- [日期] [操作者] 强制输出跳过：{协议名}连续 {n} 次未输出，需排查原因`
- **升级路径**：连续 5 次 → 建议用 hook 实现该协议（从 L2 升级到 L3 确定性执行）

## 输出结果桌面持久化规则（OUTPUT_DESKTOP_PERSIST — 死规则）

**核心原则**：所有操作结果（工具输出、巡检报告、生成文档等）MUST 保存到 `~/Desktop/` 目录，按类型分类子目录。

### 触发条件（MUST）
- 工具调用产生的诊断结果、状态信息
- 巡检报告（服务护士、代理守护者、Discord 管家等）
- 生成的文档、分析报告、配置文件
- 脚本执行结果、日志摘要

### 目录结构规范
```
~/Desktop/
├── 巡检报告/
│   ├── 服务健康/
│   ├── 代理监控/
│   ├── Discord管理/
│   └── 运营调度/
├── 文档/
│   ├── 修复指南/
│   ├── 配置说明/
│   └── 技术笔记/
└── 日志/
    ├── 错误日志/
    └── 操作记录/
```

### 执行流程（死规则）
1. **自动创建目录**：首次使用时自动创建对应子目录
2. **文件命名规范**：`{名称}-{日期}.md` 或 `{名称}-{时间戳}.md`
3. **内容格式**：使用中文，结构化输出（卡片分组、时间轴等）
4. **强制输出标签**：回复末尾附加 `📎 [{agent}] 已写入 → {文件路径}`

### 禁止行为
- ❌ 仅在终端输出结果，不保存到桌面
- ❌ 使用临时路径（`/tmp/`）保存重要结果
- ❌ 文件名含中文空格或特殊字符
- ❌ 不分类直接堆放到桌面根目录

## 回复结尾（死规则）

- 有文件写入/修改操作 → 末尾一行：`► 写入: 文件名`（多个文件用逗号分隔）
- 无操作的纯对话回复 → **不输出尾注**
- 禁止输出 `[自检]` `[PRE_GATE]` 等协议标签到用户界面（内部执行，不显示）
- 禁止 agent 名称标注（用户不需要看到模型名）

## 常用命令参考
- NixOS 重建：`sudo nixos-rebuild switch --flake /etc/nixos#charlie`
- Flake 检查：`nix flake check /etc/nixos`
- KDE 重载：`dbus-send --session --dest=org.kde.KWin --type=method_call /KWin org.kde.KWin.reconfigure`
- 磁盘池状态：`bash ~/launcher/disk-pool-mount.sh status`

## NTFS/NFS 封杀协议（NTFS_BAN — 死规则）

**核心原则**：NTFS/NFS/mergerfs 分区上禁止执行任何需要文件锁或原子写入的操作。

### 禁止操作清单
- `npm install` / `bun install` / `bun add` — 禁止在 NTFS 上运行
- `cargo build` / `rustup update` — 禁止缓存指向 NTFS
- `git worktree` / `git clone`（大型仓库）— 禁止工作目录在 NTFS
- 任何符号链接指向 NTFS 的缓存目录 → **必须先迁移到 ext4**
- Docker 镜像构建 — 禁止 build context 在 NTFS

### 已迁移到 ext4（/mnt/ai）的目录
| 原路径 | 新路径 | 用途 |
|--------|--------|------|
| `~/.npm` | `/mnt/ai/cache/npm` | npm 缓存 |
| `~/.bun` | `/mnt/ai/cache/bun` | bun 缓存/安装 |
| `~/.opencode` | `/mnt/ai/cache/opencode` | OpenCode 数据 |
| `~/.codemoss` | `/mnt/ai/data/codemoss` | CodeMoss 数据 |
| `~/.var` | `/mnt/ai/data/var` | XDG 数据 |
| `~/.android` | `/mnt/ai/data/android` | Android SDK |
| `~/Android` | `/mnt/ai/data/android-user` | Android 用户数据 |
| `~/.floorp` | `/mnt/ai/data/floorp` | Floorp 浏览器配置 |
| `XDG_CACHE_HOME` | `/mnt/ai/cache/xdg` | XDG 缓存 |

### NTFS 分区现状（只读用途）
- `/mnt/win_c` — Windows C盘（只读挂载）
- `/mnt/data` — 数据归档（可读写，但禁止缓存/编译）
- `/mnt/pool-disks/POOL-B1` — 大文件存储（禁止缓存/编译）

### 检测方法
执行 `npm install` 前运行：`df -T . | grep -i ntfs` → 命中则拒绝执行

## Windows 远程接管协议（WINDOWS_REMOTE_OWNERSHIP — 死规则）

**核心原则**：Windows 是我管理的第二台机器，通过 SSH 远程操作，与 NixOS 同等对待。

### 连接信息
- **SSH**：`ssh G@192.168.2.36`（用户名 `G`，密码 `1`）
- **Tailscale**：Windows 有 Tailscale，局域网和 VPN 都可达
- **Windows 账户**：用户名 `G` / 密码 `1`

### 执行规则（死规则）
1. **MUST 主动通过 SSH 操作 Windows**，不要求用户手动在 Windows 上执行
2. Windows 命令必须通过 `cmd /c "..."` 包裹（PowerShell 转义容易出错）
3. 长命令用 base64 编码传输：`echo BASE64 | ssh G@192.168.2.36 'cmd /c "echo BASE64 | python -c \"import base64,os;os.system(base64.b64decode(input()))\""'`
4. 文件传输用 `scp` 或 `ssh ... 'cmd /c "..." > C:\Users\G\output.txt'` 然后 `scp` 拉回
5. 大软件安装用 `winget install`（需长 timeout >60s）
6. Windows 代理设置：用 NixOS mihomo `192.168.2.100:7890`（allow-lan:true 已开）

### Windows 已安装工具
- Python 3.12 + pip 25.0.1（`C:\Users\G\AppData\Local\Programs\Python\Python312\`）
- OpenCode v1.4.6（`C:\Users\G\.opencode\bin\opencode.exe`）
- OpenSSH Server（已配置自动启动）

### 与 NixOS 的差异注意
- 路径用 `\` 不用 `/`（但 SSH cmd /c 内两者混用通常 OK）
- 无 systemd，用 `schtasks` 管理定时任务
- 防火墙用 `netsh advfirewall` 或 GUI
- 环境变量用 `setx` 持久化（`set` 仅当次会话）
- NTFS 权限模型不同，不依赖 Unix 权限


## OP 自动执行（AUTO_EXEC — 死规则）
OP 收到 op-tasks.md 中的 `[ ]` 任务 MUST 直接执行，无需确认。
CC 写入任务时已代表用户授权，OP 禁止二次确认。

## OP 前台触发（OP_FOREGROUND — 死规则）
用户要看到 OP 执行过程时，MUST 调用 `op-launch.sh` 而非 `systemctl start`：
```bash
bash ~/.local/bin/op-launch.sh  # 自动：建 tmux op-tasks session + 发命令 + 开 Ghostty
bash ~/.local/bin/op-launch.sh "自定义提示词"  # 指定任务
```
- 自动建立 tmux session `op-tasks`，发送命令（含 Enter），打开 Ghostty 窗口 attach
- 无需用户任何操作，全自动前台展示
- 后台定时任务仍走 systemd timer（不变）

## OP 完成报告协议（OP_COMPLETION_REPORT — 死规则）

**核心原则**：每次用户移交任务给 OP 后，CC MUST 在下次回复时主动汇报 OP 的完成情况。

### 触发条件
- 用户说"交给OP做"、"让OP执行"、"写入op-tasks"等
- CC 触发了 heartbeat-task-check 或 op-task-runner
- 用户在新消息中问"做完了吗""完成度怎么样"

### 执行规则（死规则 — 禁止跳过）
1. **主动检查**：不等用户问，触发 OP 任务后的下一个 CC 回复中 MUST 包含：
   - `grep "\[x\].*完成 $(date +%Y-%m-%d)" op-tasks.md` 最近完成项
   - `cat /tmp/op-task-results.json` 执行结果
   - `grep -c "- \[ \]" op-tasks.md` 剩余待办数
2. **格式**：用树状层级或卡片展示，每项显示 `[ok]`/`[fail]`/`[skip]` + 一句话摘要
3. **失败必须标注**：`[fail]` 项 MUST 说明失败原因，不允许只统计数量
4. **禁止跳过**：即使 OP 还在运行，也要输出"OP 正在执行中（已 Xmin）"

### 强制输出格式
```
▸ OP 执行报告（{时间}）
├─ [ok]  任务名 ···· 结果摘要
├─ [fail] 任务名 ··· 失败原因
└─ [skip] 任务名 ··· 跳过原因
剩余待办: N 条 | 下次触发: HH:MM
```

[INTENT_TO_RULE] 新规则已写入: OP_COMPLETION_REPORT → CLAUDE.md
