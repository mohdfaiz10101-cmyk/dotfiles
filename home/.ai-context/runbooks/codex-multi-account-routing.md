# Runbook: Codex Multi-Account Routing

Codex 三账号并行、互补和省钱路由规划。

## Current State

- Account 1: `CODEX_HOME=~/.codex`, tmux socket `/run/user/1000/tmux/codex.sock`, session `haven-codex`, Haven/WebTTY entry `2225` / `19899`.
- Account 2: `CODEX_HOME=~/.codex-2`, tmux socket `/run/user/1000/tmux/codex2.sock`, session `haven-codex2`, Haven/WebTTY entry `2226` / `19900`.
- Account 3: `CODEX_HOME=~/.codex-3`, tmux socket `/run/user/1000/tmux/codex3.sock`, session `haven-codex3`, Haven/WebTTY entry `2229` / `19902`.
- Account 4: `CODEX_HOME=~/.codex-4`, tmux socket `/run/user/1000/tmux/codex4.sock`, session `haven-codex4`, WebTTY entry `19903`, Sub2API key `codex4-sub2api` bound to group `openai-codex-4` / `group_id=14`. Account 14 is the primary upstream; account 10 is present in group 14 as a temporary fallback while account 14 is unhealthy.
- Account provisioning is script-owned. Use `~/.local/bin/codex-account-provision` or the WebTTY `生成4` button; do not repeat the old manual sequence of editing Sub2API groups, API keys, Codex auth/config/env files, and restarting ttyd by hand. With `--restart`, the script also detects stale tmux pane process API keys and recreates the session before service restart.
- Authentication, installation id, history, SQLite state, logs, cache, and shell snapshots must remain account-local.
- Shared config, skills, AGENTS.md, `~/.ai-context`, `~/memory`, and MCP definitions may be shared through the existing sync path.
- Account 2 has already added the token-safety baseline:
  - `~/.config/codex-shell-env/env.sh`
  - `~/.local/bin/codex-token-safe-run`
  - `~/.local/bin/codex-resume-or-new`
  - Haven/WebTTY Codex entries exporting `BASH_ENV`, `ENV`, and `ZDOTDIR`
  - default model lowered to `gpt-5.5` with `model_reasoning_effort="low"`

## Operating Model

Use the accounts as a dynamic resource pool. Do not permanently bind account
identity to roles such as coordinator, implementer, or reviewer, because quota,
rate limits, provider health, account risk, and active context differ over time.

Each task receives a temporary lease:

- `owner`: the account currently responsible for user-facing progress.
- `worker`: any available account assigned a bounded implementation or research subtask.
- `reviewer`: any available account assigned read-only validation.
- `fallback`: the next account allowed to continue if the owner hits quota, errors, or becomes risky.

Lease selection must be recalculated at task start and at phase boundaries. Any
of the three accounts can be owner, worker, reviewer, or fallback if its current
health and quota are suitable.

Selection inputs:

- 5-hour remaining quota, if available.
- 7-day remaining quota, if available.
- API/sub2api trusted usage state, if applicable.
- active task state in tmux/WebTTY.
- whether the account already carries useful context for the current task.
- recent usage-limit or provider-error messages.
- account-risk cooldown, described below.

2026-07-12 example from `/quota.json`:

- Account 1 Plus: 5h used 100%, 7d used 67%; not a good owner until 5h reset, but can resume after reset because it has native Plus context.
- Account 2 Team: 5h used 100%, 7d used 16%; better long-window reserve than Account 1, but currently also blocked by 5h quota.
- Account 3 API: official 5h/7d fields unavailable; use sub2api trusted usage and provider health instead of guessing official quota.

When a window is exhausted, do not keep prompting that account. Move the lease
or wait for reset.

## Conflict Rules

- Never let two accounts edit the same file class at the same time.
- Shared config must have a temporary lease owner, not a permanent account owner:
  - `~/.codex/config.toml`, `~/.codex-*/config.toml`: one active lease owner only.
  - `~/.local/bin/codex-*`, `~/.config/codex-shell-env/*`: one active lease owner only.
  - `~/.local/share/ttyd-codex/*` and WebTTY UI: one active lease owner only.
  - `~/.ai-context/runbooks/*`: one active lease owner only.
- Repo code changes should use worktree or file-level ownership:
  - owner account: main workspace and final merge.
  - worker account: one bounded module or one dedicated worktree.
  - reviewer account: read-only unless explicitly assigned a separate worktree.
- If two accounts need the same repository, create separate worktrees under `/var/mnt/ai/cache/codex-worktrees/`.
- Before editing shared files, an account must inspect current file contents and recent tmux state for the other accounts.

Lease handoff rule:

- The old owner records current state, touched files, verification status, and
  next command in `~/memory/codex-routing-ledger.jsonl`.
