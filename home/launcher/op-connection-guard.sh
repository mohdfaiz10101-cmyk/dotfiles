#!/run/current-system/sw/bin/bash
# op-connection-guard.sh — OP 连接守护（纯 bash，不依赖 LLM）
# 检测 OP agent 任务失败（Unable to connect），自动重试失败的服务
# 部署为 systemd timer，每 10 分钟检查一次

set -euo pipefail

LOG_DIR="/home/charlie/.config/opencode/logs/scheduler/charlie-b445f233ebb8"
REPORT="$HOME/.local/state/op-connection-guard-report.txt"
RESTART_LOG="/home/charlie/.local/share/op-connection-guard.log"
MAX_RETRIES=3

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$RESTART_LOG"
}

# ── 1. 检测 LiteLLM 连通性（OP 的核心依赖）──
check_litellm() {
    local code
    code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:4000/health 2>/dev/null || echo "000")
    if [[ "$code" == "000" || "$code" == "503" ]]; then
        log "[WARN] LiteLLM 不可达 (HTTP $code)，尝试重启"
        docker restart litellm-litellm-1 2>/dev/null || true
        sleep 10
        code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:4000/health 2>/dev/null || echo "000")
        if [[ "$code" == "000" ]]; then
            log "[FAIL] LiteLLM 重启后仍不可达"
            return 1
        fi
        log "[OK] LiteLLM 重启成功"
    fi
    return 0
}

# ── 2. 检测代理连通性（OP 需要 proxy 访问 API）──
check_proxy() {
    local code
    # 先检查 xray
    code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:7890 2>/dev/null || echo "000")
    if [[ "$code" == "000" ]]; then
        log "[WARN] Xray 不可达 (7890)，尝试重启"
        sudo systemctl restart xray 2>/dev/null || true
        sleep 3
    fi

    # 测试通过代理访问外网
    code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 -x http://127.0.0.1:7890 https://api.anthropic.com 2>/dev/null || echo "000")
    if [[ "$code" == "000" ]]; then
        log "[WARN] 代理出口不通，尝试切换到 mihomo 备用"
        # mihomo 备用检测
        code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 5 -x http://127.0.0.1:7891 https://api.anthropic.com 2>/dev/null || echo "000")
        if [[ "$code" != "000" ]]; then
            log "[OK] mihomo 备用可用"
        else
            log "[FAIL] 所有代理均不可用"
            return 1
        fi
    fi
    return 0
}

# ── 3. 扫描 OP 日志中的连接错误 ──
scan_errors() {
    local failed_agents=()
    local cutoff
    cutoff=$(date -d '30 minutes ago' '+%Y-%m-%dT%H:%M' 2>/dev/null || date -v-30M '+%Y-%m-%dT%H:%M')
    if [[ -d "$LOG_DIR" ]]; then
        for logfile in "$LOG_DIR"/*.log; do
            [[ -f "$logfile" ]] || continue
            local agent_name
            agent_name=$(basename "$logfile" .log)
            # 只检查最近 30 分钟内新增的"Unable to connect"行（按时间戳过滤）
            # 日志格式包含 ISO 时间戳，只取 >= cutoff 的行
            if tail -200 "$logfile" 2>/dev/null | grep "Unable to connect" | \
               awk -v cut="$cutoff" '{
                 for(i=1;i<=NF;i++) if($i ~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}T/) { ts=$i; break }
                 if(ts >= cut) found=1
               } END{exit !found}'; then
                failed_agents+=("$agent_name")
            fi
        done
    fi
    echo "${failed_agents[*]}"
}

# ── 4. 重启失败的 OP 服务 ──
restart_failed_services() {
    local agents=($1)
    for agent in "${agents[@]}"; do
        local service_name="opencode-job-charlie-b445f233ebb8-${agent}.service"
        local attempt_file="$HOME/.local/state/op-guard-retry-${agent}"
        local retries=0

        [[ -f "$attempt_file" ]] && retries=$(cat "$attempt_file" 2>/dev/null || echo "0")

        if [[ "$retries" -ge "$MAX_RETRIES" ]]; then
            log "[ESCALATE] $agent 已达最大重试次数 ($MAX_RETRIES)，流转到 CC 待办"
            escalate_to_cc "$agent"
            continue
        fi

        log "[RETRY] 重启 $agent (第 $((retries+1)) 次)"
        systemctl --user restart "$service_name" 2>/dev/null || true
        echo $((retries+1)) > "$attempt_file"
    done
}

# ── 5. 失败任务流转到 CC 待办 ──
escalate_to_cc() {
    local agent="$1"
    local task_file="/home/charlie/.claude/projects/-home-charlie/memory/op-tasks.md"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M')
    local task_line="- [ ] [OP→CC] [$ts] [high] OP agent $agent 连续 $MAX_RETRIES 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）"

    # 去重：检查是否已有相同 agent 的未完成任务
    if grep -q "\- \[ \].*$agent.*重启失败" "$task_file" 2>/dev/null; then
        log "[DEDUP] $agent 已有未完成的 CC 转交任务，跳过重复写入"
        return 0
    fi

    echo "$task_line" >> "$task_file"
    log "[OK] 已写入 CC 待办: $agent"
}

# ── 6. 清理重试计数（成功的 agent 重置）──
reset_retry_counts() {
    local agents=($1)
    for agent in "${agents[@]}"; do
        rm -f "$HOME/.local/state/op-guard-retry-${agent}"
    done
}

# ── 主流程 ──
main() {
    log "--- 守护巡检开始 ---"

    # 基础设施检查
    local infra_ok=true
    check_litellm || infra_ok=false
    check_proxy || infra_ok=false

    if [[ "$infra_ok" == "false" ]]; then
        log "[ALERT] 基础设施异常，跳过 agent 重启（等基础设施恢复）"
        echo "基础设施异常（LiteLLM/Proxy）" > "$REPORT"
        exit 1
    fi

    # 扫描失败的 agent
    local failed
    failed=$(scan_errors)

    if [[ -z "$failed" ]]; then
        log "[OK] 所有 OP agent 连接正常"
        echo "全部正常" > "$REPORT"
        exit 0
    fi

    log "[WARN] 发现连接异常 agent: $failed"
    echo "异常 agent: $failed" > "$REPORT"

    # 重启失败服务
    restart_failed_services "$failed"

    # 等 30 秒后验证
    sleep 30
    local still_failed
    still_failed=$(scan_errors)

    if [[ -z "$still_failed" ]]; then
        log "[OK] 重启后所有 agent 恢复正常"
        reset_retry_counts "$failed"
        echo "已修复: $failed" > "$REPORT"
    else
        log "[FAIL] 重启后仍有异常: $still_failed"
        echo "仍有异常: $still_failed" > "$REPORT"
    fi

    log "--- 守护巡检结束 ---"
}

main "$@"
