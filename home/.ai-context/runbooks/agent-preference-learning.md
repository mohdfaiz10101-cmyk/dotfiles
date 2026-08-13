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
