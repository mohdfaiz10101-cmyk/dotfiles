#!/run/current-system/sw/bin/bash
# op-watchdog.sh — OP 断开即时恢复守护进程
# 监控 op-task-runner 的 lock 文件，一旦消失且还有未完成任务，立即重新触发

OP_TASKS="$HOME/.claude/projects/-home-charlie/memory/op-tasks.md"
LOCK="/tmp/op-task-runner.lock"
LOG="$HOME/.local/share/cc-auditor/watchdog.log"

mkdir -p "$(dirname "$LOG")"
echo "[$(date '+%H:%M:%S')] op-watchdog 启动" >> "$LOG"

while true; do
    # 等待 lock 文件出现（OP 开始运行）
    while [ ! -f "$LOCK" ]; do sleep 3; done
    echo "[$(date '+%H:%M:%S')] OP 运行中 (lock存在)" >> "$LOG"

    # 等待 lock 消失（OP 结束/断开）
    while [ -f "$LOCK" ]; do sleep 2; done
    echo "[$(date '+%H:%M:%S')] OP 结束/断开，检查剩余任务..." >> "$LOG"

    # 等 5s 让 OP 完成最后写入
    sleep 5

    # 检查是否还有未完成任务
    PENDING=$(grep -c '^- \[ \]' "$OP_TASKS" 2>/dev/null) || PENDING=0
    if [ "$PENDING" -gt 0 ]; then
        echo "[$(date '+%H:%M:%S')] 发现 $PENDING 个未完成任务，立即触发 op-task-runner" >> "$LOG"
        systemctl --user start op-task-runner.service
    else
        echo "[$(date '+%H:%M:%S')] 无未完成任务，无需重启" >> "$LOG"
    fi

    sleep 10
done
