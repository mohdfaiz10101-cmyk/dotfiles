# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-04-21 — CC维护，禁止其他AI修改 -->

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

## AGENTS.md 所有权（死规则）
- 本文件**只能由 CC（Claude Code）写入/修改**
- 禁止：GLM / OpenCode agent / OP / 任何其他 AI 直接修改此文件
- 其他 AI 需要新增规则 → 输出 `CC_DELEGATE: 新增规则到 AGENTS.md: {内容}`，由 CC 执行

## FALSE_POSITIVE_GUARD（死规则）
- `systemctl --user is-active <svc>` 返回 `inactive` ≠ 失败
- 判断服务是否真正失败**唯一方法**：`systemctl --user show <svc> --property=Result,ActiveState,SubState`
  - `Result=success` → 正常完成（oneshot/timer），输出 `[SKIP] 正常完成`，**禁止写 [!] 或升级任务**
  - `Result=failed` 且 `ActiveState=failed` → 才是真正失败
- 典型正常 inactive 服务：opencode-job-*、heartbeat-*、*-check、*-timer

## 3000 控制台开发规则（死规则）
- 路径：`/mnt/ai/apps/agi-control-plane/frontend/app/`
- 运行模式：**dev 模式（HMR）**，改完自动生效，浏览器刷新即可
- **禁止执行** `bun run build` / `next build` / 切换 `NODE_ENV=production`
- 修改文件后无需重启服务

## 编码规则（死规则）
- 修改代码文件前 **MUST** 先用 read_file 工具读取当前内容
- 修改后 MUST：重启服务 → curl 验证 → 检查日志 → 确认前端生效
- 禁止凭记忆猜测代码结构

## 基础设施清单
| 组件 | 地址 |
|------|------|
| LiteLLM 网关 | `localhost:4000` |
| Letta 记忆 | `localhost:8283` |
| Hub API | `localhost:9800` |
| FastAPI Gateway | `localhost:9900` |
| 3000 控制台 | `localhost:3000`（dev模式） |
| ChromaDB | `localhost:8000` |
| Twenty CRM | `localhost:3001` |

---
Source: ~/CLAUDE.md | CC维护 | 禁止其他AI修改