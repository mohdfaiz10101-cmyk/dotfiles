# Hermes Actions Runner

最后更新：2026-08-01 21:28 CST

目标：让 Hermes / 8787 / 8648 的重任务呈现 GitHub Actions 风格：任务入队、运行中、完成、失败都可通知到手机，并由轻量 watcher 轮询状态。

## 当前实现

- 底层调度仍使用现有 `~/.local/bin/agent-dispatch`。
- 新增包装器：`~/.local/bin/hermes-actions`
  - `hermes-actions submit --title "..." "task text"`
  - `hermes-actions status latest`
  - `hermes-actions watch`
- 新增 watcher：
  - `~/.config/systemd/user/hermes-actions-watch.service`
  - `~/.config/systemd/user/hermes-actions-watch.timer`
- timer 当前启用，每分钟运行一次。
- 新增 Codex -> Hermes 显式委派桥：`~/.local/bin/codex-hermes-bridge`
  - user service：`~/.config/systemd/user/codex-hermes-bridge.service`
  - 只读扫描 Codex session 的新增 `user_message` 事件。
  - 仅当用户消息显式出现“委派 / 交给 Hermes / 让 Hermes 处理 / 8787 /
    8648 / 任务分拣 / handoff / delegate”等意图时，才把短任务文本排入
    `hermes-session-mesh dispatch --mode queue`。
  - 不读取完整 Codex transcript，不启动 live 并发，不自动把所有 Codex
    消息灌入 Hermes。
- `codex-ntfy-result-watcher` 仍负责 Codex 完成消息推送到 `codex` ntfy
  频道；通知已附带对应 Codex WebTTY click/action，默认 C1 是
  `http://charlie1990.duckdns.org:19899/?device=w19900422`。
- 2026-08-01 收紧：`hermes-actions watch` / `status` 是只读路径，不得调用
  `agent-dispatch watch`、`agent-dispatch status` 或任何 `--auto-handoff`
  路径。自动 watcher 只能读取
  `~/.local/state/agent-dispatch/tasks/*.json` 并通知，不能把旧失败任务重新
  交给 OP/Crush，也不能仅因“查看 latest”改写底层 latest 指针。

## 通知语义

- submit 成功：发送 `Hermes task queued`
- watcher 发现状态变化：
  - `running`
  - `completed`
  - `failed`
  - `final_failed`
- 通知走 `~/.local/bin/ntfy-send actions`。
- `hermes-actions` 通知默认 click 到 `http://charlie1990.duckdns.org:8648`，
  并通过 `NTFY_ACTIONS` 提供打开 Hermes `8648`、Actions `8787`、Codex C1
  `19899` 和 Workbench `19888` 的手机按钮。
- `codex-ntfy-result-watcher` 的 Codex 完成通知会按账号附带对应外部 WebTTY
  click/action；C1 是 `http://charlie1990.duckdns.org:19899/?device=w19900422`。
- 若 ntfy 返回 `429`，说明通知服务限流；不要重复轰炸通知，应等待下一轮 timer。
- 自建 ntfy 也有限流；这不是 ntfy 官方云限制。2026-08-01 确认本地日志出现
  `visitor_requests_remaining=0`，已在 `~/ai/ntfy/etc/server.yml` 放宽为
  `visitor-request-limit-burst: 600`、`visitor-request-limit-replenish: "1s"`、
  `visitor-message-daily-limit: 20000`，并将 `127.0.0.1`、`::1`、
  `192.168.123.71`、`100.87.238.153` 加入
  `visitor-request-limit-exempt-hosts`。这个配置项必须是逗号分隔字符串，不是
  YAML list。
- `container-ntfy.service` 必须用 `/usr/bin/podman run --pull=never`，不要用
  `/usr/bin/docker run ... latest`，否则重启可能错误拉镜像并导致 systemd active
  但 `127.0.0.1:2586` 不通。

## 架构原则

- `8787` / `8648` 做控制面、任务入口、队列/状态展示，不直接承载所有重计算。
- Codex 是常态发起者/任务分配者；Hermes 是任务管理中心、看板、分拣器和
  隔离执行空间。不要把这个关系反过来理解成“所有任务都先进入 Hermes”。
- Codex -> Hermes 的桥接必须是“意图触发 + 短任务 envelope”，不是完整上下文
  同步。任务 envelope 至少包含 source account、source session file、短任务
  文本、profile、constraints、summary hint。
- Hermes 可以作为 Codex 的看板/任务中心：展示 queued/running/done/failed、
  task_id、profile、证据路径和 ntfy 状态；但默认不读取 Codex 全量聊天历史。
