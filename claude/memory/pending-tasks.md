# 跨会话待办

## 高优先
- [x] **AGI Brain 方案 A：扩展感知源** — 30min ✓ 完成
  - [x] Paperclip Agent 监控（检测 Agent 状态，自动重启失败）
  - [x] 网络状态监控（ping/延迟/代理）
  - [x] GPU 负载感知（整合 Chronos）
- [x] **AGI Brain 方案 B：Web Dashboard** — 1h ✓ 完成
  - [x] 整合到 Chronos RPG 页面（localhost:9875/chronos.html）
  - [x] 实时显示 Sense→Think→Act 流程
  - [x] 可视化感知信号强度
- [x] **AGI Brain 方案 C：Telegram Bot** — ✅ 已完成 (2026-04-06)
  - [x] 接收决策通知
  - [x] 发送指令给 AGI
  - [x] 查询系统状态
- [x] **AGI Brain 方案 D：目标队列** — ✅ 已完成 (2026-04-08)
  - [x] 用户添加长期任务（CLI + Telegram Bot）
  - [x] AGI 自主规划执行（brain.py 集成 + DeepSeek 自动拆分）
  - [x] 进度追踪反馈（dashboard 面板 + 行动自动回写进度）
- [x] **Paperclip 通知收纳** — ✅ 已完成 (2026-04-08) 安卓风格分组/折叠通知面板（hub-api.py + notifications.html）

## 中优先
- [ ] **综合方案：你的个人 AI 系统** — ✅ Week 1-2 完成（2026-04-08），Week 3-4 待执行（详见 ideas-roadmap.md）
  - [x] Week 1：核心跑通（对话管理 + Telegram Bot + MEMORY.md 读取）
  - [x] Week 2 Part 1：主动对话（proactive.py + 意图识别 + 工具集成 + Discord Bot + Web UI）✅ 完成 (2026-04-08 23:34)
  - [ ] Week 2 Part 2：技能提炼（Qwen3 Judge + 业务知识投喂）
  - [ ] Week 3：工具接入（Playwright + 文件读写 + Qdrant）
  - [ ] Week 4：业务对接（UI-TARS + DeepSeek + 真实询盘）
  - **完成度**：Week 1-2 = 95%，超额完成（提前实现了 12 工具自动调用 + 双平台部署 + Web UI）
- [ ] **Mastra.js 自主采购代理** — 🔧 框架完成，待修复 LiteLLM 调用（方案详见 ideas-roadmap.md）
  - [x] Mastra.js 环境搭建
  - [x] GLM System Prompt 设计（采购专家逻辑）
  - [x] Firecrawl Tool 集成（模拟版）
  - [x] 评分引擎开发
  - [x] 前端思维链 UI
  - [x] LiteLLM 调用超时排查
  - [x] SEO/GEO 自动报告生成

## 低优先
- [x] **tech-digest-viewer 自动重启** — ✅ 已有 Restart=on-failure (确认 2026-04-08)
- [x] ~~安装 age + sops，升级 secrets.nix → sops-nix 加密方案~~ ✅ 已完成 (2026-04-08)
- [x] 评估 Tailscale 3 台离线设备是否继续使用
- [x] ~~P1 架构重构待办（configuration.nix 拆分、包管理统一、flake inputs 清理）~~ ✅ 已完成（612→84行，拆分为7模块，确认 2026-04-08）

## 2026-04-08 新增任务

- [x] **Mastra 采购代理 - LiteLLM 修复** — ✅ 已修复 (2026-04-08) 模型改用 auto（GLM-4-Flash），Ollama 本地模型为已知 CUDA bug
  - [x] 排查 LiteLLM 调用超时原因（所有模型均超时）
  - [x] 验证 GLM API Key 有效性
  - [x] 检查本地模型服务状态（local/qwen3-8b）
  - [x] 模型切换为 auto，工具链测试通过

