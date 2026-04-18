# OP 待办任务

## 待处理

### P1-C 混合 AI SDK（CC 已完成 2026-04-19）
- [x] P1-C1: `bun add ai @ai-sdk/openai` 安装 Vercel AI SDK
- [x] P1-C2: 创建 `app/api/chat/route.ts` 流式路由（OP agent 重写为原生 SSE 代理）
- [x] P1-C3: ChatPanel 升级为 `useChat` 流式输出（AI SDK v6）
- [x] P1-C4: 各面板加 `useCopilotReadable` 上下文感知

## 已完成（2026-04-19）

- [x] REDESIGN-P0-A：目录结构 + api.ts
- [x] REDESIGN-P0-B：Sidebar 组件
- [x] REDESIGN-P0-C：TopBar + ServiceBadge
- [x] REDESIGN-P0-D：4 hooks（useServices/useTasks/useWechat/useLetta）
- [x] REDESIGN-P1-A：ChatPanel
- [x] REDESIGN-P1-B：CopilotKit Actions（6个）+ TerminalPanel
- [x] REDESIGN-P2-A：KanbanDashboard + MetricCard（recharts）
- [x] REDESIGN-P2-B：LettaMemoryTree
- [x] REDESIGN-P3-A：WechatPanel 增强版（头像/搜索/回复/轮询）
- [x] REDESIGN-P3-B：page.tsx 重写（281行→51行）
- [x] REDESIGN-P4：生产构建通过 + dev server 验证
- [x] KANBAN-TAB：Sidebar + LauncherPanel + 构建验证
- [x] hub-api systemd 服务 + git backup
- [x] service-nurse 巡检 2026-04-19（诊断 + glm-proxy masked + 假阳性确认）

## 已完成（2026-04-18）

- [x] hub-api 联系人 API 修复：3262 联系人 + SafeJSONResponse
- [x] Letta(8283) + Hub(9801) 运行正常
- [x] CopilotKit T01-T07 完成
- [x] LiteLLM GLM 视觉模型添加
- [x] dotfiles git backup done

## 已清理（2026-04-19 过夜残留）

以下 AGI→OP/OP→CC 任务已确认服务在线或为假阳性，标记清理：
- [x] 重启 charlie-hub / letta / litellm（×11条重复，服务已在线）
- [x] OP→CC discord-butler / proxy-guardian / service-nurse 升级（假阳性：agent service 不存在）
- [x] 诊断 PID 高 CPU 占用（×2条，进程已过期）

## 执行规则
- 完成后 `[ ]` → `[x]` + 日期 | 失败 2 次 → `[!]` 流转 CC
- AGI Brain 生成的"重启服务"任务一律忽略（Letta/Hub 均已确认在线）

---

## CRM-AUTO — 营销/网站自动化 + CRM

**目标**：基于 hub-api + Letta + macg + 微信，搭建私域 CRM 和营销自动化体系。

### CRM-01 [OP] 搭建 CRM 服务骨架（端口 3001）
- [ ] [OP] 在 `/mnt/ai/apps/` 下新建 `crm/` 目录
- [ ] [OP] 初始化 Next.js 项目
- [ ] [OP] 验证：`http://localhost:3001` 可访问基础页面

### CRM-02 [OP] 客户档案存入 Letta
- [ ] [OP] 调用 Letta archival memory API 建立客户档案存储结构
- [ ] [OP] 验证写入成功，搜索可命中

### CRM-03 [OP] 微信消息 → CRM 自动归档
- [ ] [OP] 在 AGI Brain 或独立脚本中，监听 hub-api 微信消息
- [ ] [OP] 验证：发一条微信消息 → 能在 Letta 中搜索到归档记录

### CRM-04 [OP] macg 营销任务调度
- [ ] [OP] 在 `~/agi/macg.py` 中注册营销工具（schedule_followup / send_batch_message）
- [ ] [OP] 验证：调用工具后能通过 hub-api 发出微信消息

### CRM-05 [OP] CRM 看板页面（复用 9875 风格）
- [ ] [OP] 在 `/mnt/ai/apps/crm/` 创建静态 `crm.html`
- [ ] [OP] 用 Python http.server 或 nginx 在 9876 端口服务
- [ ] [OP] 在 3000 前端 Sidebar 加 `crm` tab（iframe localhost:9876/crm.html）

### CRM-06 [OP] 落地页/网站自动化（可选）
- [ ] [OP] 调研现有域名/落地页情况
- [ ] [OP] 若有落地页：接入表单提交 → 写入 Letta CRM

---

## UPGRADE-BATCH — 已有功能升级

> 升级原则：最小侵入，接入已有服务，不重建；验证：curl 测试 + 前端可见

### UPGRADE-01 [OP] Kanban Hub (9875) 接入实时数据
- [ ] `~/launcher/launcher-server.py` 添加 `GET /api/status`
- [ ] `~/launcher/kanban.html`：fetch `/api/status`，每30s刷新
- [ ] 验证：`http://localhost:9875/kanban.html` 状态栏有实时数字

### UPGRADE-02 [OP] AGI Brain 升级模型路由 + 写入 Letta
- [ ] `~/agi/brain.py`：决策→glm-5.1，执行→glm-5-turbo；关键事件写入 Letta archival
- [ ] 验证：Letta 可搜到 `AGI Brain` 标签记录

### UPGRADE-03 [OP] macg 新增工具
- [ ] `~/agi/macg.py` 追加 @tool：get_wechat_messages/search_letta_memory/get_op_pending_tasks/create_paperclip_task
- [ ] 重启 ttyd-macg.service
- [ ] 验证：`macg` CLI 输入"查微信最新消息"，能返回实际内容

