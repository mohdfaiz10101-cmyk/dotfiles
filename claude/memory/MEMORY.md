# 核心档案

## 系统信息
- OS: NixOS 26.05 (Yarara)
- Kernel: 6.18.12
- Desktop: KDE Plasma (Wayland)
- GPU: NVIDIA RTX 3060 Ti (GA104)
- CPU: 12 核
- RAM: 24GB
- 用户: charlie

## 设备清单
- **NixOS 主机**（日常主力）— RTX 3060 Ti / 12核 / 24GB RAM / KDE Plasma Wayland
- **Android 手机** — Termux 可用，Tailscale 组网，ClashForAndroid 代理
- **Android 平板** — Obsidian 同步（待配置），SSH 连接 NixOS 主机
- **VR 头显**（Meta Quest）— 串流方案待定
- **Windows 设备** — 双系统/远程联动（SSH + Tailscale）| 用户: G / 密码: 1 | 当前IP: 192.168.2.36（PDCN-客厅5G网段）
- 网络工具：Tailscale（组网）、Syncthing（数据同步）、mihomo（代理）

## AI 工具链全景（2026-04-06 更新，三套系统并存，零冲突）

### 系统 A — Claude Code 智能路由（实时交互）

**入口**：`cc`（= `claude --model sonnet --plugin-dir ~/claude-router-plugin`）
**场景**：即时编码、调试、探索、配置修改

```
用户 prompt → classify-prompt.py（$0）
  ↓
┌─ standard(60-70%) → Sonnet 直接处理（$3/M）
├─ fast(20%)        → Task(model:"haiku")（$0.01/M）
├─ deep(10%)        → Task(model:"opus")（$15/M）
├─ deepseek         → curl LiteLLM silicon/deepseek-v3.2（$0.27/M）
└─ glm              → Bash: glm "<prompt>"（免费）
```

**别名**：`cc`=智能路由 / `cco`=直接Opus / `cg`=GLM
**关键文件**：`~/CLAUDE.md` / `~/claude-router-plugin/` / `~/.local/bin/claude-with-router`

### 系统 B — Aider + LiteLLM（Git-aware 代码编辑）

**入口**：Hub → `/agent/aider/` 或 `aider` CLI
**场景**：批量代码重构、多文件编辑、Git 自动提交
**模型调用**：Aider → LiteLLM :4000 → 43 个模型端点

```
Aider CLI → http://localhost:4000/v1 (LiteLLM)
  ↓ 主模型: glm-smart（自动路由 GLM-5/GLM-4.7/Groq-70B）
  ↓ 编辑器: glm-4-flash（免费）
  ↓ 降级链: glm-4-flash → glm-4 → groq-llama-70b → 本地 qwen3-8b
  ↓ 编程降级: glm-4 → deepseek-v3.2 → mistral-codestral → local/deepseek-r1-14b
```

**配置**：`~/.aider.conf.yml` / LiteLLM: `/mnt/ai/ai-cluster/litellm/config.yaml`
**预算上限**：$10/月（LiteLLM 全局）

### 系统 C — Paperclip（异步 Agent 调度）

**入口**：Hub → `http://localhost:3100` Web UI
**场景**：团队协作、项目管理、Issue 分配、营销自动化

```
Issue 创建 → Dispatcher 关键词匹配 → Agent 分配
  ↓
┌─ 快速迭代/小修复      → GLM Coder（免费）
├─ 算法/性能优化         → DeepSeek Coder（$0.27/M）
├─ 大型重构/多文件分析   → GLM Long Context（1M 上下文）
├─ 架构设计/代码审查     → Sonnet Engineer
├─ 关键功能开发          → Sonnet Coder
├─ 审核/最终决策         → Opus Reviewer
└─ 营销                  → GLM Marketing 团队
```

**代码**：`/mnt/ai/ai-cluster/paperclip/` / **数据**：`/mnt/pool/offload/paperclip/`
**Dispatcher**：`~/.local/bin/paperclip-dispatcher`（每15分钟扫描）

