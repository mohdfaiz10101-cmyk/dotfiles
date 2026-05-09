---
name: taskboard
description: TaskBoard 定时任务管理系统 — 查看/管理 crontab、systemd timer、Docker、内置调度任务
user-invocable: true
version: "1.0.0"
category: system
tags: [system, tasks, cron, systemd, docker, scheduler]
effort: low
---

# /taskboard

TaskBoard 定时任务管理系统 — 统一管理 crontab、systemd timer、Docker restart policy、APScheduler 内置调度任务。

## 用法

```
/taskboard [子命令] [参数]
```

无参数时等同于 `/taskboard status`。

## 项目路径

- 后端: `~/projects/taskboard/backend/` (FastAPI, port 8003)
- 前端: `~/projects/taskboard/frontend/` (React + shadcn/ui, port 5173)
- API 基址: `http://localhost:8003`
- Web UI: `http://localhost:5173`

## 前置检查（每个子命令执行前）

所有子命令执行前，**必须**先检查后端是否在线：

```bash
curl -sf http://localhost:8003/ > /dev/null 2>&1 && echo "ONLINE" || echo "OFFLINE"
```

如果返回 OFFLINE，自动执行 start 子命令启动后端，再继续执行用户请求的子命令。

---

## 子命令

### /taskboard start

启动后端和前端服务。

```bash
# 1. 启动后端（后台运行）
cd ~/projects/taskboard/backend && \
  source .venv/bin/activate && \
  LD_LIBRARY_PATH="/nix/store/j2kgllgds4w7na8zqv1msi0mpvpjxda8-gcc-15.2.0-lib/lib" \
  nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8003 \
  > /tmp/taskboard-backend.log 2>&1 &

# 2. 等待后端就绪（最多 10 秒）
for i in $(seq 1 10); do
  curl -sf http://localhost:8003/ > /dev/null 2>&1 && break
  sleep 1
done

# 3. 验证后端
curl -sf http://localhost:8003/ | python3 -m json.tool

# 4. 启动前端（后台运行，可选 — 仅当需要 Web UI 时）
cd ~/projects/taskboard/frontend && \
  nohup npx vite --host 0.0.0.0 --port 5173 \
  --cache /tmp/npm-cache \
  > /tmp/taskboard-frontend.log 2>&1 &
```

**验证**: `curl -sf http://localhost:8003/` 返回 `{"status":"ok",...}`

---

### /taskboard stop

停止后端和前端服务。

```bash
# 停止后端
pkill -f "uvicorn app.main:app.*--port 8003" 2>/dev/null

# 停止前端
pkill -f "vite.*--port 5173" 2>/dev/null

# 验证已停止
curl -sf http://localhost:8003/ > /dev/null 2>&1 && echo "STILL RUNNING" || echo "STOPPED"
```

---

### /taskboard status

查看服务运行状态 + 任务统计摘要。

```bash
# 服务状态
BACKEND_UP=$(curl -sf http://localhost:8003/ > /dev/null 2>&1 && echo "ONLINE" || echo "OFFLINE")
FRONTEND_UP=$(curl -sf http://localhost:5173/ > /dev/null 2>&1 && echo "ONLINE" || echo "OFFLINE")
echo "Backend (8003): $BACKEND_UP"
echo "Frontend (5173): $FRONTEND_UP"

# 统计数据（仅在后端在线时）
curl -sf http://localhost:8003/api/stats | python3 -m json.tool
```

**输出字段说明**:
- `total_tasks` / `enabled_tasks` / `disabled_tasks` — 任务总数/启用/禁用
- `total_executions` / `success_count` / `failed_count` / `running_count` — 执行统计
- `tasks_by_type` — 按 cron/systemd/docker/apscheduler 分类计数

---

### /taskboard list [type]

列出所有任务，可选按类型过滤。

**参数**:
- `type` (可选) — `cron` | `systemd` | `docker` | `apscheduler`