- The new owner reads that ledger entry and the latest pane capture before
  continuing.
- Do not hand off by copying account-local `auth.json`, session database, cache,
  or logs into another `CODEX_HOME`.

## Cost Routing Policy

Do not do frequent hot model switching inside one long coding session. It tends to lose prompt-cache benefits and repeats large context. Route at task start, then escalate only at phase boundaries.

Default route chooses both a route class and an account lease.

- `fast`: reading, grep/search, small explanations, status checks, runbook lookups.
  - Model target: cheap/low effort.
  - Account target: healthiest available account; prefer one with low active context cost and enough quota.
- `standard`: normal code edits, single-module fixes, focused tests.
  - Model target: `gpt-5.5`, low or medium effort.
  - Account target: account with enough 5h quota and no active conflicting file lease.
- `deep`: cross-module refactor, persistent test failures, architecture decisions, security-sensitive changes, unclear root cause after one failed pass.
  - Model target: strongest available model or higher reasoning effort.
  - Account target: account with best quota/risk balance; add a separate reviewer lease if possible.

Account selection score:

- Hard block if current pane shows usage-limit, auth error, provider error, or
  repeated request failure.
- Hard block if account has an active lease on a different high-risk task.
- Prefer higher 5h remaining for interactive coding.
- Prefer higher 7d remaining for large multi-hour work.
- Prefer API/sub2api for batch, tests, and retry-heavy tasks when trusted usage
  data is available.
- Prefer native Plus/Team accounts for tasks that benefit from official Codex
  TUI behavior and prompt cache, if their quota is healthy.
- Prefer continuing on the same account when it already has useful context and
  quota is not constrained.

Account-risk cooldown:

- If an account hits usage limit, mark it unavailable until the reported reset.
- If an account shows auth/provider errors, mark it degraded until one clean
  health check passes.
- If an account has many failed or repeated prompts, reduce priority for new
  deep tasks.
- Do not route around limits by hammering all accounts with the same prompt.

Escalation triggers:

- Same failure repeats twice.
- More than three files need behavioral changes.
- Tests fail after one targeted fix.
- The task touches auth, secrets, routing, phone/Haven, systemd, SSH, router, or shared Codex config.
- The model starts broad-searching or producing large unbounded output.

De-escalation triggers:

- Task is pure lookup, summarization, command output compression, or one-line config verification.
- The next step is mechanical validation already specified by a runbook.
- A stronger account/model produced a plan and only execution remains.

## Router Shape

Current SSH entry:

- Use `codex-smart "task"` as the no-button command-line router.
- Use `codex-smart --status` to inspect account health.
- Use `codex-smart --dry-run "task"` to preview route/account/model without spending model tokens.
- Use `codex-smart --send "task"` only when deliberately sending into the selected interactive tmux pane. This uses that pane's currently running model; it does not hot-switch an already running TUI model.
- `codex-smart` is now a thin compatibility wrapper around `codex-router`; router owns task classification, account selection, explicit model parsing, model choice, and reasoning effort. Default `codex-smart "task"` submits through `codex-router` with `wait=true`.
- Explicit model names in task text (`gpt-5.6-sol`, `gpt-5.5`, `gpt-5.4`) override the route default in both `codex-router` and `codex-smart`. Explicit effort words (`high`/`medium`/`low`, `高`/`中`/`低`) override effort; `gpt-5.6-sol` defaults to high effort when no effort is specified.
- Tested 2026-07-12: with Account 1/2 5h quota exhausted, `codex-smart --exec --route fast '只回复 OK，不要运行命令，不要解释。'` selected Account 3, launched `gpt-5.5` with `reasoning effort: low` via `sub2api`, and returned `OK`.

Phase 1: manual router.

- Add explicit commands:
  - `codex-fast`: cheap route for lookup and explanation.
  - `codex-standard`: normal implementation route.
  - `codex-deep`: high-reasoning route.
  - `codex-smart`: thin CLI/WebTTY compatibility wrapper over `codex-router`;
    do not add a second classifier or model chooser there.
- Keep current token-safe command wrappers in all routes.
- Do not restart live tmux sessions automatically. Apply to new sessions first.

Phase 2: task ledger.

- Add a small ledger under `~/memory/codex-routing-ledger.jsonl`.
- Record:
  - task id
  - owner account
  - worker/reviewer/fallback accounts
  - route
  - files claimed
  - quota snapshot
  - risk/cooldown state
  - start/end status
  - verification command
- Refuse or warn when another live account claims the same file.

Phase 3: WebTTY integration.

