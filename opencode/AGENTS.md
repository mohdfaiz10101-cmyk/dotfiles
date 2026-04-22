# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-04-22 — CC维护，禁止其他AI修改。违反者输出 CC_DELEGATE 而非直接写入 -->

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`，不解释"为什么"除非被问
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`，不混用其他系统
- **R4** 紧凑布局：段落不超3行，主题切换才插空行，代码块带语言标识
- **R5** 加粗节制：每段最多1个加粗（核心结论）
- **R6** 代码限制：单块≤15行，超出用 `见 <路径>` 替代，工具输出>30行只显示关键部分
- **R7** 并行执行：能并行的工具调用一次发出
- **R8** 装饰预算：装饰元素≤回复总行数10%
**承诺标注**：涉及承诺时第一行标注 `[强制]` / `[建议]` / `[已完成]`，禁止模糊语气

## NixOS 专项
- 路径禁令：用户空间文件中 **NEVER** 硬编码 `/nix/store/xxx/bin/xxx`，MUST 用 `/run/current-system/sw/bin/xxx`
- 修改 .nix 文件前 MUST Read 当前内容，修改后 MUST `nix flake check`
- NVIDIA 相关修改先确认当前驱动状态
- 不编造不存在的 Nix option 或函数
**NEVER TOUCH**：不得随意修改 `/etc/nixos/` 下 .nix 文件，除非用户明确要求且先 `nixos-rebuild build` 验证。所有任务 MUST 在 Docker 层/用户空间完成。

## 自动验证
- 涉及第三方工具/API 先 WebSearch 验证最新用法，不凭记忆
- 绝对禁止打开 `docs.litellm.ai/docs/providers`（曾触发 Floorp 反复开标签）
- 修改服务代码后 MUST：重启 → curl测试 → 检查日志 → 验证前端
- 编辑脚本后 `bash -n <file>`（PostToolUse hook 已自动执行）

## 工作模式
- 批量并行：能并行一定并行 | 自主决策：先做后报告 | 深度思考：复杂问题用 think hard
- NixOS/Flake 问题必须先 Read 实际配置，不凭记忆编造
- 出错不重复同样方法，换思路；连续失败2次 /clear 重新开始

## 迁移/安装前强制预检（PRE_MIGRATE_CHECK — 死规则）
任何「安装大文件」「迁移数据」「docker pull」「写入目标路径」操作，执行前 MUST：
1. `df -h <目标>` → 可用空间 > 预估 × 1.5
2. `df -T <目标>` → fuseblk/ntfs 禁止写 Docker/overlayfs
未通过 → 输出 `[PRE_MIGRATE_FAIL]` 并提替代方案

## FALSE_POSITIVE_GUARD（OP死规则）
`systemctl --user is-active` 返回 `inactive` 不等于失败。
判断服务是否真正失败的唯一正确方法：`systemctl --user show <svc> --property=Result,ActiveState,SubState`
- `Result=success` → 正常完成（oneshot/timer），禁止写 [!] 或升级，输出 `[SKIP] Result=success`
- `Result=failed` → 才是真正失败

## AGENTS.md 所有权（死规则）
`~/.config/opencode/AGENTS.md` 只能由 CC（Claude Code）写入/修改。禁止 GLM / OpenCode agent / OP 直接修改。
其他 AI 需要新增规则 → 输出 `CC_DELEGATE: 新增规则到 AGENTS.md: {内容}`，由 CC 执行。

## 3000 控制台开发规则（dev 模式 — 死规则）
`localhost:3000` 是 Next.js dev 模式（HMR），改完自动生效。
禁止执行 `bun run build` 或切换 `NODE_ENV=production`。

---
Source: ~/CLAUDE.md | Auto-compiled