- ntfy 是手机上的人工决策层，不只是通知末端。它应该参与任务管理：
  - 推送任务状态、计划草案、失败原因和下一步选项。
  - 用 action buttons 承接低风险决策：打开 C1、打开 Hermes、继续、取消、
    改派、复盘、需要人工确认。
  - 用文本回复承接规划/改派输入，例如“让 C1 继续”、“交给 Hermes mobile
    profile”、“先只读复盘”、“取消这个任务”。
  - ntfy 回复/动作必须先写入 bounded inbox，再由 Codex/Hermes 消费；不要让
    ntfy 直接执行高风险系统命令、付款、登录、删除或网络变更。
- 重活交给 OP/Crush/Hermes worker、Waydroid worker、未来 redroid VM worker。
- 每个任务必须有 `task_id`、状态文件、日志路径、deadline、失败包。
- 长任务不塞满单个上下文；完成或失败只回传摘要、证据、artifact 路径。
- 多任务策略：默认“多任务入队、有限并发执行”。每个 Codex 对话可以识别出
  多个子任务并生成多个 envelope/capsule，但 Hermes Studio live worker 不默认
  并发展开；队列和看板可以并行展示，执行层按压力门控串行或小批量 drain。
- 每个对话不是变成一个无限上下文，而是变成任务树：
  `conversation -> task envelope -> child capsules -> status/result summary`。
  Codex 负责拆分和判断，Hermes 负责登记、隔离、展示和按 profile 排队。
- 旧失败任务需要重新处理时，必须人工或显式命令创建新任务；不要让通知
  watcher 自动 resurrection / handoff。
- VPS 只能改善外部入口稳定性，不能修复 Hermes 内部执行面。若 `8787` /
  `8648` 不稳定，先查本地服务常驻、自动 handoff、MCP/worker 数量、内存、
  swap、PSI 和任务队列，不要直接归因到 DuckDNS/NetBird。
- Hermes/OP/Codex/Crush 的共享记忆以 `workflow-intel`、`~/memory/workflows/`、
  `~/.ai-context/runbooks/` 和 `~/.codex/skills` 为共同源；不要为 Hermes
  单独发明一套长期记忆。
- `workflow-intel-maintain.timer` 可以启用：hourly、idle I/O、2 分钟超时。
  `ai-a2a-worker.timer` 默认保持 disabled；需要 Codex 参与评审时显式打开预算
  或手动处理，避免 30 秒轮询制造后台噪音。
- `hermes-session-mesh` 启动 chat-run 时必须使用任务对应 profile；不要把所有
  `ops/monitor/mobile` 子任务硬编码到 `secondary`。当前 `mobile` 映射到已有
  `monitor` profile；缺失 profile 才回退。
- 多子任务协作默认动态并发：可以由 Codex 拆成多个 Hermes capsule，
  `session_mesh.launch_limit_per_tick: auto` 按 load、可用内存、swap 自动计算
  本轮启动数；`launch_max_per_tick` 是硬上限，不是固定单任务。Hermes Studio
  每个 profile 会拉起大量 MCP/worker，并行过猛仍可能打满 user service
  `Tasks` 上限，出现 `can't start new thread`、`ECONNRESET` 或
  `requires_action` 卡住，所以要压力门控而不是无限启动。
- 2026-08-01：执行控制升级为 governor 模式，不再长期靠停止避免风险。
  `~/.hermes/config.yaml` 中：
  - `session_mesh.launch_mode: auto` 是常态；`manual` 只允许人工 `--force`；
    `paused` 才是硬暂停。
  - `launch_max_submitted: 2` 控制后台执行槽；submitted 达上限后自动不再开新
    任务。
  - `launch_max_per_tick: 2` 控制每轮自动启动上限；人工可用
    `hermes-session-mesh drain-queue --force --limit <n>` 临时放大。
  - `launch_failure_circuit_breaker: 3` 控制连续失败熔断。
  - `hermes-session-mesh governor` 显示 mode、pressure、service、queue、
    failure_streak 和 available_slots。
  - `hermes-actions status mesh --limit <n>` 是 8787/8648 的 Actions 风格状态面，
    输出 governor、timer 和 runs。Codex 沙箱里 Python 子进程可能无法连接
    user systemd bus，此时 timer 会显示 `timer_unavailable`；必须再用
    `systemctl --user status hermes-mesh-dispatch.timer --no-pager` 验证真实 timer。
    不要把 `timer_unavailable` 误判为 timer 未启用。
  - `submitted` 超过 45 分钟会由 `hermes-session-mesh archive-stale` 归档到
    `~/.hermes/a2a/mesh-queue/stale/<profile>/`，状态面显示为 `stale`，不再占用
    `launch_max_submitted` 执行槽；旧 stale 任务需要单独复核，不要直接删除。
  - `hermes-session-mesh drain-queue` 和 `hermes-session-mesh reconcile` 都会先执行
    stale 归档，所以 timer 每轮都会自动收敛旧 submitted。
  - `hermes-mesh-dispatch.timer` 每 5 分钟触发一次智能 drain；必须看到
    `Active: active (waiting)` 和下一次 `Trigger`，不能是 `active (elapsed)` /
    `Trigger: n/a`。
  - `launch_mode: paused` 或兼容旧 `launch_paused: true` 时，
    `hermes-8648-http-proxy.js` 返回 `503 Hermes 8648 execution is paused`，
    并不唤醒 `hermes-web-ui.service`。
