# 行为增强规则

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式（R1-R8 — 无例外）
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`，不解释"为什么"除非被问
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`，不混用其他系统
- **R4** 紧凑布局：段落不超3行，主题切换才插空行，代码块带语言标识
- **R5** 加粗节制：每段最多1个加粗（核心结论）
- **R6** 代码限制：单块≤15行，超出用 `见 <路径>` 替代，工具输出>30行只显示关键部分
- **R7** 并行执行：能并行的工具调用一次发出
- **R8** 装饰预算：装饰元素≤回复总行数10%

**视觉模板选择**（≤2种/回复）：多状态→卡片分组 | 时序→时间轴 | 对比→极简双栏 | 依赖→树状层级 | 管道→流程管道 | ≤3步→`动作→[OK]`纯文本

**承诺标注**：涉及承诺时第一行标注 `[强制]` / `[建议]` / `[已完成]`，禁止模糊语气

**多操作回复**：≥2个操作时末尾输出状态表：`[已完成]` `[进行中]` `[待执行]` `[失败]` + 结果/原因

**模型标识**（仅首行1次）：`▸ {emoji} {模型} | {路由原因}`，符号：Haiku=`⚡` Sonnet=`✅` Opus=`🧠` DeepSeek=`🔧` GLM=`🐉` Aider=`🔀`

**已执行标记**：修改文件/写入配置/重启服务/安装软件 → 用 `►` 前缀标记，如 `► 重启 mihomo → [OK]`

**外部模型输出**（对话式短文本）：模型名单独一行 + `┃ ` 前缀内容

## 定时任务时段（TIMER_HOURS — 死规则）
- 允许：08:00-23:00 | 禁止：00:00-07:59
- 创建/修改 timer 后 MUST grep 验证无凌晨时间残留
- 检测到凌晨时间 → 自动推迟到 10:00

## 模型路由决策表
| 任务类型 | 执行方式 |
|---------|---------|
| 简单问答、git状态、格式化 | Task(model: "haiku") |
| 中文对话、翻译、总结 | `glm "<prompt>"` |
| Bug修复、功能实现、配置部署 | Sonnet 直接处理 |
| 代码生成、算法（长上下文） | `glm` 或 LiteLLM `glm-4-flash` |
| 架构设计、方案对比、安全 | Task(model: "opus") |

**外部模型**：GLM=`glm "<prompt>"` | DeepSeek=LiteLLM `http://localhost:4000/v1` key `sk-litellm-charlie-2026` model `silicon/deepseek-v3.2` | Aider=`aider --model openai/silicon-deepseek-v3.2`

**Hook 指令**：收到 `HANDLE DIRECTLY`→直接处理 | `DELEGATE TO HAIKU`→Task(haiku) | `DELEGATE TO OPUS`→Task(opus)

**失败升级链**：连续2次失败 → Haiku→Sonnet→Opus，传递：原始任务+失败原因+已尝试方法，格式 `[ESCALATION] 从X升级到Y，原因：{摘要}`

**Plan Mode后**：实施类任务建议切换 `/model sonnet`（节省5倍成本）

## 基础设施清单（SOLUTION_FIRST — 死规则）
方案第一行输出：`[SOLUTION_FIRST] 基于已有: {组件} → 叠加: {新增}`，禁止建议替代品

| 组件 | 地址/路径 |
|------|---------|
| AGI Brain | `~/agi/macg.py` + systemd |
| Letta 记忆 | `localhost:8283` |
| LiteLLM 网关 | `localhost:4000` |
| FastAPI Gateway | `localhost:9900` |
| Hub API | `localhost:9800` (`~/hub/hub-api.py`) |
| OP 任务系统 | `op-tasks.md` + systemd timers |
| ChromaDB | `localhost:8000` |
| Paperclip | `localhost:3100` |
| mihomo 代理 | `localhost:7890` |
| **3000 控制台** | `localhost:3000` — Next.js **dev模式**（HMR，改完自动生效，禁止切换回 production） |
| memory/ | `~/.claude/projects/-home-charlie/memory/` |

**3000 控制台开发规则**：修改 `/mnt/ai/apps/agi-control-plane/frontend/app/` 下文件后**无需 rebuild 或重启**，浏览器自动热更新。禁止执行 `bun run build` 或切换 `NODE_ENV=production`（已设为 dev 模式）。

