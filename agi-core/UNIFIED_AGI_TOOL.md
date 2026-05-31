# Unified AGI Tool

`agi` is the unified local entry point for Charlie's existing AGI stack.

Path:

```bash
/home/charlie/.local/bin/agi
```

## Daily Commands

```bash
agi status
agi doctor
agi open
```

Submit work into the unified task ledger:

```bash
agi task -p high 修复 LiteLLM 500 并验证 /health/readiness
agi task -r local -p low 记录一个只进入本地账本的任务
```

Ask through LiteLLM. If LiteLLM is down, the request is downgraded into an OP task:

```bash
agi ask 现在系统最该修什么
```

Search or add memory:

```bash
agi memory search LiteLLM
agi memory add 用户希望所有 AGI 能力都从 agi 统一入口进入
```

Run existing AGI flows:

```bash
agi flow self_heal --spec 检查 Letta 和 LiteLLM
agi flow task_decompose --spec 把统一入口接入 Web 控制面板
```

Wechat bridge:

```bash
agi wechat status
agi wechat reply 联系人 消息内容
```

## Current Role

`agi` is intentionally not a new daemon. It is a practical facade over existing
systems:

- AGI Brain status
- OP task queue
- local task/event SQLite ledger
- memory files
- existing AGI flows
- LiteLLM ask path
- Letta/LiteLLM/Chroma/Ollama health probes
- Hub/WeChat endpoints
- major Web entry points

## Next Integration

The next step is to make `agi-control-plane` expose the same task/event model
over HTTP:

- `POST /a2a/task`
- `GET /a2a/task/{id}`
- `GET /a2a/tasks`
- `POST /a2a/event`

Then CLI, Web UI, Telegram, Tasker, Claude Code, and OpenCode can all use the
same task ledger and approval model.
