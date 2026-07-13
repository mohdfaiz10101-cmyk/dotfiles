#!/usr/bin/env bash
# ============================================================
# APK 管理器 - 一键推送 APK 到安卓设备
# 用法：
#   apk-manager.sh install xxx.apk    # 安装到连接的设备
#   apk-manager.sh list               # 列出可用 APK
#   apk-manager.sh push xxx.apk       # 推送到设备不安装
#   apk-manager.sh scan               # 扫描所有设备
# ============================================================

set -euo pipefail

APK_DIR="$HOME/APKs"
mkdir -p "$APK_DIR"

log() { echo "[APK管理] $1"; }

# 检查 ADB 设备
check_device() {
    local devices
    devices=$(adb devices 2>/dev/null | grep -v "List" | grep "device$" | awk '{print $1}')
    if [[ -z "$devices" ]]; then
        log "未发现设备。请确认 USB 调试已开启或 WiFi ADB 已连接"
        log "尝试连接: adb connect <手机IP>:5555"
        return 1
    fi
    echo "$devices"
}

# 安装 APK
cmd_install() {
    local apk="$1"
    if [[ ! -f "$apk" ]]; then
        # 在 APK_DIR 里找
        apk="$APK_DIR/$apk"
    fi
    if [[ ! -f "$apk" ]]; then
        log "找不到: $apk"
        return 1
    fi

    local devices
    devices=$(check_device) || return 1

    while IFS= read -r dev; do
        log "正在安装到 $dev: $(basename "$apk")"
        adb -s "$dev" install -r "$apk" && log "安装成功: $dev" || log "安装失败: $dev"
    done <<< "$devices"
}

# 推送文件到设备
cmd_push() {
    local apk="$1"
    local dest="${2:-/sdcard/Download/}"
    if [[ ! -f "$apk" ]]; then
        apk="$APK_DIR/$apk"
    fi

    local devices
    devices=$(check_device) || return 1

    while IFS= read -r dev; do
        log "推送到 $dev: $(basename "$apk") → $dest"
        adb -s "$dev" push "$apk" "$dest"
    done <<< "$devices"
}

# 列出本地 APK
cmd_list() {
    log "APK 目录: $APK_DIR"
    if ls "$APK_DIR"/*.apk 1>/dev/null 2>&1; then
        ls -lh "$APK_DIR"/*.apk | awk '{print $5, $9}'
    else
        log "没有 APK 文件。把 APK 放到 $APK_DIR/ 即可"
    fi
}

# 扫描设备
cmd_scan() {
    log "已连接设备:"
    adb devices -l 2>/dev/null | grep -v "^List"

    log ""
    log "扫描局域网 ADB 设备 (5555端口)..."
    local subnet
    subnet=$(ip route | grep default | awk '{print $3}' | sed 's/\.[0-9]*$/./')
    for i in $(seq 1 254); do
        timeout 0.3 bash -c "echo >/dev/tcp/${subnet}${i}/5555" 2>/dev/null && \
            log "发现: ${subnet}${i}:5555" &
    done
    wait
}

# 批量安装目录下所有 APK
cmd_batch() {
    local dir="${1:-$APK_DIR}"
    local devices
    devices=$(check_device) || return 1

    for apk in "$dir"/*.apk; do
        [[ -f "$apk" ]] || continue
        log "安装: $(basename "$apk")"
        while IFS= read -r dev; do
            adb -s "$dev" install -r "$apk" 2>/dev/null && log "  $dev ✓" || log "  $dev ✗"
        done <<< "$devices"
    done
}

case "${1:-help}" in
    install|i)  cmd_install "${2:?需要指定 APK 文件}" ;;
    push|p)     cmd_push "${2:?需要指定 APK 文件}" "${3:-}" ;;
    list|l)     cmd_list ;;
    scan|s)     cmd_scan ;;
    batch|b)    cmd_batch "${2:-}" ;;
    *)
        echo "用法: $(basename "$0") <命令>"
        echo "  install <apk>   安装 APK 到所有连接设备"
        echo "  push <apk>      推送 APK 到设备(不安装)"
        echo "  list            列出本地 APK 文件"
        echo "  scan            扫描可用设备"
        echo "  batch [目录]    批量安装目录下所有 APK"
        ;;
esac
