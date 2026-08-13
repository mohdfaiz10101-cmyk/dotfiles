# Runbook: Workflow Intelligence

Shared workflow extraction and optimization layer for Codex, OpenCode, Crush,
Goose, and Aider.

## Goal

Build a CodeGraph-like system for operational workflows:

- CodeGraph indexes source symbols, calls, and relationships.
- Workflow Intelligence indexes tasks, steps, tools, evidence, failures, fixes,
  and reusable procedures.
- `~/.local/bin/hermes-experience-map` is the compact read path for Hermes:
  it summarizes workflow hits, blacklist rules, search health, and phone/network
  state into `~/.local/state/hermes-experience-map/latest.md` and `.json`.
  Use it for system/router/phone/Hermes memory recall; do not try to put those
  operational facts into CodeGraph.
- Codex, OpenCode, and Crush should all publish task events to one shared
  workflow bus and consume the same workflow recall before acting.

Do not implement three separate learning systems. The strongest architecture is
one shared extractor/indexer with thin adapters for each agent surface.

## Current Baseline

- Phase 1 is implemented locally:
  `~/.local/bin/workflow-intel` captures, extracts, recalls, audits, and
  dry-runs publish proposals. It writes compact JSONL state under
  `~/memory/workflows/` and audit state under `~/.local/state/workflow-intel/`.
- Automation: `workflow-intel-maintain.timer` runs hourly and calls
  `workflow-intel maintain --limit 200` at idle I/O priority. Capture hooks
  use bounded 1 MiB tail reads and the same idle scheduling, so workflow
  indexing cannot contend with the interactive desktop or database writes.
- 2026-08-01 current policy: keep `workflow-intel-maintain.timer` enabled for
  shared Codex/OpenCode/Crush/Hermes recall. Keep `ai-a2a-worker.timer`
  disabled by default because its 30-second cadence is too noisy for routine
  operation; process A2A review requests manually or only inside an explicit
  Codex budget window.

Verify the resource guard after changing these units:

```bash
systemctl --user show workflow-intel-maintain.service -p Nice -p CPUWeight -p IOWeight
systemctl --user show workflow-intel-maintain.timer -p NextElapseUSecRealtime
cat /proc/pressure/io
```
- Immediate capture hooks:
  - OpenCode post-learning calls
    `workflow-intel capture --source opencode --limit 80`.
  - `agent-dispatch status/watch` calls
    `workflow-intel capture --source agent-dispatch --limit 50` after task
    state changes.
- File-event capture hooks:
  - `workflow-intel-codex-capture.path` watches `~/.codex/history.jsonl` and
    starts `workflow-intel-codex-capture.service`.
  - `workflow-intel-crush-capture.path` watches
    `~/.local/state/crush-eval/latest.md` and starts
    `workflow-intel-crush-capture.service`.
- OpenCode pre-recall now includes bounded `workflow_hits` from
  `workflow-intel recall`.
- Crush and Codex are covered by both file-event capture and timer-based
  maintenance.
- OpenCode already has the richest lifecycle:
  `~/.config/opencode/.opencode/plugins/agent-lifecycle.mjs` calls
  `~/.local/bin/opencode-lifecycle.py pre|post`, stores task journal entries,
  knowledge candidates, recall accuracy reports, correction candidates, and
  RAG records under `~/.local/state/opencode-lifecycle/`.
- Crush has structured completion output in `/var/home/charlie/.config/crush/CRUSH.md`
  and quality scoring via `~/.local/bin/crush-session-eval`, but OpenCode
  post-task lifecycle does not run inside Crush.
- Codex has skills, AGENTS rules, history, MCPs, and WebTTY account surfaces,
  but no always-on local post-task extractor equivalent to OpenCode lifecycle.
- `agent-dispatch` already creates task contracts and coordinates OP/Crush
  handoff with Codex failure review through `ai-a2a`.
- Goose/Aider use a separate, deliberately narrower adapter:
  `~/.local/bin/agent-goose-aider-router`. `diagnose` creates a compact task
  dossier under `~/.local/state/goose-aider-router/tasks/`, runs Goose in a
  read-only diagnosis stage, and makes Aider unavailable until `apply` is
  given explicit workspace-relative files. It immediately captures compact
  task metadata through `workflow-intel capture --source goose-aider-router`;
  this is not connected to `agent-dispatch`, so it cannot alter OP/Crush
  routing.
- `~/.local/bin/goose-smart` injects `~/.ai-context/agent-bootstrap.md` using
  Goose Top Of Mind. `goose-smart-loop` exposes `delegate`, `apply`, and
  `status` in Guise WebTTY. The bootstrap is standing policy only; relevant
  maps/runbooks are loaded per task.

## Target Architecture

### 1. Event Capture

All agent surfaces append normalized task events to:

`~/memory/workflows/events.jsonl`

Each event should be compact and structured:

