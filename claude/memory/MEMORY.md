# 核心档案

## 反馈规则
- [必须提供访问入口](feedback_entry_point.md) — 部署服务后 MUST 给出 URL 和启动命令
- [架构连续性](feedback_architecture_continuity.md) — 方案必须基于已有基础设施叠加

## 系统信息
- OS: NixOS 26.05 (Yarara) | Kernel: 6.18.12 | KDE Plasma (Wayland)
- GPU: RTX 3060 Ti | CPU: 12核 | RAM: 24GB | 用户: charlie

## 设备清单
- **NixOS 主机** — 日常主力，RTX 3060 Ti / KDE Plasma Wayland
- **Android 手机** — Termux + Tailscale + Clash
- **Android 平板** — Obsidian 同步，SSH 连接主机
- **VR 头显** — Meta Quest，串流待定
- **Windows** — SSH `G@192.168.2.36` 密码 `1` | Tailscale 组网
- 网络：Tailscale + Syncthing + mihomo

## AI 架构（详见独立文件）
- [AI 三套系统详情](ai-cluster-architecture.md) — CC/Aider/Paperclip + 端口 + Letta
- [OP Agent 巡查体系](op-agent-system.md) — Skill 路由 + Letta Agents + Timer 调度
- [AI 工具对比](ai-tools.md) — OpenCode/Aider/Cline 等

## 架构决策
- [Chronos-Zenith](codebase-map.md) — Sensory/Subconscious/Bio-feedback 三模块
- [HyperChat + Hermetic Ledger](ai-cluster-architecture.md) — CRM + 微信 + 营销

## 偏好
- 终端: Konsole + ttyd(7690-7693) | 编辑器: VS Code + Aider | 浏览器: Floorp + Chrome
- 主题: Catppuccin Mocha | 代理: mihomo | 通知: Telegram | 语言: 中文
- 成本: LiteLLM $10/月上限，Claude Code Sonnet 默认 + Hook 路由

## 进行中的项目
- [微信数据合并](wechat-merge-plan.md) — 双端 DB 合并，Windows 密钥待提取
- [BalanceTrigger App](app-dev-journal.md) — App 开发经验日志
- [手机远程方案](setup-plan.md) — SSH + tmux + Tailscale（已确认最佳方案）

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
