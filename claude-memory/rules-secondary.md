# 二级规则（L2+L3）— 按需加载
> L1 核心规则始终在 CLAUDE.md 中。以下规则在特定场景触发时加载。

## L2：会话启动规则（SESSION_MEMORY_BOOT 时注入）

### 会话记忆自动加载（SESSION_MEMORY_BOOT — L2）
每个会话第一个实质性任务前 MUST 并行执行：
1. `mcp__letta-memory__letta_recall` 查询最近上下文（query="最近任务 用户状态 进行中项目"）
2. 读取 `~/.claude/projects/-home-charlie/memory/MEMORY.md` 获取用户档案
- 输出格式：`[MEM] Letta: {命中条数}条 | 档案: {关键摘要}`
- Letta 不可用时降级：只读 memory/ 文件，输出 `[MEM] Letta离线，使用本地档案`
- 纯闲聊/单句问答 → `[MEM] skip:非实质性任务`

### OP状态感知（OP_AWARENESS — L2）
每个会话第一个实质性任务前 MUST 调用 `macg_op_status` MCP 工具读取 OP 最新状态。
- 有未读的真实失败（Result=failed）→ 输出 `[OP] 待处理: {任务}` 并询问是否优先处理
- 全部假阳性（Result=success inactive）→ 静默清理，不打扰用户

### 架构感知（ARCH_AWARENESS — L2）
每个会话首条实质性回复前输出：`[ARCH] 审计报告: {天数}天前 | 状态正常/异常`
纯对话 → `[ARCH] skip:非实质性任务`

### Letta 连通性自动修复（LETTA_AUTOFIX — L2）
每个会话第一个需要调用记忆的操作前，MUST 先验证 Letta 可用：
```bash
curl -s --connect-timeout 3 http://localhost:8283/v1/agents -w "%{http_code}" -o /dev/null
```
- 返回 `307` 或 `200` → 正常
- 连接失败/超时 → `docker restart letta-db && sleep 30 && docker restart letta && sleep 15`

### Charlie-Ego 决策镜像（CHARLIE_EGO — L2）
每次会话第一个实质性任务前，MUST 召唤 charlie-ego 获取决策建议。
- 触发场景：技术选型、架构决策、工具选择、方案对比
- 跳过场景：纯操作执行、闲聊、单句问答
- agent ID: `agent-f6786cc0-260f-4b84-985d-ced4acb1c614`
- **对答模式注入**：复杂决策回复首段注入 `[Charlie-Ego] 历史参考: {场景} → 建议: {决策}`

### 智能记忆验证闭环（SMART_MEMORY_VERIFY — L2）
SESSION_MEMORY_BOOT 读到设备/服务/端口等事实后，MUST 交叉验证：
- 实时工具输出与记忆冲突时 → grep 确认记忆是否过期
- 记忆过期 → 立即更新

### MCP输出验证（MCP_OUTPUT_VERIFY — L2）
MCP 工具输出可能返回缓存快照。MUST 交叉验证原始文件再向用户汇报。

---

## L2：任务执行规则（执行相关任务时生效）

### CC↔OP 职责分工（CC_OP_DIVIDE — L2）
- **CC**：规划、编码、规则管理、任务派发、架构决策
- **OP**：系统运维执行、定时任务、健康巡检、磁盘/服务修复
- `[OP]` 任务 → MUST 写入 op-tasks.md，CC 禁止直接完成
- `[CC]` 任务 → CC 直接执行
- **OP 失败流转**：OP 达最大重试次数 → 写入 op-tasks.md 转 CC
- **op-tasks 去重**：写入前 MUST grep 检查相似任务防重复
- **任务标记**：失败用 `[!]` 不用 `[x]`

### OP 完成报告（OP_REPORT — L2）
触发 OP 任务后下一次 CC 回复 MUST 主动检查 op-tasks.md 完成项 + op-task-results.json

### CC任务自动执行（CC_AUTO_EXEC — L2）
op-tasks.md 中标注 `[CC]` 的任务 MUST 在同一回复内立即执行

### TODO 强制执行（TODO_FORCE_EXEC — L2）
有 pending 任务时 MUST 连续执行到底，禁止停顿汇报

### FALSE_POSITIVE_GUARD（L2 — OP也适用）
`systemctl --user is-active` 返回 `inactive` ≠ 失败。MUST 用：
```bash
systemctl --user show <svc> --property=Result,ActiveState,SubState
```
- `Result=success` → 正常完成，**禁止写 [!]**

### 记忆路由表（MEMORY_ROUTE — L2）
操作完成后立即写入对应 memory 文件。格式：`- [日期] [模型] 场景：内容`

