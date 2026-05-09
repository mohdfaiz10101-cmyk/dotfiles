#!/usr/bin/env bash
# Docker Compose 有序启动脚本
# 启动顺序：基础设施 → 核心服务 → 依赖服务 → 辅助服务
set -euo pipefail

COMPOSE="docker compose"
WAIT_TIMEOUT=120

wait_healthy() {
    local container=$1 timeout=${2:-$WAIT_TIMEOUT}
    echo "[startup] 等待 $container 健康..."
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        local status
        status=$(docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "missing")
        if [ "$status" = "healthy" ]; then
            echo "[startup] $container ✓ 健康 (${elapsed}s)"
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    echo "[startup] $container ✗ 超时 (${timeout}s)，继续启动其他服务"
    return 1
}

wait_port() {
    local host=$1 port=$2 timeout=${3:-60}
    echo "[startup] 等待 ${host}:${port}..."
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -sf --connect-timeout 2 "http://${host}:${port}" -o /dev/null 2>/dev/null; then
            echo "[startup] ${host}:${port} ✓ (${elapsed}s)"
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    echo "[startup] ${host}:${port} ✗ 超时"
    return 1
}

# ── Tier 1: 基础设施（数据库、缓存）──
echo "=== Tier 1: 基础设施 ==="
$COMPOSE -f /mnt/ai/ai-cluster/litellm/docker-compose.yml up -d
$COMPOSE -f /mnt/ai/ai-cluster/letta/docker-compose.yml up -d --no-deps postgres chromadb
$COMPOSE -f /mnt/ai/ai-cluster/langfuse/docker-compose.yml up -d --no-deps langfuse-db
$COMPOSE -f /mnt/ai/ai-cluster/twenty-crm/docker-compose.yml up -d --no-deps twenty-db-1 twenty-redis-1

wait_healthy litellm-redis 60
wait_healthy letta-db 60
wait_healthy langfuse-db 60

# ── Tier 2: 核心网关（LiteLLM）──
echo "=== Tier 2: 核心网关 ==="
$COMPOSE -f /mnt/ai/ai-cluster/litellm/docker-compose.yml up -d
wait_healthy litellm-litellm 90
wait_port localhost 4000 60

# ── Tier 3: AI 服务（依赖 LiteLLM）──
echo "=== Tier 3: AI 服务 ==="
$COMPOSE -f /mnt/ai/ai-cluster/letta/docker-compose.yml up -d
$COMPOSE -f /mnt/ai/ai-cluster/langfuse/docker-compose.yml up -d
$COMPOSE -f /mnt/ai/ai-cluster/twenty-crm/docker-compose.yml up -d

wait_healthy letta 90 || true
wait_healthy langfuse 60 || true

# ── Tier 4: 辅助服务 ──
echo "=== Tier 4: 辅助服务 ==="
$COMPOSE -f /mnt/ai/apps/musetalk/docker-compose.yml up -d 2>/dev/null || true
$COMPOSE -f /home/charlie/agi/docker/virtual-person/docker-compose.yml up -d 2>/dev/null || true

echo "=== 全部启动完成 ==="
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null
