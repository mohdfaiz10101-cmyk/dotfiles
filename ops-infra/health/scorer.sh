#!/usr/bin/env bash
# health-scorer.sh v2 — 统一健康评分引擎 + 空跑检测 + L4事务测试
# 用法: health-scorer.sh [--json] [--summary] [--self-test]
# 新系统: 修改 SERVICE_LIST 后运行 --self-test 验证服务存在性

STATE_DIR="$HOME/.local/state/ops-infra"
SCORE_FILE="$STATE_DIR/health-scores.jsonl"
mkdir -p "$STATE_DIR"

# ====== 服务注册表 ======
# 格式: "服务名|host|port|l2_path|l3_check_type|l4_script|type"
# type: systemd/docker/both
# l3_check_type: json/html/none (HTML检查title/body, JSON验证结构, none跳过)
# l4_script: 事务测试函数名 (空=SKIP)
SERVICE_LIST=(
    "letta|localhost|8283|/v1/agents/|json|test_letta_write_read|docker"
    "litellm-litellm|localhost|4000||none||docker"
    "agi-gateway|localhost|9900|/docs|html||systemd"
    "hub-api|localhost|9800|/|html||systemd"
    "agi-frontend|localhost|3000|/|html|test_frontend_content|systemd"
    "mihomo|localhost|9090|/|html||systemd"
    "letta-db|localhost|0||none||docker"
    "letta-chromadb|localhost|8000|/api/v2/heartbeat|json||docker"
)

# ====== L4 事务测试函数 ======

test_letta_write_read() {
    # Letta: 写入 → 回读 → 删除 → 确认删除
    local test_id="l4-$(date +%s)"
    local agent="agent-9b3bcec2-0a26-458c-a2e0-639c0f9686ca"

    # Write
    local write_resp
    write_resp=$(curl -s -X POST "http://localhost:8283/v1/agents/$agent/archival-memory" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"$test_id\",\"tags\":[\"l4-test\"]}" --max-time 5 2>/dev/null)
    local passage_id
    passage_id=$(echo "$write_resp" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    if isinstance(d,list) and d: print(d[0].get('id',''))
    elif isinstance(d,dict) and 'detail' in d: print('API_ERR')
    else: print('')
except: print('PARSE_ERR')
" 2>/dev/null)

    case "$passage_id" in
        ""|"PARSE_ERR"|"API_ERR")
            echo "L4:FAIL($passage_id)"
            return 1 ;;
    esac

    # Read back (ascending=false!)
    sleep 1
    local read_back
    read_back=$(curl -s "http://localhost:8283/v1/agents/$agent/archival-memory?limit=50&ascending=false" --max-time 5 2>/dev/null)
    local found
    found=$(echo "$read_back" | python3 -c "
import sys,json
items=json.load(sys.stdin)
match=[i for i in items if '$test_id' in i.get('text','')]
print('1' if match else '0')
" 2>/dev/null)

    [ "$found" != "1" ] && echo "L4:FAIL(read)" && return 1

    # Delete (best effort)
    curl -s -X DELETE "http://localhost:8283/v1/agents/$agent/archival-memory/$passage_id" --max-time 5 >/dev/null 2>&1

    echo "L4:PASS"
    return 0
}

test_frontend_content() {
    # 3000前端: 检查HTML含关键标识
    local html
    html=$(curl -s --max-time 5 "http://localhost:3000/" 2>/dev/null)
    if echo "$html" | grep -q "AGI Control Plane"; then
        echo "L4:PASS"
        return 0
    else
        echo "L4:FAIL(no-title)"
        return 1
    fi
}

# ====== 空跑检测: 验证服务是否存在 ======
self_test() {
    echo "=== 空跑检测 (--self-test) ==="
    echo ""
    local ghosts=0
    for svc in "${SERVICE_LIST[@]}"; do
        IFS='|' read -r name host port path l3_type l4_script type <<< "$svc"
        local found=false
        case "$type" in
            systemd)
                systemctl --user is-active --quiet "${name}.service" 2>/dev/null && found=true
                systemctl is-active --quiet "${name}.service" 2>/dev/null && found=true
                ;;
            docker)
                docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$name" && found=true
                ;;
            both)
                systemctl --user is-active --quiet "${name}.service" 2>/dev/null && found=true
                docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$name" && found=true
                ;;
        esac
        if $found; then
            echo "  ✅ $name ($type)"
        else
            echo "  👻 $name ($type) — 服务不存在!"
            ((ghosts++))
        fi
    done
    echo ""
    if [ "$ghosts" -gt 0 ]; then
        echo "⚠️ $ghosts 个鬼服务 — 从SERVICE_LIST删除或修复L0检测"
    else
        echo "✅ 无鬼服务"
    fi
    [ "$ghosts" -eq 0 ]
}

