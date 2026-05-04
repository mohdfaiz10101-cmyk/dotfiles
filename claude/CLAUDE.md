# 行为增强规则（L1 核心 + 基础设施）
> L2/L3 规则见 `memory/rules-secondary.md`，按需加载

## 规则分层说明
- **L1**（本文件）：始终生效的核心规则，~15 条
- **L2**（rules-secondary.md 上半）：会话启动 + 任务执行时加载
- **L3**（rules-secondary.md 下半）：特定场景查询时参考

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式（R1-R8）
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`
- **R4** 紧凑布局：段落不超3行
- **R5** 加粗节制：每段最多1个
- **R6** 代码限制：单块≤15行
- **R7** 并行执行：能并行一定并行
- **R8** 装饰预算：≤10%

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

## NixOS 专项
- 路径禁令：NEVER 硬编码 `/nix/store/xxx/bin/xxx`，用 `/run/current-system/sw/bin/xxx`
- NEVER TOUCH：不得随意修改 `/etc/nixos/`，除非用户明确要求且先验证
- 常用命令：
```bash
sudo nixos-rebuild switch --flake /etc/nixos#charlie
nix flake check /etc/nixos
```

## 定时任务时段（TIMER_HOURS — 死规则）
- 允许：08:00-23:00 | 禁止：00:00-07:59
- 创建/修改 timer 后 MUST grep 验证无凌晨时间残留

## 用户偏好自动执行（USER_PREF_AUTO — 死规则）
Charlie 说过的话、做过的选择 → MUST 作为永久偏好自动执行，禁止回问确认。
- 违反时 → 写入 lessons-learned.md

## 模型路由决策表
| 任务类型 | 执行方式 |
|---------|---------|
| 简单问答、格式化 | `glm "<prompt>"` 或直接处理 |
| 中文对话、翻译 | `glm "<prompt>"` |
| Bug修复、功能实现 | 直接处理 |
| 代码生成（长上下文） | `glm` 或 LiteLLM `glm-4-flash` |
| 架构设计、方案对比 | `glm` 完整版 |

**外部模型**：GLM=`glm "<prompt>"` | DeepSeek=LiteLLM `localhost:4000` key `sk-litellm-charlie-2026` model `silicon/deepseek-v3.2`

**Deep 路由自动升级（DEEP_ROUTE_UPGRADE）**：Router `Route: deep | Confidence: 80%+` 且当前为 Turbo → `glm` 委派

**失败升级链**：连续2次失败 → 传递原始任务+失败原因，格式 `[ESCALATION] 从X升级到Y`

## 基础设施清单（SOLUTION_FIRST — 死规则）
方案第一行输出：`[SOLUTION_FIRST] 基于已有: {组件} → 叠加: {新增}`

| 组件 | 地址/路径 |
|------|---------|
| AGI Brain | `~/agi/macg.py` + systemd |
| Letta 记忆 | `localhost:8283` |
| LiteLLM 网关 | `localhost:4000` |
| FastAPI Gateway | `localhost:9900` |
| Hub API | `localhost:9800` |
| OP 任务系统 | `op-tasks.md` + systemd timers |
| ChromaDB | `localhost:8000` |
| Paperclip | `localhost:3100` |
| mihomo 代理 | `localhost:7890` |
| **3000 控制台** | `localhost:3000` — Next.js dev模式（HMR） |
| memory/ | `~/.claude/projects/-home-charlie/memory/` |
| L2/L3规则 | `memory/rules-secondary.md` |

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
