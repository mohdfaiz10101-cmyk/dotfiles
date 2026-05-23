#!/usr/bin/env bash
# incident-reporter.sh — 每周故障报告 + 错误预算追踪
# 用法: incident-reporter.sh [--week] [--json]
# SLO目标: 每周故障≤5次, MTTD≤30min, MTTR≤2h

set -euo pipefail

LESSONS_FILE="$HOME/.claude/projects/-home-charlie/memory/lessons-learned.md"
STATE_DIR="$HOME/.local/state/ops-infra"
ERROR_BUDGET="$STATE_DIR/error-budget.json"
REPORT_DIR="$STATE_DIR/reports"
mkdir -p "$STATE_DIR" "$REPORT_DIR"

# ====== 错误预算配置 ======
# SLO: 99.5% uptime → 每周允许 3.6h down → 保守设3次严重故障
MAX_WEEKLY_INCIDENTS=5
MAX_MTTD_MINUTES=30
MAX_MTTR_MINUTES=120

# ====== 从lessons-learned提取本周故障 ======
# 格式: - [2026-05-23] [OP] 修复: xxx | 原因: xxx | 修复: xxx
extract_incidents() {
    local week_start week_end
    week_start=$(date -d "last monday" +%Y-%m-%d 2>/dev/null || date -d "7 days ago" +%Y-%m-%d)
    week_end=$(date +%Y-%m-%d)

    grep "^\- \[20" "$LESSONS_FILE" | while IFS= read -r line; do
        local entry_date
        entry_date=$(echo "$line" | grep -oP '^\- \[\K[0-9-]+')
        if [[ "$entry_date" > "$week_start" || "$entry_date" == "$week_start" ]] && [[ "$entry_date" < "$week_end" || "$entry_date" == "$week_end" ]]; then
            echo "$line"
        fi
    done
}

# ====== 分析MTTD/MTTR ======
# 简化版：从条目描述中提取时间信息
analyze_timeline() {
    echo "TODO: 解析故障时间线"
    # 未来可从runbook执行日志中提取精确MTTD/MTTR
}

# ====== 主逻辑 ======
MODE="${1:---week}"

incidents=$(extract_incidents)
incident_count=$(echo "$incidents" | grep -c "\[" 2>/dev/null || echo "0")

if [ "$MODE" = "--json" ]; then
    python3 -c "
import json
print(json.dumps({
    'week': '$(date -d "last monday" +%Y-%m-%d 2>/dev/null || echo "N/A") → $(date +%Y-%m-%d)',
    'incident_count': $incident_count,
    'error_budget': {'max': $MAX_WEEKLY_INCIDENTS, 'used': $incident_count, 'remaining': $((MAX_WEEKLY_INCIDENTS - incident_count))},
    'status': 'OK' if $incident_count <= $MAX_WEEKLY_INCIDENTS else 'BUDGET_EXCEEDED'
}, indent=2))
"
    exit
fi

# 生成Markdown报告
report_file="$REPORT_DIR/incident-report-$(date +%Y-W%V).md"

cat > "$report_file" << REPORT
# 故障周报 — $(date +%Y年%m月%d日)

**周期**: $(date -d "last monday" +%Y-%m-%d 2>/dev/null || echo "过去7天") → $(date +%Y-%m-%d)

---

## 错误预算

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 故障次数 | ≤${MAX_WEEKLY_INCIDENTS} | ${incident_count} | $([ "$incident_count" -le "$MAX_WEEKLY_INCIDENTS" ] && echo "✅ 达标" || echo "🚨 超预算") |
| MTTD | ≤${MAX_MTTD_MINUTES}min | TBD | ⏳ |
| MTTR | ≤${MAX_MTTR_MINUTES}min | TBD | ⏳ |

**剩余错误预算**: $((MAX_WEEKLY_INCIDENTS - incident_count)) 次

---

## 本周故障

$([ "$incident_count" -eq 0 ] && echo "🎉 本周无故障！" || echo "$incidents" | while IFS= read -r line; do
    echo "- $line"
done)

---

## 自愈统计

| Runbook | 触发 | 成功 | 失败 |
|---------|------|------|------|
REPORT

# 添加runbook统计
if [ -f "$STATE_DIR/runbook-executions.jsonl" ]; then
    python3 -c "
import json
from collections import Counter
stats = Counter()
with open('$STATE_DIR/runbook-executions.jsonl') as f:
    for line in f:
        try:
            d = json.loads(line.strip())
            # 只看本周
            if '$(date +%Y-%m-%d)' in d.get('ts',''):
                stats[d['id'] + '_' + d['status']] += 1
        except: pass
for k, v in stats.items():
    print(f'| {k} | {v} |')
" >> "$report_file" 2>/dev/null || echo "| 暂无数据 | 0 | 0 | 0 |" >> "$report_file"
fi

cat >> "$report_file" << REPORT

---

## 待处理项

$(
    grep "^\- \[ \]" "$LESSONS_FILE" 2>/dev/null | head -5 || echo "无待处理项"
)

---

*由 ops-infra/incident-reporter.sh 自动生成*
REPORT

# 保存错误预算
python3 -c "
import json
json.dump({
    'week': '$(date +%Y-W%V)',
    'incidents': $incident_count,
    'budget_remaining': $((MAX_WEEKLY_INCIDENTS - incident_count)),
    'generated': '$(date -Is)'
}, open('$ERROR_BUDGET','w'), indent=2)
"

echo "报告已生成: $report_file"
echo ""
head -20 "$report_file"