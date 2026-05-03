# 系统全局索引（AI 冷启动必读）
> 生成时间: 2026-05-03 | 用途: AI 会话启动时读此文件即可掌握全局架构

## 一、数据流总览

```
[感知层]
  screenshot-watcher → GLM-4V 意图 → ~/Desktop/latest-intent.json
  adb sensors → ~/agi/sensor-bridge.py
  browser CDP → ~/agi/browser_sense.py
  wechat-bridge(Windows:192.168.2.36) → MCP wechat tools
       ↓
[AGI Brain] ~/agi/brain.py (systemd: agi-brain)
  sense() → think.py → LLM(LiteLLM) → act(op-tasks.md / telegram / discord)
  每60秒循环 | 主动推送每30分钟 | Letta archival 记录(常超时)
       ↓
[执行层]
  CC (Claude Code CLI) — 编码/规划/架构，受 CLAUDE.md 约束
  OP (opencode --agent sisyphus) — 运维执行，读 op-tasks.md
  op-push — 监听 op-tasks.md 变更 → 推送 Telegram 通知
       ↓
[通知层]
  Telegram: @charlie_1688_bot → chat_id 5036541266（走代理 7890）
  Discord: alerts 频道（走 webhook）
  Desktop: notify-send / KDE 通知
```

## 二、端口地图

| 端口 | 服务 | 进程/配置 | 说明 |
|------|------|-----------|------|
| 22 | SSH | systemd | 远程登录 |
| 3000 | AGI 控制台 | Next.js dev (frontend) | `/mnt/ai/apps/agi-control-plane/` |
| 3001 | Twenty CRM | Docker | 客户关系管理 |
| 4000 | LiteLLM 网关 | Docker litellm-litellm | AI 模型统一网关 |
| 4533 | Navidrome | navidrome.service | 音乐流媒体 |
| 5037 | ADB | adb server | Android 调试 |
| 5244 | AList | Docker alist | 网盘聚合 |
| 5678 | n8n | Docker n8n | 工作流自动化 |
| 6379 | Redis | Docker litellm-redis | LiteLLM 缓存 |
| 7681 | ttyd | ttyd-aider | Aider Web 终端 |
| 7690 | ttyd | ttyd-cct | CC Web 终端 |
| 7691 | ttyd | ttyd-claude | Claude Web 终端 |
| 7693 | ttyd | ttyd-opencode | OP Web 终端 |
| 7694 | ttyd | ttyd-macg | MACG Web 终端 |
| 7890 | mihomo | mihomo.service | HTTP 代理（所有出站） |
| 7891 | mihomo | mihomo.service | SOCKS5 代理 |
| 8000 | ChromaDB | Docker letta-chromadb | 向量数据库(Letta) |
| 8001 | MuseTalk | Docker musetalk | 口型同步 |
| 8080 | OpenCode | opencode-web.service | OpenCode Web UI |
| 8283 | Letta API | Docker letta | 记忆/Agent 管理 |
| 8284 | Letta Admin | Docker letta | Letta 管理界面 |
| 8384 | Syncthing | — | 文件同步 |
| 8788 | — | — | 备用 |
| 8789 | — | — | 备用 |
| 9091 | mihomo API | mihomo.service | 代理管理 API |
| 9800 | Hub API | hub-api.service | `~/hub/hub-api.py` |
| 9880 | GPT-SoVITS | Docker gptsovits | 语音合成 |
| 9900 | AGI Gateway | agi-gateway.service | FastAPI 网关 |
| 9977 | — | python3 | OCR 服务 |
| 9980 | — | python3 | 内容服务 |

## 三、目录结构（关键文件索引）

### ~/agi/ — AGI Brain 核心
| 文件 | 职责 | 被谁调用 |
|------|------|---------|
| `brain.py` | Sense→Think→Act 主循环 | systemd agi-brain |
| `think.py` | LLM 分析 + MEMORY.md 上下文 | brain.py |
| `proactive.py` | 30分钟主动推送生成 | brain.py |
| `conversation.py` | 自然语言对话接口 | telegram_bot/discord_bot |
| `telegram_bot_enhanced.py` | Telegram Bot (polling) | systemd agi-telegram-bot |
| `discord_bot_enhanced.py` | Discord Bot | systemd agi-discord-bot |
| `op_push_service.py` | OP任务→Telegram推送 | systemd op-push |
| `wechat_agent.py` | 微信消息处理 | systemd wechat-agent |
| `macg.py` | MACG 多 Agent 编排 | systemd agent-orchestrator |
| `macg_api.py` | MACG HTTP API | macg.py |
| `cognitive_engine.py` | 认知能力量化 | systemd agi-cognitive-engine |
| `sensor-bridge.py` | 传感器数据桥接 | brain.py |
| `browser_sense.py` | 浏览器状态感知 | brain.py |
| `context_graph.py` | 上下文关系图 | brain.py |
| `audit_log.py` | 自动处理审计日志 | brain.py |
| `report_generator.py` | 每日报告生成 | daily_summary |
| `letta-sync.py` | Letta 记忆同步 | letta-sync timer |
| `self_improve.py` | 自我改进引擎 | agi-self-improve timer |

### ~/hub/ — Hub API
| 文件 | 职责 |
|------|------|
| `hub-api.py` | Hub REST API (9800) |
| `office-agent.py` | Office 自动化 Agent |

