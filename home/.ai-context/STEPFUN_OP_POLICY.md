# StepFun OP Policy

Source of truth for OpenCode model behavior and verification when StepFun or
Step Router models are active.

## Model Roles

- `step-router-v1`: orchestration and fallback only. Use it to decide task
  shape, delegate, and recover from model/provider failures. Do not use it as
  the default OP execution model or the only verifier because it may route
  between engines with different field constraints and has been observed
  returning HTTP 200 with empty `content`.
- `step-3.7-flash`: high-difficulty agent work, multimodal/UI/screenshot
  reasoning, architecture, code review, and tasks where one complete pass is
  better than many cheap retries. Use medium by default and high for complex
  planning, code analysis, math, or root-cause work.
- `step-3.5-flash-2603`: high-frequency coding and agent execution. Prefer it
  for build/refactor/explore tasks where reliable tool calls and token
  efficiency matter. Use low only for extraction/summarization; use high for
  non-trivial debugging and code changes.
- `step-3.5-flash`: stable fallback for text reasoning and tool use when 2603
  or 3.7 is unavailable.

## Hard Routing

- `sisyphus`: main controller only. It plans, delegates, compares evidence,
  and decides whether acceptance is PASS/UNCLEAR/FAIL. It does not directly
  mutate source code or perform device/message write actions.
- `build`: implementation, fixes, config changes, and focused tests.
- `explore`: code/location/call-chain discovery and evidence gathering.
- `refactor`: behavior-preserving changes, impact analysis, and API boundary
  changes.
- `arch`: architecture, root-cause analysis, self-healing loops, lifecycle
  design, cross-component decisions, and high-risk system plans.
- `tech-researcher`: web/UI/browser/vision/page-state investigation.
- `ops-dispatcher`: devices, Haven, phones, tablets, Windows, and external
  operation dispatch.
- `telegram-operator`: Telegram operations only after explicit user intent.
- `router-auditor`: use `step-router-v1` only after failure or uncertainty for
  second opinion, rerouting advice, and DeepSeek/Step cross-check. It must not
  directly mutate code, operate devices/messages, or provide final PASS.

## Execution Rules

- Before tool use, state the observable target and the expected evidence.
- Prefer one precise probe over broad searching. For code tasks use CodeGraph
  list/find/relationships before broad text search.
- If a tool call fails twice with the same fingerprint, stop repeating it.
  Change transport, scope, model, or verification method.
- After repeated failure, verification `FAIL`/`UNCLEAR`, or model-output
  anomaly, `router-auditor` may participate. Its output is advisory: it should
  name the likely failure signal, next agent, next model, and minimum evidence
  needed. Execution then returns to the appropriate direct model agent.
- If `step-router-v1` returns empty `content` twice, stop using router for
  that task. Switch to direct `step-3.7-flash` for reasoning/root-cause work or
  `step-3.5-flash-2603` for coding/tool execution.
- For disabled/on-demand MCPs, call `mcp-broker` plan/probe first. Do not claim
  a disabled MCP is available.
- For UI/visual work, use Step 3.7 native multimodal when the image is already
  in the model context; otherwise use vision MCP through broker.

## Completion Rules

- Non-trivial tasks cannot finish with only a summary. They must include
  acceptance evidence: command output, endpoint status, screenshot/DOM check,
  service state, test result, or a reason the check could not be run.
- Mark result `PASS` only when the acceptance evidence directly tests the user
  request. Use `UNCLEAR` when only indirect evidence exists.
- After completion, produce a concise self-review: changed surface, checks run,
  remaining risk, and what should be remembered next time.
