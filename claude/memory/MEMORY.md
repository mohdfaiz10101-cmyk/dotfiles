# 核心档案

## 全局索引
- [SYSTEM-INDEX.md](SYSTEM-INDEX.md) — **AI 冷启动必读**：端口/服务/依赖/数据流/故障定位
- [rules-secondary.md](rules-secondary.md) — **L2/L3 规则**：会话启动/任务执行/参考规则（CLAUDE.md 只保留 L1 核心）

## 反馈规则
- [必须提供访问入口](feedback_entry_point.md) — 部署服务后 MUST 给出 URL 和启动命令
- [架构连续性](feedback_architecture_continuity.md) — 方案必须基于已有基础设施叠加
- [手机操作自动执行](feedback_phone_operations.md) — 手机操作 MUST 用 ADB/Chrome CDP 直接执行，禁止让用户手动操作手机
- [压缩输出格式](compaction-output-format.md) — opencode/诊断输出遵循 R1-R8 规则，禁用过渡句
- [AI工具决策必须联网搜最新](feedback_ai_tools_search_first.md) — OpenCode/LiteLLM/MCP等方案前MUST WebSearch验证当前版本行为
- [公网入口必须用 DuckDNS](feedback_public_access.md) — 公网地址 MUST 用 `charlie1990.duckdns.org`，不用 Tailscale Funnel
- [Waybar 管理](feedback_waybar-management.md) — 只用 systemctl --user 管理，禁止手动启动
- [Hyprland配置错误诊断](feedback_hyprland_configerrors.md) — 报错先 `hyprctl configerrors`；windowrule 0.54+ 块语法
- [OpenCode Token 消耗优化](opencode-cost-optimization.md) — L1+L2 已完成（MCP 裁剪、模型降级、快捷指令）
- [OpenCode 架构审计](opencode-architecture-audit.md) — 诊断不合理配置，L3 优化方案已执行
- **L3 完成**：自动降级链 + 成本监控 + 权限加固（成本从 ¥240/天 → ¥18/天，降幅 92.5%）

## 系统信息
- OS: NixOS 26.05 (Yarara) | Kernel: 6.18.12 | KDE Plasma (Wayland)
- GPU: RTX 3060 Ti | CPU: 12核 | RAM: 24GB | 用户: charlie

## 设备清单
- **NixOS 主机** — 日常主力，RTX 3060 Ti / KDE Plasma Wayland
- **Android 手机** — OnePlus Ace 5 Pro (PKR110) Android 16，**已 Root (Magisk)**，**ADB WiFi 已连接** (port 5555)，Termux + Tailscale
- **Android 平板** — 小米平板5 (24117RK2CC)，Obsidian 同步，SSH 连接主机，**已 Root (Magisk)**，ADB WiFi Tailscale IP: 100.104.211.70:5555
- **VR 头显** — Meta Quest，串流待定
- **Windows** — SSH 密码 `1` | 192.168.2.36 已失效 | 连接方式: `ssh winpc`(FRP:2222) > `ssh winpc-ts`(Tailscale:100.91.93.99) > `ssh winpc-wifi`(192.168.123.100 静态)
- 网络：Tailscale + Syncthing + mihomo
- **代理订阅源**：
  - 良心云（主）：`https://liangxin.xyz/api/v1/liangxin?OwO=648440cdc61b35fff7e4176ba7dac827`
  - 道长（备）：`https://skr.daozhangnb.dpdns.org/clash`
  - TrojanFlare（备）：`https://s1.trojanflare.one/clashx/01737539-508d-4504-aa37-f7643b037cf7`
  - mihomo API：`localhost:9091`（9090被Cockpit占用）
  - **手机SOCKS5隧道**（Cloudflare封禁绕过）：`ssh -D 1080 phone` → systemd user service 持久化
  - claude.com/anthropic.com 路由到 🌟 付费专线 → 📱 手机移动（SOCKS5）

## AI 架构（详见独立文件）
- [AI 双系统详情](ai-cluster-architecture.md) — CC/Aider + 端口 + Letta
- [OP Agent 巡查体系](op-agent-system.md) — Skill 路由 + Letta Agents + Timer 调度
- [AI 工具对比](ai-tools.md) — OpenCode/Aider/Cline 等
- [OP 升级 1.15.3 + 记忆修复](opencode-upgrade-1.15.3.md) — 2026-05-17 全面升级记录