- Implemented 2026-07-13 in `~/.local/bin/ttyd-device-gate-proxy`:
  - `/smart/status` calls `codex-smart --status`.
  - `/smart/decide` calls `codex-smart --dry-run`.
  - `/smart/send` calls `codex-smart --send`.
  - `/smart/exec` calls `codex-smart --exec`.
  - `/smart/*` is retained only as a compatibility API for older callers; the
    visible WebTTY UI must expose a single Router panel, not a separate
    `0 Smart` panel.
  - Account `1/2/3` clicks are captured and rendered as same-page iframe tabs
    at z-index `2147483646`, so switching does not navigate away from the
    current terminal page.
  - Account 4 Sub2API setup defaults to `group_id=14` (`openai-codex-4`);
    do not reuse `group_id=3`, because that makes Codex 3 and Codex 4 compete
    for the same upstream account pool.
  - The `生成4` button calls `/smart/setup-account4`, which wraps
    `~/.local/bin/codex-account-provision --account 4 --primary-account-id 14
    --fallback-account-id 10 --restart --health-check --json`.
  - If account 4 shows `401 Unauthorized` with `API_KEY_DISABLED`, distinguish
    WebTTY/device-gate auth from Sub2API/model auth. A healthy page on `19003`
    can still have a stale Codex process environment. Check the pane pid from
    `/run/user/1000/tmux/codex4.sock` and compare `/proc/$PID/environ`
    `OPENAI_API_KEY` with the active `codex4-sub2api` key preview/hash. Rerun
    the provision command above so stale tmux sessions are killed and
    `/v1/responses` is health-checked.
  - Browser-level check on `19000`: clicking account `2` kept top-level
    `location.href` on `http://127.0.0.1:19000/`, created one iframe, and made
    account `2` visible.
  - Implemented 2026-07-13: each top-level Codex WebTTY page exposes
    `/model` and `/model/switch`. The visible compact dock is a right-side
    vertical bar with quick buttons for `gpt-5.4` and `gpt-5.5-mini`; switching
    writes the current account `config.toml`, archives the current screen, and
    restarts the account tmux session only after browser confirmation.
- Add route buttons to `/sessions` or the Codex task manager:
  - `Fast`
  - `Standard`
  - `Deep`
  - `Review`
- Show live ownership and claimed files beside each account.
- Use existing `/quota.json` and `/sessions.json` data to prefer the healthiest
  account and to avoid accounts currently capped, busy, or degraded.

Phase 4: bounded automatic escalation.

- Keep hot switching conservative:
  - no mid-turn model swap;
  - no automatic restart of live Codex panes;
  - escalation creates a new task handoff or asks the coordinator to resume with a stronger profile.
- Use the router classifier only for new tasks or explicit `codex-smart` launches.

## Implementation Tasks

1. Preserve Account 2's token-safety work.
   - Verify `env.sh` syntax.
   - Verify `codex-token-safe-run` clamps noisy commands.
   - Keep `codegraphcontext update /var/home/charlie` blocked.

2. Add route profiles.
   - Create `fast.config.toml`, `standard.config.toml`, and `deep.config.toml` for each `CODEX_HOME`.
   - Keep auth and provider details account-local.
   - Share only common policy text and MCP definitions.

3. Maintain `codex-smart` as a wrapper.
   - Do not duplicate deterministic keyword rules, explicit model parsing, or account scoring in `codex-smart`.
   - Add new routing policy to `codex-router` first.
   - Keep `codex-smart --send` as tmux paste only; it cannot hot-switch the running TUI model.
   - If all suitable accounts are capped, report reset times instead of forcing retries.

4. Add conflict ledger.
   - Start with advisory warnings, not hard locks.
   - Store ledger in shared memory.
   - Make entries expire or close when the pane/task completes.

5. Add verification.
   - `bash -n` for all wrappers.
   - TOML parse for all profile configs.
   - Dry-run classification examples:
     - "查一下日志为什么失败" -> fast
     - "修复这个单文件 bug 并跑测试" -> standard
     - "重构 Haven/Codex 多账号入口避免冲突" -> deep

6. Provision or repair API-backed Codex accounts with the script.
   - Example:
     `~/.local/bin/codex-account-provision --account 4 --primary-account-id 14 --fallback-account-id 10 --restart --health-check --json`
   - The script creates/repairs the `openai-codex-N` group, `codexN-sub2api`
     key, `~/.codex-N/auth.json`, `~/.codex-N/config.toml`,
     `~/.config/codexN-sub2api.env`, service restart, and a tiny responses
     health check.

## Non-Goals

- Do not implement continuous in-session hot model switching first.
- Do not share account auth files.
- Do not permanently assign one account to one role.
- Do not treat unknown quota as unlimited quota.
- Do not route the same failing prompt through all accounts to bypass rate limits.
- Do not enable heavy MCPs globally just to make routing easier.
- Do not auto-restart existing Haven/WebTTY tmux sessions while user tasks are running.
