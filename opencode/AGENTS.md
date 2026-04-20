# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-04-16 12:34 -->

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

## 回复结尾（死规则）
- **每次有实际操作的回复**，末尾 MUST 附 1 行：`📎 [{agent}] 已写入 → {文件名}`
- **agent 标注（强制）**：`📎 [GLM-5.1/Sonnet/Opus/DeepSeek/explore/oracle...] 已写入 → {文件名}`
- **纯对话、无操作的回复** → 不附加尾注

## 工作模式

<!-- truncated: exceeded size limit -->
## OP 任务系统（2026-04-20更新）
- op-tasks路径：`~/op-tasks.md`（不是 memory/ 下）
- `[ ]` 普通待办 + `[!]` 失败任务都要扫描执行
- `[low]` 任务：检查 CPU idle（`vmstat 1 1 | tail -1 | awk '{print $15}'`），<60% 则跳过
- 禁止输出"是否执行""需要确认"，CC写入即授权

## 假阳性识别（MUST — 防误报）
- `opencode-job-*` service failed → 先检查 `systemctl --user show xxx --property=Result`
- `Result=success` + `ExecMainStatus=0` = **正常oneshot结束**，标 `[x]` 不上报CC

## 定时任务时段（TIMER_HOURS — 死规则）
- 所有 OnCalendar MUST 在 08:00-23:00 内
- **禁止**凌晨（00:00-07:59）执行任何AI/LLM任务

## Windows远程
- SSH: `ssh G@192.168.2.36` 密码 `1`
- 命令用 `cmd /c "..."` 包裹，代理: `http_proxy=http://192.168.2.100:7890`

## opencode自检（启动前必做）
- `bash ~/.local/bin/opencode-config-guard.sh`
- 检测循环链接 → 从备份恢复 → 通知CC

## 基础设施（必须在已有组件叠加，禁止替代）
LiteLLM:4000 | Letta:8283 | AGI:9900 | Hub-API:9801 | Launcher:9875 | Paperclip:3100

## Docker 部署验证协议（DOCKER_DEPLOY_VERIFY — 死规则）
部署 Docker 容器后，MUST 按以下顺序验证，**不得跳过任何步骤**：
1. `docker ps --filter name=<容器名> --format "{{.Status}}"` → 确认 Up
2. `docker inspect <容器名> --format '{{.State.Health.Status}}'` → 循环等待直到 `healthy`（最多60次，每5秒一次）
3. `curl -sf http://localhost:<端口>/<健康路径>` → HTTP 200 才算成功
4. 若步骤3失败 → 立即 `docker logs <容器名> --tail 30` 输出错误，标记 `[FAIL]` 不汇报成功
- **禁止**：容器 Created/Starting 时就汇报"修复成功"
- **禁止**：不 curl 验证就说端口可访问

## 服务修复后验证（SERVICE_FIX_VERIFY — 死规则）
修复任何服务/端口问题后，MUST 输出验证结果：
- `curl -s http://localhost:<端口>/ -o /dev/null -w "%{http_code}"` → 200/301/302 才算可访问
- 非 2xx/3xx → 不汇报成功，继续排查日志
