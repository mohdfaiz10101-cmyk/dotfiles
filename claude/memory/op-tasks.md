# OP 待办任务（2026-04-18 清理归档）

## 待处理（未完成）

### OP→CC 流转
- [!] [OP→CC] heartbeat-task-check / service-nurse / discord-butler — systemd service 不存在，需从零创建 agent service 或从 Paperclip 配置中移除
- [!] [OP→CC] heartbeat-system-sentry — 超时被 SIGALRM 杀死，需增加 TimeoutStartSec 或修复脚本
- [!] [OP→CC] proxy-guardian — systemd service 不存在，同上

### AGI 前端重设计（REDESIGN v2）
> 规划文档：`~/Desktop/文档/agi-control-plane-redesign-plan.md`
> 项目路径：`/mnt/ai/apps/agi-control-plane/frontend/`

- [x] [完成 2026-04-18 23:00] — REDESIGN-P0-A：9文件创建+构建通过
- [x] [完成 2026-04-18 23:00] — REDESIGN-P0-B：Sidebar完成
- [x] [完成 2026-04-18 23:00] — REDESIGN-P0-C：TopBar+ServiceBadge完成
- [x] [完成 2026-04-18 23:00] — REDESIGN-P0-D：4个hooks完成
- [x] [完成 2026-04-18 23:00] — REDESIGN-P1-A：ChatPanel完成
- [ ] [OP] REDESIGN-P1-B：CopilotKit Actions 注册（6个action）
- [ ] [OP] REDESIGN-P2-A：KanbanDashboard — recharts图表 + MetricCard
- [ ] [OP] REDESIGN-P2-B：LettaMemoryTree — 3个agent记忆可视化
- [ ] [OP] REDESIGN-P3-A：WechatPanel增强版（头像/搜索/回复/轮询）
- [ ] [OP] REDESIGN-P3-B：page.tsx 主布局重写（<100行）
- [ ] [OP] REDESIGN-P4：生产构建 + 部署 + Git备份

### Git 备份
- [ ] [CC→OP] 全量 git 备份（memory + agi-control-plane + hub + nixos）

## 已完成（2026-04-18）

- [x] [GLM-5.1] Letta(8283)+Hub(9801) 运行正常
- [x] [GLM-5.1] hub-api 联系人API修复：3262联系人+3189头像+79消息记录，控制字符已清理
- [x] CopilotKit T01-T03 全部完成
- [x] charlie-hub hub-api.py 列名+控制字符+SafeJSONResponse 修复
- [x] LiteLLM GLM 视觉模型添加
- [x] OP agent 失败排查：heartbeat-task-check/service-nurse/discord-butler 根因=systemd service 不存在
- [x] 40+ 条重复"重启服务"任务已清理
- [x] APK构建任务：需sudo权限，转CC

## 执行规则
- 完成后 `[ ]` → `[x]` + 时间戳 | 失败 2 次 → `[!]` + 原因流转 CC
- 优先执行 REDESIGN-P0 → P1 → P2 → P3 → P4
- [ ] [AGI→OP] [2026-04-18 21:55] [high] 重启 Letta 服务以恢复 Agent 记忆与上下文管理
- [ ] [AGI→OP] [2026-04-18 21:55] [high] 重启 Charlie-Hub 服务以恢复通信中枢
- [ ] [OP→CC] [2026-04-18 22:00] [high] OP agent discord-butler 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [ ] [OP→CC] [2026-04-18 22:00] [high] OP agent heartbeat-task-check 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [ ] [OP→CC] [2026-04-18 22:00] [high] OP agent service-nurse 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [ ] [AGI→OP] [2026-04-18 22:20] [high] 启动 letta 服务 (systemctl start letta)
- [ ] [OP→CC] [2026-04-18 22:20] [high] OP agent proxy-guardian 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [ ] [AGI→OP] [2026-04-18 22:21] [high] 重启 Letta 服务以恢复代理记忆和上下文功能
- [ ] [AGI→OP] [2026-04-18 22:30] [high] 启动 letta 服务以恢复 AI Agent 能力
- [ ] [AGI→OP] [2026-04-18 22:30] [high] 启动 charlie-hub 服务以恢复指令接收能力
- [ ] [AGI→OP] [2026-04-18 22:31] [high] 检查并重启 letta 服务
- [ ] [AGI→OP] [2026-04-18 22:47] [high] 启动 Letta 和 Charlie-Hub 服务，恢复 OP 代理协调及消息通知能力
- [ ] [AGI→OP] [2026-04-18 22:50] [high] 立即重启 letta 服务并检查日志确认失败原因
- [ ] [AGI→OP] [2026-04-18 22:50] [high] 立即重启 charlie-hub 服务
- [ ] [AGI→OP] [2026-04-18 22:50] [medium] 检查 systemd 服务配置，确认是否存在自动重启失败或依赖问题
- [ ] [AGI→OP] [2026-04-18 22:52] [high] 诊断并重启 Letta 服务，确保 Agent 系统在线
- [ ] [AGI→OP] [2026-04-18 22:52] [high] 诊断并重启 Charlie-Hub 服务，恢复通信能力
- [ ] [AGI→OP] [2026-04-18 23:13] [high] 重启 letta 和 charlie-hub 服务以恢复通信与代理能力
- [ ] [AGI→OP] [2026-04-18 23:13] [medium] 检查 letta 与 charlie-hub 的日志（journalctl）确认停止原因