```bash
# 列出全部
curl -sf http://localhost:8003/api/tasks | python3 -m json.tool

# 按类型过滤
curl -sf "http://localhost:8003/api/tasks?type=cron" | python3 -m json.tool
curl -sf "http://localhost:8003/api/tasks?type=systemd" | python3 -m json.tool
curl -sf "http://localhost:8003/api/tasks?type=docker" | python3 -m json.tool
curl -sf "http://localhost:8003/api/tasks?type=apscheduler" | python3 -m json.tool

# 按启用状态过滤
curl -sf "http://localhost:8003/api/tasks?enabled=true" | python3 -m json.tool

# 搜索
curl -sf "http://localhost:8003/api/tasks?search=backup" | python3 -m json.tool
```

**格式化输出建议**（用 jq 提取关键列）:

```bash
curl -sf http://localhost:8003/api/tasks | \
  python3 -c "
import json,sys
tasks=json.load(sys.stdin)
for t in tasks:
    enabled='✓' if t['enabled'] else '✗'
    print(f\"{t['id'][:8]}  {enabled}  {t['type']:12s}  {t['schedule']:20s}  {t['name']}\")
"
```

---

### /taskboard add \<name\> \<schedule\> \<command\>

快速创建 APScheduler 类型的任务。

**参数**:
- `name` — 任务名称（唯一标识）
- `schedule` — Cron 表达式，如 `*/5 * * * *` 或 `0 8 * * *`
- `command` — 要执行的命令

```bash
curl -sf -X POST http://localhost:8003/api/tasks \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$NAME\",
    \"display_name\": \"$NAME\",
    \"type\": \"apscheduler\",
    \"schedule\": \"$SCHEDULE\",
    \"command\": \"$COMMAND\",
    \"enabled\": true
  }" | python3 -m json.tool
```

**示例**:
```bash
# 每 5 分钟检查磁盘空间
curl -sf -X POST http://localhost:8003/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"name":"disk-check","display_name":"Disk Space Check","type":"apscheduler","schedule":"*/5 * * * *","command":"df -h / /mnt/ai","enabled":true}'

# 每天凌晨 3 点清理 Docker
curl -sf -X POST http://localhost:8003/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"name":"docker-cleanup","display_name":"Docker Cleanup","type":"apscheduler","schedule":"0 3 * * *","command":"docker system prune -f","enabled":true}'
```

---

### /taskboard run \<name|id\>

手动触发一次任务执行。

**参数**:
- `name|id` — 任务名称或 ID（前缀匹配）

```bash
# 如果参数是完整 UUID
TASK_ID="$NAME_OR_ID"

# 如果参数是名称，先查找 ID
TASK_ID=$(curl -sf "http://localhost:8003/api/tasks?search=$NAME_OR_ID" | \
  python3 -c "
import json,sys
tasks=json.load(sys.stdin)
matches=[t for t in tasks if t['name']=='$NAME_OR_ID']
if matches: print(matches[0]['id'])
else:
  # 尝试前缀匹配 ID
  tasks2=[t for t in json.load(sys.stdin) if t['id'].startswith('$NAME_OR_ID')]
  if tasks2: print(tasks2[0]['id'])
  else: sys.exit(1)
")

# 触发执行
curl -sf -X POST "http://localhost:8003/api/tasks/$TASK_ID/run" | python3 -m json.tool
```

**输出**: ExecutionResponse 对象，含 `status`, `output`, `exit_code`, `started_at`, `finished_at`。

---

### /taskboard toggle \<name|id\>

启用/禁用任务切换。

**参数**:
- `name|id` — 任务名称或 ID