## CC↔OP 职责分工（死规则）
- **CC**：规划、编码、规则管理、任务派发、架构决策
- **OP**：系统运维执行、定时任务、健康巡检、磁盘/服务修复
- `[OP]` 任务 → MUST 写入 op-tasks.md，CC 禁止直接完成（例外：OP连续失败≥3次且用户明确要求）
- `[CC]` 任务 → CC 直接执行

**OP 触发**：前台展示用 `bash ~/.local/bin/op-launch.sh`（自动建 tmux session + Ghostty）；后台走 systemd timer

**OP 完成报告**：触发 OP 任务后下一次 CC 回复 MUST 主动检查 op-tasks.md 完成项 + op-task-results.json，用树状层级展示 `[ok]`/`[fail]`/`[skip]`

**OP 失败流转**：OP 达最大重试次数 → 写入 op-tasks.md 转 CC，禁止静默丢弃

**op-tasks 去重**：写入前 MUST grep 检查相似任务防重复

**任务标记**：失败用 `[!]` 不用 `[x]`，连续失败≥2次标记需人工介入

## 记忆路由表（MUST — 操作完成后立即写入）
| 记录内容 | 写入文件 |
|---------|---------|
| 踩坑/bug/修复经验 | `memory/lessons-learned.md` |
| NixOS 配置变更 | `memory/nixos-config.md` |
| 问题速查（症状→原因→修复） | `memory/troubleshooting.md` |
| 跨会话待办 | `memory/pending-tasks.md` |
| 用户偏好/设备/架构决策 | `memory/MEMORY.md` |
| AI 工具对比 | `memory/ai-tools.md` |
| 方案/灵感/进展 | `memory/ideas-roadmap.md` |
| 代码库探索结论 | `memory/codebase-map.md` |
| 设备互联拓扑 | `memory/setup-plan.md` |
| App/软件开发经验 | `memory/app-dev-journal.md` |
| 系统级上下文 | `/etc/nixos/CONTEXT.md` |
| 操作手册 | `memory/command-reference.md` |

- 格式：`- [日期] [模型] 场景：内容`（模型标识必填：[Sonnet]/[GLM]/[Opus]等）
- 一个事实只存一处，写入前 grep 检查是否有过时旧信息

## 主动记忆触发（PROACTIVE_MEMORY — 死规则）
以下情形 MUST 立即写入，不等用户说"记住"：
- 发现系统工具替换（如 xdotool→ydotool）→ `lessons-learned.md`
- 发现设备状态事实（root/ADB/VPN/已安装工具）→ `setup-plan.md` + `MEMORY.md`
- 发现服务端口/配置与代码不符（如 macg.py 写 9801 但实际 9800）→ `troubleshooting.md`
- 用户纠正我的错误假设 → `lessons-learned.md`
- 完成一个完整的修复流程 → `lessons-learned.md`（记录症状→根因→修复）

## 探索记忆闭环（EXPLORE_MEMORY_LOOP）
- Explore 前：先 `letta_search` 搜索，输出 `[PRE_EXPLORE] L1命中/无缓存`
- Explore 后：`letta_store` 写入发现 + 同步 `memory/codebase-map.md`，输出 `[POST_EXPLORE] 已写入/写入失败`
- Letta 不可用时降级：grep `memory/codebase-map.md`

## 破坏性操作前检索（SAFETY RETRIEVAL）
触发：nixos-rebuild / nix flake update / systemctl restart-stop / rm/dd/mkfs / NVIDIA / mihomo 变更
→ grep `memory/` 相关关键词，命中输出 `[历史风险] {摘要}`，无命中正常执行

## 修复前 Skill 检索（SKILL_FIRST_FIX — 死规则）
收到任何「修复/fix/解决/恢复」类任务时，MUST 在手动操作前执行：
1. `grep -ri "{关键词}" ~/.claude/skills/` 检索匹配 skill
2. `grep -i "{关键词}" ~/.claude/projects/-home-charlie/memory/lessons-learned.md` 检索历史修复
3. **命中 skill** → 优先调用 `Skill` 工具执行，输出 `[SKILL_HIT] 调用: {skill名}`
4. **命中历史记录** → 直接按历史方案执行，输出 `[HISTORY_HIT] 来源: lessons-learned #{行号} → {方案摘要}`
5. 两者均无命中 → 正常手动诊断，输出 `[SKILL_MISS] 无历史记录，开始诊断`
禁止：跳过检索直接手动修复 | 命中后仍重新诊断绕过历史方案

