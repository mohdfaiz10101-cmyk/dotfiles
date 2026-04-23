# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-04-22 — CC维护。OpenCode agent: 可追加新规则，严禁删除/修改已有内容 -->

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

## 声明式优先（DECLARATIVE_FIRST — 死规则）
配置稳定后 MUST 声明式固化，禁止用"备份+恢复脚本"替代。
触发信号：用户说「稳定了」「永久化」「每次都丢」「备份一下」
→ MUST 提示：`[DECL] 建议声明式固化，路径：{nix模块}，方案：{home-manager/nixos module}`
→ 禁止只给 backup/restore 脚本方案

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

## Letta 记忆强制读取（LETTA_MEMORY_FIRST — 死规则）
每个任务执行前 MUST 先查记忆，禁止凭空操作：
1. **修复/配置/运维类任务** → `letta_search("{关键词}")` 搜索历史经验
2. **新任务/探索类任务** → `letta_search("{领域关键词}")` 查找已有上下文
3. 搜索无命中 → 输出 `[LETTA_MISS] 无历史记忆`，再开始操作
4. 搜索命中 → 输出 `[LETTA_HIT] {摘要}`，优先按历史方案执行
5. 任务完成后 → `letta_store("{结论}", tags="{标签}")` 写回记忆
**触发场景**：代理节点选择、服务修复、系统配置、重复性操作、用户提到"之前做过"
**禁止**：跳过记忆直接操作 | 假装 Letta 不可用而不尝试

## 修复前 Skill 检索（SKILL_FIRST_FIX — 死规则）
收到任何「修复/fix/解决/恢复」类任务时，MUST 先执行：
1. `grep -ri "{关键词}" ~/.claude/skills/` 检索匹配 skill
2. `grep -i "{关键词}" memory/lessons-learned.md` 检索历史修复
3. 命中 skill → 调用 Skill 工具，输出 `[SKILL_HIT] 调用: {skill名}`
4. 命中历史 → 按历史方案执行，输出 `[HISTORY_HIT] lessons-learned #{行} → {摘要}`
5. 均无命中 → 手动诊断，输出 `[SKILL_MISS] 无历史，开始诊断`
禁止：跳过检索直接手动修复

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
`~/.config/opencode/AGENTS.md` 和 `~/dotfiles/opencode/AGENTS.md` **只能由 CC（Claude Code）写入/修改**。
禁止 GLM / OpenCode agent / OP / sisyphus / 任何其他 AI 直接修改。
需要新增规则 → 输出 `CC_DELEGATE: 新增规则到 AGENTS.md: {内容}`，由 CC 执行。
opencode-config-guard.sh 修复时 MUST 从 git 恢复 CC 提交的版本，禁止覆盖。

## 3000 控制台开发规则（dev 模式 — 死规则）
`localhost:3000` 是 Next.js dev 模式（HMR），改完自动生效。
路径：`/mnt/ai/apps/agi-control-plane/frontend/app/`
禁止执行 `bun run build` / `next build` 或切换 `NODE_ENV=production`。修改文件后无需重启服务。

## 模型标识（强制输出 — 死规则）
每次回复第一行 MUST 输出：`▸ {emoji} {模型代号} | {路由原因}`
- GLM-4.7：`▸ ⚡ GLM-4.7 | 快速任务`
- GLM-Z-Flash（glm-5-turbo）：`▸ 🔧 GLM-Z-Flash | 均衡任务`
- GLM-Z-Air（glm-5.1 coding）：`▸ 🐉 GLM-Z-Air | 代码/SWE任务`
- Claude Sonnet：`▸ ✅ Sonnet | CC直接处理`
禁止：跳过首行标识 | 把标识放在回复末尾 | 只有部分回复有标识

---
Source: ~/CLAUDE.md | Auto-compiled | CC-only writes

## 云端备份（CLOUD_BACKUP — 死规则）
用户说「备份」「推送」「云端」「保存配置」时，MUST 执行：
```bash
bash ~/dotfiles/push-to-cloud.sh "auto backup $(date '+%Y-%m-%d %H:%M')"
```
- 该脚本同步 skills/memory/CLAUDE.md/agents 到 `~/dotfiles/` 并 git push 到 GitHub
- `opencode.json` 已是软链接→dotfiles，无需额外同步
- 执行后输出 `[BACKUP_OK] 已推送 GitHub: mohdfaiz10101-cmyk/dotfiles`
- 禁止：只说"可以备份"但不执行脚本
- **搜索年份死规则**：WebSearch 关键词 MUST 包含当前年份（2026），禁止只搜 2024/2025

## 会话记忆自动加载（SESSION_MEMORY_BOOT — 死规则）
每个会话第一个实质性任务前 MUST 并行执行：
1. `mcp__letta-memory__letta_recall` 查询最近上下文（query="最近任务 用户状态 进行中项目"）
2. 读取 `~/.claude/projects/-home-charlie/memory/MEMORY.md` 获取用户档案
- 输出格式：`[MEM] Letta: {命中条数}条 | 档案: {关键摘要}`
- Letta 不可用时降级：只读 memory/ 文件，输出 `[MEM] Letta离线，使用本地档案`
- 纯闲聊/单句问答 → `[MEM] skip:非实质性任务`
