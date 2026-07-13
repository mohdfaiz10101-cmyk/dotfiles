# Home Agent Instructions

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