### 三套系统关系

```
               ┌─ 系统 A: Claude Code (cc) ──→ Anthropic API 直连
用户 ──────────┤  系统 B: Aider             ──→ LiteLLM :4000 ──→ 43 模型
               └─ 系统 C: Paperclip         ──→ LiteLLM :4000 ──→ 43 模型
                                                      ↑
                                                 共享基础设施
                                           Redis 缓存 + 预算保护
```

**核心原则**：
- A 做**即时交互**（在终端中与 Claude 对话）
- B 做**批量代码修改**（Git-aware，diff 模式节省 token）
- C 做**异步项目管理**（Issue → Agent → Review → 报告）
- A 可调用 B/C：`用 aider 重构 X` 或 `在 paperclip 创建 issue`
- B 和 C 共享 LiteLLM，A 独立走 Anthropic API

## 服务端口清单（2026-04-06 更新）

| 服务 | 端口 | 状态 | 说明 |
|------|------|------|------|
| Charlie Hub (Caddy) | 9800 | running | 总控 UI + 反向代理 |
| Charlie Hub API | 9801 | running | FastAPI 后端 |
| ttyd-claude | 7690 | running | Claude Code 终端 |
| ttyd-gemini | 7691 | running | Gemini CLI 终端 |
| ttyd-opencode | 7692 | running | OpenCode 终端 |
| ttyd-aider | 7693 | running | Aider 终端 |
| HyperChat CRM | 9098 | running | WeChat + CRM |
| Paperclip | 3100 | running | 任务管理 |
| LiteLLM | 4000 | running | 模型路由代理 |
| Letta API | 8283 | running | 记忆系统 |
| Letta Proxy | 8284 | running | 代理 |
| Letta MCP | 8788 | running | MCP SSE 端点 |
| ChromaDB | 8000 | running | 向量数据库 |
| Ollama | 11434 | running | 本地模型 |
| LangChain Hub | 8899 | running | 知识检索 |
| Whisper | 8178 | running | 语音识别 |

## Letta 记忆体系（2026-04-06 更新）

**容器**：letta + letta-proxy + letta-db（Docker）
**Agents**：code-assistant / nixos-sysadmin
**MCP 工具**：letta_recall / letta_search / letta_store / letta_update_core / letta_ask / letta_agents
**Systemd**：letta-mcp.service + 5 个 timers（health-check/guard/monitor/sync/distill）
**炼化**：letta-distill.timer 每日 03:00 → archival memory → md 文件双向同步

## 架构决策
- Chronos-Zenith 三模块架构（用户空间，不碰 NixOS 配置）
  - Sensory（环境音）：`~/launcher/chronos-sensory.py` → 常驻 service，CPU/GPU 负载驱动音频 profile 切换
  - Subconscious（梦境分析）：`~/launcher/chronos-subconscious.py` → oneshot+timer，空闲时 Ollama 跨文件分析
  - Bio-feedback（屏幕保护）：`~/launcher/chronos-biofeedback.py` → 常驻 service，KDE 亮度/对比度分级调节
  - 模块间通过 `/tmp/chronos/*.json` 通信
  - numpy 通过 `nix profile install` 安装，service 中 PYTHONPATH 指向 nix store

## AI Cluster 架构
- HyperChat: `http://localhost:9098` — CRM + WeChat 浏览器 + Hermetic Ledger
  - Hermetic Ledger 模块：CustomerHeartbeat 引擎 + 页面生成器 + Marketing Recommendations
  - API 端点：`/api/ledger/heartbeat/*`, `/api/ledger/page/*`, `/api/ledger/marketing/*`
  - 前端仪表盘：`/ledger` → `web/ledger.html`
  - 页面生成模块：`ledger_pages.py`（wechat_bubble / newsletter / card 三模板）
  - 数据源：`wechat_clean.db`（SQLite WAL），CRM `crm.db`
  - LiteLLM 情绪分析：`http://localhost:4000` → `local/qwen3-8b`