```bash
# 查找任务 ID（同 run 子命令的查找逻辑）
TASK_ID=$(curl -sf "http://localhost:8003/api/tasks?search=$NAME_OR_ID" | \
  python3 -c "
import json,sys
tasks=json.load(sys.stdin)
matches=[t for t in tasks if t['name']=='$NAME_OR_ID']
if matches: print(matches[0]['id'])
else: sys.exit(1)
")

# 切换状态
curl -sf -X POST "http://localhost:8003/api/tasks/$TASK_ID/toggle" | python3 -m json.tool
```

**输出**: 更新后的 TaskResponse，`enabled` 字段已翻转。

---

### /taskboard logs \<name|id\>

查看任务最近的执行日志。

**参数**:
- `name|id` — 任务名称或 ID

```bash
# 查找任务 ID（同 run 子命令）
TASK_ID=$(curl -sf "http://localhost:8003/api/tasks?search=$NAME_OR_ID" | \
  python3 -c "
import json,sys
tasks=json.load(sys.stdin)
matches=[t for t in tasks if t['name']=='$NAME_OR_ID']
if matches: print(matches[0]['id'])
else: sys.exit(1)
")

# 获取最近 10 条执行记录
curl -sf "http://localhost:8003/api/executions?task_id=$TASK_ID&limit=10" | \
  python3 -m json.tool

# 获取单条执行的完整输出（包含 output 和 error 字段）
EXECUTION_ID="..."  # 从上面结果中取
curl -sf "http://localhost:8003/api/executions/$EXECUTION_ID" | python3 -m json.tool
```

**格式化输出建议**:
```bash
curl -sf "http://localhost:8003/api/executions?task_id=$TASK_ID&limit=5" | \
  python3 -c "
import json,sys
execs=json.load(sys.stdin)
for e in execs:
    status=e['status']
    exit_code=e.get('exit_code','-')
    started=e.get('started_at','N/A')
    print(f\"{e['id'][:8]}  {status:10s}  exit={exit_code}  {started}\")
"
```

---

### /taskboard discover

手动触发系统任务发现（扫描 crontab、systemd timer、Docker restart policy）。

```bash
curl -sf -X POST http://localhost:8003/api/tasks/discover | python3 -m json.tool
```

**输出**: 发现摘要，包含各类别新导入的任务数量。

---

### /taskboard open

在浏览器中打开 TaskBoard Web UI。

```bash
xdg-open http://localhost:5173 2>/dev/null
```

如果前端未运行，先执行 start 子命令启动前端。

---

## 辅助函数

### 按名称查找任务 ID

多个子命令需要按名称查找 ID，统一用以下逻辑：

```bash
_find_task_id() {
  local query="$1"
  curl -sf "http://localhost:8003/api/tasks?search=$query" | \
    python3 -c "
import json,sys
tasks=json.load(sys.stdin)
# 精确名称匹配
matches=[t for t in tasks if t['name']=='$query']
if matches:
    print(matches[0]['id'])
    sys.exit(0)
# ID 前缀匹配
prefix=[t for t in json.load(open('/dev/stdin')) if t['id'].startswith('$query')]
if prefix:
    print(prefix[0]['id'])
    sys.exit(0)
print('NOT_FOUND', file=sys.stderr)
sys.exit(1)
"
}
```

---

## 重要注意事项

- **NixOS 兼容性**: 后端启动时 **必须** 设置 `LD_LIBRARY_PATH`（greenlet 依赖 gcc lib）
- **npm 缓存问题**: 前端启动时 **必须** 用 `--cache /tmp/npm-cache` 避免权限问题
- **任务类型**: `cron` | `systemd` | `docker` | `apscheduler`（创建时 type 字段必须是这四个之一）
- **API 文档**: http://localhost:8003/docs （Swagger UI，后端在线时可用）
- **WebSocket**: `ws://localhost:8003/ws/logs` 实时日志推送
- **后端自动发现**: 后端启动时自动扫描 crontab/systemd timer/Docker，无需手动 discover
- **进程管理**: 使用 `pkill -f` 按命令行特征停止进程，不依赖 PID 文件
