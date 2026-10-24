# Runbook: Hermes Memory And Session Quality

## Purpose

Use this before diagnosing Hermes "forgets previous work", starts from zero,
misses skills, or behaves worse after session compression.

## Current Control Points

- Pre-task context hook: `~/.local/bin/hermes-hook-runner`
- Fast memory brief: `~/.local/bin/hermes-memory-brief`
- Workflow memory: `~/.local/bin/workflow-intel`, state under
  `~/memory/workflows/`
- A2A knowledge pipeline: `~/.hermes/a2a/queue/` ->
  `~/.hermes/a2a/knowledge/`
- Session switch audit: `hermes-session-switch-audit.timer`

## First Checks

```bash
~/.local/bin/hermes-memory-brief --json 'current task text'
systemctl --user list-timers a2a-skills.timer workflow-intel-maintain.timer hermes-session-switch-audit.timer --no-pager
cat ~/.local/state/workflow-intel/audit.json
find ~/.hermes/a2a/queue/pending -maxdepth 2 -type f | wc -l
find ~/.hermes/a2a/knowledge -maxdepth 2 -type f -printf '%p %TY-%Tm-%Td %TH:%TM\n'
```

## Known Failure Modes

- Workflow events from Codex can be `codex_history_goal_only` with
  `status=skipped`; this proves the user asked about the task but does not
  contain final tool evidence. Prefer current runbooks/state files over these
  weak workflow hits.
- A2A `pending` proposals are not durable memory. They must be approved and
  synced before treating them as knowledge.
- `a2a-skills.service` must use deterministic summaries. Do not let routine
  skill scanning call Sub2API/StepFun for every changed skill; 503/timeouts make
  memory maintenance slow and unreliable.
- Do not replace `model.default: step-router-v1` unless the user explicitly
  asks. It is the intended router model path.
- Do not broad-search `~/.hermes/profiles/**/node_modules` or LSP caches when
  auditing memory/skills.
- When Hermes appears to ignore compression or rollover threshold tuning, first
  check for duplicate top-level YAML keys in `~/.hermes/config.yaml`. On
  2026-08-28, an earlier `session_mesh` block with higher thresholds was
  overridden by a later full `session_mesh` block still set to
  `rollover_threshold_tokens: 60000` and `rollover_threshold_messages: 70`.
  Keep a single `session_mesh` block and validate the loaded values with
  `python3 -c "import yaml; p=yaml.safe_load(open('/var/home/charlie/.hermes/config.yaml')); print(p['compression']['threshold'], p['session_mesh']['rollover_threshold_tokens'], p['session_mesh']['rollover_threshold_messages'])"`.

## Safe A2A Backlog Drain

```bash
# Preview conservative decisions.
~/.local/bin/a2a-curate-safe --since-days 7 --limit 200

# Apply only high-confidence substantive items, then sync to knowledge.
~/.local/bin/a2a-curate-safe --since-days 7 --limit 200 --apply
python3 ~/.hermes/a2a/scripts/sync.py
```

Do not bulk-approve all pending items. Low-confidence or short proposals should
stay pending for human review.

## Verification

```bash
python3 -m py_compile ~/.local/bin/hermes-memory-brief ~/.local/bin/hermes-hook-runner ~/.local/bin/a2a-curate-safe
~/.local/bin/hermes-hook-runner pre-task --text 'hermes memory skill session test'
systemctl --user show a2a-skills.service -p Environment -p TimeoutStartUSec
```

## Output Density / Layering (2026-10-22)

- Global output rules live in `~/.hermes/SOUL.md`, under `Output contract`.
- Default: concise result only; details appear only on explicit request. Avoid the conflicting wording "summary first, details second", which encourages emitting both.
- Prefer one result sentence and 2-3 useful points; no forced headings, repetitive closing offers, or per-tool narration. Necessary deliverables and material failures must remain visible.
- Back up SOUL.md before editing. Verify with `python3 -c 'from agent.prompt_builder import load_soul_md; s=load_soul_md(); assert "默认只输出「简略版」" in s; print("PASS")'`.
- Loader verification proves instruction loading only. Verify real answer quality separately; do not report it as proven by a string check.
- Apply in a new WebUI session. Do not reset existing conversations or restart shared services just to replace their cached prompts. No WebUI code or port changes are required.
- Session detail endpoint: `/api/session?session_id=<id>`; `/api/session/<id>` returns 404 and `?id=` returns 400.

