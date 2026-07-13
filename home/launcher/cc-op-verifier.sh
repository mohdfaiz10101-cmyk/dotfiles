#!/run/current-system/sw/bin/bash
# cc-op-verifier.sh — CC 主动验证 OP 已完成任务（互审阶段自动启用）
RESULTS="$HOME/.local/state/op-task-results.json"
LOG="$HOME/.local/share/cc-auditor/verify.log"
TASKS="$HOME/.claude/projects/-home-charlie/memory/op-tasks.md"
[[ -f "$RESULTS" ]] || exit 0
# 读取最近完成的任务，验证关键服务状态是否与结果一致
recent=$(tail -20 "$RESULTS" 2>/dev/null | grep '"status":"success"' | tail -5)
if [[ -z "$recent" ]]; then
    echo "[$(date +%H:%M:%S)] 无新完成任务需验证" >> "$LOG"
    exit 0
fi
# 验证：抽查 systemd 服务类任务是否真的 active
echo "$recent" | while read -r line; do
    task=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task',''))" 2>/dev/null || echo "")
    svc=$(echo "$task" | grep -oP '(?<=重启|启动|修复)\s*\K[\w-]+(?:\.service)?' | head -1)
    if [[ -n "$svc" ]]; then
        state=$(systemctl --user is-active "$svc" 2>/dev/null || systemctl is-active "$svc" 2>/dev/null || echo "unknown")
        echo "[$(date +%H:%M:%S)] 验证 $svc: $state" >> "$LOG"
        if [[ "$state" != "active" ]]; then
            echo "- [ ] [CC验证失败] [$(date '+%Y-%m-%d %H:%M')] [high] OP标记成功但服务未运行: $svc" >> "$TASKS"
        fi
    fi
done
