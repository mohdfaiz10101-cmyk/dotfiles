# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-05-22 00:39 -->

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`
- **R4** 紧凑布局：段落不超3行
- **R5** 加粗节制：每段最多1个
- **R6** 代码限制：单块≤15行
- **R7** 并行执行：能并行一定并行
- **R8** 装饰预算：≤10%

## NixOS 专项
- 路径禁令：NEVER 硬编码 `/nix/store/xxx/bin/xxx`，用 `/run/current-system/sw/bin/xxx`
- NEVER TOUCH：不得随意修改 `/etc/nixos/`，除非用户明确要求且先验证
- **REBUILD_SAFE（死规则）**：rebuild 前 MUST 执行 `nixos-rebuild-safe`（构建VM→测试→通过才写boot），禁止直接 `switch` 后 `reboot`
- 常用命令：

## 自动验证
- 涉及第三方工具/API 先 WebSearch 验证最新用法
- **搜索年份**：MUST 包含当前年份（2026）
- 绝对禁止打开 `docs.litellm.ai/docs/providers`
- 修改服务代码后 MUST：重启 → curl测试 → 检查日志 → 验证前端

## 工作模式
- 批量并行 | 自主决策先做后报告 | 复杂问题 think hard
- NixOS/Flake 问题必须先 Read 实际配置
- 出错不重复同样方法，连续失败2次 /clear

## DISCOVERY_RECORD（发现即记录 — 死规则）
任何外部系统状态发现（路由器配置、Docker容器、远端服务、API响应中包含的未知配置）MUST在发现后立即写入三层记忆：
1. `memory_write("lessons-learned.md", ...)` — 一行摘要
2. `letta_store(...)` — 关键事实+标签
3. `memory_set(...)` — 实体化到Memgraph（如有明确实体名）

触发条件：
- 查询外部系统时发现配置与预期不符（如"以为没有，实际已有"）
- 发现新的端口/服务/端点/凭据
- 任何"这个信息以后会用到的"系统状态

记录格式（≤50字）：
`[auto] 发现: {系统}.{属性} = {值} | 原预期: {预期}`

> 此规则填补TOOL_LEARN(只记工具调用)与Letta写回(只记任务完成)之间的盲区：系统状态被动发现。


## 记忆系统状态（自动注入 2026-05-24 18:17）
| 指标 | 值 |
|------|-----|
| KG实体/关系 | 125 / 14 |
| Letta MCP | active |
| lessons-learned条目 | 21 |
| 历史会话数 | 2 |

### 高频主题（最近）


> 以上由 memory-bootstrap.sh 自动注入，每小时更新

---
Source: ~/CLAUDE.md | Auto-compiled

## FALSE_POSITIVE_GUARD（假阳性识别 — 死规则）

以下情况 **不是失败**，禁止误报为故障：
- `opencode-job-*` systemd service 显示 failed/重启 → 先检查 `systemctl --user show xxx --property=Result`，`Result=success` = **正常结束**（oneshot timer job），无需处理
- `ExecMainStatus=0` = 成功退出，不视为异常
- 看到 "连续3次重启失败" 且目标是 opencode timer job → **先验证 Result 再上报**，禁止直接标记 [!]

## CONFIG_PROTECT（配置保护边界 — 死规则）
以下文件禁止修改，修改会破坏自身运行环境，只能由 CC dev.*模式处理：
- `~/.config/opencode/opencode.json`
- `~/dotfiles/opencode/opencode.json`
- `~/.config/opencode/agents/*.md`
- `~/dotfiles/opencode/agents/*.md`
- `~/dotfiles/opencode/oh-my-openagent.jsonc`
违反 → 标记 [!] 交 CC 处理，不得自行回滚