# ====== 单服务检查 ======
check_service() {
    local name="$1" host="$2" port="$3" path="$4" l3_type="$5" l4_script="$6" type="$7"
    local l0="SKIP" l1="SKIP" l2="SKIP" l3="SKIP" l4="SKIP"
    local ok=0 total=0

    # L0: 进程存活
    case "$type" in
        systemd)
            if systemctl --user is-active --quiet "${name}.service" 2>/dev/null; then l0="PASS"
            elif systemctl is-active --quiet "${name}.service" 2>/dev/null; then l0="PASS"
            else l0="FAIL"; fi ;;
        docker)
            if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$name"; then l0="PASS"
            else l0="FAIL"; fi ;;
        both)
            if systemctl --user is-active --quiet "${name}.service" 2>/dev/null || \
               docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$name"; then l0="PASS"
            else l0="FAIL"; fi ;;
    esac
    [ "$l0" = "PASS" ] && ok=$((ok + 1))
    total=$((total + 1))

    # L1: 端口监听 (port=0跳过,docker内部网络)
    if [ -n "$port" ] && [ "$port" != "0" ]; then
        if ss -tlnp 2>/dev/null | grep -q ":$port "; then l1="PASS"; ok=$((ok + 1))
        else l1="FAIL"; fi
        total=$((total + 1))
    fi

    # L2: HTTP响应
    if [ -n "$path" ] && [ -n "$port" ]; then
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$host:$port$path" 2>/dev/null || echo "000")
        if [ "$code" = "200" ] || [ "$code" = "307" ] || [ "$code" = "401" ] || [ "$code" = "403" ]; then
            # 401/403也算L2通过（服务活着，只是需要认证）
            l2="PASS"; ok=$((ok + 1))
        else l2="FAIL"; fi
        total=$((total + 1))
    fi

    # L3: 数据完整性
    if [ -n "$path" ] && [ -n "$port" ] && [ "$l3_type" != "none" ]; then
        local data
        data=$(curl -s --max-time 5 "http://$host:$port$path" 2>/dev/null)
        case "$l3_type" in
            json)
                if [ -n "$data" ] && echo "$data" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
                    l3="PASS"; ok=$((ok + 1))
                else l3="FAIL"; fi ;;
            html)
                if echo "$data" | grep -qE '<html|<body|<div'; then
                    l3="PASS"; ok=$((ok + 1))
                else l3="FAIL"; fi ;;
        esac
        total=$((total + 1))
    fi

    # L4: 事务完整性
    l4_result=""
    if [ -n "$l4_script" ] && declare -f "$l4_script" >/dev/null 2>&1; then
        l4_result=$($l4_script 2>/dev/null)
        if [ "$l4_result" = "L4:PASS" ]; then l4="PASS"; ok=$((ok + 1))
        else l4="FAIL"; fi
        total=$((total + 1))
    fi

    local score=0
    [ "$total" -gt 0 ] && score=$((ok * 100 / total))

    # 空跑警告: L0=L1=PASS但L2=SKIP/Fail → 可能是路径错误
    local ghost=""
    if [ "$l0" = "PASS" ] && [ "$l1" = "PASS" ] && { [ "$l2" = "SKIP" ] || [ "$l2" = "FAIL" ]; }; then
        ghost=" 👻NOOP"
    fi

    echo "$name|$l0|$l1|$l2|$l3|$l4|$score|$total|$ghost"
}