```json
{
  "schema": "workflow-event-v1",
  "source": "codex|opencode|crush|agent-dispatch|ai-a2a|goose-aider-router",
  "session_id": "...",
  "task_id": "...",
  "ts": "ISO-8601",
  "phase": "pre|tool|checkpoint|final|review|correction",
  "goal": "short user goal",
  "cwd": "/absolute/path",
  "tools": ["rg", "systemctl --user is-active ..."],
  "touched": ["/path/file"],
  "evidence": ["short verified evidence only"],
  "status": "completed|unclear|failed|skipped",
  "failure_mode": "optional stable key",
  "candidate_workflow": "optional extracted procedure"
}
```

Adapters must never store secrets, full raw logs, or large transcripts.

### 2. Workflow Extractor

Create one deterministic helper:

`~/.local/bin/workflow-intel`

Core subcommands:

```bash
workflow-intel capture --source opencode --session <id>
workflow-intel capture --source crush --task <dispatch-id>
workflow-intel capture --source codex --session <id>
workflow-intel extract --limit 50
workflow-intel recall '<task text>'
workflow-intel audit
workflow-intel publish --dry-run
```

Extraction should turn repeated successful patterns into workflow candidates:

- trigger words and task profile
- required first reads or probes
- ordered steps
- forbidden approaches from `FAILURE_BLACKLIST.md`
- acceptance checks
- rollback or safe-stop condition
- preferred executor: Codex, OP, Crush, or dispatch router
- confidence, support count, last verified timestamp

### 3. Workflow Index

Store indexed workflows separately from raw events:

- `~/memory/workflows/index.jsonl` for machine-readable records
- `~/memory/workflows/candidates.jsonl` for unapproved candidates
- `~/.local/state/workflow-intel/audit.json` for health and drift

Workflow record shape:

```json
{
  "schema": "workflow-v1",
  "id": "stable-slug",
  "title": "short name",
  "scope": "opencode|codex|crush|phone|router|frontend|repo",
  "triggers": ["18910", "任务停止", "stale busy"],
  "steps": ["read runbook", "run bounded probe", "apply fix", "verify"],
  "avoid": ["known bad path"],
  "verification": ["exact command or API probe"],
  "confidence": 0.0,
  "support_count": 0,
  "last_verified": "ISO-8601",
  "published_to": ["runbook|skill|script|button|none"]
}
```

### 4. Recall Path

Before an agent acts:

- OpenCode: `agent-lifecycle.mjs` calls `workflow-intel recall` beside the
  existing `opencode-lifecycle.py pre` output.
- Crush: add a small pre-prompt wrapper or CRUSH rule that calls
  `workflow-intel recall` for non-trivial tasks and injects only top matches.
- Codex: add a Codex skill or AGENTS rule that says to call
  `workflow-intel recall` for system/Codex/OP/Crush/workflow tasks.
- Agent dispatch: `agent-dispatch decide` can use workflow hits as another
  score input when choosing OP vs Crush.
- Hermes: lightweight watchers must read the shared event/task state only.
  They must not call mutating `agent-dispatch watch/status` paths just to show
  status or send notifications.
- Hermes pre-task hook now also calls `~/.local/bin/hermes-memory-brief`, which
  injects bounded current memory state: workflow-intel audit counts, selected
  workflow hits, A2A pending/synced counts, key state files such as
  `phone-network-stabilize/latest.json`,
  `hermes-search-health/latest.json`, `hermes-experience-map/latest.md`, and
  the required first-read files.
  This is the fast recall path for compressed or resumed sessions; update it
  when a new high-value state file becomes the source of truth.
- A2A pending proposals are not durable memory. Use
  `~/.local/bin/a2a-curate-safe --since-days 7 --limit 200 --apply` followed
  by `python3 ~/.hermes/a2a/scripts/sync.py` to conservatively approve only
  high-confidence substantive proposals and write them into
  `~/.hermes/a2a/knowledge/`.

Recall output must be short, sourced, and bounded. It should name the workflow
ID, confidence, first checks, and verification commands. Live evidence and the
current user request always override old workflow memory.

### 5. Promotion Rules

Do not automatically rewrite runbooks or skills from a single task.

Promotion levels:

1. `candidate`: extracted from one task; visible in audit only.
2. `verified`: supported by at least two compatible tasks or one direct manual
   approval plus verification evidence.
3. `published`: written to the smallest durable artifact:
   runbook, skill, helper script, WebTTY button/API endpoint, or AGENTS rule.

Use this mapping:

- exact repeated commands -> script
- phone/mobile one-tap operation -> Workbench or WebTTY button
- operational topology or service sequence -> runbook
- future-agent procedural knowledge -> Codex skill / Crush rule / AGENTS rule
- task routing heuristic -> `agent-dispatch` classifier

### 6. Quality Gates

Every extracted workflow needs:

