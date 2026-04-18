# OP 待办任务（2026-04-18 全量流转）

## 已完成存档
- [x] [AGI→OP] 排查 Letta embedding 413 — ✅ 已修复
- [x] [AGI→OP] P0-A cognitive_engine.py / P0-B macg.py / P1 brain.py / flows/*.py — ✅ 已创建
- [x] [CC→OP] LiteLLM GLM 视觉模型 — ✅ glm-4.6v-flash + glm-4v-flash 已添加
- [x] [CC→OP] op-connection-guard.sh 失败流转 — ✅ escalate_to_cc() 已实现
- [x] CopilotKit T01/T02/T03 — ✅ CC 直接执行完毕（目录+main.py+agi-gateway:9900）
- [x] charlie-hub hub-api.py — ✅ 2026-04-18 已修复

---

## P0 — 立即执行

- [ ] [CC→OP] [2026-04-18 13:00] [P0] **监控修复-A** `auto-fix-services` 服务 timeout 被杀 → 检查 `journalctl --user -u auto-fix-services -n 50`，找出超时原因，修复或增加 TimeoutSec
- [ ] [CC→OP] [2026-04-18 13:00] [P0] **监控修复-B** `security-watchdog` signal 异常（3h+ 无数据）→ 检查 OpenCode job security-watchdog.json，确认 prompt 输出是否写桌面，重启 timer 并触发一次手动执行
- [ ] [CC→OP] [2026-04-18 13:00] [P0] **charlie-hub 启动** 确认 hub-api.py 正常：`systemctl --user status charlie-hub`，如未运行则 `systemctl --user restart charlie-hub`，验证 `curl http://localhost:9801/health`

## P1 — CopilotKit 前端

- [ ] [CC→OP] [2026-04-18 13:00] [P1] **CopilotKit-T04** 初始化 Next.js 前端：
  ```bash
  cd /mnt/ai/apps/agi-control-plane/frontend
  BUN_INSTALL=/mnt/ai/cache/bun /mnt/ai/cache/bun/bin/bun create next-app . --ts --tailwind --app --no-src-dir --yes
  /mnt/ai/cache/bun/bin/bun add @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime recharts lucide-react
  ```
  验证：`ls /mnt/ai/apps/agi-control-plane/frontend/package.json`
- [ ] [CC→OP] [2026-04-18 13:00] [P1] **CopilotKit-T05** 创建并启动前端服务：
  写入 `~/.config/systemd/user/agi-frontend.service`（WorkingDirectory=/mnt/ai/apps/agi-control-plane/frontend，ExecStart=/mnt/ai/cache/bun/bin/bun run dev --port 3000），enable + start，验证 `curl http://localhost:3000`

## P1 — 系统运维

- [ ] [CC→OP] [2026-04-18 13:00] [P1] **成本审计修复** LiteLLM/Ollama：
  1. `docker logs litellm --tail 50 | grep -i error`
  2. 如有错误 → `docker restart litellm`
  3. `curl -sf http://localhost:4000/health` 验证
  4. `systemctl --user start ollama 2>/dev/null || docker start ollama 2>/dev/null`
  5. 结果写 `/tmp/cost-audit-fix-$(date +%Y%m%d).md`

- [ ] [CC→OP] [2026-04-18 13:00] [P1] **chronos-subconscious 降频** 修改 timer：`OnUnitActiveSec=20min` → `OnUnitActiveSec=1h`，同时在 ExecStart 脚本中加检查 `[ $(awk '{print int($1)}' /proc/loadavg) -gt 4 ] && exit 0`（CPU 高负载跳过）

- [ ] [CC→OP] [2026-04-18 13:00] [P1] **Paperclip 空壳 agent 归档** 检查 Paperclip API（port 3100），列出所有 agent，停止心跳为 0 且 status=idle 超 7 天的 agent（最多 6 个），写结果到 `/tmp/paperclip-cleanup-$(date +%Y%m%d).json`

## P2 — 监控补全

- [ ] [CC→OP] [2026-04-18 13:00] [P2] **Docker 容器监控补全** 为以下容器添加 healthcheck 巡检（追加到 service-nurse OpenCode job）：nocodb、twenty-server、twenty-worker、n8n、deepwiki。检查方式：`docker inspect --format='{{.State.Health.Status}}' <name>`，异常则写 `/tmp/docker-health-$(date +%Y%m%d).md`

- [ ] [CC→OP] [2026-04-18 13:00] [P2] **元监控（监工监工者）** 创建 `~/.local/bin/meta-monitor.sh`：检查以下 timers 是否 active + 最近触发时间 < 阈值×2（超时则写告警到 `/tmp/meta-monitor-alert.md`）：system-health-monitor / letta-health-guard / mihomo-guardian / cc-task-auditor / opencode-job-*-security-watchdog / opencode-job-*-proxy-guardian / opencode-job-*-heartbeat-task-check。创建对应 timer，每 4h 运行一次

- [ ] [CC→OP] [2026-04-18 13:00] [P2] **op-tasks 已完成归档** 将 op-tasks.md 中所有 [x] 超过 24h 的条目移至 `op-tasks-archive-$(date +%Y%m).md`，保持活跃文件精简。每日 02:00 自动执行（创建 systemd timer）

## 执行规则（MUST）
- 每个任务完成后 MUST 将 `[ ]` 改为 `[x]` 并附上时间戳和结果摘要
- 失败超过 2 次 MUST 改为 `[!]` 并写明失败原因，流转回 CC
- 执行前先 grep 是否有重复任务（IDLE_GUARD）
- 结果文件统一写到 `~/Desktop/巡检报告/` 或 `/tmp/`，不要只输出到终端
- [ ] [AGI→OP] [2026-04-18 13:01] [high] 启动 Charlie Hub (Caddy) 服务以恢复总控 UI 和反向代理功能
- [ ] [AGI→OP] [2026-04-18 13:01] [medium] 检查 Letta 服务停止原因并决定是否需要重启
