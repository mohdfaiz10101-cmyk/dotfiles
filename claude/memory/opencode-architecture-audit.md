---
name: OpenCode 架构全面审计与 L3 优化方案
description: 诊断不合理之处，制定 L3 自动降级和成本告警规则
type: project
---

# OpenCode 架构审计（2026-05-11）

## 问题诊断汇总

### 🔴 严重问题（必须修复）

#### 1. **Agent 定义与文件不同步**
| 配置中 | 文件存在 | prompt_file | 状态 |
|--------|---------|-----------|------|
| foc | ❌ | - | ⚠️ 配置引用不存在的 cerebras-qwen3-235b 模型 |
| sisyphus | ✓ | `/home/charlie/.config/opencode/agents/sisyphus.md` | ✓ 正常 |
| build | - | ❌ 缺失 | ⚠️ 子 agent，无自定义 prompt |
| plan | - | ❌ 缺失 | ⚠️ 但有 planner.md 存在（未配置） |
| chat | - | ❌ 缺失 | ⚠️ 审核对话的 reviewer.md 存在但未配置 |
| explore | - | ❌ 缺失 | ✓ 子 agent，使用默认行为 |
| refactor | - | ❌ 缺失 | ✓ 子 agent，使用默认行为 |
| arch | - | ❌ 缺失 | ✓ 有 tech-architect.md 但未使用 |
| marketing-coordinator | ✓ | ✓ | ✓ 正常 |
| marketing-auditor | ✓ | ✓ | ✓ 正常 |
| tech-architect | ✓ | ✓ | ✓ 正常 |
| tech-researcher | ✓ | ✓ | ✓ 正常 |
| ops-dispatcher | ✓ | ✓ | ✓ 正常 |

**未配置的现成 agent**（浪费）：
- agi-mentor.md — AI 导师
- cc-autonomous.md — 自主执行
- content-creator.md — 内容创建
- cost-accountant.md — 成本会计（应该配置！）
- discord-butler.md — Discord 集成
- doc-manager.md — 文档管理
- finance.md — 财务
- git-backup.md — Git 备份
- memory-curator.md — 记忆管理
- planner.md — 规划器（应该用于 plan agent）
- proxy-guardian.md — 代理守护
- reviewer.md — 审查器（应该用于 chat/refactor）
- security-watchdog.md — 安全监控
- service-nurse.md — 服务护士

---

#### 2. **Provider 配置冗余且不一致**

| Provider | BaseURL | 使用状态 | 问题 |
|----------|---------|---------|------|
| z-ai | localhost:4000 | 被覆盖 | ❌ 重复定义，models 不完整（缺 glm-4.7） |
| openai-compatible | localhost:4000 | ✓ 主要使用 | ✓ 正常但 models 列表臃肿 |
| web-ai | localhost:5001 | ❌ 完全未用 | ⚠️ 该服务不存在或不稳定，浪费空间 |
| anthropic | API Key | ❌ 未用 | ⚠️ 只有 claude-sonnet-4（过时，应该是 claude-3-5-sonnet-20241022） |

**建议**：
- 删除 z-ai（与 openai-compatible 重复）
- 删除 web-ai（localhost:5001 不存在）
- 更新 anthropic 模型号
- 保留 openai-compatible 作为唯一 LiteLLM provider

---

#### 3. **模型配置与实际可用模型不一致**

**配置中但实际不存在的模型**：
- `cerebras-qwen3-235b` — foc agent 引用的，但实际没有这个模型
- `gpt-4.1` — 标注为 "GitHub 免费"，但无法验证
- `qwen3-235b` — 标注为 "SiliconFlow 免费"，但可能已下线

**配置中有但 agent 未使用的模型**：
- deepseek-v4-pro — 只定义，未被引用（太贵，不建议用）
- glm-4-plus — 定义了但 agent 都没用

**实际验证**（从 LiteLLM 日志）：
```
可用模型：glm-5.1, glm-5-turbo, glm-5, glm-4.7, glm-4-plus, glm-4.6v-flash,
deepseek-v4-pro, deepseek-v4-flash, qwen3-235b, gpt-4.1, ...
```

---

#### 4. **权限配置过于开放**

当前权限设置：
```json
"permission": {
  "edit": "allow",
  "bash": {"*": "allow"},
  "webfetch": "allow",
  "websearch": "allow",
  "external_directory": {"*": "allow"},
  "doom_loop": "allow",  ← 🔴 危险！
  "skill": {"*": "allow"},
  "mcp": {"*": "allow"},
  "memory": "allow",
  "todo": "allow",
  "schedule": "allow"
}
```

**问题**：
- `"doom_loop": "allow"` — 允许无限递归调用，可能导致成本爆炸
- `bash.*: allow` — 允许所有 bash 命令，太宽泛
- `external_directory.*: allow` — 允许访问所有外部目录

