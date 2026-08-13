# Runbook: System Sanity Evolve

保守的桌面/用户态自清理与演化入口。目标是定期清掉已确认安全的旧状态、坏结构和误报 failed 标记，而不是替代人工诊断。

## Desired State

- Script: `~/.local/bin/system-sanity-evolve`
- Timer: `system-sanity-evolve.timer`（每 6 小时，低 CPU/idle I/O）
- Service: `system-sanity-evolve.service`
- Report:
  - `~/.local/state/system-sanity-evolve/latest.json`
  - `~/.local/state/system-sanity-evolve/latest.md`

## Safe Auto-Fix Scope

`system-sanity-evolve --fix` 只做这些低风险动作：

- 修正用户 systemd drop-in 中放错位置的 `StartLimitIntervalSec=` / `StartLimitBurst=`：从 `[Service]` 移到 `[Unit]`。
- 删除 `~/.config/systemd/user/**/*.wants/*` 下目标不存在的坏 symlink。
- 归档 `~/.local/bin` 的 `*.bak*`、`*~`、`*.old` 到 `~/.local/state/bin-backups/<timestamp>/`。
- 调用 `mobile-ai-browser-cleanup` 和 `sway-tab-cleanup`，保守关闭旧/重复 AI 浏览器页和旧 WebTTY 窗口。
- 检测并迁移旧 OpenCode MCP schema：`command` 字符串/`args` 和 `type: http` 自动转成 `type: local|remote`、数组 `command`、显式 `enabled`；core MCP 保持 enabled，on-demand MCP 默认 disabled。
- 执行 `systemctl --user daemon-reload` 和 `systemctl --user reset-failed`。
- 仅对陈旧 `systemd-coredump@*.service` system failed 标记执行 `sudo -n systemctl reset-failed <unit>`；不清其它系统级失败。

## Verify

```bash
systemctl --user is-active system-sanity-evolve.timer
~/.local/bin/system-sanity-evolve --fix | jq '.actions, .failed_user_tail, .failed_system_tail'
sed -n '1,120p' ~/.local/state/system-sanity-evolve/latest.md
systemctl --user --failed --plain --no-legend
systemctl --failed --plain --no-legend
```

静态验证用户 unit：

```bash
find ~/.config/systemd/user -maxdepth 1 -type f \( -name '*.service' -o -name '*.timer' -o -name '*.socket' -o -name '*.path' \) -print0 | xargs -0 systemd-analyze --user verify
```

## Change Rules

- 不要把危险动作加入这个脚本：不要删除 coredump、cache、browser profile、active DB、container volume、`~/memory` 或项目源码。
- 新清理项必须满足：可重复、低风险、可回滚或只是标记清理、输出进入 `latest.json`。
- 大文件/跨盘迁移不要放进 `system-sanity-evolve`；使用专用 timer，例如 `opencode-cold-archive-migrate.timer`。
- OpenCode MCP schema 迁移必须先备份 `~/.config/opencode/opencode.json.bak-mcp-schema-<timestamp>`，不要把 on-demand MCP 全量启用。
- 发现新故障模式后，优先更新本 runbook 或 `~/.ai-context/FAILURE_BLACKLIST.md`，再扩展脚本。

## 2026-07-24 auto-evolve

- **scope**: phone
- **avoid**: 拦截 adb disconnect：修改 phone-connect-mcp.py，在 adb() 和 adb_with_device() 中增加 disconnect 拦截逻辑
- **confidence**: 90%
- **source_task**: 修复 Hermes 操控手机时反复弹出 USB 调试授权框

## 2026-07-24 auto-evolve

- **scope**: phone
- **avoid**: 不要让 Hermes/agent 直接执行 adb disconnect 已知设备地址；这会销毁已授权会话并触发 Android RSA 授权弹窗。
- **confidence**: 95%
- **source_task**: 修复 Hermes 操控手机时反复弹出 USB 调试授权框

## 2026-07-24 auto-evolve

- **scope**: phone
- **avoid**: 手机端弹出 USB 调试授权框时，必须勾选“始终允许”并保存对应电脑 RSA 指纹；这是系统层面记住授权的唯一方式。
- **confidence**: 95%
- **source_task**: 修复 Hermes 操控手机时反复弹出 USB 调试授权框