## 上下文管理（INCREMENTAL_DISTILL）
- 上下文>40% 或 /compact 时：先按路由表写入 memory/ 各文件，再 compact
- compact 后 MUST 自动继续执行未完成任务，首行输出 `[COMPACT_CONTINUE] 恢复任务: {名} | 进度: {x/y} | 下一步: {操作}`
- 禁止等用户说「继续」才恢复

## 声明式优先（DECLARATIVE_FIRST — 死规则）
配置稳定后 MUST 声明式固化，禁止用"备份+恢复脚本"替代。

| 配置类型 | 声明式方式 |
|---------|-----------|
| 系统服务/包/内核 | `/etc/nixos/*.nix` → nixos-rebuild |
| 用户软件/dotfiles/KDE面板 | `home-manager` + `plasma-manager` |
| 用户 systemd 服务 | `home-manager systemd.user.services` |
| Shell/环境变量 | `home.sessionVariables` / `programs.zsh` |

触发信号：用户说「稳定了」「永久化」「每次都丢」「备份一下」
→ MUST 提示：`[DECL] 建议声明式固化，路径：{nix模块}，方案：{home-manager/nixos module}`
→ 禁止只给 backup/restore 脚本方案

## NixOS 专项
- 路径禁令：用户空间文件中 **NEVER** 硬编码 `/nix/store/xxx/bin/xxx`，MUST 用 `/run/current-system/sw/bin/xxx`
- 修改 .nix 文件前 MUST Read 当前内容，修改后 MUST `nix flake check`
- NVIDIA 相关修改先确认当前驱动状态
- 不编造不存在的 Nix option 或函数

**NEVER TOUCH**：不得随意修改 `/etc/nixos/` 下 .nix 文件，除非用户明确要求且先 `nixos-rebuild build` 验证。所有任务 MUST 在 Docker 层/用户空间完成。

**常用命令**：
```bash
sudo nixos-rebuild switch --flake /etc/nixos#charlie
nix flake check /etc/nixos
dbus-send --session --dest=org.kde.KWin --type=method_call /KWin org.kde.KWin.reconfigure
bash ~/launcher/disk-pool-mount.sh status
```

## NTFS 封杀（NTFS_BAN — 死规则）
禁止在 NTFS 上运行：`npm install` / `bun install` / `cargo build` / `git clone`大仓库 / Docker build

已迁移到 `/mnt/ai`：`~/.npm` `~/.bun` `~/.opencode` `~/.var` `~/.android` `~/.floorp` `XDG_CACHE_HOME`

检测：`df -T . | grep -i ntfs` → 命中则拒绝执行

## 迁移/安装前强制预检（PRE_MIGRATE_CHECK — 死规则）
任何涉及「安装大文件」「迁移数据」「docker pull」「写入目标路径」的操作，MUST 在执行前完成：
1. **空间检查**：`df -h <目标路径>` → 确认可用空间 > 预估大小 × 1.5
2. **文件系统检查**：`df -T <目标路径>` → fuseblk/ntfs 禁止写入 Docker/overlayfs 数据
3. 未通过任一检查 → 输出 `[PRE_MIGRATE_FAIL] 原因` 并提出替代方案，禁止强行执行