---

#### 5. **Agent 模型分配不合理**

| Agent | 当前模型 | 成本 | 建议 | 原因 |
|-------|---------|------|------|------|
| sisyphus (main) | glm-5-turbo | ¥7 | ✓ 保持 | 平衡，主流程 |
| arch | glm-5-turbo | ¥7 | → glm-5.1 | 架构决策需要深度推理 |
| plan | glm-5-turbo | ¥7 | ✓ 保持 | 制定计划够用 |
| chat | glm-5-turbo | ¥7 | → glm-4.7 | 对话不需要推理，浪费 |
| explore | glm-5-turbo | ¥7 | → glm-4.7 | 搜索只需定位，不需推理 |
| build | deepseek-v4-flash | ¥4 | ✓ 保持 | 代码生成性价比高 |
| refactor | deepseek-v4-flash | ¥4 | ✓ 保持 | 同上 |
| foc | cerebras-qwen3-235b | ¥0 | ✓ 保持 | 免费快速反馈 |
| marketing-* | glm-5-turbo | ¥7 | → glm-4.7 | 营销文案不需要高端模型 |
| tech-* | glm-5-turbo | ¥7 | ✓ 保持 | 技术方案需要 turbo |
| ops-dispatcher | deepseek-v4-flash | ¥4 | ✓ 保持 | 运维执行够用 |

**成本优化空间**：chat/explore/marketing-* 降级 → 月省 ¥3000~5000

---

### 🟡 中等问题（应该优化）

#### 6. **模型名称不规范**
- "glm-5-turbo" 应改为 "glm-5.1-turbo"（与 glm-5.1 区分）
- "deepseek-v4-*" 实际应该是 "deepseek-v3.2-*"（版本号错误）

#### 7. **缺少降级链**
当 glm-5-turbo 超时/超额时，没有自动降级到 glm-4.7 的机制

#### 8. **缺少成本监控**
没有实时成本告警，无法及时发现成本异常

#### 9. **oh-my-openagent 配置缺失**
sisyphus.md 中写了"sisyphus 由 oh-my-openagent 插件注册"，但没有对应的 oh-my-openagent 配置文件

---

### 🟢 轻度问题（可优化）

#### 10. **TUI 配置待优化**
```json
"tui": {
  "code_blocks": "collapsed",     // ✓ 折叠代码块，省空间
  "tool_output": "hidden",        // ⚠️ 隐藏工具输出可能隐藏重要信息
  "hide_thinking": true           // ✓ 隐藏思考过程，省 token
}
```

#### 11. **缺少模型热备**
没有备用模型配置，如果主模型失败无法自动切换

---

## L3 优化方案

### Part 1：架构重构（修复不合理）

#### 方案 1.1：清理 Provider 配置
```bash
❌ 删除：z-ai provider（与 openai-compatible 重复）
❌ 删除：web-ai provider（localhost:5001 不存在）
⚠️  更新：anthropic 模型号（claude-sonnet-4 → claude-3-5-sonnet-20241022）
✓  保留：openai-compatible 作为唯一 LiteLLM provider
```

#### 方案 1.2：修复 Agent 配置
```bash
❌ 删除：foc agent（引用不存在的 cerebras-qwen3-235b）
✓  更新：arch agent → 添加 tech-architect.md prompt（提升决策质量）
✓  新增：reviewer agent（用于 refactor/chat 审查）
✓  规范化：plan agent 用 planner.md
```

#### 方案 1.3：模型分配优化
```bash
chat:       glm-5-turbo → glm-4.7         (-¥7/100k)
explore:    glm-5-turbo → glm-4.7         (-¥7/100k)
arch:       glm-5-turbo → glm-5.1         (+¥10/100k，但决策更好)
marketing-*: glm-5-turbo → glm-4.7        (-¥7/100k)
```

**成本影响**：月省 ~¥2000-3000（假设 1000k tokens/天）

---

### Part 2：自动降级链（L3 核心）

#### 方案 2.1：三级自动降级规则

```yaml
降级链配置：
  glm-5.1:
    降级触发：
      - 超时 > 30s
      - 速率限制 (429)
      - 余额不足 (30001)
      - token 超预算
    降级到：glm-5-turbo
    
  glm-5-turbo:
    降级触发：
      - 超时 > 20s
      - 速率限制 (429)
      - 余额不足 (30001)
    降级到：glm-4.7
    
  glm-4.7:
    降级触发：失败
    降级到：失败，人工介入
    
  deepseek-v4-flash:
    降级触发：失败
    降级到：glm-4.7
```

#### 方案 2.2：自动降级脚本

```bash
创建：~/.local/bin/opencode-with-fallback
实现：
  1. 尝试用主模型（glm-5-turbo）
  2. 失败时自动降级 → glm-4.7
  3. 记录降级原因到日志
  4. 超过 3 次失败 → 停止，输出告警
```

