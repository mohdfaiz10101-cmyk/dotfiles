# Hermes 端口绑定锁

## 当前绑定（禁止无审批变更）

| 端口 | 绑定关系 | 服务/实现 | 审批要求 |
|------|----------|-----------|----------|
| `8787` | `nesquena/hermes-webui` | systemd `hermes-webui.service` | 必须弹窗审批后方可修改 |
| `8648` | `Hermes Studio` 本地入口 | systemd `hermes-8648-proxy.service` -> `18648` | 必须弹窗审批后方可修改 |
| `18648` | `Hermes Studio` 主服务 | systemd `hermes-web-ui.service` | 必须弹窗审批后方可修改 |
| `19999` | Hermes Monitor Panel | systemd `hermes-monitor-panel.service` | 不要动 |
| `19910` | Hermes WebTTY backend | systemd `ttyd-hermes-backend.service` | 不要动 |

## 锁定机制

**自动看门狗**：`hermes-port-lock.timer` 每 5 分钟运行一次 `hermes-port-lock.sh`

- 检查 8787/8648 是否绑定到正确进程
- `18648` 是 Hermes Studio 后端，可空闲为未监听；由 `8648` 轻量代理在真实
  访问时按需启动 `hermes-web-ui.service`
- 发现异常自动修复对应 service
- 修复成功/失败都发 `ntfy` 到 `charlie-system`
- 日志：`~/.local/state/hermes-port-lock/hermes-port-lock.log`

**快速核验命令**
```bash
bash ~/.local/bin/hermes-port-lock.sh status
bash ~/.local/bin/hermes-port-lock.sh check
```

## 硬规则

- 不得擅自修改 `8787` / `8648` / `18648` 的监听服务、转发目标或 `frpc` 映射。
- `8787` 的 `nesquena/hermes-webui` 程序更新必须先走
  `~/.local/bin/hermes-webui-safe-update --check`。只有输出
  `ok: fast-forward available` 或 `already up to date` 才允许继续执行
  `~/.local/bin/hermes-webui-safe-update --apply --restart`。
- 不要用 WebUI 自带更新按钮或裸 `git pull` 处理 `8787`，除非已明确确认没有本地
  改动、没有 `hermes-update-autostash`、且愿意承担自动 stash/恢复冲突风险。
- `~/.local/bin/hermes-webui-safe-update` 永远不得自动 `stash`、`reset`、`rebase`、
  或创建 merge commit；遇到 dirty/diverged/lock 状态必须阻断并人工复核。
- 如需变更，必须先创建 `Workbench manual action` 或等价弹窗审批，等用户确认后再执行。
- 审批通过前，禁止：
  - 改 `systemd` service 的 `ExecStart` / `Environment=PORT=...`
  - 改 `hermes-*-http-proxy.js` 的 `TARGET_PORT`
  - 改 `frpc.toml` 的 `localPort` / `remotePort`
  - 改 `nesquena/hermes-webui` 的 `.env` 端口

## 测试记录

- 2026-07-27：发现并修复 watchdog 两个 bug：
  - `extract_proc_name` 使用 `grep -oP` 无法从 `ss` 输出提取进程名，改为 `sed`
  - `ss -tlnp` 即使无匹配也返回 exit 0，导致端口存在检查失效，改为 `grep -q 'LISTEN'`
- 验证结果：
  - 停掉 `hermes-webui.service` 后，watchdog 自动检测到 8787 异常并在 4 秒内修复
  - 停掉 `hermes-8648-proxy.service` 后，watchdog 自动检测到 8648 异常并修复
  - 三次 `check` 全部通过，端口绑定正确

## 变更记录

- 2026-07-27：锁定 `8787=nesquena`、`8648->18648=Hermes Studio`，并明确要求弹窗审批后方可修改。
- 2026-07-27：增加自动看门狗 `hermes-port-lock.timer`，每 5 分钟检查并自动修复端口绑定。
- 2026-08-01：收紧看门狗，不再为了检查端口而启动/保活 `18648`。后台只保活
  `8787` 和轻量 `8648` proxy，避免 Hermes Studio 常驻拉起 worker/MCP 导致
  内存、swap 和任务调度不稳定。
- 2026-08-01：修复手机公网访问 `duckdns:8648`。根因不是 Hermes 代理崩溃，
  而是 Fedora firewalld 没开放普通 `8648/tcp`，公网 DNAT 进来的连接被拒绝；
  同时路由器有旧 `8648 -> 192.168.123.71:2244` 重复 DNAT。已在
  `FedoraWorkstation` zone 临时/永久加入 `8648/tcp`，并在路由器
  `/etc/storage/post_iptables_script.sh` 追加清理/重建 `8648 -> 192.168.123.71:8648`。
  验证：手机侧 `curl http://charlie1990.duckdns.org:8648/` 返回 HTTP 200。
- 2026-08-01：`19910` 是 Hermes WebTTY device gate，路由器原来没有公网 DNAT；
  已追加 `19910 -> 192.168.123.71:19910`。验证：手机侧
  `curl http://charlie1990.duckdns.org:19910/` 返回 HTTP 200。
- 2026-08-02：`8787` WebUI 自更新后出现更新冲突提示。复核结果：当前仓库
  没有未解决 merge/rebase/conflict marker，`master` 干净但落后 `origin/master`
  29 个提交；存在 `stash@{0}: hermes-update-autostash`，包含上次自更新临时保存的
  本地改动。已新增 `~/.local/bin/hermes-webui-safe-update`，以后只允许
  fast-forward 更新，禁止自动 stash/reset/rebase，避免再次把本地补丁和上游更新混在一起。
- 2026-08-10：网络不稳定排查确认 `duckdns:8787` 与 `duckdns:18300` 不是有效
  Hermes 公网入口；公网 `8787` 没有路由器 DNAT/FRPC 映射，`18300` 当前也不可达。
  手机/公网入口应使用 `duckdns:8648` 访问 Hermes Studio，使用 `duckdns:19976`
  访问 `8787` WebUI auth proxy。已修正 `hermes-actions` 通知按钮、
  `mobile-ai-workbench` 和 `phone-webtty-route-probe` 的 `h8787` DuckDNS 端口。
- 2026-08-10：`hermes-port-lock` 曾把 `8648` 的合法 `MainThread` 监听误判为
  异常，导致每 5 分钟重启 `hermes-studio-8648.service` 并短暂打断入口。现在
  `8648` 允许 `MainThread,python3`，`hermes-port-lock.sh check` 返回 OK。
- 2026-08-10：本地 Hermes terminal 以 `19910` WebTTY 使用的 tmux 会话为主。
  `~/.local/bin/hermes-attach.sh` 固定 attach 到
  `/run/user/1000/tmux/hermes-cli.sock` 的 `hermes` session；不要让本地入口再
  使用默认 tmux socket 或直接新启一个独立 `hermes chat` 会话。同步验证：
  `tmux -S /run/user/1000/tmux/hermes-cli.sock display-message -p -t '=hermes:' '#{session_name} #{socket_path}'`。
