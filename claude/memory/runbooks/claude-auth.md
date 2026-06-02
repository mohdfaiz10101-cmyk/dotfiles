# Claude Auth Runbook

适用场景:
- `claude` 提示 `can not connect to api`
- `Malformed API Key`
- `claude.ai` OAuth 与本地 API key 冲突

检查步骤:
1. 确认 `~/.local/bin/claude` 指向本机 LiteLLM `http://127.0.0.1:4000`
2. 优先使用 `ANTHROPIC_AUTH_TOKEN`
3. 清空 `ANTHROPIC_API_KEY`
4. 如需 API 模式，移走 `~/.claude/.credentials.json`

验证:
- `claude --help`
- `claude -p 'reply with ok only'`
