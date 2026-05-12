#!/usr/bin/env bash
# 等待 LiteLLM 健康后再启动依赖服务
# 最多等待 60 秒，轮询端口 4000 和 4002
set -e

MAX_RETRIES=30  # 30 * 2s = 60s
SLEEP=2
URLS=("http://localhost:4000/v1/models" "http://localhost:4002/v1/models")
TOKEN="Authorization: Bearer sk-litellm-charlie-2026"

for url in "${URLS[@]}"; do
    for i in $(seq 1 "$MAX_RETRIES"); do
        if curl -sf "$url" -H "$TOKEN" >/dev/null 2>&1; then
            break
        fi
        sleep "$SLEEP"
    done
done

exec "$@"
