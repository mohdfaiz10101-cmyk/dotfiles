# Hermes MCP Quality

Last updated: 2026-08-10

## Default rule

- Keep Hermes default MCP profile small: `fetch` and `agent-comms`.
- Keep profile configs aligned: `~/.hermes/config.yaml`,
  `~/.hermes/profiles/dispatcher/config.yaml`, and
  `~/.hermes/profiles/secondary/config.yaml` must all use
  `web.search_backend: fetch`, `web.extract_backend: fetch`, and the same
  light default MCP set unless an explicit task profile is being launched.
- Do not keep device/UI/heavy/external-write MCPs enabled by default.
- Use `~/.local/bin/mcp-profile-manager.py doctor` before changing MCP state.
- Use `~/.local/bin/mcp-profile-manager.py auto '<task text>'` to predict the needed profile.
- Use `~/.local/bin/hermes-search-health` to verify search config, proxy/DNS,
  and web fallback health before blaming Hermes tools.

## Profiles

- `lite` / `standard`: `fetch`, `agent-comms`.
- `ops`: adds `sys-info` through `sys-info-mcp-wrapper.sh`.
- `mobile`: adds `phone-connect` and `mobile-browser-bridge`.
- `haven`: explicit Haven MCP/SSH debugging only.
- `memory`: `memory-engine`; `memory-deep`: `memory-engine` plus `letta`.
- `research-deep`: `firecrawl` only for explicit crawl/deep web tasks.
- `windows`: `win` only for explicit Windows tasks.

## Known failure modes

- `sys-info-mcp.py` is a single-instance Streamable HTTP service on
  `127.0.0.1:18095`; clients must use
  `~/.local/bin/sys-info-mcp-wrapper.sh`, not start the Python server directly.
- `haven-mcp-bridge.service` is disabled and should not be kept always-on.
  `haven-mcp-wrapper.sh` may start it only for explicit Haven tasks.
- Do not treat `Transport closed` as a server bug until checking duplicate or
  stale MCP processes.
- `mcp-orphan-killer.sh --dry-run` is the first cleanup step. Do not kill MCP
  processes that still have a live `codex` or `opencode` ancestor.
- `firecrawl` must remain disabled unless its API key is known-good. Search
  should use `fetch` as baseline; deep crawl uses `research-deep` only.
- Do not search Hermes session dumps or config backups for routine MCP/search
  diagnosis. Use `hermes-search-health`, exact config files, and MCP logs.

## Verification

```bash
python3 ~/.local/bin/mcp-profile-manager.py doctor
~/.local/bin/hermes-search-health
python3 ~/.local/bin/mcp-profile-manager.py auto '手机 adb netbird 网络不稳定'
python3 ~/.local/bin/hermes-session-mesh route --task '记忆冲突 以前做过的任务召回'
systemctl --user is-active haven-mcp-bridge.service
```
