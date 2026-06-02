# OpenClaw Session Runbook

适用场景:
- `oc` 打开后进入错误窗口
- `oc` 出现日志流/乱码
- `19890` 黑屏或 attach 到 dead pane

检查步骤:
1. `tmux list-windows -t openclaw`
2. 确认工作窗口为 `window 1`
3. 清理 dead pane / dead window
4. `openclaw-tmux-wrap` 默认固定到 `window 1`
5. `oc` 与 `19890` 必须走同一入口

验证:
- `oc`
- `curl -I http://127.0.0.1:19890`
- `tmux list-panes -t openclaw -F '#{window_index}.#{pane_index} dead=#{pane_dead}'`
