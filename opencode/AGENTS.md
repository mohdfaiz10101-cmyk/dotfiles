# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-04-20 -->

## 输出约束（硬规则 — 最高优先级）
- **每条任务结果 ≤ 1 行**，格式：`[ok/fail/skip] 任务名 — 结果`
- **总输出 ≤ 15 行**，超出截断，不续写
- **禁止**：解释执行过程、列操作步骤、"我将..."、"首先..."、markdown 大标题（##）、无关代码块
- **禁止**：重复输出任务描述或 prompt 内容
- **禁止**：输出"完成""好的""已经"等无信息量的确认语
- 只输出结论和关键数据，不输出推理过程

## 语言规则
- MUST 始终使用中文回复用户，所有对话、解释、报告均用中文
- 代码注释可以用英文，但所有面向用户的输出必须是中文

## 输出格式规则
**R1 零废话**：禁止寒暄前缀（"好的""我来""接下来"）、禁止第一人称动作描述、禁止过渡句。直接输出结果。
**R2 指令式语态**：每行是状态更新，格式 `动作 → 结果 → 下一步`。不解释"为什么要这样做"，除非用户问。
**R3 统一状态标记**：只用一套前缀语法 — `[OK]` `[FAIL]` `[SKIP]`。不混用其他状态系统（emoji 状态、框线状态等）。
**R4 紧凑布局**：段落不超 3 行。只在**主题切换**时插入空行，同一主题内连续输出。代码块带语言标识。
**R5 加粗节制**：每段最多 **1 个加粗**（核心结论）。用加粗替代 markdown 标题做分节。
**R6 代码/输出限制**：单个代码块不超 15 行，超出用 `见 <文件路径>` 替代。工具输出超 30 行只显示关键部分。
**R7 并行执行**：能并行的工具调用一次发出。每次工具调用前 1 句意图说明，返回后 1 句状态确认。
**R8 装饰预算**：装饰元素（分隔线、标记符号、框线）不超过回复总行数的 10%。信息密度优先。
- 操作 ≤ 3 步 → 直接用 `动作 → [OK]` 格式，不用模板
- 多个独立状态 → 卡片分组
- 时间顺序重要 → 时间轴
- 前后对比 → 极简双栏
- 有明确依赖 → 树状层级
- 流程/管道 → 流程管道
**禁止**：一次回复中使用超过 2 种模板（视觉疲劳）。

## 受保护文件
- **NixOS Generation** — 不得随意修改 /etc/nixos/ 下的 .nix 文件，除非用户明确要求且先 `nixos-rebuild build` 验证
- 任何任务（P0-P7）MUST 在 Docker 层 / 用户空间完成，不碰 NixOS modules

## 自动验证
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

## 安全检索协议
执行破坏性操作前，MUST 先检索 `memory/` 中的历史经验，避免重蹈覆辙。
- `nixos-rebuild` / `nix flake update` / `nix-env`
- `systemctl` restart/stop/disable
- 修改 `/etc/nixos/` 下任何文件
- `rm` / `dd` / `mkfs` / `fdisk` 等磁盘操作
- Docker `rm` / `prune` / 网络变更
- NVIDIA 驱动相关任何操作
- 代理/网络/mihomo 配置变更
   - 命中历史故障 → 输出 `[历史风险] 检测到相关记录：...`，评估与当前操作的关联性
   - 无命中 → 正常执行

## NixOS 常用命令（死规则 — 必须用完整格式）
- **重建系统**：`sudo nixos-rebuild switch --flake /etc/nixos#charlie`（禁止省略 `--flake /etc/nixos#charlie`）
- **验证语法**：`nix flake check /etc/nixos`
- **只构建不切换**：`sudo nixos-rebuild build --flake /etc/nixos#charlie`
- `charlie` 是此机器的 flake 输出名，还有 `minipc` 是另一台机器，不要搞混

## 回复结尾（死规则）
- **每次有实际操作的回复**，末尾 MUST 附 1 行：`📎 [{agent}] 已写入 → {文件名}`
- **agent 标注（强制）**：`📎 [GLM-5.1/Sonnet/Opus/DeepSeek/explore/oracle...] 已写入 → {文件名}`
- **纯对话、无操作的回复** → 不附加尾注

## 工作模式

<!-- truncated: exceeded size limit -->