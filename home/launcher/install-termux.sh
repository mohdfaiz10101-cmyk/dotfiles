#!/usr/bin/env bash
# ============================================================
# Termux 自动安装脚本
# 功能：下载 Termux APK → 连接平板 → 推送安装
# ============================================================

set -euo pipefail

APK_DIR="$HOME/APKs"
TERMUX_APK="$APK_DIR/termux-arm64.apk"
TERMUX_VERSION="0.118.3"
# 多个备用下载源
DOWNLOAD_URLS=(
    "https://f-droid.org/repo/com.termux_1002.apk"
    "https://github.com/termux/termux-app/releases/download/v${TERMUX_VERSION}/termux-app_v${TERMUX_VERSION}+apt-android-7-github-debug_arm64-v8a.apk"
    "https://mirrors.tuna.tsinghua.edu.cn/fdroid/repo/com.termux_1002.apk"
)

log() { echo "[Termux安装] $1"; }
error() { echo "[错误] $1" >&2; exit 1; }

# 1. 下载 Termux APK
download_termux() {
    mkdir -p "$APK_DIR"

    if [[ -f "$TERMUX_APK" ]]; then
        local size=$(stat -c%s "$TERMUX_APK" 2>/dev/null || stat -f%z "$TERMUX_APK" 2>/dev/null)
        if [[ $size -gt 100000 ]]; then
            log "APK 已存在: $TERMUX_APK ($(du -h "$TERMUX_APK" | cut -f1))"
            return 0
        fi
    fi

    log "下载 Termux ${TERMUX_VERSION}..."

    # 尝试所有下载源
    local success=0
    for url in "${DOWNLOAD_URLS[@]}"; do
        log "尝试: $url"

        if command -v wget &>/dev/null; then
            if timeout 30 wget --no-proxy -O "$TERMUX_APK" "$url" 2>/dev/null || \
               timeout 30 wget -O "$TERMUX_APK" "$url" 2>/dev/null; then
                success=1
                break
            fi
        elif command -v curl &>/dev/null; then
            if timeout 30 curl --noproxy '*' -L -o "$TERMUX_APK" "$url" 2>/dev/null || \
               timeout 30 curl -L -o "$TERMUX_APK" "$url" 2>/dev/null; then
                success=1
                break
            fi
        fi
    done

    if [[ $success -eq 0 ]]; then
        log ""
        log "========== 自动下载失败，请手动下载 =========="
        log "1. 在浏览器中打开以下任一链接："
        for url in "${DOWNLOAD_URLS[@]}"; do
            log "   $url"
        done
        log ""
        log "2. 下载完成后，将 APK 文件移动到："
        log "   $TERMUX_APK"
        log ""
        log "3. 重新运行此脚本"
        log "=============================================="
        exit 1
    fi

    # 验证下载
    local size=$(stat -c%s "$TERMUX_APK" 2>/dev/null || stat -f%z "$TERMUX_APK" 2>/dev/null)
    if [[ $size -lt 100000 ]]; then
        error "下载失败，文件太小: ${size} 字节"
    fi

    log "下载完成: $(du -h "$TERMUX_APK" | cut -f1)"
}

# 2. 扫描并连接平板
connect_tablet() {
    log "检查 ADB 设备..."

    # 检查已连接设备
    local devices=$(adb devices 2>/dev/null | grep -v "List" | grep "device$" | awk '{print $1}')
    if [[ -n "$devices" ]]; then
        log "已连接设备: $devices"
        return 0
    fi

    log "未发现设备，尝试扫描局域网..."

    # 获取局域网段
    local subnet=$(ip route | grep default | awk '{print $3}' | sed 's/\.[0-9]*$/\./')
    log "扫描网段: ${subnet}0/24"

    # 扫描常见 IP
    local found=0
    for ip in 100 101 102 103 104 105 106 107 108 109 110; do
        timeout 0.5 bash -c "echo >/dev/tcp/${subnet}${ip}/5555" 2>/dev/null && {
            log "发现设备: ${subnet}${ip}:5555"
            adb connect "${subnet}${ip}:5555" && found=1 && break
        }
    done

    if [[ $found -eq 0 ]]; then
        log ""
        log "========== 平板连接指南 =========="
        log "1. 在平板上启用 USB 调试："
        log "   设置 → 关于平板 → 连续点击版本号 7 次 → 开发者选项 → USB 调试"
        log ""
        log "2. 启用无线 ADB（推荐）："
        log "   开发者选项 → 无线调试 → 使用配对码配对设备"
        log "   或者运行: adb tcpip 5555"
        log ""
        log "3. 手动连接："
        log "   adb connect <平板IP>:5555"
        log ""
        log "4. 重新运行此脚本"
        log "=================================="
        exit 1
    fi
}

# 3. 安装 Termux
install_termux() {
    local devices=$(adb devices 2>/dev/null | grep -v "List" | grep "device$" | awk '{print $1}')
    if [[ -z "$devices" ]]; then
        error "没有连接的设备"
    fi

    while IFS= read -r dev; do
        log "正在安装到 $dev..."

        # 尝试安装
        if adb -s "$dev" install -r "$TERMUX_APK" 2>&1 | tee /tmp/termux-install.log; then
            log "✓ 安装成功: $dev"
        elif grep -q "INSTALL_FAILED_UPDATE_INCOMPATIBLE" /tmp/termux-install.log; then
            log "检测到旧版本，尝试卸载后重装..."
            adb -s "$dev" uninstall com.termux 2>/dev/null || true
            adb -s "$dev" install "$TERMUX_APK" && log "✓ 重装成功: $dev" || error "重装失败"
        else
            error "安装失败: $dev"
        fi

        # 验证安装
        if adb -s "$dev" shell pm list packages | grep -q "com.termux"; then
            log "✓ 验证成功: Termux 已安装"
        else
            error "验证失败: 未找到 Termux 包"
        fi
    done <<< "$devices"
}

# 4. 配置 Termux（可选）
configure_termux() {
    log ""
    log "========== Termux 配置建议 =========="
    log "1. 打开 Termux 并运行以下命令："
    log "   pkg update && pkg upgrade"
    log "   pkg install openssh termux-api"
    log ""
    log "2. 启动 SSH 服务器："
    log "   sshd"
    log "   passwd  # 设置密码"
    log ""
    log "3. 从 NixOS 连接："
    log "   ssh -p 8022 <平板IP>"
    log ""
    log "4. 安装常用工具："
    log "   pkg install git python nodejs vim"
    log "===================================="
}

# 主流程
main() {
    log "开始 Termux 自动安装流程..."

    download_termux
    connect_tablet
    install_termux
    configure_termux

    log ""
    log "✓ 安装完成！"
}

main "$@"
