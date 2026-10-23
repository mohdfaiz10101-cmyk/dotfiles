# Hermes Local Hook Policy

## Protected scopes
- `~/.hermes/profiles/*/skills`, `plugins`, `cron`, `memories`: block unless explicitly approved.
- Hermes Studio task/session state: block mass rewrite/delete unless explicitly user-requested.
- Phone ADB authorization: block `adb disconnect` against known devices.
- Destructive shell patterns: block obvious recursive delete, disk formatting, chmod 777, curl|sh.

## Hook phases
- `pre-task`: route memory/workflow/skill hints.
- `pre-tool`: detect dangerous commands or writes before execution.
- `post-tool`: suggest verification after writes/services/builds/network changes.
- `quality-exit`: ensure final answer has result/evidence/next-step and decide whether post-task evolve is needed.

## Approval override
Pass `--allow-risk` only after explicit user instruction for that exact action.