## OpenCode Agents（别名速查）
- **sisy / sisyphus** = opencode `--agent sisyphus`，OP 运维执行 Agent，配置：`~/.config/opencode/agents/sisyphus.md`，模型：glm-5.1
- **atlas** = 大师编排器，多 agent 并行
- **prometheus** = 规划器，Plan Mode
- **hephaestus** = 深度执行器，长上下文代码生成
- ttyd-opencode 端口 7692 → 启动命令：`opencode --agent sisyphus`（tmux session "sisyphus"）

## 架构决策
- [Chronos-Zenith](codebase-map.md) — Sensory/Subconscious/Bio-feedback 三模块
- [HyperChat + Hermetic Ledger](ai-cluster-architecture.md) — CRM + 微信 + 营销

## 磁盘分配规则（DISK_ALLOCATION — 死规则）
| 分区 | 类型 | 大小 | 已用 | 用途 | 文件系统限制 |
|------|------|------|------|------|-------------|
| `/` 根分区 | NVMe | 89G | 86% | **仅系统级**：NixOS包、kernel、boot | ❌禁止装应用数据 |
| `/mnt/ai` | HDD ext4 | 920G | 31% | **AI应用+服务数据**：Docker、apps、documents | ✅ ext4 可全操作 |
| `/mnt/data` | HDD NTFS | 932G | 80% | **个人数据**：视频、音乐、下载、微信备份 | ❌NTFS禁npm/bun/docker |
| `/mnt/pool` | mergerfs | 6.4T | 30% | **冷存储+归档**：游戏、ISO、backup、archive | ❌NTFS禁npm/bun/docker |
| `/mnt/win_c` | NVMe NTFS | 233G | 75% | **只读挂载** Windows C盘 | ❌只读，禁止写入 |

### 软件安装分配决策树
```
需要安装软件？
├─ 系统包（DE/浏览器/CLI工具）→ NixOS packages.nix → 根分区
├─ Docker容器/AI服务 → /mnt/ai/apps/{name}/ → ext4
├─ Python venv/Node项目 → /mnt/ai/apps/{name}-venv/ → ext4
├─ 用户配置文件 → ~/dotfiles/ → 根分区（小文件无压力）
├─ 大文件下载/媒体 → /mnt/data/downloads/ → NTFS
└─ 归档/备份 → /mnt/pool/backup/ → mergerfs
```

### 双机软件分工
| 类别 | NixOS (主力机) | Windows (存档机) |
|------|---------------|----------------|
| AI/ML 服务 | ✅ Docker | ❌ |
| 微信 | Wine (bridge) | ✅ 原生微信 |
| Office/文档 | OnlyOffice | ✅ WPS/Office |
| 文件存档 | /mnt/ai/documents/ | C:\Users\G\sync\documents\ |
| 数据库 | ✅ PostgreSQL/SQLite | ❌ |
| 开发环境 | ✅ 全栈 | Python脚本 |

### 安装前强制检查（与 PRE_MIGRATE_CHECK 合并）
1. `df -hT <目标路径>` → 可用空间 > 预估×1.5 且 非 NTFS（Docker/npm/bun）
2. 根分区 >85% → 禁止装新系统包，用 nix-collect-garbage 清理

## 偏好
- 终端: Konsole + ttyd(7690-7694) | 编辑器: VS Code + Aider | 浏览器: Floorp + Chrome
- 主题: Catppuccin Mocha | 代理: mihomo | 通知: Telegram | 语言: 中文
- 成本: LiteLLM $10/月上限，Claude Code Sonnet 默认 + Hook 路由
- **Agent创建**: 必须先搜索互联网已有开源 agent/skill，推荐参考后再决策，不要闭门造车
- **工作流设计**: 先调研业界已有方案（GitHub trend、LangChain Hub、n8n community），再讨论
- **mihomo GLOBAL**: MUST 保持 `⚡ 自动选择`（URLTest），禁止设为 DIRECT（直连访问 anthropic 会 403）

## 进行中的项目
- [微信数据合并](wechat-merge-plan.md) — 双端 DB 合并，Windows 密钥待提取
- [BalanceTrigger App](app-dev-journal.md) — App 开发经验日志
- [手机远程方案](setup-plan.md) — SSH + tmux + Tailscale（已确认最佳方案）