- `--mode live` 只用于单个 smoke 或明确需要立即回传的短任务。若模型触发
  `approval.requested`，默认不批准，把该任务当失败/需人工复核处理；不要为了
  smoke 放行写入、归档或扫描命令。
- 2026-08-01：`hermes-web-ui.service.d/override.conf` 的 `TasksMax` 从 `180`
  提到 `512`，后因用户要求动态最大化多任务，继续调整为 `TasksMax=1024`、
  `MemoryHigh=10G`、`MemoryMax=14G`、`CPUWeight=100`、`IOWeight=100`。
  这表示 Hermes 可以使用更多本机服务器资源，但仍保留服务级上限，避免把
  桌面、网络和 WebTTY 一起拖死。
  验证命令：`systemctl --user status hermes-web-ui.service --no-pager`，应看到
  `Tasks: <n> (limit: 1024)` 和 `Memory: ... (high: 10G, max: 14G, ...)`。

## 验证

```bash
python3 -m py_compile ~/.local/bin/hermes-actions
systemd-analyze --user verify ~/.config/systemd/user/hermes-actions-watch.service ~/.config/systemd/user/hermes-actions-watch.timer
systemctl --user is-active hermes-actions-watch.timer
hermes-actions watch
ntfy-task-inbox --classify 'plan: 怎么拆分网络维护任务'
codex-hermes-bridge --once
hermes-session-mesh drain-queue --dry-run
hermes-session-mesh governor
hermes-session-mesh archive-stale
hermes-actions status mesh --limit 8
systemctl --user status hermes-mesh-dispatch.timer --no-pager
curl -sI http://127.0.0.1:8648/
systemctl --user status hermes-web-ui.service hermes-8648-proxy.service --no-pager
curl -fsS http://127.0.0.1:2586/v1/health
ntfy-send system "ntfy smoke" "local ntfy ok"
```

## 职责矩阵

| 组件 | 主要职责 | 不应该做 |
| --- | --- | --- |
| Codex C1 | 主判断、任务拆分、用户对话、最终汇总 | 不把全量上下文推给 Hermes |
| Codex C2-C10 | 并行子任务、备用执行、专门账号/额度路由 | 不绕过 C1/任务 envelope 乱改共享状态 |
| Hermes `8787` | 任务分拣入口、Actions 风格任务状态、轻量看板 | 不承载所有重计算和长上下文 |
| Hermes `8648` | Studio/深度复盘/隔离 session，按 queue capsule 进入 | 不常驻拉满 worker，不默认 live 并发 |
| ntfy | 手机人工决策层、状态通知、回复/按钮进入 inbox | 不直接执行高风险系统动作 |
| `agent-dispatch` | OP/Crush 执行路由和失败包 | 通知 watcher 不得自动复活旧失败任务 |

## ntfy task inbox

- 脚本：`~/.local/bin/ntfy-task-inbox`
- 服务：`~/.config/systemd/user/ntfy-task-inbox.service`
- 轮询：60 秒，避免触发 ntfy `429`。
- 输入 topic：`charlie-actions`、`charlie-codex`。
- 支持的手机回复格式：
  - `c1: <任务>` -> `codex-smart --account 1 --send`
  - `hermes: <任务>` -> `hermes-session-mesh dispatch --mode queue`
  - `plan: <问题>` -> Hermes queue，只读规划
  - `status` / `cancel <id>` -> 先记录到 inbox，等待 Codex/Hermes 消费
- 状态文件：
  - `~/.local/state/ntfy-task-inbox/inbox.jsonl`
  - `~/.local/state/ntfy-task-inbox/actions.jsonl`