## 系统审查 — 2026-04-09
- [x] **P1 paperclip-auto-sync.log inode 损坏** — ✅ 已修复 (2026-04-15) rm 损坏文件（注意：该 user service 已不存在于 systemd）
- [x] **P2 memory-dream 容错** — ✅ 已修复 (2026-04-15) exit 1 → exit 0，空后端跳过不报错
- [x] **P2 CPU IO Wait 排查** — ✅ 已定位 (2026-04-15) loop0(/mnt/ai) 为瓶颈，IO Wait 35%，Letta 容器 160MB IO 最高
- [x] **P3 browser-cookie-sync 清理** — ✅ 已确认 not-found (2026-04-15)，无需清理
- [x] **P3 Docker 清理** — ✅ mystifying_wing 已不存在 (2026-04-15)

## 微信遗留问题 — 2026-04-11
- [x] **P2 微信 .xwechat 迁移到 ext4** — ✅ 已确认在 ext4 (2026-04-15) 实际指向 POOL-D1(ext4)，非 NTFS，无需迁移
- [x] **P3 微信启动脚本 bwrap 参数** — ✅ 已有 ~/.local/bin/start-wechat (2026-04-15)，自动去掉 --die-with-parent

## 配置持久化后续任务（2026-04-11 添加）

### 立即执行（P0）
- [ ] 为新 git 仓库设置远程 origin
  - `~/.claude/projects/-home-charlie` → 设置远程仓库 URL
  - `~/.claude/skills` → 如果需要独立远程仓库
  - 推送到远程：`git push -u origin master`

### 本周完成（P1）
- [x] 设置 IDE 自动备份 cron job — ✅ 已改用 systemd timer (2026-04-15) backup-ide-configs.timer 每日 02:00，首次运行成功

- [ ] 虚拟机测试完整恢复流程
  - 按 6 步恢复指南验证可行性
  - 记录恢复过程中的问题

- [x] 敏感配置加密备份
  - ✅ 已完成 (2026-04-15) `/mnt/ai/ai-cluster/litellm/.env.age` 使用 age 加密

### 长期优化（P2）
- [x] **NixOS 声明式 VSCode 配置** — ✅ 已完成 (2026-04-16) 决定：保留现有配置
  - 🔧 根因：`programs.vscode` / `xdg.configFile` 均为 home-manager 模块（非 NixOS）
  - 📝 方案选择：
    1. 引入 home-manager（完整声明式，需修改 flake.nix）
    2. 使用 systemd tmpfiles（NixOS 原生，但不推荐）
    3. **保留现有 settings.json**（✅ 已选择）- 最轻量，适合手动安装的 VSCode
  - 📝 配置：保留 ~/.config/Code/User/settings.json（212 项 roo-code-nightly 命令）
  - 📚 参考：Librarian 文档查询结果（完整 3 种方案对比）
  - ✅ NixOS 配置语法检查通过

- [x] **LiteLLM/Letta systemd service 模块化** — ✅ 已完成 (2026-04-16) 决定：保留 Docker Compose
  - 🔧 评估：迁移到 systemd 原生服务
  - 📝 结果：创建 `/etc/nixos/modules/litellm.nix` 和 `letta.nix`（配置分析文档）
  - 🎯 建议：**保留 Docker Compose**（推荐）
    - LiteLLM：2 个服务（redis + litellm），host 网络模式迁移复杂
    - Letta：4 个服务（letta + postgres + chromadb + n8n），依赖链复杂
    - 收益有限：Docker Compose 工作稳定，管理简单
  - 📄 文档：litellm.nix/letta.nix 包含详细迁移评估和步骤

- [ ] 自动化健康检查
  - 定期验证 Docker 容器状态
  - Git 仓库完整性检查

## 2026-04-15 批量待办执行记录