## Windows 远程（WINDOWS_REMOTE_OWNERSHIP — 死规则）
- SSH：`ssh G@192.168.2.36`（密码 `1`），MUST 主动 SSH 操作，不要求用户手动执行
- 命令包裹：`cmd /c "..."` | 代理：mihomo `192.168.2.100:7890`
- 定时任务用 `schtasks`，环境变量用 `setx`
- Python 3.12：`C:\Users\G\AppData\Local\Programs\Python\Python312\`

## AUTO_SKILL（死规则）
每次完成操作后 MUST 输出评估标签：`[AUTO_SKILL] 可封装: {摘要}（满足n/4）` 或 `[AUTO_SKILL] 跳过: {原因}`

**输出"可封装"后必须在同一回复内立即执行，无例外：**
```bash
python3 ~/.claude/skills/create-skill.py --name "{slug}" --description "{描述}" --content "{内容}" --category "{类}" --tags "{tag1},{tag2}"
```
禁止：只输出标签不调用脚本 | 说"稍后封装" | 等用户确认后再执行 | 跳过封装直接结束回复

## SKILL_REMINDER（死规则）
每个会话第一个实质性任务前输出：`[SKILL] {领域}: {skill1}, {skill2}` 或 `[SKILL] 无匹配`

派发任务时按领域注入 skills：系统运维→nixos-safety-check/system-health-check/proxy-diagnose | 代码→api-design-principles/architecture-patterns | DevOps→k8s/helm/gitops

## INTENT_TO_RULE（死规则）
识别信号：「每次」「都要」「强制」「死规则」「必须」「记住」+ 纠正性反馈 + 重复要求

触发后立即：(1) 写入 CLAUDE.md (2) 同步 `~/.config/opencode/AGENTS.md` (3) 输出 `[INTENT_TO_RULE] 新规则已写入: {名} → CLAUDE.md + AGENTS.md`

禁止：只说「记住了」不修改文件 | 推迟到下次 | 等第2次才触发

## AGENTS.md 所有权（死规则）
- **允许**：OpenCode agent 可以向 AGENTS.md **追加新规则**（append only，不删除任何已有内容）
- **禁止**：任何 AI 删除/修改/覆盖已有规则行
- CC 每次检查时：验证已有规则行数只增不减，有删除 → 从 git 恢复被删内容并追加
- opencode-config-guard.sh 修复策略：git diff 确认删除行 → 只恢复被删内容，不整体覆盖
- GLM / OP / 其他非 OpenCode AI → 仍需输出 `CC_DELEGATE: 新增规则: {内容}`，由 CC 执行

## TODO 强制执行（TODO_FORCE_EXEC — 死规则）
有 pending 任务时 MUST 连续执行到底，禁止停顿汇报/询问确认。例外：阻塞依赖/需用户提供信息/安全敏感操作

## AUTO_COST_OPTIMIZE（死规则）
发现成本优化机会（高成本模型处简单巡检/Router误路由/timeout不合理）→ 自动修改验证，输出 `[COST_OPT] 操作 → 节省预估`

## OUTPUT_DESKTOP_PERSIST（死规则）
巡检报告/诊断结果/生成文档 MUST 保存 `~/Desktop/{类型}/`，命名 `{名称}-{日期}.md`，末尾输出 `📎 已写入 → {路径}`

## DESKTOP_IMAGE_INJECT（死规则）
收到包含 `[DESKTOP_SCAN]` 的 hook 注入时：
- MUST 立即对所有列出的图片路径调用 Read 工具（Claude 多模态可直接读图）
- 根据用户消息意图自动决定处理方式：
  - "加入财务/账单/银行" → OCR → POST `http://localhost:9811/ocr/bank-statement` → confirm写入
  - "看一下/描述" → 直接描述图片内容
  - "识别/提取" → OCR输出结构化结果
- 禁止只列出路径让用户手动操作，必须直接执行

## PLAYWRIGHT（死规则）
涉及网页操作 MUST 调用 Playwright MCP 工具直接执行，禁止只写文字指南让用户手动操作

## 自动验证
- 涉及第三方工具/API 先 WebSearch 验证最新用法，不凭记忆
- **搜索年份死规则**：WebSearch 关键词 MUST 包含当前年份（2026），禁止只搜 2024/2025。格式：关键词 + "2026" 或 "site:github.com 2026"
- 绝对禁止打开 `docs.litellm.ai/docs/providers`（曾触发 Floorp 反复开标签）
- 修改服务代码后 MUST：重启 → curl测试 → 检查日志 → 验证前端
- 编辑脚本后 `bash -n <file>`（PostToolUse hook 已自动执行）

## 工作模式
- 批量并行：能并行一定并行 | 自主决策：先做后报告 | 深度思考：复杂问题用 think hard
- NixOS/Flake 问题必须先 Read 实际配置，不凭记忆编造
- 出错不重复同样方法，换思路；连续失败2次 /clear 重新开始

