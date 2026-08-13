# Local Agent Bootstrap

Use this as standing context for local agents. It is deliberately short; load
the mapped source files for the current task instead of carrying all history.

## Required checks for system and AI-tool tasks

Before investigating Codex, Aider, Goose/Guise, WebTTY, OpenCode, networking,
input, or desktop behavior, read in this order:

1. `~/.ai-context/SYSTEM_MAP.md`
2. `~/.ai-context/FAILURE_BLACKLIST.md`
3. The relevant `~/.ai-context/runbooks/*.md`
4. `~/.claude/projects/-home-charlie/memory/router-infra.md`

For WebTTY input problems, check iOS/WebKit input, IME composition, repeated
key events, autocorrect, hardware-keyboard repeat, and websocket replay before
changing the terminal backend.

## Operating contract

- State the target workspace, files/services, and intended verification before
  changing anything.
- Prefer targeted reads and bounded logs. Do not scan the whole home directory.
- Treat remembered chat/session content as hints, not authority; current maps,
  runbooks, and service state win.
- Do not write secrets into task output, runbooks, or memory.
- Finish with `STATUS`, `SCOPE`, `CHANGES`, `VERIFY`, and `NEXT`.

## Delegation boundary

- Goose is the diagnosis/research executor and is read-only by default.
- Aider is the only editor in a delegated task, and only receives files named
  in the task dossier.
- Never recursively delegate between agents. Escalate uncertainty to the user.
- A learned rule is only durable after a verified result and explicit review;
  record it as `symptom -> check -> fix -> verification` in the appropriate
  runbook or workflow record.