## 桌面资产（Desktop Assets）
- **APK**: `~/Desktop/charlie-hub.apk` — Charlie Hub Android 客户端（3.8MB），通过 ADB 推送到手机/平板安装
- **手机备份**: `~/Desktop/手机备份/PKR110-20260419/` — OnePlus Ace 5 Pro 完整备份
- **商业文件**: `~/Desktop/商业文件/` — 外贸合同、发票 PDF
- **开发工具**: `~/Desktop/开发工具/` — 桌面快捷方式(.desktop)、ADB 脚本、平板安装脚本
- **巡检报告**: `~/Desktop/巡检报告/` — 系统巡检 JSONL feed、competitive 报告
- **微信配置**: `~/Desktop/微信配置/` — 微信相关配置文件
- **系统文档**: `~/Desktop/系统文档/` — NixOS 配置备份
- **数据库**: `~/Desktop/crm.db` — CRM 数据库副本

## 桌面目录结构速查
```
~/Desktop/
├── charlie-hub.apk          # Hub Android APK
├── crm.db                   # CRM 数据库
├── init_boot.img            # OnePlus boot 镜像
├── 安卓开发/                # Android 开发资源
├── 手机备份/PKR110-20260419/ # OnePlus 备份
├── 开发工具/                # .desktop 快捷方式 + ADB 脚本
├── 商业文件/                # 外贸合同发票
├── 巡检报告/                # 系统报告 JSONL
├── 微信配置/                # 微信配置
├── 系统文档/                # 系统配置文档
├── 网络代理/                # 代理相关
├── agent-reports/           # AI Agent 报告
├── research/                # 技术调研
├── glm-tasks/               # GLM 任务
└── GLM-Output/              # GLM 输出
```

## OpenCode 审计
- [配置审计 2026-05-17](opencode-audit-2026-05-17.md) — P0/P1/P2 问题 + 社区 Bug 匹配 + config-auditor 方案

## 知识库索引
- [踩坑日志](lessons-learned.md) — 错误修复经验（append-only）
- [踩坑归档](lessons-learned-archive.md) — 30天以上旧条目
- [NixOS 配置笔记](nixos-config.md) — 系统配置变更记录
- [问题速查表](troubleshooting.md) — 症状→原因→修复
- [跨会话待办](pending-tasks.md) — 未完成任务
- [方案灵感](ideas-roadmap.md) — 规划项汇总
- [代码库地图](codebase-map.md) — 探索缓存
- [操作手册](command-reference.md) — Hub/Discord/API/systemd
- [LiteLLM 部署](litellm-deployment.md) — 配置和诊断
- [OP 任务](op-tasks.md) — CC↔OP 异步协作
- [北极星文档](north-star.md) — Charlie 的 AI OS 终极目标，每次会话必读，所有建议必须对齐

## 数据恢复系统
- [智能数据恢复部署](data-recovery-deployment.md) — 三层防护（启动检测+运行监控+定时备份）

## NixOS FRP 隧道（永久）
- frps: `192.168.123.1:7000`, token=`12345`
- `192.168.123.209:2223` → NixOS:22 (SSH) — `ssh -p 2223 charlie@192.168.123.209`
- `192.168.123.209:24801` → NixOS:24801 (KVM ydotool-bridge)
- `192.168.123.209:17699` → NixOS:7699 (Caddy AI Launcher)
- systemd 用户服务: `frpc.service` + `ydotool-bridge.service`（enabled）
- Tailscale SSH 因 OpenSSH 版本不兼容，走 frpc 隧道绕过
- 2026-05-10 验证通过

## CLI 偏好
- `session_list` 默认 `limit=500`（之前是50），alias: `ses` / `ses-new` / `ses-old`

## FRP 状态 (2026-05-21 更新)
- frps: NixOS 本机 (192.168.123.209) :7000, dashboard :7500, token=frp-token-charlie-2026
- NixOS frpc: 11个代理(ssh:2223/tty:17699/mosh×3/opencode:19890/hub:19891/letta:19892/openclaw:19893/sisy:18090/crewai:18091/agi:18300/openagents:18093/adb:15555)
- Windows frpc: 2个代理(ssh:2222/rdp:3389), 路径 C:\Toolsrpc\, 开机自启 schtasks FRPClient
- Win IP: **静态 192.168.123.100** (WLAN, DHCP已关闭), 连 frps 用 192.168.123.209:7000
- **固定公网地址**: https://nixos-1.tail60cff7.ts.net (Tailscale Funnel → :7699 Launcher)
- NixOS Tailscale IP: 100.119.174.25
- 关键修复: frpc.service 必须清除 http_proxy(防 mihomo 拦截 FRP 协议)
- 注意: openagents 用18093(18092被macg_mcp.py占用)