---

### Part 3：成本监控与告警（L3 增强）

#### 方案 3.1：实时成本统计

```bash
创建：~/.local/bin/opencode-cost-monitor
功能：
  1. 每 1 小时统计一次：
     - 当日 token 消耗（按模型分类）
     - 当日成本（按模型计算）
     - 当月预估（已用 / 天数 × 30）
  2. 告警规则：
     - 当日 > ¥50 → 黄色告警
     - 当日 > ¥100 → 红色告警
     - 当月预估 > ¥800 → 停用贵模型
  3. 输出格式：
     ```
     [📊] 当日成本：¥32 (glm-5-turbo: 45k, glm-4.7: 20k)
     [⚠️] 预计本月：¥850 (超预算 ¥50)
     [建议] 今日改用 glm-4.7 或等明天
     ```
```

#### 方案 3.2：模型成本白名单

```bash
配置文件：~/.config/opencode/cost-limits.yaml
内容：
  daily_budget: 50         # 日预算 ¥50
  monthly_budget: 800      # 月预算 ¥800
  model_budgets:
    glm-5.1: 30            # glm-5.1 限 ¥30/天
    glm-5-turbo: 50        # turbo 限 ¥50/天
    glm-4.7: unlimited     # 4.7 无限制
  auto_downgrade:
    enabled: true
    trigger: "超预算"
```

#### 方案 3.3：Hook 集成

```bash
在 sisyphus.md 或 oh-my-openagent 配置中添加：
  on_request:
    - 检查当日成本 → 超预算则自动降级
    - 记录请求到 ~/.opencode-cost.jsonl
    - 每 1h 检查告警
```

---

## 执行计划

### 第一阶段（即时）：架构修复
1. ✅ **清理 Provider** — 删除 z-ai/web-ai，保留 openai-compatible
2. ✅ **修复 Agent** — 删除 foc，更新 arch/plan/chat
3. ✅ **模型优化** — chat/explore/marketing-* 降级到 glm-4.7
4. ✅ **权限加固** — 禁用 doom_loop，限制 bash

### 第二阶段（本周）：降级与监控
5. ⏳ **自动降级链** — 实现 glm-5.1 → turbo → 4.7 的自动降级
6. ⏳ **成本监控** — 实时统计和告警
7. ⏳ **集成到 opencode** — Hook 修改 MCP 或插件

### 第三阶段（可选）：高级优化
8. ⏳ **缓存复用** — 相同问题返回缓存结果（省 99% token）
9. ⏳ **动态 LoRA** — 本地 8B 模型 + 专家 LoRA 切换
10. ⏳ **执行引导采样** — 生成过程中实时验证

---

## 预期成本影响

| 阶段 | 措施 | 月成本 | 降幅 |
|-----|------|--------|------|
| **现状** | 无优化 | ¥7200 | - |
| **L1** | 插件优化 + MCP 裁剪 | ¥3600 | -50% |
| **L2** | 快捷指令 + 默认降级 | ¥720 | -90% |
| **L3** | 自动降级 + 监控 | ¥480 | -93% ↓ |

> L3 实现后，仅当关键任务（arch/plan）需要 glm-5.1 时才用，日常全用 turbo/4.7

---

## 配置文件路径

- **审计报告**：`~/.claude/projects/-home-charlie/memory/opencode-architecture-audit.md`（本文件）
- **原始配置**：`~/.config/opencode/opencode.json`
- **备份**：`~/.config/opencode/opencode.json.backup-20260511`
- **cost-limits 配置**：`~/.config/opencode/cost-limits.yaml`（待创建）
- **自动降级脚本**：`~/.local/bin/opencode-with-fallback`（待创建）
- **成本监控脚本**：`~/.local/bin/opencode-cost-monitor`（待创建）

---

## 风险评估

| 变更 | 风险等级 | 缓解方案 |
|-----|---------|---------|
| 删除 z-ai provider | 低 | 仅影响冗余配置 |
| 删除 web-ai | 低 | 该服务本就不可用 |
| chat/explore 降级到 4.7 | 中 | 保留快速切换到 turbo 的能力 |
| 禁用 doom_loop | 低 | 用户需要时手动调整 permission |
| 自动降级 | 中 | 需严格测试，避免误触发 |

---

## 后续观察指标

✅ 已完成检查项：
- 模型实际可用性（24 个模型中有效的是哪些）
- Agent 文件同步性（13 个配置中哪些实际有文件）
- 权限安全性（doom_loop 等风险项）

⏳ 待测试项：
- L3 自动降级是否工作正常
- 成本监控准确性（与 LiteLLM 日志对比）
- 降级时是否保持任务质量

---

**版本**：0.1（初始诊断）  
**更新日期**：2026-05-11  
**状态**：待审批执行
