# Home Agent Instructions

For all Codex accounts and sessions:

1. Always reply to the user in Simplified Chinese, even when the user writes in another language.
2. Keep code, commands, file paths, identifiers, logs, quoted text, and user-requested foreign-language artifacts in their required original language.
3. Only use another human language in the conversational reply when the user explicitly asks for that specific output language for that turn.

Expert reply mode for all Codex accounts and sessions:

1. Act like a senior expert: fast, practical, concise, and action-first.
2. Start with the direct answer or best recommendation.
3. Prefer bullet points, short checklists, exact commands, exact file paths, and clear next steps.
4. Avoid long theory, repeated caveats, generic explanations, and large raw logs unless explicitly requested.
5. Ask at most one concise clarification question only when truly blocked; otherwise make a reasonable assumption and continue.
6. For code, system, networking, desktop, or account tasks: inspect targeted context first, use the smallest sufficient scope, make safe changes, and verify.
7. Final answers should be short: what changed, decisive evidence, and the next useful step.
8. Escalate detail, planning, or reasoning only when the task is risky, ambiguous, or complex.

Before investigating system, OpenCode, Codex, networking, port forwarding, input, or desktop issues, read:

1. `~/.ai-context/SYSTEM_MAP.md`
2. `~/.ai-context/FAILURE_BLACKLIST.md`
3. Relevant `~/.ai-context/runbooks/*.md`
4. `~/.claude/projects/-home-charlie/memory/router-infra.md`

Use these files as the first source of truth. Avoid broad filesystem searches until the mapped checks are exhausted.

For Codex web TTY, OpenCode web TTY, browser terminal, or similar input surfaces:

1. Always check for iOS input-layer issues early, especially repeated characters, duplicated submissions, delayed composition, stuck keys, or input lag.
2. Treat iOS Safari/WebKit, IME/composition events, mobile autocorrect, hardware keyboard repeat, and websocket/event replay as likely causes before assuming the terminal backend is at fault.
3. When reproducing, compare iOS touch keyboard, iOS hardware keyboard if available, and a non-iOS desktop browser.

For Android phone / ADB operations:

1. Prefer `~/.local/bin/adb-record --tag <short-task> -- <adb args...>` instead of raw `adb` for diagnostic or configuration commands, so each operation is logged for later learning.
2. The log is `~/.local/state/adb-ops/history.jsonl`; it stores timestamp, cwd, serial, redacted command, return code, elapsed time, bounded stdout/stderr tails, and hashes.
3. Do not put secrets in `--note` or commands. The wrapper redacts common token/password patterns, but agents must still avoid dumping credentials, private keys, Mattermost tokens, setup keys, or full app databases into logs.
4. Use raw `adb` only for interactive/streaming operations where wrapping would break behavior, and record the summary/fix in the relevant runbook afterward.

For Fedora Silverblue package installs:

1. Never use `rpm ostree`; the command is `rpm-ostree`.
2. Do not default to bare `rpm-ostree install` for new packages.
3. For ordinary new layered packages, use `rpmi <package...>` by default. It wraps `rpm-ostree install --apply-live --idempotent -y` so packages are applied live when rpm-ostree supports it.
4. Use bare `rpm-ostree install`, `rpm-ostree uninstall`, `rpm-ostree upgrade`, or `rpm-ostree rebase` only when `rpmi` is not applicable or has failed, and tell the user when a reboot is still required.
5. Prefer Flatpak for GUI apps and toolbox/distrobox/container installs for development tools before adding more rpm-ostree layered packages.

For source-code tasks:

1. Call CodeGraphContext `list_indexed_repositories` first.
2. Use `find_code` to locate symbols and `analyze_code_relationships` for callers, callees, inheritance, and impact.
3. Use `rg` only when the repository is not indexed, the graph has no result, or exact text/config search is required.
4. Do not repeat a failed approach before checking `~/.ai-context/FAILURE_BLACKLIST.md` and memory MCP.
5. After structural code changes, refresh the repository with CodeGraphContext before declaring completion.

For app/program/APK changes:

1. After changing a running web/app program, build or typecheck first, then restart/reload the smallest relevant service so the user can see the result immediately.
2. After changing an Android APK, rebuild and install/overwrite it on the target device when ADB or the project install script is available; then restart or bring the app/IME/service to the foreground when safe.
3. If automatic restart/install is unsafe or unavailable, state the exact blocker and give the one command or tap action needed.
4. Do not claim UI completion from source changes alone; include the build/restart/install evidence in the final answer.

For token, context, and latency efficiency:

1. Prefer the smallest sufficient read scope: exact files, exact symbols, exact services, exact journals.
2. Never run `codegraphcontext update /var/home/charlie` or any other home-wide/global refresh.
3. Only refresh a specific indexed repository, and bound it: `timeout 120s codegraphcontext update /absolute/repo`.
4. Before any CodeGraph refresh, try `codegraphcontext list`, `codegraphcontext stats`, `find`, or `analyze`; do not block on refresh if lookup already works.
5. For home-directory tasks, scripts, systemd units, WebTTY, router, Haven, FRP, or config work, prefer targeted file reads and `rg`; do not invoke CodeGraph unless the task is actually repository code structure work.
6. Do not broad-search noisy trees unless the task explicitly requires them: `~/memory`, `~/timeline`, `~/Games`, browser profiles, caches, app data, backups, swapfiles, container overlays, large generated exports.
7. Prefer bounded command output. Examples: `journalctl --no-pager | tail -n 120`, quiet test mode, `git diff --stat` before full diff, and first-failure test runs before full suites.
8. When a command may produce large output, use `~/.local/bin/codex-token-safe-run ...` or an equivalent bounded wrapper first.
9. Do not paste large raw logs or repeated command output into final answers; summarize key evidence and quote only the decisive lines.

For task-end skill and workflow evolution:

1. Before finalizing a task, automatically check whether the work revealed a repeatable workflow, new failure mode, changed rule, button-worthy action, or reusable script/skill opportunity.
2. If the improvement is clear and low-risk, update the smallest durable artifact immediately: an existing skill, runbook, local helper script, WebTTY button/API endpoint, or `AGENTS.md` rule.
3. Prefer scripts/buttons for fragile multi-step operations; prefer skills for when future Codex agents need procedural knowledge; prefer runbooks for topology, ports, services, and operational checks.
4. Do not store secrets in skills, runbooks, or final answers. Store only paths, key names, previews, non-secret ids, commands, and verification steps.
5. Validate changed skills with the skill validator and validate changed scripts with syntax checks or a bounded health check before declaring completion.

For preference learning and decision scoring:

1. For every non-trivial task step, user correction, explicit preference, design decision, and final outcome, record a concise event with:
   `~/.local/bin/agent-preference-record`.
2. Use positive scores for preferences the user requests or reinforces; use negative scores for patterns the user corrects or rejects.
3. Default scoring:
   - `+1` user likes/requests/reinforces a behavior
   - `-1` user corrects/rejects a behavior
   - `+0.2` successful implementation evidence
   - `-0.2` weak/failed implementation evidence
4. Read `~/.ai-context/runbooks/agent-preference-learning.md` and
   `~/.local/state/agent-preferences/scores.json` before design-heavy,
   workflow-heavy, or repeated personal-preference tasks.
5. Do not store secrets or full private content in preference records. Store only stable preferences, rejected patterns, paths, non-secret ids, and short reasons.

For Codex account, Sub2API, claim-code, quota, routing, and WebTTY account operations:

1. Treat these as durable operational knowledge, not one-off fixes.
2. After any confirmed account-related change, update the smallest durable artifact that future agents will actually read:
   - `~/.codex/skills/codex-account-ops/SKILL.md` for reusable procedures
   - `~/.ai-context/runbooks/codex-multi-account-routing.md` for topology, bindings, failure history, and verification
   - `AGENTS.md` only when the rule is broad and should apply to all future account work
3. “Account-related” includes at least:
   - upstream account replacement or rotation
   - claim-code redeem / lookup / historical download flows
   - Sub2API group or API-key rebinding
   - fallback/independence rules between slots
   - quota/reset-time behavior and UI exposure
   - account labels, slot mapping, and WebTTY account-switch behavior
   - 401/429/502/503 repair paths
4. When a deterministic script exists, record that script as the default path and stop teaching the older manual sequence.
5. For slot `1/2/3` claim-code based upstream replacement, remember that a code showing “已用完” is not automatically invalid; if `lookup` still returns historical `download.json`, that remains a valid rotation source.
6. After any account rotation or rebinding, verify both data plane and UI plane:
   - Sub2API binding points to the intended upstream account
   - slot-local `CODEX_HOME` / env / service state is correct
   - WebTTY `/quota.json` and `/status` reflect the new upstream

For mobile-facing WebTTY/Workbench issues, do not declare health from Fedora/PC checks alone. First classify the path actually used by the phone: USB adb reverse `127.0.0.1:<external-port>`, LAN `192.168.123.71:<external-port>`, NetBird `100.87.238.153:<external-port>`, or DuckDNS/FRP `charlie1990.duckdns.org:<external-port>`. Use ADB phone-side probes and screenshots before finalizing any fix. A local `127.0.0.1:1900x` or Fedora curl result proves only the gate/backend, not phone usability. For Codex WebTTY, `19000-19007` are loopback-only gates; phone paths must use external ports `19899/19900/19902/19903/19904/19905/19906/19907`, or USB reverse to those same external ports. Keep `webtty-usb-reverse-ensure.timer`, `phone-webtty-route-probe.timer`, and `codex-webtty-perf-summary.timer` as the evidence chain.
