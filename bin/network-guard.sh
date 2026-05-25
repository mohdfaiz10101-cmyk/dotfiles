#!/usr/bin/env bash
# network-guard.sh — WiFi 断连自动恢复 + FRP 重连保障
# 检测 WiFi 断开 → 重连 → 确认 FRP 通 → 不通则重启 frpc
set -euo pipefail

STATE_DIR="$HOME/.local/state/network-guard"
mkdir -p "$STATE_DIR"

WIFI_DEV="wlp0s20f0u5"
WIFI_CONN="PDCN 1"
FRPC_SERVICE="frpc.service"
GATEWAY="192.168.123.1"
FAIL_COUNT_FILE="$STATE_DIR/wifi-fail-count"
MAX_FAILS=3

fail_count=$(cat "$FAIL_COUNT_FILE" 2>/dev/null || echo 0)

# 1. 检查 WiFi 设备状态
wifi_state=$(nmcli -t -f DEVICE,STATE dev status 2>/dev/null | grep "^$WIFI_DEV:" | cut -d: -f2)

if [ "$wifi_state" = "connected" ]; then
    # WiFi 连着，测试网关可达性
    if ping -c 1 -W 3 "$GATEWAY" >/dev/null 2>&1; then
        # 一切正常，清零
        echo 0 > "$FAIL_COUNT_FILE"
        exit 0
    fi
    # 连着但网关不通 → 可能路由器问题
    fail_count=$((fail_count + 1))
    echo "$fail_count" > "$FAIL_COUNT_FILE"
    if [ "$fail_count" -ge "$MAX_FAILS" ]; then
        notify-send -u critical "网络守护" "WiFi 已连接但网关不可达，尝试重连" 2>/dev/null || true
        nmcli connection down "$WIFI_CONN" 2>/dev/null || true
        sleep 2
        nmcli connection up "$WIFI_CONN" 2>/dev/null || true
        echo 0 > "$FAIL_COUNT_FILE"
    fi
    exit 0
fi

# 2. WiFi 未连接 → 自动重连
notify-send -u normal "网络守护" "WiFi 已断开($wifi_state)，正在重连..." 2>/dev/null || true
fail_count=$((fail_count + 1))
echo "$fail_count" > "$FAIL_COUNT_FILE"

# 尝试重连
nmcli connection up "$WIFI_CONN" 2>/dev/null
sleep 3

# 3. 验证重连
if nmcli -t -f DEVICE,STATE dev status 2>/dev/null | grep -q "^$WIFI_DEV:connected"; then
    notify-send -u normal "网络守护" "WiFi 重连成功" 2>/dev/null || true
    echo 0 > "$FAIL_COUNT_FILE"
else
    notify-send -u critical "网络守护" "WiFi 重连失败(第${fail_count}次)" 2>/dev/null || true
fi

# 4. 检查 FRP — WiFi 恢复后确保 FRP 重连
sleep 2
if ! ping -c 1 -W 2 "$GATEWAY" >/dev/null 2>&1; then
    exit 0  # 网络还没恢复，等下次
fi

# 检查 frpc 是否需要重启（连接超过 2 小时或异常）
frpc_pid=$(systemctl --user show "$FRPC_SERVICE" -p MainPID --value 2>/dev/null || echo 0)
if [ "$frpc_pid" = "0" ]; then
    systemctl --user restart "$FRPC_SERVICE" 2>/dev/null || true
    notify-send -u normal "网络守护" "FRP 已重启" 2>/dev/null || true
fi
