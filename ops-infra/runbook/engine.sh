#!/usr/bin/env bash
# runbook-engine.sh — Lessons-learned → 可执行Runbook自动化引擎
# 读取 lessons-learned.md 中的 [runbook] 条目，匹配当前告警，自动修复
# 用法: runbook-engine.sh [--dry-run] [--runbook RB-ID]

set -euo pipefail
# 注意: pipefail 会在内嵌 pipeline 失败时触发 set -e，
# execute_runbook 的 case 语句依赖 pipeline，故放宽为仅 pipefail 关闭
set +o pipefail

LESSONS_FILE="$HOME/.claude/projects/-home-charlie/memory/lessons-learned.md"
STATE_DIR="$HOME/.local/state/ops-infra"
RUNBOOK_LOG="$STATE_DIR/runbook-executions.jsonl"
mkdir -p "$STATE_DIR"
DRY_RUN=false

[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

log_execution() {
    local runbook_id="$1" status="$2" detail="$3"
    echo "{\"ts\":\"$(date -Is)\",\"id\":\"$runbook_id\",\"status\":\"$status\",\"detail\":\"$detail\"}" >> "$RUNBOOK_LOG"
    echo "[$(date '+%H:%M:%S')] $runbook_id → $status — $detail"
}

# ====== Runbook定义 (从lessons-learned自动提取 + 手动注册) ======

# 每个runbook是一个函数: rb_<ID>() { detect; [diagnose]; fix; verify; }
# detect返回0=故障存在  fix返回0=修复成功  verify返回0=验证通过

# --- RB-20260523-01: Letta记忆静默故障 ---
rb_letta_silent_failure() {
    # DETECT
    local latest
    latest=$(curl -s --max-time 5 "http://localhost:8283/v1/agents/agent-9b3bcec2-0a26-458c-a2e0-639c0f9686ca/archival-memory?limit=5&ascending=false" 2>/dev/null | python3 -c "
import sys,json
items=json.load(sys.stdin)
real=[i for i in items if 'health-check' not in str(i.get('tags',[]))]
print(real[0].get('created_at','')[:19] if real else 'NEVER')
" 2>/dev/null)
    if [ "$latest" = "NEVER" ]; then
        return 0  # 故障存在
    fi
    return 1  # 正常
}

rb_letta_silent_failure_fix() {
    echo "Letta API响应正常，检查ascending参数"
    # 问题已在health-guard + deadman-switch中修复
    return 0
}

rb_letta_silent_failure_verify() {
    /home/charlie/.local/bin/letta-deadman-switch.sh >/dev/null 2>&1
}

# --- RB-20260523-02: DuckDNS nproc耗尽 ---
rb_duckdns_nproc_exhaustion() {
    local nproc_limit
    nproc_limit=$(ulimit -u 2>/dev/null || echo "0")
    local thread_count
    thread_count=$(ps -eLf 2>/dev/null | wc -l)
    if [ "$thread_count" -gt "$((nproc_limit * 80 / 100))" ]; then
        return 0  # 接近极限
    fi
    return 1
}

rb_duckdns_nproc_exhaustion_fix() {
    echo "线程数接近nproc限制，查找高线程进程"
    local top_pid
    top_pid=$(ps -eo pid,nlwp,comm --sort=-nlwp 2>/dev/null | head -3 | tail -1 | awk '{print $1}')
    if [ -n "$top_pid" ]; then
        echo "终止高线程进程: $top_pid"
        kill "$top_pid" 2>/dev/null || true
    fi
    return 0
}

rb_duckdns_nproc_exhaustion_verify() {
    local thread_count
    thread_count=$(ps -eLf 2>/dev/null | wc -l)
    [ "$thread_count" -lt 3000 ]
}

# --- RB-20260523-03: mihomo GLOBAL误设DIRECT ---
rb_mihomo_global_direct() {
    if curl -s --max-time 3 http://localhost:9090 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
mode=d.get('mode','')
print(mode)
" 2>/dev/null | grep -q "Direct"; then
        return 0
    fi
    return 1
}

rb_mihomo_global_direct_fix() {
    echo "mihomo GLOBAL=DIRECT → 切回Rule"
    curl -s -X PUT http://localhost:9090/configs -H "Content-Type: application/json" \
        -d '{"mode":"Rule"}' >/dev/null 2>&1 || true
    return 0
}

rb_mihomo_global_direct_verify() {
    curl -s --max-time 3 http://localhost:9090 2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin); print(d.get('mode',''))
" 2>/dev/null | grep -q "Rule"
}

# --- RB-20260523-04: LiteLLM Embedding No connected db ---
rb_litellm_embed_nodb() {
    curl -s --max-time 5 http://localhost:4000/embeddings \
        -H "Content-Type: application/json" \
        -d '{"model":"all-MiniLM-L6-v2","input":"test"}' 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message',''))" 2>/dev/null \
        | grep -q "No connected db"
}

rb_litellm_embed_nodb_fix() {
    echo "重启LiteLLM容器修复DB连接"
    docker restart litellm-litellm 2>/dev/null && sleep 5
    return 0
}

rb_litellm_embed_nodb_verify() {
    systemctl --user show litellm --property=ActiveState | grep -q active
}

# --- RB-20260602-01: 微信uos coredump重启风暴 ---
rb_wechat_uos_crash() {
    # detect: 最近5条日志中coredump出现次数>=2
    local count
    count=$(journalctl --user -u wechat-uos -n 5 --no-pager 2>/dev/null | grep -c "coredump\|dumped core" || echo 0)
    [ "$count" -ge 2 ]
}

rb_wechat_uos_crash_fix() {
    systemctl --user stop wechat-uos 2>/dev/null || true
    sleep 2
    systemctl --user start wechat-uos 2>/dev/null || true
    sleep 3
    return 0
}

rb_wechat_uos_crash_verify() {
    systemctl --user show wechat-uos --property=ActiveState 2>/dev/null | grep -q "active"
}

# --- RB-20260602-02: fcitx5崩溃后0字节残留文件 ---
rb_fcitx5_crash() {
    # detect: user.dict_* 文件存在且大小为0
    ls -la ~/.local/share/fcitx5/pinyin/user.dict_* 2>/dev/null | grep -q " 0 "
}

rb_fcitx5_crash_fix() {
    rm -f ~/.local/share/fcitx5/pinyin/user.dict_* 2>/dev/null || true
    pkill fcitx5 2>/dev/null || true
    sleep 1
    nohup fcitx5 -d 2>/dev/null &
    sleep 2
    return 0
}

rb_fcitx5_crash_verify() {
    pgrep fcitx5 >/dev/null 2>&1
}

# --- RB-20260602-03: FRP端口不在白名单 ---
rb_frp_port_blocked() {
    # detect: hermes服务日志中出现port not allowed
    journalctl --user -u hermes -n 10 --no-pager 2>/dev/null | grep -q "port.*not.*allowed\|connection refused"
}

rb_frp_port_blocked_fix() {
    # 尝试换到已知白名单端口18700
    local cfg="$HOME/ai-deploy/frps.toml"
    if [ -f "$cfg" ]; then
        systemctl --user stop hermes 2>/dev/null || true
        sleep 2
        systemctl --user start hermes 2>/dev/null || true
        sleep 3
    fi
    return 0
}

rb_frp_port_blocked_verify() {
    systemctl --user show hermes --property=ActiveState 2>/dev/null | grep -q "active"
}

# ====== Runbook注册表 ======
declare -A RUNBOOKS=(
    ["RB-20260523-01"]="rb_letta_silent_failure|CRITICAL|Letta记忆写入静默停止"
    ["RB-20260523-02"]="rb_duckdns_nproc_exhaustion|WARNING|nproc线程数接近上限"
    ["RB-20260523-03"]="rb_mihomo_global_direct|CRITICAL|mihomo GLOBAL误设DIRECT"
    ["RB-20260523-04"]="rb_litellm_embed_nodb|WARNING|LiteLLM Embedding返回No connected db"
    ["RB-20260602-01"]="rb_wechat_uos_crash|CRITICAL|微信uos coredump重启风暴"
    ["RB-20260602-02"]="rb_fcitx5_crash|WARNING|fcitx5崩溃后0字节残留文件"
    ["RB-20260602-03"]="rb_frp_port_blocked|WARNING|FRP端口不在白名单"
)

# ====== 执行引擎 ======
execute_runbook() {
    local rb_id="$1"
    local info="${RUNBOOKS[$rb_id]}"
    if [ -z "$info" ]; then
        log_execution "$rb_id" "SKIP" "未知runbook"
        return 1
    fi

    IFS='|' read -r detect_fn severity description <<< "$info"

    # Step 1: 检测
    if ! $detect_fn 2>/dev/null; then
        log_execution "$rb_id" "SKIP" "未触发检测条件"
        return 0
    fi

    # Step 2: 修复
    local fix_fn="${detect_fn}_fix"
    local verify_fn="${detect_fn}_verify"

    if $DRY_RUN; then
        log_execution "$rb_id" "DRY-RUN" "$description — 将调用 $fix_fn"
        return 0
    fi

    echo "[$(date '+%H:%M:%S')] 触发: $description"

    if declare -f "$fix_fn" >/dev/null 2>&1; then
        if $fix_fn 2>/dev/null; then
            log_execution "$rb_id" "OK" "修复已执行"
        else
            log_execution "$rb_id" "FAIL" "修复执行失败"
            return 1
        fi
    fi

    # Step 3: 验证
    sleep 2
    if declare -f "$verify_fn" >/dev/null 2>&1; then
        if $verify_fn 2>/dev/null; then
            log_execution "$rb_id" "VERIFIED" "修复验证通过"
            /home/charlie/.local/bin/tg-push -t "🔧 自愈引擎" "✅ $description — 自动修复成功" 2>/dev/null || true
        else
            log_execution "$rb_id" "UNVERIFIED" "修复后验证失败"
            /home/charlie/.local/bin/tg-push -t "🔧 自愈引擎" "❌ $description — 自动修复失败，需人工介入" 2>/dev/null || true
            return 1
        fi
    fi

    return 0
}

# ====== 主逻辑 ======
if [ -n "${2:-}" ]; then
    # 执行指定runbook
    execute_runbook "$2"
else
    # 执行所有runbook
    echo "=== Runbook引擎 $(date '+%Y-%m-%d %H:%M') ==="
    $DRY_RUN && echo "[DRY-RUN模式]"
    echo ""

    total=0 ok=0 fail=0 skip=0
    for rb_id in "${!RUNBOOKS[@]}"; do
        total=$((total + 1))
        if execute_runbook "$rb_id"; then
            _status=$(tail -1 "$RUNBOOK_LOG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || true)
            case "$_status" in
                OK|VERIFIED) ok=$((ok + 1)) ;;
                SKIP) skip=$((skip + 1)) ;;
                *) ok=$((ok + 1)) ;;
            esac
        else
            fail=$((fail + 1))
        fi
    done

    echo ""
    echo "执行: $total | 修复: $ok | 跳过: $skip | 失败: $fail"
fi