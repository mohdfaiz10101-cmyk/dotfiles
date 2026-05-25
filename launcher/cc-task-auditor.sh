#!/run/current-system/sw/bin/bash
# cc-task-auditor.sh — CC 定期审计 OP 任务执行状态
# Why: 防止任务被静默跳过或卡死，实现失败自动回流
# How: 扫描 op-tasks.md → 分类超时/失败任务 → 生成报告 → 写回流任务给 CC

set -euo pipefail

OP_TASKS="$HOME/.claude/projects/-home-charlie/memory/op-tasks.md"
RESULTS_FILE="$HOME/.local/state/op-task-results.json"
REPORT_DIR="$HOME/Desktop/巡检报告/任务审计"
CC_QUEUE="$HOME/.claude/projects/-home-charlie/memory/cc-queue.md"
LOG="$HOME/.local/share/cc-auditor/audit.log"

mkdir -p "$REPORT_DIR" "$(dirname "$LOG")"

NOW=$(date +%s)
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
REPORT="$REPORT_DIR/task-audit-${DATE}.md"

echo "[$(date +%H:%M:%S)] CC 任务审计开始" | tee -a "$LOG"

# ── 统计各状态任务 ────────────────────────────────────────
total_done=$(grep -c '^\- \[x\]' "$OP_TASKS" 2>/dev/null || echo 0)
total_todo=$(grep -c '^\- \[ \]' "$OP_TASKS" 2>/dev/null || echo 0)
total_fail=$(grep -c '^\- \[!\]' "$OP_TASKS" 2>/dev/null || echo 0)

# ── 找超时未执行任务（时间戳超过4小时的 [ ] 任务）─────────
stale_tasks=()
while IFS= read -r line; do
    # 提取时间戳 [2026-04-18 11:29]
    if [[ "$line" =~ \[([0-9]{4}-[0-9]{2}-[0-9]{2})\ ([0-9]{2}:[0-9]{2})\] ]]; then
        task_date="${BASH_REMATCH[1]}"
        task_time="${BASH_REMATCH[2]}"
        task_ts=$(date -d "$task_date $task_time" +%s 2>/dev/null || echo 0)
        age_hours=$(( (NOW - task_ts) / 3600 ))
        if [[ $age_hours -ge 4 ]]; then
            stale_tasks+=("${age_hours}h | $line")
        fi
    fi
done < <(grep '^\- \[ \]' "$OP_TASKS" 2>/dev/null || true)

# ── 找失败任务（需回流给 CC）────────────────────────────────
failed_tasks=()
while IFS= read -r line; do
    failed_tasks+=("$line")
done < <(grep '^\- \[!\]' "$OP_TASKS" 2>/dev/null || true)

# ── OP→CC 回流任务（已标注需 CC 处理的）────────────────────
cc_return_tasks=()
while IFS= read -r line; do
    cc_return_tasks+=("$line")
done < <(grep '^\- \[ \].*\[OP→CC\]' "$OP_TASKS" 2>/dev/null || true)

# ── 生成审计报告 ──────────────────────────────────────────
cat > "$REPORT" << EOF
# CC 任务审计报告 — $DATE $TIME

## 总体状态
- 已完成：$total_done 条
- 待执行：$total_todo 条
- 失败标记：$total_fail 条

## 超时未执行（>4小时）
EOF