- source session/task IDs
- positive evidence, not just model summary
- a named failure mode or clear trigger
- bounded verification command
- confidence and support count
- stale policy: lower confidence if not verified recently

Bad candidates should be rejected when they:

- include secrets or raw logs
- describe one-off user-specific text as a general rule
- contradict `SYSTEM_MAP.md`, `FAILURE_BLACKLIST.md`, or a current runbook
- recommend a previously blacklisted path
- lack a reproducible verification step

### Goose/Aider Failure Notes

- Goose can select `read_image` for Markdown paths when prompts say “Read
  `<path>`”. The Goose/Aider router must label required context as text and
  explicitly require a shell/text reader. It now embeds short text excerpts in
  the diagnosis prompt, so the model does not need to select a reader for its
  mandatory policy context; further reads must use bounded shell commands.
- A final contract line is not the last output line. Parse completion with a
  line-bound pattern such as `^STATUS:[ \t]*READY[ \t]*$`, not a pattern that
  assumes end-of-document after `READY`. Goose headless output can concatenate
  a tool result that lacks a final newline with `STATUS`; the router therefore
  has a narrow `STATUS:` fallback for that renderer artifact.
- A home-directory diagnosis without a named repository, file, service, or
  other concrete target must return `STATUS: UNCLEAR`; it must not scan the
  entire home directory trying to infer the target.
- A read-only diagnosis has a three-tool-call budget. Once direct evidence
  answers the question, Goose must return its contract immediately instead of
  expanding inspection scope.

### 7. Minimal Rollout

Phase 1: Read-only foundation

- Done. `workflow-intel` supports `capture`, `extract`, `recall`, `audit`,
  `status`, `maintain`, and `publish --dry-run`.
- Done. It ingests OpenCode lifecycle journal, agent-dispatch tasks, Crush eval
  reports, Codex history, and verified blacklist seed workflows.
- Done. Durable publishing is still dry-run only.

Phase 2: Recall integration and non-OP immediate capture

- Done for OpenCode: bounded `workflow-intel recall` is added to lifecycle
  pre-context as `workflow_hits`.
- Done for Codex and Crush capture: file-event path units trigger capture when
  Codex history or Crush eval changes.
- Add a Crush pre-task rule/wrapper.
- Add a Codex skill or AGENTS rule for workflow/system tasks.

Phase 3: Publishing

- Add `workflow-intel publish --dry-run` to propose runbook/skill/script/button
  updates.
- Require manual or high-confidence approval before durable writes.
- Validate changed skills/runbooks/scripts before completion.

Phase 4: Control-plane visibility

- Expose `workflow-intel audit` in Hub `:9800` and Mobile AI Workbench
  `:19888`.
- Show top workflows, new candidates, rejected candidates, stale workflows, and
  executor-specific drift.

## Verification

Baseline checks before implementation:

```bash
~/.local/bin/opencode-lifecycle.py status
~/.local/bin/agent-dispatch list
~/.local/bin/crush-session-eval --limit 10
~/.local/bin/ai-a2a status --limit 10
```

After implementation:

```bash
workflow-intel audit
workflow-intel recall 'op任务停止了，检查18910和4097并修复'
workflow-intel recall 'codex webtty iOS 输入重复'
workflow-intel publish --dry-run
systemctl --user is-active workflow-intel-maintain.timer
systemctl --user is-active workflow-intel-codex-capture.path workflow-intel-crush-capture.path
~/.local/bin/opencode-lifecycle.py recall 'op任务停止了，检查18910和4097并修复' | rg 'workflow_hits'
agent-goose-aider-router diagnose --workspace ~/termhive '只读诊断一个任务，不要修改文件'
agent-goose-aider-router status latest
# Aider is only authorized after explicit files are listed:
agent-goose-aider-router apply <task-id> src/example.ts
```

## Non-Goals

- Do not let agents silently rewrite all runbooks after every task.
- Do not store full transcripts as workflow memory.
- Do not use vector recall alone for procedural safety. Workflow recall must
  include exact triggers, steps, avoid rules, and verification evidence.
- Do not replace CodeGraph. Workflow Intelligence should complement CodeGraph:
  CodeGraph answers "where is code and what calls what"; Workflow Intelligence
  answers "what sequence worked before, why, and how to verify it."

## Phone GUI Flow Source

2026-07-19: `phone-flow` is the default capture wrapper for foreground Android GUI workflows. It records events to:

- `~/memory/workflows/phone-events.jsonl` with schema `phone-flow-event-v1`
- `~/memory/workflows/events.jsonl` with source `phone-flow`
- n8n webhook `POST http://127.0.0.1:5678/webhook/phone-flow-event`

Seeded workflow id: `phone-alipay-luckin-smart-order`. Use `phone-flow recall '<query>'` before repeating phone ordering flows. Payment, authorization, agreement, SMS, phone-number, and order-submit steps are sensitive and must stop for user confirmation.