# ====== 评分等级 ======
score_grade() {
    local score="$1"
    if [ "$score" -ge 100 ]; then echo "🟢优秀"
    elif [ "$score" -ge 75 ]; then echo "🟡良好"
    elif [ "$score" -ge 50 ]; then echo "🟠警告"
    elif [ "$score" -ge 25 ]; then echo "🔴危险"
    else echo "💀死亡"; fi
}

# ====== 主逻辑 ======
case "${1:-table}" in
    --self-test)
        self_test
        exit ;;
    --json)
        echo "["
        first=true
        for svc in "${SERVICE_LIST[@]}"; do
            IFS='|' read -r name host port path l3_type l4_script type <<< "$svc"
            result=$(check_service "$name" "$host" "$port" "$path" "$l3_type" "$l4_script" "$type")
            IFS='|' read -r n l0 l1 l2 l3 l4 score total ghost <<< "$result"
            $first || echo ","
            first=false
            printf '  {"service":"%s","l0":"%s","l1":"%s","l2":"%s","l3":"%s","l4":"%s","score":%s,"noop":%s}' \
                "$n" "$l0" "$l1" "$l2" "$l3" "$l4" "$score" "$([ -n "$ghost" ] && echo "true" || echo "false")"
        done
        echo ""
        echo "]" ;;
    --summary)
        total_ok=0 total_svc=0 total_fail=0 noop_count=0
        for svc in "${SERVICE_LIST[@]}"; do
            IFS='|' read -r name host port path l3_type l4_script type <<< "$svc"
            result=$(check_service "$name" "$host" "$port" "$path" "$l3_type" "$l4_script" "$type")
            IFS='|' read -r n l0 l1 l2 l3 l4 score total ghost <<< "$result"
            total_svc=$((total_svc + 1))
            [ "$l0" = "FAIL" ] && total_fail=$((total_fail + 1))
            [ -n "$ghost" ] && noop_count=$((noop_count + 1))
        done
        echo "服务: $total_svc | 存活: $((total_svc - total_fail)) | 故障: $total_fail | 空跑: $noop_count" ;;
    *)
        printf "%-18s %6s %6s %6s %6s %6s %6s %s\n" "服务" "L0" "L1" "L2" "L3" "L4" "评分" "等级"
        printf "%-18s %6s %6s %6s %6s %6s %6s %s\n" "────" "──" "──" "──" "──" "──" "──" "──"

        overall=0 count=0 noop_total=0
        for svc in "${SERVICE_LIST[@]}"; do
            IFS='|' read -r name host port path l3_type l4_script type <<< "$svc"
            result=$(check_service "$name" "$host" "$port" "$path" "$l3_type" "$l4_script" "$type")
            IFS='|' read -r n l0 l1 l2 l3 l4 score total ghost <<< "$result"
            grade=$(score_grade "$score")
            printf "%-18s %6s %6s %6s %6s %6s %5s%% %s%s\n" "$n" "$l0" "$l1" "$l2" "$l3" "$l4" "$score" "$grade" "$ghost"
            overall=$((overall + score))
            count=$((count + 1))
            [ -n "$ghost" ] && noop_total=$((noop_total + 1))
        done

        echo ""
        avg=$((overall / (count > 0 ? count : 1)))
        echo "整体评分: ${avg}% — $(score_grade "$avg")"
        [ "$noop_total" -gt 0 ] && echo "👻 空跑警告: $noop_total 个服务L0/L1正常但L2无法验证 (路径可能错误)"

        echo "{\"ts\":\"$(date -Is)\",\"overall\":$avg,\"services\":$count,\"noop\":$noop_total}" >> "$SCORE_FILE"
        ;;
esac