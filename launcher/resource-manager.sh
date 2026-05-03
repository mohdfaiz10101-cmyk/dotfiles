#!/usr/bin/env bash
# 动态资源管理器 — 按需启停非核心服务
# 保护名单：绝对不停

PROTECTED="wechat-uos spectrai-office the-companion agi-brain agi-telegram-bot
           mihomo litellm letta charlie-hub plasma-kwin_wayland plasma-plasmashell
           fcitx5 pipewire wireplumber dbus ydotoold voxtype"

# whisper：voxtype 空闲超 5 分钟后停止（节省 1.7GB）
manage_whisper() {
    local status=$(voxtype status 2>/dev/null)
    if [[ "$status" == "idle" ]]; then
        local last=$(journalctl --user -u voxtype -n 1 --no-pager 2>/dev/null | grep "Recording stopped" | tail -1)
        if [[ -n "$last" ]]; then
            local last_ts=$(date -d "$(echo $last | awk '{print $1,$2,$3}')" +%s 2>/dev/null)
            local now_ts=$(date +%s)
            if (( now_ts - last_ts > 300 )); then
                systemctl --user stop whisper 2>/dev/null && echo "[OK] whisper 已停止（空闲5min）"
            fi
        fi
    elif [[ "$status" == "recording" || "$status" == "transcribing" ]]; then
        systemctl --user start whisper 2>/dev/null
    fi
}

# sunshine：无串流连接时停止（节省 ~50MB CPU）
manage_sunshine() {
    local connected=$(ss -tn | grep ":47984\|:47989\|:48010" | grep ESTAB | wc -l)
    if (( connected == 0 )); then
        systemctl --user stop sunshine 2>/dev/null && echo "[OK] sunshine 已停止（无连接）"
    fi
}

# baloo：CPU > 70% 时暂停索引
manage_baloo() {
    local cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d. -f1)
    if (( cpu > 70 )); then
        systemctl --user stop kde-baloo 2>/dev/null && echo "[SKIP] baloo 暂停（CPU ${cpu}%）"
    elif (( cpu < 30 )); then
        systemctl --user start kde-baloo 2>/dev/null
    fi
}

case "${1:-all}" in
    whisper)  manage_whisper ;;
    sunshine) manage_sunshine ;;
    baloo)    manage_baloo ;;
    all)
        manage_whisper
        manage_sunshine
        manage_baloo
        ;;
    status)
        echo "=== 资源占用前10 ==="
        ps aux --sort=-%mem | awk 'NR>1 && $4>0.3 {printf "%5.1f%% %5dMB %s\n", $4, $6/1024, $11}' | head -10
        ;;
esac

# 自动扫描新服务（内存>200MB 且不在保护名单）
auto_scan() {
    echo "=== 扫描高内存非保护服务 ==="
    systemctl --user list-units --type=service --state=active --no-pager 2>/dev/null \
    | awk '{print $1}' | grep "\.service$" | while read svc; do
        name="${svc%.service}"
        # 跳过保护名单
        if echo "$PROTECTED" | grep -qw "$name"; then continue; fi
        mem=$(systemctl --user show -p MemoryCurrent "$svc" 2>/dev/null | cut -d= -f2)
        if [[ "$mem" =~ ^[0-9]+$ ]] && (( mem > 209715200 )); then  # >200MB
            echo "[候选] $svc $(( mem/1024/1024 ))MB — 可考虑按需管理"
        fi
    done
}

if [[ "$1" == "scan" ]]; then auto_scan; fi
