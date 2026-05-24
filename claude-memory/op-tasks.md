# OP 待办任务

## DECAY（2026-05-19 批量清理 — 超30天未执行）

以下任务派发于 2026-04-19~04-27，距今超30天未执行，标记 DECAY：

- [DECAY] BUSINESS-DATA-IMPORT — 外贸业务数据索引入库（2026-04-19）
- [DECAY] CRM-WECHAT-BRIDGE — 客户管理+微信+记忆打通（2026-04-19）
- [DECAY] HYPER-ABSORB — HyperChat/HyperOS精华吸收到3000（2026-04-19）
- [DECAY] FEATURES-3000 — 3000面板缺失功能补全（2026-04-19）
- [DECAY] WECHAT-LIVE — 微信实时监控 + 看板推送（2026-04-19）
- [DECAY] MONITOR-UNIFIED — 统一监控入口（2026-04-19）
- [DECAY] CRM-01~06 — CRM全系列（2026-04-19）
- [DECAY] UPGRADE-01~09 — 功能升级全系列（2026-04-19）
- [DECAY] SELF-IMPROVE-01~02（2026-04-19）
- [DECAY] SENSE-01~04 — 感知系统升级（2026-04-19）
- [DECAY] WECHAT-3000-02~03（2026-04-19）
- [DECAY] LETTA-01~03 — Letta健康修复（2026-04-19）
- [DECAY] VERIFY-01~03 + BUG-OPGUARD（2026-04-19）
- [DECAY] PANEL-01~03 — 面板升级（2026-04-19）
- [DECAY] DEPT-01~04 — 部门化执行（2026-04-19）
- [DECAY] 双机热备份 步骤3.1（2026-04-20）
- [DECAY] MEMORY-ENHANCEMENT（2026-04-25）
- [DECAY] PI-WEB-UI（2026-04-25）
- [DECAY] AI-STACK-EXPAND P0~P3（2026-04-25）
- [DECAY] WECHAT-CRM P0~P2（2026-04-25）
- [DECAY] OFFICE-AGENT v2.1 CLI增强（2026-04-25）
- [DECAY] 移动端AI能力升级（2026-04-27）

## 已完成

### 2026-05-21

  - Docker: 5容器运行中（letta-chromadb unhealthy）
  - 磁盘: `/` 85% | `/mnt/ai` 30% | `/mnt/data` 80%
  - 端口: 3000/4000/4001/8000/8283/9900/9800/9977/7699/7890/7891 监听中
  - 8290-8299 未监听（预留/已停止服务）

  - [x] [2026-05-24] 18092已激活+已改用18093 — 无需nixos-rebuild

### 2026-05-19

### 2026-05-19 巡检结果（Service-Nurse）
**Docker**: 7容器运行中，letta-chromadb unhealthy
**磁盘**: `/` 89% (9.3G可用) | `/mnt/ai` 29% | `/mnt/data` 80%
**端口**: 4000[OK] 8283[OK] 9800[OK] 9900[OK] 3000[OK] 7890[OK] 3100[FAIL]
**[!] 根分区 89%，接近85%阈值**

### 2026-05-19 17:55 — Hub API 补全 + 任务清理

## 执行规则
新任务应从DECAY列表中按需复活，不要盲目重试。优先级由Charlie确认。

  - Docker: 5容器运行中（letta-chromadb unhealthy）
  - 磁盘: `/` 85% | `/mnt/ai` 30% | `/mnt/data` 80%
  - 端口: 3000/4000/4001/8000/8283/9900/9800/9977/7699/7890/7891 监听中
  - 8290-8299 未监听（预留/已停止服务）

- [2026-05-19 22:37] [GLM] GLM API 不可用 → 已 fallback 到 Step

- [2026-05-20 20:05] [GLM] GLM API 不可用 → 已 fallback 到 Step

- [2026-05-20 22:30] [GLM] GLM API 不可用 → 已 fallback 到 Step

  - [x] [2026-05-24] 18092已激活+已改用18093 — 无需nixos-rebuild



- [2026-05-21 11:00] [GLM] GLM API 不可用 → 已 fallback 到 Step









  - opencode-autoupgrade: GitHub下载超时 → 移除SOCKS5代理，下载正常(47M/32s)
  - opencode-session-guard: dry-run显示0损坏session，问题已自行恢复
  - 升级脚本增强: 强制杀进程+3次重试复制，解决"文本文件忙"



### [SELF-IMPROVE 2026-05-22] GLM 自动代码审查

### [SELF-IMPROVE 2026-05-23] GLM 自动代码审查
- [ ] [SELF-IMPROVE] brain.py: 修复文件末尾的语法截断错误（补全 `TRIGGER_FI` 等未写完的代码）。
- [ ] [SELF-IMPROVE] think.py: `_letta_recall` 函数缺少右括号和 `return` 语句导致语法截断不完整。
- [ ] [SELF-IMPROVE] kanban.html: 代码在 `.wip-bar` 样式定义处被意外截断，需要补全缺失的样式代码并确保HTML结构和JS逻辑完整闭合。
- [ ] [SELF-IMPROVE] launcher-server.py: 命令启动逻辑中未对传入参数进行严格的白名单校验，存在严重的命令注入风险，应仅允许预定义的安全命令而非直接拼接执行。
- [ ] [SELF-IMPROVE] hub-api.py: 将数据库查询逻辑及全局变量（如`_ws_clients`、`REPLY_QUEUE`）重构为独立的依赖注入服务或类模块，以降低路由函数的耦合度并提升代码的可测试性与可维护性。
- [ ] 测试TTS：验证语音播报功能是否正常工作
- [ ] 快速测试：echo hello
- [ ] 快速TTS测试：验证spd-say语音播报

## TTS 测试任务

- [ ] TTS-TEST-001 — 测试TTS播报：执行echo "TTS测试成功"并验证spd-say播报
# test 1779638866
# test 1779639005
# test2 1779639080
- [ ] [OP] [2026-05-25 00:53] AI配置告警(自愈失败): 🔴 AGENTS.md 处理后仍缺: FALSE_POSITIVE_GUARD 只能由 CC dev.*模式