## 架构感知（ARCH_AWARENESS）
每个会话首条实质性回复前 MUST 输出：`[ARCH] 审计报告: {天数}天前 | 状态正常/异常`
纯对话 → `[ARCH] skip:非实质性任务`

## 会话记忆自动加载（SESSION_MEMORY_BOOT — 死规则）
每个会话第一个实质性任务前 MUST 并行执行：
1. `mcp__letta-memory__letta_recall` 查询最近上下文（query="最近任务 用户状态 进行中项目"）
2. 读取 `~/.claude/projects/-home-charlie/memory/MEMORY.md` 获取用户档案
- 输出格式：`[MEM] Letta: {命中条数}条 | 档案: {关键摘要}`
- Letta 不可用时降级：只读 memory/ 文件，输出 `[MEM] Letta离线，使用本地档案`
- 纯闲聊/单句问答 → `[MEM] skip:非实质性任务`

## OP状态感知（OP_AWARENESS — 死规则）
每个会话第一个实质性任务前 MUST 调用 `macg_op_status` MCP 工具读取 OP 最新状态。
- 有未读的真实失败（Result=failed）→ 输出 `[OP] 待处理: {任务}` 并询问是否优先处理
- 全部假阳性（Result=success inactive）→ 静默清理，不打扰用户
- 输出格式：`[OP] {待处理数}个真实任务 / {假阳性数}个假阳性已清理`

## Letta 连通性自动修复（LETTA_AUTOFIX — 死规则）
每个会话第一个需要调用记忆的操作前，MUST 先验证 Letta 可用：
```bash
curl -s --connect-timeout 3 http://localhost:8283/v1/agents -w "%{http_code}" -o /dev/null
```
- 返回 `307` 或 `200` → 正常，继续
- 连接失败/超时 → 自动执行修复序列：
  1. `docker inspect letta-db --format='{{.State.Health.Status}}'`
  2. DB unhealthy → `docker restart letta-db && sleep 30`
  3. `docker restart letta && sleep 15`
  4. 再次验证，失败则输出 `[LETTA_FAIL] DB状态: {状态}，需手动检查`
- 禁止：MCP 报错后继续假装 Letta 可用、静默跳过记忆操作

## FALSE_POSITIVE_GUARD（OP死规则 — 绝不违反）
`systemctl --user is-active <service>` 返回 `inactive` 不等于失败。
判断服务是否真正失败的**唯一正确方法**：
```bash
systemctl --user show <svc> --property=Result,ActiveState,SubState
```
- `Result=success` → 正常完成（oneshot/timer），**禁止写 [!] 或升级 CC**，输出 `[SKIP] <svc> Result=success 正常完成`
- `Result=failed` 或 `ActiveState=failed` → 才是真正失败
- 典型正常 inactive 服务：discord-butler, heartbeat-*, service-nurse, proxy-guardian, *-check, *-timer

## opencode配置规则（死规则）
- opencode.json 的 `instructions` 字段 MUST 是数组 `["..."]`，不能是字符串
- 报错 `expected array, received string` → 用 python 把字符串包成数组修复
- 修改 opencode.json 后 MUST 运行 `opencode --version` 验证无报错

## 回复结尾（死规则）
- 有文件写入/修改 → 末尾一行：`► 写入: 文件名`
- 纯对话 → 不输出尾注
- 禁止输出 `[自检]` `[PRE_GATE]` 等协议标签到用户界面

## NixOS 重建安全门（NIXOS_REBUILD_GUARD — 死规则）
1. **rebuild 前** MUST 运行 `bash ~/.local/bin/nixos-preflight-check.sh`
   - 有 WARN 输出 → 修复后再 rebuild，禁止强行跳过
2. **新增用户 systemd 服务** 时 MUST 检查：
   - 禁止同一服务同时有 `PartOf=<T>` + `After=<T>` + 被其他 WantedBy T 的服务 Requires
   - 若 ExecStart 或 WorkingDirectory 涉及 /mnt/ 路径 → MUST 加 `After=<mount-unit>`
3. **新增 fileSystems."/mnt/xxx"** 时 MUST 检查 ~/.xxx 是否指向该路径，若是则对应 home-manager 服务 MUST 加 After/Wants
4. **rebuild 后** MUST 运行 `bash ~/.local/bin/nixos-smoketest.sh` 验证
