# Memory Pressure Runbook

适用场景:
- swap 接近或达到 100%
- 用户态 systemd 报 `Resource temporarily unavailable`

检查步骤:
1. `free -h`
2. `ps -eo pid,ppid,%mem,%cpu,cmd --sort=-%mem | head -20`
3. `systemctl --user --failed`
4. `systemctl --user list-timers --all`

修复方向:
- 关闭低价值高频 timer
- 清理重复 `opencode/claude/openclaw` 会话
- 把 waybar 健康统计改成只盯关键服务
