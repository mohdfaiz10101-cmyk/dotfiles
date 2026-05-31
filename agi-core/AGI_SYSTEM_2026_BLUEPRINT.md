# Charlie AGI System 2026 Blueprint

Date: 2026-05-31

## Positioning

Build a personal AGI operating system on top of the existing stack, not a new chatbot.

The system should act as a governed agent runtime for Charlie's devices, services,
codebases, memories, workflows, and communications.

## Current Assets

- AGI Brain: `~/agi/brain.py`, `think.py`, sensors, Telegram/Discord notification.
- Orchestration: `~/agi/macg.py` LangGraph CLI, flows, OP delegation.
- Model gateway: LiteLLM on `:4000`, Ollama on `:11434`, GLM/DeepSeek/Claude routes.
- Memory: Letta `:8283`, ChromaDB `:8000`, memory files, memory-engine graph.
- Work execution: OpenCode agents, Claude Code, Aider, Paperclip, n8n.
- Control plane: `/mnt/ai/apps/agi-control-plane`, Hub API, Caddy entry points.
- Observability: Langfuse `:3010`, health sensors, op-tasks, Telegram alerts.
- Device layer: rooted Android phone/tablet, Tasker bridge, ADB, Windows host, Tailscale.

## Target Architecture

```text
Human intent / system events / device events
        |
        v
AGI Gateway and Event Bus
        |
        v
Policy Router
  - risk classification
  - budget classification
  - privacy classification
  - approval gate
        |
        v
Stateful Orchestrator
  - urgent self-heal graph
  - coding graph
  - research graph
  - CRM/WeChat graph
  - daily planning graph
        |
        +--> Memory Fabric
        |     - working context
        |     - episodic log
        |     - semantic vector memory
        |     - graph facts
        |     - procedural skills
        |
        +--> Tool/MCP Broker
        |     - local shell/files
        |     - systemd/docker
        |     - browser/desktop
        |     - phone/tablet/Windows
        |     - web/search/docs
        |     - WeChat/CRM/finance
        |
        +--> Agent Pool
              - CC planner/reviewer
              - OP executor
              - GLM low-cost worker
              - DeepSeek coder
              - local Ollama fallback
              - domain agents
        |
        v
Verification, Trace, Learning
  - Langfuse traces
  - task outcome DB
  - regression/eval checks
  - memory distillation
  - route tuning
```

## Design Decisions

### 1. One gateway, many runtimes

`agi-control-plane` becomes the stable public/private API. Claude Code, OpenCode,
n8n, Telegram, Tasker, and Hub call the same gateway instead of each writing
directly to `op-tasks.md`.

Initial endpoints:

- `POST /a2a/task`
- `GET /a2a/task/{id}`
- `POST /a2a/event`
- `POST /a2a/approve`
- `GET /a2a/capabilities`

Keep `op-tasks.md` as a compatibility sink until all agents migrate.

### 2. LangGraph only where state matters

Use LangGraph for workflows that need persistence, checkpointing, approval, retry,
or explicit order. Use a simple tool loop for one-shot tasks.

Core graphs:

- `self_heal`: event -> diagnose -> repair -> verify -> learn.
- `code_loop`: spec -> inspect -> patch -> test -> review -> commit suggestion.
- `memory_distill`: collect -> dedupe -> rank -> write -> verify.
- `crm_wechat`: ingest -> classify -> draft -> approve -> send -> ledger.
- `daily_ops`: summarize -> prioritize -> schedule -> delegate.

### 3. Memory Fabric, not one memory database

Keep multiple memory stores, but assign ownership:

- Files: canonical rules, architecture decisions, user preferences.
- Letta: episodic conversational and operational memory.
- ChromaDB: semantic retrieval over documents and history.
- Memgraph/SQLite memory-engine: durable facts and service dependency graph.
- LangGraph checkpoints: run-local working memory.
- Langfuse: trace memory for evaluation and debugging.

Every agent run should read through a common `memory_context(query, scope)` API
and write through a common `memory_commit(event)` API.

### 4. Tool Broker with security policy

All high-impact tools go through a broker. The broker attaches identity, risk,
timeout, audit log, and approval requirements.

Risk levels:

- L0 read-only: status, search, logs, docs.
- L1 reversible: restart user service, clear cache, create task.
- L2 persistent: edit files, write memory, change config.
- L3 destructive/security: delete, rebuild, expose public ports, credentials.

Default policy:

- L0 auto.
- L1 auto if verified and rate-limited.
- L2 requires test/verification and trace.
- L3 requires explicit user approval.

### 5. Event-driven brain

Move from fixed 60 second polling to hybrid event mode:

- systemd path units for status files.
- docker events for container changes.
- journal alerts for service failures.
- Tasker/ADB events from phone/tablet.
- browser/desktop focus events when available.
- 5 minute heartbeat for baseline state.

### 6. Verification-first autonomy

No autonomous action counts as complete until verified.

Every action record must include:

- intent
- selected model
- tools used
- files/services touched
- verification command/result
- outcome
- lesson candidate

## Implementation Phases

### Phase 0: Stabilize foundation

- Fix Letta and LiteLLM health mismatch.
- Resolve open self-improve issues in `hub-api.py`, `launcher-server.py`,
  `brain.py`, and `think.py`.
- Create `feedback.db` for task outcome tracking.
- Normalize service health checks in one module.

### Phase 1: Unified A2A gateway

- Add task/event/approval endpoints to `agi-control-plane`.
- Add task IDs and lifecycle states.
- Make OP/CC/macg write to gateway first, `op-tasks.md` second.
- Add Langfuse trace ID to every task.

### Phase 2: Memory and policy broker

- Implement `memory_context()` and `memory_commit()`.
- Add risk classifier for tool calls.
- Wrap shell/systemd/docker/browser/ADB tools behind broker APIs.
- Add approval queue in control plane.

### Phase 3: Stateful workflows

- Promote existing flows to LangGraph graphs with checkpoints.
- Add `self_heal`, `code_loop`, `memory_distill`, `crm_wechat`, `daily_ops`.
- Add human interrupt nodes for L2/L3 operations.

### Phase 4: Learning loop

- Weekly route analysis by success rate, cost, latency, false-positive rate.
- Auto-tune model routes through LiteLLM.
- Distill repeated failures into lessons and tests.
- Generate a monthly architecture audit.

## Immediate Next Build

Start with Phase 0 and Phase 1.

Minimum viable AGI core:

- stable health for Letta/LiteLLM
- `/a2a/task` gateway
- `feedback.db`
- `memory_context()`
- tool risk levels
- `self_heal` graph with verify step

This converts the existing system from many useful agents into one governed
agent operating system.