- WeChat Archive: `generate_static.py --ledger` 可导出 ledger 页面至 Vercel 静态站点
- Paperclip skill: `skills/hermetic-ledger/SKILL.md` — Agent 交互协议

## 偏好
- **终端**：Konsole（KDE 默认），ttyd 多终端（Claude/Gemini/OpenCode/Aider 各一个端口）
- **编辑器**：VS Code + Cline 扩展（需 `--extensions-dir` 启动），Aider（Git-aware 批量编辑）
- **浏览器**：Floorp（日常）+ Chrome（Playwright 自动化）
- **Shell**：Zsh，多行指令封装
- **主题**：Catppuccin Mocha 暗色（Chronos/HyperChat 统一风格）
- **代理**：mihomo 透明代理，KDE 系统代理 kwriteconfig6 配置
- **通知**：Telegram + 终端输出（不用桌面通知）
- **语言**：中文为第一语言，所有输出必须中文
- **成本控制**：LiteLLM 预算上限 $10/月，Claude Code Sonnet 默认 + Hook 路由降级

### 2026-04-06：Paperclip Agent 架构升级

**新增**：
- GLM Long Context agent (119d681f-2b6c-446e-822e-2283e25a8f4e)
  - 模型：cloud/glm-4-long (1M 上下文)
  - 职责：大型代码库重构、多文件依赖分析
  - 角色：Engineer / Refactor Specialist

**更新**：
- DeepSeek Coder (4dc77eed-49d4-457b-b588-c3c717e67d15)
  - 从 deepseek/deepseek-chat → silicon/deepseek-v3.2 (SiliconFlow)
  - 通过 LiteLLM 统一网关 (localhost:4000)
  - 成本降低 50%，164K 上下文

**配置方式**：
- 直接操作嵌入式 PostgreSQL (端口 54329)
- API 和 UI 功能有限，无法编辑 aider_worker 详细配置
- 修改后需重启服务生效

## Skill→Agent 智能路由映射（2026-04-16）

### 规则：派发任务时按领域自动匹配 skills

**nixos-sysadmin**（系统运维）：
`nixos-safety-check` `nixos-ntfs-chrome-fix` `system-health-check` `proxy-diagnose` `security-audit` `docker-cleanup` `docker-network-troubleshooting` `browseros-setup` `browser-cookie-sync` `timer-schedule-manager` `taskboard` `age-key-backup` `merge-sub`

**code-assistant**（代码开发）：
`api-design-principles` `architecture-patterns` `async-python-patterns` `code-review-excellence` `e2e-testing-patterns` `javascript-testing-patterns` `python-testing-patterns` `typescript-advanced-types` `python-packaging` `temporal-python-testing` `microservices-patterns` `git-advanced-workflows` `github-actions-templates` `helm-chart-scaffolding` `k8s-manifest-generator` `gitops-workflow` `deployment-pipeline-design` `terraform-module-library` `multi-cloud-architecture` `secrets-management` `tool-calling-patterns` `skill-create`

**PM/编排层**（主 agent 自用）：
`mpm*` `pm-*` `paperclip*` `memory-maintenance` `para-memory-files` `proactive-maintenance-planner` `claude-rules-audit` `agent-learning-framework` `discord-bot-diagnostics` `inquiry-automation` `digital-marketing`

**plain-speech**（语言翻译）：无特定 skill 需求，纯 LLM 对话

### Letta Agents（2026-04-16）
- `agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea` → code-assistant
- `agent-8651643c-e753-47ed-9759-bd955c6ac240` → nixos-sysadmin
- `agent-4cc72483-c830-4d2f-a624-86e56f11276a` → plain-speech

### 2026-04-09 Letta Distill
- 详细记录了基于NixOS的系统架构设计，涵盖远程操控方案、数据同步策略、跨桌面环境兼容性配置及触控优化方案等核心架构决策。