## Network task quality correction (2026-10-23)
Before continuing session d14ccbbd9ffe or diagnosing phone/DuckDNS/FRP, read
`~/.ai-context/runbooks/hermes-network-evidence.md`. SOUL.md now requires evidence
for causal claims, correct path labeling, and actual phone validation. The pre-task
memory brief prioritizes that file for phone/network queries; no model change or
conversation reset is needed for that retrieval path.

## 2026-10-23 自动容量兜底修复（c016a43ccbca）
- 原curator只整理分隔符并报告大小，没有按SAFE=85%归档；原lifecycle仅首次迁移热文件，后续新写入可能在重生成时丢失。两小时频率也不能阻止任务内连续加满。
- canonical `memory-index.json`完整保存条目；每次lifecycle先导入当前MEMORY/USER新条目再生成热记忆，flock与原子写保护文件；分类库包括archived条目。
- 热MEMORY目标1200、触发线1500、硬上限仍2200。`hermes-memory-capacity.path`每次写后检查，timer每5min兜底，memory工具调用前hook同步整理，memory-brief也检查。未提高2200上限。
- 原curator现在调用同一生命周期；已去掉“锁文件存在就是正在写/删除空锁文件”的判断，避免破坏flock并发安全。
- `hermes-submemory add --category ops --text '经验'`直接写cold；`hermes-submemory search '主题' --limit 5`按需召回，无LLM/联网依赖。
- 真实MemoryStore.add从1169增加到1646后，path自动整理到1105且新条目能从索引/分类库召回；清理陈旧事实后965，预留1235字符。模拟1700字符输入确认无丢失、两次运行幂等。
- 当前脚本：`~/.hermes/memories/scripts/memory-lifecycle.py`、`~/.local/bin/hermes-memory-capacity-guard`、`~/.local/bin/hermes-submemory`。状态`~/.local/state/hermes-memory-capacity/latest.json`。
- 现有会话系统提示快照不会追改；实际memory工具操作会从磁盘重读，pre-tool hook和冷库CLI可即时使用。不要宣称SOUL修改让旧系统提示热更新。

- 分类导出现在标记`state=historical/active`，过时拓扑保留冷库并明确历史状态，避免下次重新当当前事实。
- 最终主记忆965/2200，用户记忆目标<=1000/1375；新增内容和原始记录保存在canonical索引，测试确认原文保留及重复运行幂等。

## 2026-10-24 Codex 经验共享与 Hermes 主动召回

- 路径已核对：`~/.hermes/skills` 指向 `~/.shared-agent/skills`，Codex 的 `skills.lean/wechat-linux-desktop` 指向同一文件。引用更新可共用；共享文件存在不证明模型本轮读过。
- 已发现并修复 `hermes-memory-brief` 分类缺口：微信/WeChat/Weixin 优先匹配 `wechat`，不再被“转发”归入网络。返回 `must_read_first` 现在含本主题技能与 runbook。
- `~/.hermes/SOUL.md` 的 `Shared experience recall` 要求每个非简单执行/排障任务先跑 memory brief 并读取返回文件；微信经验入口已补到共享技能正文及 description。已有配置的自动钩子是 `on_session_start`，不是逐消息 `pre_llm_call`；不能宣称已实现每轮强制注入。
- 验证：中英文微信问题、网络端口转发、手机5G分类均通过；实际 brief 返回微信必读文件；共享文件 samefile 通过；技能校验通过。SOUL 规则对新会话生效，旧会话缓存不强改；已有会话可先执行 `~/.local/bin/hermes-memory-brief --json '微信转发窗口异常'` 并读取其返回文件。
- 保证层级：共享文件 + 召回路径 + 行为指令已验证；模型在真实后续任务中是否实际读取仍须看工具记录，不能用静态检查冒充端到端使用成功。