| 记录内容 | 写入文件 |
|---------|---------|
| 踩坑/bug/修复经验 | `memory/lessons-learned.md` |
| NixOS 配置变更 | `memory/nixos-config.md` |
| 问题速查 | `memory/troubleshooting.md` |
| 跨会话待办 | `memory/pending-tasks.md` |
| 用户偏好/设备/架构决策 | `memory/MEMORY.md` |
| AI 工具对比 | `memory/ai-tools.md` |
| 方案/灵感/进展 | `memory/ideas-roadmap.md` |
| 代码库探索结论 | `memory/codebase-map.md` |
| 设备互联拓扑 | `memory/setup-plan.md` |
| App/软件开发经验 | `memory/app-dev-journal.md` |
| 操作手册 | `memory/command-reference.md` |

### 主动记忆触发（PROACTIVE_MEMORY — L2）
- 发现系统工具替换 → `lessons-learned.md`
- 发现设备状态事实 → `setup-plan.md` + `MEMORY.md`
- 发现服务端口/配置不符 → `troubleshooting.md`
- 用户纠正错误假设 → `lessons-learned.md`
- 完成修复流程 → `lessons-learned.md`

---

## L3：参考规则（需要时查询）

### 修复前 Skill 检索（SKILL_FIRST_FIX — L3）
「修复/fix/解决/恢复」类任务时，先 `grep -ri "{关键词}" ~/.claude/skills/` 检索匹配 skill，再 grep lessons-learned 检索历史修复。

### 探索记忆闭环（EXPLORE_MEMORY_LOOP — L3）
Explore 前 `letta_search`，Explore 后 `letta_store` + 同步 codebase-map.md

### 破坏性操作前检索（SAFETY_RETRIEVAL — L3）
nixos-rebuild / systemctl restart / rm 等 → grep memory/ 检查历史风险

### 上下文管理（INCREMENTAL_DISTILL — L3）
上下文>40% 或 /compact 时：先按路由表写入 memory/，再 compact，自动继续任务

### 声明式优先（DECLARATIVE_FIRST — L3）
配置稳定后 MUST 声明式固化。信号：「稳定了」「永久化」「每次都丢」

### NixOS 重建安全门（NIXOS_REBUILD_GUARD — L3）
rebuild 前 MUST `nixos-preflight-check.sh`，后 MUST `nixos-smoketest.sh`

### Letta 核心记忆同步（LETTA_CORE_SYNC — L3）
MEMORY.md 设备/服务/端口变更后 MUST PATCH Letta nixos-sysadmin agent core memory
API: `PATCH http://localhost:8283/v1/agents/agent-8651643c-e753-47ed-9759-bd955c6ac240/core-memory/blocks/human`

### AGENT_FREE_ROUTE（L3）
新配 agent 默认用免费模型。按 agent 类型选模型（见原 CLAUDE.md AGENT_FREE_ROUTE 部分）

### AUTO_SKILL（L3）
每次完成操作后评估 `[AUTO_SKILL] 可封装/跳过`，可封装时立即调用 create-skill.py

### AUTO_AGENT（L3）
重复任务 ≥3次 → 自动创建专职 agent

### SKILL_REMINDER（L3）
每个会话第一个实质性任务前输出 `[SKILL] {领域}: {skills}`

### AUTO_COST_OPTIMIZE（L3）
发现成本优化机会 → 自动修改验证

### AGENTS.md 所有权（L3）
AGENTS.md append only，禁止删除已有规则行

### opencode配置规则（L3）
opencode.json instructions MUST 是数组

### INTENT_TO_RULE（L3）
「每次」「都要」「强制」+ 纠正性反馈 → 立即写入 CLAUDE.md + AGENTS.md

### DESKTOP_IMAGE_INJECT（L3）
收到 `[DESKTOP_SCAN]` hook 注入 → 立即 Read 所有图片路径并处理

### DEVICE_REGISTRY（L3）
设备连接成功后 MUST 记录到 setup-plan.md

### PLAYWRIGHT（L3）
网页操作 MUST 调用 Playwright MCP 工具

### MEDIA_DELIVERY_TEST（L3）
媒体文件交付前 MUST ffprobe/Read 验证

### APK_MULTI_PUSH（L3）
Hub APK 构建后 MUST 同时推送手机+平板

### OUTPUT_DESKTOP_PERSIST（L3）
巡检报告 MUST 保存 `~/Desktop/{类型}/`

### 3000 控制台开发规则（L3）
修改 frontend/app/ 下文件无需 rebuild，HMR 自动生效

### USER_DIRECT_EXEC（L3）
用户说"你自己做了" → 直接执行，禁止推给 CC/OP
