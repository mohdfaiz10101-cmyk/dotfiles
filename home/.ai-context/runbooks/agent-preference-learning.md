# Agent Preference Learning Hook

Purpose: record Charlie's operational preferences, design corrections, and decision scores so future agents reuse them.

## Required behavior

For each non-trivial task step, correction, preference, design decision, and final outcome, append a concise event:

```bash
agent-preference-record --event decision --topic <area> --item '<stable preference>' --delta 1 --reason '<why>'
agent-preference-record --event correction --topic <area> --item '<rejected pattern>' --delta -1 --reason '<user correction>'
```

State:

```text
~/.local/state/agent-preferences/events.jsonl
~/.local/state/agent-preferences/scores.json
```

Scoring convention:

- `+1`: user likes/requests/reinforces a behavior.
- `-1`: user corrects/rejects a behavior.
- `+0.2`: successful implementation evidence.
- `-0.2`: weak/failed implementation evidence.

Current FlexIME preferences:

- Prefer home-surface controls over burying primary mode switches in settings.
- Prefer one `页` page switch over separate permanent `中/英/九/全` buttons.
- Programmer mode must be sectioned/adaptive, not a pile of all keys.
- P2P sync must include settings, lexicon, input history, and clipboard.
- AI features should use desktop Step bridge; no provider secrets in APK.
- Future UI/product work must reference local design-reference skill and phone app baselines.

## Task closeout visibility (2026-10-24)

- 用户明确要求：每个任务结束都自动做智能总结和经验提取，并在最终回复中展示，不能只后台落盘。
- 简短呈现：完成结果及验证；提取出的可复用经验/偏好/失败模式；实际更新文件的链接。
- 无新增经验时如实写“本次无新增可复用经验”，不凑数、不重复造文件；未完成必须说明阻塞。
- 规则入口：`~/AGENTS.md` 的 task-end skill and workflow evolution。
