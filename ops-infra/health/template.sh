#!/usr/bin/env bash
# 健康检查模板 — 复制此文件创建新服务健康检查
# 使用: ./template.sh
# 替换: SERVICE_NAME, HOST, PORT, API_PATH

set -euo pipefail

SERVICE_NAME="{{SERVICE_NAME}}"
HOST="{{HOST:-localhost}}"
PORT="{{PORT:-8080}}"
API_PATH="{{API_PATH:-/health}}"
TIMEOUT=5

# L0: 进程存活
check_l0() {
    if systemctl --user is-active --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
        echo "L0:OK"
    elif docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^$SERVICE_NAME$"; then
        echo "L0:OK"
    else
        echo "L0:FAIL"
    fi
}

# L1: 端口监听
check_l1() {
    if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
        echo "L1:OK"
    else
        echo "L1:FAIL"
    fi
}

# L2: HTTP响应
check_l2() {
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "http://$HOST:$PORT$API_PATH" 2>/dev/null || echo "000")
    if [ "$code" = "200" ] || [ "$code" = "307" ]; then
        echo "L2:OK"
    else
        echo "L2:FAIL"
    fi
}

# L3: 数据完整性 (需根据服务自定义)
check_l3() {
    # 模板: 检查返回数据是否非空且有预期字段
    local data
    data=$(curl -s --max-time "$TIMEOUT" "http://$HOST:$PORT$API_PATH" 2>/dev/null)
    if [ -n "$data" ] && echo "$data" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "L3:OK"
    else
        echo "L3:FAIL"
    fi
}

# L4: 事务完整性 (需根据服务自定义写→读→删链路)
check_l4() {
    # 模板: 写入测试数据 → 回读验证 → 删除
    local test_key="health-check-$(date +%s)"
    # TODO: 实现服务的写→读→删逻辑
    echo "L4:SKIP"
}

# === 主逻辑 ===
if [ "${1:-}" = "--level" ]; then
    case "${2:-all}" in
        l0|0) check_l0 ;;
        l1|1) check_l1 ;;
        l2|2) check_l2 ;;
        l3|3) check_l3 ;;
        l4|4) check_l4 ;;
        *) echo "Usage: $0 --level {l0|l1|l2|l3|l4}" ;;
    esac
    exit
fi

# 全部检查
echo "=== $SERVICE_NAME 健康检查 ==="
check_l0
check_l1
check_l2
check_l3
check_l4