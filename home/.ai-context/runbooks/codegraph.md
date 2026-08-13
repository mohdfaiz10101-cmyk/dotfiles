# CodeGraph Runbook

## Agent Lookup Order
1. Call MCP `list_indexed_repositories`.
2. Use `find_code` for definitions and relevant snippets.
3. Use `analyze_code_relationships` for callers, callees, inheritance, and impact.
4. Use `rg` only for exact text/config search or when the graph has no result.
5. Check `~/.ai-context/FAILURE_BLACKLIST.md` before retrying a failed path.

## Local CLI
- Health: `codegraphcontext doctor`
- Repositories: `codegraphcontext list`
- Statistics: `codegraphcontext stats`
- Find symbol: `codegraphcontext find name SYMBOL`
- Fuzzy find: `codegraphcontext find pattern TEXT`
- Callers: `codegraphcontext analyze callers SYMBOL`
- Callees: `codegraphcontext analyze calls SYMBOL`
- Refresh: `codegraphcontext update /absolute/repo/path`
- Initial index: `codegraphcontext index /absolute/repo/path`

## Current Repositories
- `/var/home/charlie/termhive`
- `/var/home/charlie/dotfiles`
- `/var/home/charlie/hub`

## Client Configuration
- OpenCode: `~/.config/opencode/opencode.json`, MCP key `codegraph`
- Codex: `~/.codex/config.toml`, MCP key `codegraph`
- Command: `/var/home/charlie/.local/bin/codegraphcontext mcp start`

## Refresh Policy
- Agents must run `codegraphcontext update REPO` after structural code changes.
- Official Git hooks refresh after commit and checkout.
- Do not run permanent watchers by default; multiple AI clients may access the same embedded database.
- 2026-06-26: If MCP reports `Error 111 connecting to ... falkordb.sock` or `Connection refused`, the graph is usually not corrupt; the embedded FalkorDB/Redis socket is cold or stale. Run `~/.local/bin/opencode-lifecycle.py codegraph-warmup` or `codegraphcontext list` to warm it, then retry MCP `list_indexed_repositories`.
- OpenCode lifecycle integration: `opencode-lifecycle.py status/audit` now reports CodeGraph health and stats; code-task recall includes `codegraph_status`; `opencode-codegraph-warmup.timer` warms the database hourly and on boot without running a permanent file watcher.

## Task Closeout
- There is no guaranteed native post-task auto-write to CodeGraph.
- At task end, first decide whether the work changed indexed source structure, durable workflow, or reusable operational knowledge.
- If yes, update the smallest durable artifact first; if the repo changed, run `codegraphcontext update /absolute/repo/path`.
- If no indexed repo or durable workflow changed, do not force a CodeGraph refresh.