### UPGRADE-04 [OP] wechat-agent 接入 Letta + macg
- [ ] 检查 wechat-agent 主入口
- [ ] 新消息调用 `search_letta_memory` 补充上下文
- [ ] 验证：wechat-agent 日志显示 Letta 写入成功

### UPGRADE-05 [OP] hub-mobile APK 升级 — webview 改为 3000
- [ ] capacitor.config.json：server.url 指向 Tailscale IP:3000
- [ ] 更新 web/ 入口 HTML 硬编码地址
- [ ] 验证：浏览器打开 index.html 显示 3000 控制台

### UPGRADE-06 [OP] Chronos-Zenith 数据接入 3000 Dashboard
- [ ] hub-api 加 `GET /api/chronos/status` → 读 `/tmp/chronos/*.json`
- [ ] KanbanDashboard.tsx 新增 Chronos 状态卡片
- [ ] 验证：3000 Dashboard 显示 Chronos 卡片

### UPGRADE-07 [OP] tech-digest 接入 3000 Dashboard
- [ ] hub-api 加 `GET /api/digest/latest`
- [ ] Dashboard 加"本周 AI 热点"卡片
- [ ] 验证：curl 有内容

### UPGRADE-08 [OP] Letta distill 升级
- [ ] 查 distill 脚本路径
- [ ] 追加聚合来源：agi.db + lessons-learned + op-tasks 完成
- [ ] 验证：Letta archival 新增条目

### UPGRADE-09 [OP] Twenty CRM 启动 + HyperChat 数据迁移
- [ ] 检查：`docker ps | grep twenty`
- [ ] 若未运行：`docker compose up -d`
- [ ] 更新 Sidebar 加 tab
- [ ] 导出 HyperChat 联系人，导入 Twenty
- [ ] 验证：浏览器访问 Twenty CRM 能看到客户列表

---

## SELF-IMPROVE — GLM 自我改进 Agent

### SELF-IMPROVE-01 [OP] 创建 self-improve-agent.py
- [ ] 新建 `~/agi/self_improve.py`
- [ ] 验证：`python3 ~/agi/self_improve.py`，op-tasks.md 新增 SELF-IMPROVE 条目

### SELF-IMPROVE-02 [OP] 创建每日定时器
- [ ] 新建 systemd service + timer（每日 03:00）
- [ ] `systemctl --user daemon-reload && systemctl --user enable --now self-improve.timer`
- [ ] 验证：`systemctl --user list-timers self-improve`
- [ ] [AGI→OP] [2026-04-19 01:23] [high] 检查并修复系统监控服务，恢复 CPU 和内存数据读取
- [ ] [AGI→OP] [2026-04-19 01:26] [high] 调查并处理 opencode 进程高 CPU 占用问题
- [ ] [AGI→OP] [2026-04-19 01:26] [medium] 检查并修复系统监控数据采集服务
- [ ] [AGI→OP] [2026-04-19 01:28] [medium] 检查系统监控服务状态，修复 CPU/内存 数据采集为空的问题
- [ ] [OP→CC] [2026-04-19 01:30] [high] OP agent discord-butler 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [ ] [AGI→OP] [2026-04-19 01:42] [high] 强制终止僵死的 ps 进程 (PID: 1771037)
- [ ] [AGI→OP] [2026-04-19 01:43] [high] 检查进程 opencode (PID: 1675619) 的状态，确认是否为正常工作负载（如编译/渲染），若异常则执行终止操作
- [ ] [AGI→OP] [2026-04-19 01:45] [high] 检查进程 opencode (PID: 1675619) 状态，若为无响应或死循环则执行终止
- [ ] [AGI→OP] [2026-04-19 01:45] [medium] 检查系统监控脚本，修复 CPU/内存 总量数据获取缺失的问题
- [ ] [AGI→OP] [2026-04-19 01:46] [high] 检查系统监控脚本或服务状态，修复 CPU 与 内存数据获取失败的问题
- [ ] [AGI→OP] [2026-04-19 01:55] [high] 调查并可能终止占用 99.4% CPU 的 opencode 进程 (PID: 1675619)
- [ ] [AGI→OP] [2026-04-19 01:57] [low] 修复系统监控数据获取服务
- [ ] [OP→CC] [2026-04-19 02:00] [high] OP agent service-nurse 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [ ] [AGI→OP] [2026-04-19 02:18] [low] 检查系统监控服务，恢复 CPU 和内存数据采集
- [ ] [OP→CC] [2026-04-19 02:20] [high] OP agent proxy-guardian 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [ ] [AGI→OP] [2026-04-19 02:22] [medium] 修复系统资源监控服务，确保 CPU 和内存数据正常采集
- [ ] [AGI→OP] [2026-04-19 02:24] [medium] 诊断并修复系统监控脚本，确保能正确获取 CPU、内存及服务状态
- [ ] [AGI→OP] [2026-04-19 02:27] [high] 调查进程 opencode (PID: 1675619)，确认是否卡死或死循环，必要时执行 kill 命令终止
- [ ] [AGI→OP] [2026-04-19 02:27] [medium] 检查系统监控服务，修复 CPU 和内存总数据返回为空的问题
- [ ] [AGI→OP] [2026-04-19 02:39] [high] 分析进程 opencode (PID: 1675619) 的状态，若为死循环或无响应则执行终止操作。