- [x] **修复 litellm-healthcheck** — ✅ /health → /health/liveliness（/health 需认证返回 401）
- [x] **修复 health-monitor.sh** — ✅ chromadb cd 改为 docker start（/mnt/ai/ai-cluster/chroma 不存在）
- [x] **修复 memory-dream 容错** — ✅ 无后端时 exit 0（而非 exit 1）
- [x] **修复 uv 工具链** — ✅ ~/.local/share/uv 符号链接指向不存在的 NTFS offload → 重建目录
- [x] **age 加密 litellm .env** — ✅ /mnt/ai/ai-cluster/litellm/.env.age（key: age1hvscxx...）
- [x] **4 个 GLM systemd timer** — ✅ glm-health(09:00) glm-docker(11:00) glm-tasks(16:00) glm-proxy(18:00)
- [x] **IDE 自动备份 timer** — ✅ backup-ide-configs.timer 每日 02:00
- [x] **terminal-pet 安装** — ✅ uv tool install，Pip the Blob 已孵化 🥚
- [x] **桌面宠物部署** — ✅ terminal-pet + tamagotchi 已安装 (2026-04-15)
- [x] **SpectrAI 营销调研** — ✅ 已完成 (2026-04-16)
  - 📝 基于 8 个行业报告调研 2026 年 AI 工具营销趋势
  - 📄 5 条简短摘要已输出（AI Agent 自主执行、开发者社区营销、GEO 优化、多 Agent 协作、结果导向定价）
- [ ] **Claude Code 风格宠物** — 参考 usik/tamagotchi Phase 2，开发 AI Agent 互动插件
- [x] **firewall.service 诊断** — ✅ 已完成 (2026-04-16) 问题：自定义防火墙与 NixOS 内置冲突
  - 🛠️ 修复脚本：`/etc/nixos/scripts/fix-firewall.sh`（4 步自动修复）
  - ⏳ **待执行**：需要用户手动运行 `sudo /etc/nixos/scripts/fix-firewall.sh`
  - 📝 修复步骤：
    1. 禁用自定义 firewall.service
    2. 删除 /etc/systemd/system/firewall.service
    3. 重新构建 NixOS 配置（启用内置防火墙）
    4. 验证防火墙规则（nft list ruleset）
- [ ] **P0 Git 远程 origin** — 等用户提供远程仓库地址

### 待诊断
- **IO Wait 高**（35%）— loop0(/mnt/ai) 为瓶颈，Letta 容器 160MB IO 最高，考虑限制 Letta 写入频率

## 2026-04-16 认知孪生 + Agent 体系 + 微信合并

### 已完成
- [x] **6 个 Agent Timer 创建** — security-watchdog/proxy-guardian/service-nurse/discord-butler/pet-feeder/cost-accountant 全部 active
- [x] **Timer 格式修复** — OnCalendar 格式 + perl 路径 + PATH 修正（NixOS 适配）
- [x] **Happy CLI 安装** — v1.1.6, npm i -g happy（不兼容 OpenCode）
- [x] **手机远程方案确认** — SSH+tmux+Tailscale 为最佳方案
- [x] **微信旧系统恢复** — 找到 windows-wechat-sync 脚本和 6 个微信 skill
- [x] **wechat-finance 架构映射** — 1003 行工具完整分析
- [x] **Agent 知识库架构审查** — skills(87) + memory(16) + Letta(3) + shared-knowledge 映射

### 卡点（需用户操作）
- [ ] **微信 Windows 端密钥提取** — 用户需在 Windows 上运行 pywxdump 或旧脚本 wechat-auto-decrypt.ps1
  - Windows DB: /mnt/data/WeChat Files/w422417869/Msg/（79 个加密文件）
  - 旧脚本: ~/launcher.bak.1776340007/windows-wechat-sync/
  - 提取密钥后可用 wechat-finance 工具解密

### 待执行
- [ ] **微信管理平台开发** — CLI + Web UI + PostgreSQL + 连接 OpenCode
- [ ] **pycryptodome + zstandard 安装** — wechat-finance 缺失依赖
- [ ] **Agent 知识库可视化方案设计**
- [ ] **memory 文件清理** — lessons-learned.md 196KB/1496行，pending-tasks.md 177行大量已完成

