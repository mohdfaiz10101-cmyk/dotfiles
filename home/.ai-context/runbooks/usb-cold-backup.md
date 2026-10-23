# 固态便携 USB 冷备

入口：`~/.local/bin/cold-backup-to-usb.sh`；SQLite 快照 helper：`~/.local/bin/cold-backup-sqlite-snapshot.py`。
Skill：`~/.shared-agent/skills/devops/usb-cold-backup-dr/SKILL.md`。
操作说明：`~/workspace/cold-backup/README.md`。

- 目标 UUID `423CC8003CC7ED4B`，卷标固态便携；USB 序列号 `012345680068`，当前端口 `1-5`。
- 每周一 04:00；盘上12轮、本地2轮，每轮成对保留 home/sys/manifest。
- 状态：`systemctl --user list-timers cold-backup-usb.timer`；实际运行日志在 `~/workspace/cold-backup/staging/`。
- 测试不发通知：`COLD_BACKUP_NOTIFY=0 ~/.local/bin/cold-backup-to-usb.sh`。
- `.hermes/skills` 实为 `.shared-agent/skills` 软链接，tar 默认不遍历；真实目标必须入归档。
- 活跃 SQLite 用 `Connection.backup`，不能只归档主库排除 WAL。独立 DB 验证 quick_check。
- `ConditionPathIsMountPoint=/var/home/charlie` 会导致每周 service 被跳过；当前已换脚本存在检查。
- `SuccessExitStatus=0 1` 会掩盖备份失败；只允许0。
- 卸载失败不得取消授权或报告成功。USB authorized=0 不保证物理 VBUS 断电。
- 不要运行旧应急启动手册；它未验收，且包含 btrfs send/receive 会复制 filesystem UUID 等错误。当前盘仅用于归档。
- 本次改动前快照：`~/.local/state/usb-cold-backup-repair/20261023/`。

## 2026-10-23 实盘验收
- 成功轮次：`20261023_175719`，17:59:32 完成，home 208 MiB、sys 344 MiB。
- 三个 SQLite 快照 quick_check 通过；归档恢复演练 config/真实技能/state.db 通过；盘上 SHA-256 比对通过。
- 最终卸载成功、`authorized=0`；本次 `COLD_BACKUP_NOTIFY=0`，不以此声称通知链路已重新验证。
- 首次修复验证遇到 root 归档继承 umask 077 导致普通用户不能校验，已加入新 sys 产物 chown/chmod 600。失败路径正常卸载，未写目标备份。
- 修复脚本入口 bash -n、helper Python 编译、skill validator、udevadm verify、systemd 条件验证均通过。
- 故障注入：卸载失败时不取消USB授权且返回1；显式exit4时发送失败分支且保留exit4。
