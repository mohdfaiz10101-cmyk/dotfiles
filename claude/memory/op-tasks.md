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

### 2026-05-19
- [x] [OP] [2026-05-18 18:40] Service-Nurse巡检 — 已执行
- [x] [OP] [2026-05-19 12:40~14:00] 任务跟进×9 — 已执行，历史任务全部标记DECAY

### 2026-05-19 巡检结果（Service-Nurse）
**Docker**: 7容器运行中，letta-chromadb unhealthy
**磁盘**: `/` 89% (9.3G可用) | `/mnt/ai` 29% | `/mnt/data` 80%
**端口**: 4000[OK] 8283[OK] 9800[OK] 9900[OK] 3000[OK] 7890[OK] 3100[FAIL]
**[!] 根分区 89%，接近85%阈值**

### 2026-05-19 17:55 — Hub API 补全 + 任务清理
- [x] [完成 2026-05-19 17:55] Hub API /api/glm/workbench 补全 — 新增 competitive/codebase/aider/jobs 4个数据字段
- [x] [完成 2026-05-19 17:55] 任务跟进×20 — 批量清理 14:20~17:40 累积的重复任务

## 执行规则
新任务应从DECAY列表中按需复活，不要盲目重试。优先级由Charlie确认。

- [ ] [OP] [2026-05-19 18:00] Service-Nurse巡检：Docker容器状态+systemd服务+磁盘空间+关键端口可达性


- [ ] [OP] [2026-05-19 18:10] 任务跟进：检查 op-tasks.md 未完成任务进展，更新状态或标记 DECAY


- [ ] [OP] [2026-05-19 18:20] 任务跟进：检查 op-tasks.md 未完成任务进展，更新状态或标记 DECAY


- [ ] [OP] [2026-05-19 18:30] 任务跟进：检查 op-tasks.md 未完成任务进展，更新状态或标记 DECAY


- [ ] [OP] [2026-05-19 18:40] 任务跟进：检查 op-tasks.md 未完成任务进展，更新状态或标记 DECAY