### ~/.local/bin/ — 运维脚本 (138个)
关键脚本分组：
- **代理**: `mihomo-guardian` `mihomo-watch` `proxy-403-monitor`
- **ADB**: `adb-autoconnect.sh` `adb-tablet-keepalive.sh`
- **AI配置**: `ai-config-guard.sh` `ai-rules-sync.sh` `baseline-update.sh`
- **恢复**: `boot-recovery.sh` `crash-recovery.sh`
- **NixOS**: `nixos-preflight-check.sh` `nixos-smoketest.sh`
- **OP**: `op-launch.sh` `op-auto-exec-hook.sh`
- **Letta**: `letta-health-check.sh` `letta-context-ops.sh`
- **CC**: `cc-autoagent-hook.sh` `cc-op-verifier.sh`

### /etc/nixos/ — 系统声明式配置
| 文件 | 职责 |
|------|------|
| `flake.nix` | Flake 入口 |
| `configuration.nix` | 主配置 |
| `hardware-configuration.nix` | 硬件 |
| `home/charlie.nix` | Home Manager |
| `modules/proxy.nix` | mihomo 代理 |
| `modules/docker-nat-fix.nix` | Docker NAT 修复 |
| `modules/networking.nix` | 网络/Tailscale |
| `modules/services/` | systemd 服务定义 |
| `modules/services/timers.nix` | 定时任务 |
| `modules/packages.nix` | 系统包 |
| `modules/ai.nix` | AI 相关配置 |
| `modules/storage.nix` | 磁盘挂载 |

### /mnt/ai/apps/ — 应用数据
| 目录 | 职责 |
|------|------|
| `agi-control-plane/` | 3000 控制台前端 (Next.js dev) |
| `hub-mobile/` | Hub Android App |
| `crm/` | CRM 数据 |
| `launcher/` | 桌面启动器 |
| `embed-server/` | Embedding 服务 |
| `musetalk/` | 口型同步 |
| `nginx/` | Nginx 配置 |
| `onlyoffice/` | OnlyOffice |

### ~/.config/opencode/agents/ — OpenCode Agent 定义 (20个)
| Agent | 模型 | 职责 |
|-------|------|------|
| `sisyphus.md` | GLM-5.1 | OP 运维执行 |
| `charlie-ego.md` | — | 决策镜像 |
| `finance.md` | — | 财务记账 |
| `discord-butler.md` | — | Discord 管理 |
| `service-nurse.md` | — | 服务巡检 |
| `proxy-guardian.md` | — | 代理守护 |
| `security-watchdog.md` | — | 安全监控 |
| `marketing-coordinator.md` | — | 营销协调 |
| `memory-curator.md` | — | 记忆管理 |

## 四、依赖关系图

```
mihomo (7890) ← 所有出站流量依赖
  ├── Telegram Bot API (通知)
  ├── LiteLLM → OpenAI/Anthropic/GLM/DeepSeek (AI 调用)
  ├── AGI Brain (think → LLM)
  └── op-push (任务通知)

LiteLLM (4000) ← 所有 AI 调用入口
  ├── AGI Brain think.py
  ├── conversation.py (对话)
  ├── cognitive_engine.py
  └── 外部 Agent 调用

Letta (8283) ← 长期记忆
  ├── brain.py archival 写入（常超时）
  ├── CC letta_recall/search/store
  └── letta-sync.py 定期同步

Docker ← 服务基础设施
  ├── LiteLLM + Redis
  ├── Letta + ChromaDB + PostgreSQL
  ├── Twenty CRM + PostgreSQL + Redis
  ├── n8n (工作流)
  ├── MuseTalk + GPT-SoVITS (语音)
  └── AList (网盘)
```

## 五、CC↔OP 协作协议

```
CC 发现运维任务 → 写入 op-tasks.md [OP] 标签
  → op-push 检测变更 → Telegram 通知
  → OP 读取 op-tasks.md → 执行 → 标记 [✓]
  → CC 下次回复检查 → 确认完成

CC 发现编码任务 → 直接执行（不经过 OP）
```

## 六、常见故障快速定位

| 症状 | 先检查 | 常见原因 |
|------|--------|---------|
| Telegram 不通知 | `curl --proxy 7890 api.telegram.org` | mihomo 节点挂了 |
| AI 调用失败 | `curl localhost:4000/health` | LiteLLM 挂/Key 过期 |
| 记忆丢失 | `curl localhost:8283/v1/agents` | Letta DB 超时 |
| 微信断连 | SSH G@192.168.2.36 检查 | Windows 端 bridge 挂了 |
| 代理不通 | `curl localhost:9091/proxies` | mihomo 节点选中坏节点 |
| ADB 断连 | `adb devices` | WiFi ADB 需重连 |
| 磁盘满 | `df -h / /mnt/ai` | Nix store / Docker 镜像 |

## 七、配置文件链路

```
CLAUDE.md (CC 行为规则)
  ↕ ai-rules-sync.sh
ai-shared-rules.md (三层规则源)
  ↕ ai-rules-sync.sh
AGENTS.md (OP/Agent 行为规则)

ai-config-guard.sh — 监控配置篡改
baseline-update.sh — 合法修改后更新基线
```

## 八、定时任务调度 (systemd timers)

通过 `systemctl --user list-timers` 查看活跃定时器。主要周期：
- **每60秒**: agi-brain 循环
- **每30分钟**: 主动推送
- **每6小时**: letta-health-check
- **每日**: docker-cleanup, daily-summary, nix-store-check
- **每周**: architecture-audit, security-audit
