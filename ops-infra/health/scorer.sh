#!/usr/bin/env bash
# health-scorer.sh — 统一健康评分引擎
# 扫描所有已注册服务，按L0-L4深度评分，输出汇总
# 用法: health-scorer.sh [--service name] [--json] [--summary]
# 新系统部署: 修改 SERVICE_LIST 数组

# 不使用 set -e: 健康检查脚本会故意遇到FAIL，不应触发退出

STATE_DIR="$HOME/.local/state/ops-infra"
SCORE_FILE="$STATE_DIR/health-scores.jsonl"
mkdir -p "$STATE_DIR"

# ====== 服务注册表 (新系统需修改此处) ======
# 格式: "服务名|host|port|path|type"
# type: systemd=docker=systemd user, docker=docker容器, both=双重检查
SERVICE_LIST=(
    "letta|localhost|8283|/health|docker"
    "litellm|localhost|4000|/health|docker"
    "agi-gateway|localhost|9900|/|systemd"
    "hub-api|localhost|9801|/health|systemd"
    "agi-frontend|localhost|3000|/|systemd"
    "mihomo|localhost|9090|/|systemd"
    "letta-db|localhost|5432||docker"
    "letta-chromadb|localhost|8000|/api/v1/heartbeat|docker"
)

# ====== 单服务L0-L4检查 ======
check_service() {
    set +e  # 防止((total++))从0开始时触发set -e
    local name="$1" host="$2" port="$3" path="$4" type="$5"
    local l0="SKIP" l1="SKIP" l2="SKIP" l3="SKIP" l4="SKIP"
    local ok=0 total=0

    # L0: 进程存活
    case "$type" in
        systemd)
            if systemctl --user is-active --quiet "${name}.service" 2>/dev/null; then
                l0="PASS"
            elif systemctl is-active --quiet "${name}.service" 2>/dev/null; then
                l0="PASS"
            else
                l0="FAIL"
            fi
            ;;
        docker)
            if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
                l0="PASS"
            else
                l0="FAIL"
            fi
            ;;
        both)
            if systemctl --user is-active --quiet "${name}.service" 2>/dev/null || docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
                l0="PASS"
            else
                l0="FAIL"
            fi
            ;;
    esac
    [ "$l0" = "PASS" ] && ((ok++)) || true
    ((total++))

    # L1: 端口监听
    if [ -n "$port" ] && [ "$port" != "0" ]; then
        if ss -tlnp 2>/dev/null | grep -q ":$port "; then
            l1="PASS"; ((ok++))
        else
            l1="FAIL"
        fi
        ((total++))
    fi

    # L2: HTTP响应
    if [ -n "$port" ] && [ "$port" != "0" ] && [ -n "$path" ]; then
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$host:$port$path" 2>/dev/null || echo "000")
        if [ "$code" = "200" ] || [ "$code" = "307" ]; then
            l2="PASS"; ((ok++))
        else
            l2="FAIL"
        fi
        ((total++))
    fi

    # L3: 数据完整性 (JSON验证)
    if [ -n "$port" ] && [ "$port" != "0" ] && [ -n "$path" ]; then
        local data
        data=$(curl -s --max-time 5 "http://$host:$port$path" 2>/dev/null)
        if [ -n "$data" ] && echo "$data" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
            l3="PASS"; ((ok++))
        else
            l3="FAIL"
        fi
        ((total++))
    fi

    # L4: 事务完整性 (需要服务特定逻辑，默认SKIP)
    l4="SKIP"

    local score=0
    [ "$total" -gt 0 ] && score=$((ok * 100 / total))

    echo "$name|$l0|$l1|$l2|$l3|$l4|$score|$total"
}

# ====== 评分等级 ======
score_grade() {
    local score="$1"
    if [ "$score" -ge 100 ]; then echo "🟢优秀"
    elif [ "$score" -ge 75 ]; then echo "🟡良好"
    elif [ "$score" -ge 50 ]; then echo "🟠警告"
    elif [ "$score" -ge 25 ]; then echo "🔴危险"
    else echo "💀死亡"
    fi
}

# ====== 主逻辑 ======
OUTPUT_FORMAT="${1:-table}"  # table, json, summary

if [ "$OUTPUT_FORMAT" = "--json" ]; then
    echo "["
    first=true
    for svc in "${SERVICE_LIST[@]}"; do
        IFS='|' read -r name host port path type <<< "$svc"
        result=$(check_service "$name" "$host" "$port" "$path" "$type")
        IFS='|' read -r n l0 l1 l2 l3 l4 score total <<< "$result"
        $first || echo ","
        first=false
        printf '  {"service":"%s","l0":"%s","l1":"%s","l2":"%s","l3":"%s","l4":"%s","score":%s}' "$n" "$l0" "$l1" "$l2" "$l3" "$l4" "$score"
    done
    echo ""
    echo "]"
elif [ "$OUTPUT_FORMAT" = "--summary" ]; then
    total_ok=0 total_svc=0 total_fail=0
    for svc in "${SERVICE_LIST[@]}"; do
        IFS='|' read -r name host port path type <<< "$svc"
        result=$(check_service "$name" "$host" "$port" "$path" "$type")
        IFS='|' read -r n l0 l1 l2 l3 l4 score total <<< "$result"
        ((total_svc++))
        [ "$l0" = "FAIL" ] && ((total_fail++))
    done
    echo "服务总数: $total_svc | 存活: $((total_svc - total_fail)) | 故障: $total_fail"
else
    # 表格输出
    printf "%-15s %6s %6s %6s %6s %6s %6s %s\n" "服务" "L0" "L1" "L2" "L3" "L4" "评分" "等级"
    printf "%-15s %6s %6s %6s %6s %6s %6s %s\n" "────" "──" "──" "──" "──" "──" "──" "──"

    overall_score=0 overall_count=0
    for svc in "${SERVICE_LIST[@]}"; do
        IFS='|' read -r name host port path type <<< "$svc"
        result=$(check_service "$name" "$host" "$port" "$path" "$type")
        IFS='|' read -r n l0 l1 l2 l3 l4 score total <<< "$result"
        grade=$(score_grade "$score")
        printf "%-15s %6s %6s %6s %6s %6s %5s%% %s\n" "$n" "$l0" "$l1" "$l2" "$l3" "$l4" "$score" "$grade"
        overall_score=$((overall_score + score))
        ((overall_count++))
    done

    echo ""
    overall=$((overall_score / (overall_count > 0 ? overall_count : 1)))
    echo "整体评分: ${overall}% — $(score_grade "$overall")"

    # 记录到日志
    echo "{\"ts\":\"$(date -Is)\",\"overall\":$overall,\"services\":$overall_count}" >> "$SCORE_FILE"
fi