# Task Profiles

Profiles are selected by keyword matching in `opencode-lifecycle.py pre()`.
Each profile limits injected context to its `max_chars` budget and prioritizes
its `runbook_refs`.

| Profile | Keywords (partial) | Runbook Refs | Max Chars |
|---------|-------------------|--------------|-----------|
| `opencode_core` | opencode, codex, memory, mcp, session, 18910, 4097, proxy, lifecycle | opencode-core.md, ai-infra.md | 800 |
| `phone_network` | 手机, adb, 无线调试, tailscale, 5g, 公网, frp, haven, iphone | haven.md, frp.md, duckdns.md | 800 |
| `frontend_verification` | 前端, 界面, ui, css, tsx, jsx, browser, 截图, __oc-fast | opencode-core.md | 600 |
| `deployment` | systemctl, service, 服务, 端口, port, health, gateway, telegram, timer | opencode-core.md, ai-infra.md, frp.md | 700 |
| `code_change` | 代码, 源码, 函数, 测试, lint, build, typescript, python, repo | opencode-core.md, codegraph.md | 600 |
| `default` | (fallback) | opencode-core.md | 400 |

## Selection Rules

- Multiple profiles can match; all are recorded in the `profiles:` header line.
- Profile runbook refs are injected first, then generic `relevant_runbooks()` hits fill remaining budget.
- Already-injected context is deduplicated by context hash; profiles do not cause duplicate injection.
- Profile selection is recorded in `~/.local/state/opencode-lifecycle/<session_id>.json`.
