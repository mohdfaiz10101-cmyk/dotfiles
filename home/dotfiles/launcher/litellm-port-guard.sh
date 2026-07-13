#!/usr/bin/env bash
# litellm-port-guard.sh — LiteLLM 端口级健康守护
# Why: 容器 running 不代表端口可用，需检测 :4000 实际监听状态
# What: 检查端口 → 未监听则重启容器 → 等待恢复 → 仍失败则升级到 CC
# Test: 手动 docker compose stop litellm 后运行此脚本，验证自动恢复

set -euo pipefail

PORT=4000
COMPOSE_FILE="/mnt/ai-cluster/litellm/docker-compose.yml"
OP_TASKS="$HOME/.config/opencode/op-tasks.md"
LOG="$HOME/.local/share/litellm-guard/port-guard.log"
WAIT_SECONDS=90

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

# ── 检查端口是否在监听 ─────────────────────────────────────
port_listening() { ss -tlnp | grep -q ":${PORT} "; }

# ── 主流程 ─────────────────────────────────────────────────
if port_listening; then
    log "端口 ${PORT} 正常监听，无需操作"
    exit 0
fi

log "端口 ${PORT} 未监听，开始排查"

# 检查容器状态
CONTAINER_STATUS=$(docker compose -f "$COMPOSE_FILE" ps --format '{{.State}}' litellm 2>/dev/null || echo "unknown")

if [[ "$CONTAINER_STATUS" != "running" ]]; then
    log "容器未运行（状态: ${CONTAINER_STATUS}），启动容器"
    docker compose -f "$COMPOSE_FILE" up -d litellm 2>>"$LOG"
else
    log "容器运行中但端口未监听，重启容器"
    docker compose -f "$COMPOSE_FILE" restart litellm 2>>"$LOG"
fi

log "等待 ${WAIT_SECONDS} 秒（LiteLLM 启动约需 70 秒）"
sleep "$WAIT_SECONDS"

# ── 二次检查 ───────────────────────────────────────────────
if port_listening; then
    log "恢复成功，端口 ${PORT} 已监听"
    exit 0
fi

# ── 升级到 CC 排查 ─────────────────────────────────────────
DATE=$(date '+%Y-%m-%d')
FAIL_LINE="- [ ] [${DATE}] LiteLLM 端口 ${PORT} 未恢复，需 CC 排查"

log "恢复失败，写入 op-tasks 升级到 CC"

# 去重检查
if grep -qF "LiteLLM 端口 ${PORT} 未恢复" "$OP_TASKS" 2>/dev/null; then
    log "op-tasks 已有相同任务，跳过写入"
else
    mkdir -p "$(dirname "$OP_TASKS")"
    echo "$FAIL_LINE" >> "$OP_TASKS"
    log "已写入: ${FAIL_LINE}"
fi

exit 1
