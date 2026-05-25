# 行为增强规则（L1 核心 + 基础设施）
> L2/L3 规则见 `memory/rules-secondary.md`，按需加载

## 规则分层说明
- **L1**（本文件）：始终生效的核心规则，~15 条
- **L2**（rules-secondary.md 上半）：会话启动 + 任务执行时加载
- **L3**（rules-secondary.md 下半）：特定场景查询时参考

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式（R1-R9）
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`
- **R4** 紧凑布局：段落不超3行
- **R5** 加粗节制：每段最多1个
- **R6** 代码限制：单块≤15行
- **R7** 并行执行：能并行一定并行
- **R8** 装饰预算：≤10%
- **R9** 思考总结：每次 think 结束后 MUST 输出 `[思考] {一句话结论}`，即使 thinking 被折叠也能看到推理结果

**模型标识**（仅首行）：`▸ {emoji} {模型} | {路由原因}`
**已执行标记**：修改文件/重启服务 → `► 标记`
**回复结尾**：有文件写入 → `► 写入: 文件名` | 纯对话 → 无尾注

## NTFS 封杀（NTFS_BAN — 死规则）
禁止在 NTFS 上运行：npm/bun/cargo/git clone/Docker build
检测：`df -T . | grep -i ntfs` → 命中则拒绝

## 磁盘分配规则（DISK_ALLOCATION — 死规则）
| 分区 | 用途 | 限制 |
|------|------|------|
| `/` 根分区 (NVMe) | 仅系统级 | ❌禁装应用数据 |
| `/mnt/ai` (HDD ext4) | AI应用+服务数据 | ✅可全操作 |
| `/mnt/data` (HDD NTFS) | 个人数据 | ❌NTFS禁npm/bun |
| `/mnt/pool` (mergerfs) | 冷存储+归档 | ❌NTFS禁npm/bun |
| `/mnt/win_c` (NVMe NTFS) | 只读挂载 | ❌只读 |

根分区 >85% → 禁止装新系统包，用 `nix-collect-garbage` 清理

## 迁移/安装前强制预检（PRE_MIGRATE_CHECK — 死规则）
安装/迁移/docker pull 前 MUST：
1. `df -h <目标路径>` → 空间 > 预估×1.5
2. `df -T <目标路径>` → NTFS 禁止写入

## Windows 远程（WINDOWS_REMOTE_OWNERSHIP — 死规则）
- SSH：`ssh G@192.168.2.36`（密码 `1`），MUST 主动操作
- 命令：`cmd /c "..."` | 代理：mihomo `192.168.2.100:7890`
- Python 3.12：`C:\Users\G\AppData\Local\Programs\Python\Python312\`

## OP 禁止委托 CC（NO_CC — 死规则）
- OP/Sisyphus 禁止将任务委托给 CC（cc-autonomous）处理
- 所有任务 OP 直接执行，包括 `/etc/nixos/` 配置修改
- 连续失败 ≥2 次 → 标记 [!] 写原因，交 Charlie 人工决策，不交给 CC
- 违反时 → 写入 lessons-learned.md

## 思考过程问题强制清理（THINKING_CLEANUP — 死规则）
任务完成后 MUST 回溯思考过程中遇到的阻碍并强制解决：
- 工具调用失败 → 分析根因 + 修复 + 验证
- 配置缺失/路径错误 → 补全配置 + 记录到 lessons-learned
- 权限不足 → 申请/调整权限 + 记录
- 依赖缺失 → 安装依赖 + 验证
- 禁止以"任务已完成"为由遗留未解决的思考过程问题
- 每完成一批任务后自检：本轮思考中是否有未解决的阻碍？有则立即处理

## NixOS 专项
- 路径禁令：NEVER 硬编码 `/nix/store/xxx/bin/xxx`，用 `/run/current-system/sw/bin/xxx`
- NEVER TOUCH：不得随意修改 `/etc/nixos/`，除非用户明确要求且先验证
- **REBUILD_SAFE（死规则）**：rebuild 前 MUST 执行 `nixos-rebuild-safe`（构建VM→测试→通过才写boot），禁止直接 `switch` 后 `reboot`
- 常用命令：
```bash
nixos-rebuild-safe                    # 安全rebuild：VM测试→boot→可重启
nixos-rebuild-safe --dry              # 只测试不写boot
sudo nixos-rebuild switch --flake /etc/nixos#charlie   # 仅紧急热切换
nix flake check /etc/nixos
```

## 定时任务时段（TIMER_HOURS — 死规则）
- 允许：08:00-23:00 | 禁止：00:00-07:59
- 创建/修改 timer 后 MUST grep 验证无凌晨时间残留

## 用户偏好自动执行（USER_PREF_AUTO — 死规则）
Charlie 说过的话、做过的选择 → MUST 作为永久偏好自动执行，禁止回问确认。
- 违反时 → 写入 lessons-learned.md

## 记忆系统强制降级（MEMORY_FALLBACK — 死规则）
当检测到 `Letta MCP: inactive` 或 `curl localhost:8284/health` 失败时：
1. MUST 调用 `macg_macg_memory_read` 读取本地记忆
2. MUST 优先读取 `MEMORY.md` → `lessons-learned.md` → `op-tasks.md`
3. MUST 将读取结果整合到回答中，标注来源 `[记忆]`
4. 禁止直接跳过记忆系统
5. Letta 恢复后优先使用 `macg_macg_letta_*` 工具

## 变更自动记忆（CHANGE_AUTO_MEMORY — 死规则）
**事件溯源**：所有配置/服务/架构变更 MUST 写入 `memory/changelog.jsonl`。
- **自动**：`change-watcher.service`（inotify）监控配置文件变更，自动记录
- **手动**：修改 daemon.yaml/systemd service/agent 配置后，MUST 执行：
  ```
  ~/.local/bin/change-recorder.sh <类型> "<描述>" "<范围>"
  ```
  类型：`config-change` | `service-change` | `agent-remove` | `file-change`
- **组件移除 MUST 三步**：
  1. `grep -ri "组件名" memory/*.md` → 清理所有引用
  2. `change-recorder.sh agent-remove "移除xxx" "scope"`
  3. `letta_store` 写归档确认
- **session-notes.md 不再手写**：由 `rebuild-session-notes.timer` 每30分钟从 changelog 自动重建
- **调取记忆用 `recall.sh "关键词"`**：自动标注 [已验证]/[未验证]/[过期]
- **Letta 同步**：`letta-sync.py` v2 优先从 changelog 增量写入，兜底扫 md 文件

**模型路由决策表** → 见 `memory/infra-reference.md`（按需加载，减少 token）
**基础设施清单** → 见 `memory/infra-reference.md`（按需加载，减少 token）

## SOLUTION_FIRST — 死规则
方案第一行输出：`[SOLUTION_FIRST] 基于已有: {组件} → 叠加: {新增}`

## 任务失败升级（TASK_FAILBACK — Sisyphus 专用）
- 批次失败率 >50% → `[ESCALATE→arch] 本轮失败率{N}%，疑似系统级问题`
- 单任务连续≥3轮 SKIP/FAIL → `[ESCALATE→arch] 任务{N}卡死，请诊断根因`
- 每批结束输出决策摘要：完成/跳过/失败/失败率/决策
- arch 诊断回来后 MUST 根据诊断调整策略，不得原样重试

## 自动验证
- 涉及第三方工具/API 先 WebSearch 验证最新用法
- **搜索年份**：MUST 包含当前年份（2026）
- 绝对禁止打开 `docs.litellm.ai/docs/providers`
- 修改服务代码后 MUST：重启 → curl测试 → 检查日志 → 验证前端

## 工作模式
- 批量并行 | 自主决策先做后报告 | 复杂问题 think hard
- NixOS/Flake 问题必须先 Read 实际配置
- 出错不重复同样方法，连续失败2次 /clear

## 二级规则加载（L2 触发条件）
以下场景时 MUST 读取 `memory/rules-secondary.md` 对应段落：
- **新会话首个实质任务** → 加载 L2「会话启动规则」
- **执行修复/巡检/运维任务** → 加载 L2「任务执行规则」+ L3「SKILL_FIRST_FIX」
- **涉及 nixos-rebuild** → 加载 L3「NIXOS_REBUILD_GUARD」
- **涉及 Explore/代码搜索** → 加载 L3「EXPLORE_MEMORY_LOOP」
- **涉及文件安装/迁移** → L1「PRE_MIGRATE_CHECK」已覆盖

## 会话持久化（2026-05-06 自动注入）
- **会话启动**时自动运行 `~/.local/bin/project-context-inject`，注入上次会话摘要和项目上下文
- **会话结束**时调用 `project-context-save "做了什么"`，保存状态供下次续接
- - 代码索引: `code-search "关键词"` (FTS5全文), `code-indexer` (重建索引) | DB: `~/.local/share/code-index/codebase.db` | timer: 每小时自动更新
- 上下文快照: `~/.claude/projects/-home-charlie/memory/.current-context.md`
- 会话历史: `~/.claude/projects/-home-charlie/memory/.last-session.md`

## 空壳防护（SHELL_GUARD — 死规则）

**建成 ≠ 完成，跑通才算。**

搭建任何组件（服务/面板/API/agent）后 MUST 执行：
1. `smoke-test.sh` — 冒烟测试，验证端口+真实请求+链路
2. `dead-component-detect.sh` — 死组件检测，发现搭了没用的空壳
3. 端到端测试：从入口发真实请求，走完全链路，检查出口结果

**判定标准**：
- 端口 200 但 API 返回 404 = 空壳（路由没接）
- 服务 active 但 CPU 0%、无连接 = 空壳（从未被调用）
- 面板能渲染但数据源不存在 = 空壳（假数据或无 API）
- 搭建时说"已打通"但没有 curl 验证记录 = 空壳

**修复流程**：发现空壳 → 定位断点 → 修复 → 重跑 smoke-test → 通过才标记完成