if [[ ${#stale_tasks[@]} -eq 0 ]]; then
    echo "无超时任务" >> "$REPORT"
else
    for t in "${stale_tasks[@]}"; do
        echo "- $t" >> "$REPORT"
    done
fi

cat >> "$REPORT" << EOF

## 失败任务（[!] 标记，需返工或 CC 接管）
EOF

if [[ ${#failed_tasks[@]} -eq 0 ]]; then
    echo "无失败任务" >> "$REPORT"
else
    for t in "${failed_tasks[@]}"; do
        echo "$t" >> "$REPORT"
    done
fi

cat >> "$REPORT" << EOF

## OP→CC 回流任务（OP 无法解决，需 CC 处理）
EOF

if [[ ${#cc_return_tasks[@]} -eq 0 ]]; then
    echo "无回流任务" >> "$REPORT"
else
    for t in "${cc_return_tasks[@]}"; do
        echo "$t" >> "$REPORT"
    done
fi

# ── 将回流任务写入 CC 队列 ────────────────────────────────
if [[ ${#cc_return_tasks[@]} -gt 0 ]] || [[ ${#failed_tasks[@]} -gt 0 ]]; then
    {
        echo ""
        echo "## CC 审计接管 [$DATE $TIME]"
        for t in "${failed_tasks[@]}"; do
            # 失败任务转为 CC 接管（去掉 [!] 换成 CC 待办格式）
            task_desc=$(echo "$t" | sed 's/^\- \[!\]//')
            echo "- [ ] [CC接管-失败返工] [$DATE $TIME] [high]$task_desc"
        done
        for t in "${cc_return_tasks[@]}"; do
            task_desc=$(echo "$t" | sed 's/^\- \[ \] \[OP→CC\]//')
            echo "- [ ] [CC接管-OP回流] [$DATE $TIME] [high]$task_desc"
        done
    } >> "$CC_QUEUE"
    echo "[$(date +%H:%M:%S)] 写入 $((${#failed_tasks[@]} + ${#cc_return_tasks[@]})) 条回流任务到 CC 队列" | tee -a "$LOG"
fi

# ── 超时任务重新派给 OP（加 [RETRY] 标记）────────────────
if [[ ${#stale_tasks[@]} -ge 3 ]]; then
    echo "[$(date +%H:%M:%S)] 警告：${#stale_tasks[@]} 条任务超时，可能 OP 未运行" | tee -a "$LOG"
    # notify-send 通知用户
    notify-send "CC 任务审计" "发现 ${#stale_tasks[@]} 条超时任务\n失败: $total_fail 条\n见 $REPORT" 2>/dev/null || true
fi

echo "[$(date +%H:%M:%S)] 审计完成 → $REPORT" | tee -a "$LOG"
echo "待办:$total_todo 完成:$total_done 失败:$total_fail 超时:${#stale_tasks[@]} 回流:${#cc_return_tasks[@]}"

# ── 互审自动升级（条件满足后 CC 自己修改架构，无需用户干预）──
cc_queue="$HOME/.claude/projects/-home-charlie/memory/cc-queue.md"
mutual_review_flag="$HOME/.local/share/cc-auditor/mutual-review-enabled"

if [[ -f "$cc_queue" ]] && [[ ! -f "$mutual_review_flag" ]]; then
    queue_count=$(grep -c '^\- \[ \]' "$cc_queue" 2>/dev/null || echo 0)
    if [[ $queue_count -ge 10 ]]; then
        echo "[ARCH] cc-queue.md 已有 ${queue_count} 条失败任务，自动启动互审机制" | tee -a "$LOG"

        # 创建 CC 验证脚本：抽查 OP 已完成任务结果
        cat > "$HOME/launcher/cc-op-verifier.sh" << 'VERIFIER'
#!/usr/bin/env bash
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
VERIFIER
        chmod +x "$HOME/launcher/cc-op-verifier.sh"

        # 创建验证 timer（每2小时）
        cat > "$HOME/.config/systemd/user/cc-op-verifier.service" << 'SVC'
[Unit]
Description=CC 验证 OP 任务结果（互审阶段）
[Service]
Type=oneshot
ExecStart=/home/charlie/launcher/cc-op-verifier.sh
SVC
        cat > "$HOME/.config/systemd/user/cc-op-verifier.timer" << 'TMR'
[Unit]
Description=CC↔OP 互审验证（每2小时）
[Timer]
OnBootSec=1h
OnUnitActiveSec=2h
Persistent=true
[Install]
WantedBy=timers.target
TMR
        systemctl --user daemon-reload
        systemctl --user enable --now cc-op-verifier.timer

        # 写入启用标记，防止重复触发
        touch "$mutual_review_flag"
        echo "[ARCH] 互审机制已启用 → cc-op-verifier.timer 每2小时运行" | tee -a "$LOG"

        # 更新 ideas-roadmap.md 状态
        sed -i 's/当前状态：已建 cc-task-auditor/当前状态：互审已自动启用（触发于 '"$(date +%Y-%m-%d)"'）/' \
            "$HOME/.claude/projects/-home-charlie/memory/ideas-roadmap.md" 2>/dev/null || true
    fi
fi