## 2026-04-15 智谱额度消耗 + Letta 修复（进行中）

### 已完成
- [x] **tui.json 配置** — 写入 `~/.config/opencode/tui.json`（dynamic_details_max_lines=5, diff_style=stacked）
- [x] **智谱消耗计划** — 四路线完整规划（见本会话对话）

### 待执行（重启后继续）
- [x] **Letta 容器修复** — ✅ 已确认 (2026-04-15) agents 已存在且 UUID 正确（code-assistant + nixos-sysadmin），letta-mcp 无需更新
- [x] **crontab 写入** — ✅ 已改用 systemd timer (2026-04-15) glm-health(09:00) + glm-docker(11:00) + glm-tasks(16:00) + glm-proxy(18:00)

## 2026-04-14 系统重启后待办

### 立即验证（重启后 5 分钟内）
- [x] Docker 服务自动启动 — ✅ 已确认 (2026-04-15) active (running) 6h+
- [x] LiteLLM 容器运行且 healthy — ✅ 已确认 (2026-04-15) Up 43min (healthy)
- [ ] KDE systemsettings 可打开 — 点击系统设置图标验证
- [x] 关键端口监听 — ✅ 已确认 (2026-04-15) 4000(LiteLLM) + 9875(Chronos) 正常

### Letta 容器调试（优先级高）
- [x] Letta 数据库连接问题 — ✅ 已恢复 (2026-04-15) letta + letta-db 均运行 3h+
- [x] Letta NLTK 初始化超时 — ✅ 已解决 (2026-04-15) 容器正常运行

### Git 仓库初始化和提交
- [ ] 初始化 home 目录 Git 仓库 — `cd ~ && git init`（不推荐，home 目录太大）
- [x] 提交脚本修改 — ✅ 已完成 (2026-04-16) launcher/auto-train-deepseek.sh 已提交
- [x] 初始化 Letta 配置仓库 — ✅ 已完成 (2026-04-15) git init + commit
- [x] 初始化 LiteLLM 配置仓库 — ✅ 已完成 (2026-04-15) git init + commit

### 服务清理（优先级中）
- [x] 禁用未使用服务 — ✅ 已确认 (2026-04-15) ocr-indexer/browser-cookie-sync 均 not-found，无需操作
- [ ] 解决 Paperclip 合并冲突 — 7 个文件需要手动合并
- [ ] 配置 DeepSeek 训练环境 — 安装 PyTorch 或配置 Docker 容器

### 系统更新
- [ ] **NixOS nixpkgs 更新** — `nix flake update nixpkgs --flake /etc/nixos` + rebuild（当前锁定 2026-04-09）
- [ ] **根分区扩容** — GParted 从 LiveCD 操作，p7(8.9G) 或 p1(21.8G) 释放空间给 p9(90G)

### 长期优化
- [ ] HyperChat 部署评估 — 确认是否需要部署
- [ ] 系统健康监控优化 — 调整 system-health-monitor 检查项，避免 HyperChat 导致失败
- [x] **Paperclip → OpenCode subagent 迁移** — ✅ 完成 (2026-04-15)，心跳系统已上线
- [>] **跟踪 OpenCode 前沿** — PR #7756（subagent 间委托）+ #12711（Agent Teams），逐步实现 AGI 级自主能力
- [ ] **Paperclip 空壳 agent 归档** — 停止 6 个空壳 agent 心跳，保留 business-data 只读引用

- [ ] [ORCH→CC] [2026-04-17 13:41] 设计移动端状态卡片的信息架构与交互原型，明确核心指标（状态、负载、错误数）的展示层级与快捷操作（如重启）流程。
- [ ] [ORCH→CC] [2026-04-17 13:41] 定义移动端数据接口需求，确保数据轻量、实时，并制定分级告警与聚合视图的展示规则。
- [ ] [ORCH→CC] [2026-04-17 13:41] 负责移动端视图的前端实现或与前端开发团队的对接，确保UI/UX符合移动监管场景。
