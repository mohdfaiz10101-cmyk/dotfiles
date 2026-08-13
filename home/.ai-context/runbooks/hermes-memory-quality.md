# Runbook: Hermes Memory And Session Quality

## Purpose

Use this before diagnosing Hermes "forgets previous work", starts from zero,
misses skills, or behaves worse after session compression.

## Current Control Points

- Pre-task context hook: `~/.local/bin/hermes-hook-runner`
- Fast memory brief: `~/.local/bin/hermes-memory-brief`
- Workflow memory: `~/.local/bin/workflow-intel`, state under
  `~/memory/workflows/`
- A2A knowledge pipeline: `~/.hermes/a2a/queue/` ->
  `~/.hermes/a2a/knowledge/`
- Session switch audit: `hermes-session-switch-audit.timer`

## First Checks

```bash
~/.local/bin/hermes-memory-brief --json 'current task text'
systemctl --user list-timers a2a-skills.timer workflow-intel-maintain.timer hermes-session-switch-audit.timer --no-pager
cat ~/.local/state/workflow-intel/audit.json
find ~/.hermes/a2a/queue/pending -maxdepth 2 -type f | wc -l
find ~/.hermes/a2a/knowledge -maxdepth 2 -type f -printf '%p %TY-%Tm-%Td %TH:%TM\n'
```

## Known Failure Modes

- Workflow events from Codex can be `codex_history_goal_only` with
  `status=skipped`; this proves the user asked about the task but does not
  contain final tool evidence. Prefer current runbooks/state files over these
  weak workflow hits.
- A2A `pending` proposals are not durable memory. They must be approved and
  synced before treating them as knowledge.
- `a2a-skills.service` must use deterministic summaries. Do not let routine
  skill scanning call Sub2API/StepFun for every changed skill; 503/timeouts make
  memory maintenance slow and unreliable.
- Do not replace `model.default: step-router-v1` unless the user explicitly
  asks. It is the intended router model path.
- Do not broad-search `~/.hermes/profiles/**/node_modules` or LSP caches when
  auditing memory/skills.

## Safe A2A Backlog Drain

```bash
# Preview conservative decisions.
~/.local/bin/a2a-curate-safe --since-days 7 --limit 200

# Apply only high-confidence substantive items, then sync to knowledge.
~/.local/bin/a2a-curate-safe --since-days 7 --limit 200 --apply
python3 ~/.hermes/a2a/scripts/sync.py
```

Do not bulk-approve all pending items. Low-confidence or short proposals should
stay pending for human review.

## Verification

```bash
python3 -m py_compile ~/.local/bin/hermes-memory-brief ~/.local/bin/hermes-hook-runner ~/.local/bin/a2a-curate-safe
~/.local/bin/hermes-hook-runner pre-task --text 'hermes memory skill session test'
systemctl --user show a2a-skills.service -p Environment -p TimeoutStartUSec
```
