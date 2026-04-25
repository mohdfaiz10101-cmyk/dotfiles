# 核心档案

## 反馈规则
- [必须提供访问入口](feedback_entry_point.md) — 部署服务后 MUST 给出 URL 和启动命令
- [架构连续性](feedback_architecture_continuity.md) — 方案必须基于已有基础设施叠加

## 系统信息
- OS: NixOS 26.05 (Yarara) | Kernel: 6.18.12 | KDE Plasma (Wayland)
- GPU: RTX 3060 Ti | CPU: 12核 | RAM: 24GB | 用户: charlie

## 设备清单
- **NixOS 主机** — 日常主力，RTX 3060 Ti / KDE Plasma Wayland
- **Android 手机** — OnePlus Ace 5 Pro (PKR110) Android 16，**已 Root (Magisk)**，**ADB WiFi 已连接** (port 5555)，Termux + Tailscale
- **Android 平板** — 小米平板5 (24117RK2CC)，Obsidian 同步，SSH 连接主机，**已 Root (Magisk)**，ADB WiFi Tailscale IP: 100.104.211.70:5555
- **VR 头显** — Meta Quest，串流待定
- **Windows** — SSH `G@192.168.2.36` 密码 `1` | Tailscale 组网
- 网络：Tailscale + Syncthing + mihomo

## AI 架构（详见独立文件）
- [AI 三套系统详情](ai-cluster-architecture.md) — CC/Aider/Paperclip + 端口 + Letta
- [OP Agent 巡查体系](op-agent-system.md) — Skill 路由 + Letta Agents + Timer 调度
- [AI 工具对比](ai-tools.md) — OpenCode/Aider/Cline 等

## OpenCode Agents（别名速查）
- **sisy / sisyphus** = opencode `--agent sisyphus`，OP 运维执行 Agent，配置：`~/.config/opencode/agents/sisyphus.md`，模型：glm-5.1
- **atlas** = 大师编排器，多 agent 并行
- **prometheus** = 规划器，Plan Mode
- **hephaestus** = 深度执行器，长上下文代码生成
- ttyd-opencode 端口 7692 → 启动命令：`opencode --agent sisyphus`（tmux session "sisyphus"）

## 架构决策
- [Chronos-Zenith](codebase-map.md) — Sensory/Subconscious/Bio-feedback 三模块
- [HyperChat + Hermetic Ledger](ai-cluster-architecture.md) — CRM + 微信 + 营销

## 偏好
- 终端: Konsole + ttyd(7690-7694) | 编辑器: VS Code + Aider | 浏览器: Floorp + Chrome
- 主题: Catppuccin Mocha | 代理: mihomo | 通知: Telegram | 语言: 中文
- 成本: LiteLLM $10/月上限，Claude Code Sonnet 默认 + Hook 路由

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
