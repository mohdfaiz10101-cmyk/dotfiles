#!/usr/bin/env bash
# 磁盘监控 + 智能清理 - 当根分区超过 90% 时自动清理

set -euo pipefail

THRESHOLD=90
LOG="/home/charlie/.local/share/disk-monitor.log"
mkdir -p "$(dirname "$LOG")"

# 获取根分区使用率（去掉 % 号）
USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')

echo "[$(date)] 磁盘使用率: ${USAGE}%" >> "$LOG"

if [ "$USAGE" -ge "$THRESHOLD" ]; then
    echo "[$(date)] ⚠️ 磁盘使用率超过 ${THRESHOLD}%，开始清理..." >> "$LOG"
    
    # 1. 清理 IntelliJ 缓存（如果未运行）
    if ! pgrep -f "IntelliJIdea" > /dev/null; then
        rm -rf ~/.cache/JetBrains/IntelliJIdea*/index ~/.cache/JetBrains/IntelliJIdea*/caches 2>/dev/null || true
        echo "[$(date)] ✓ 清理 IntelliJ 缓存" >> "$LOG"
    fi
    
    # 2. 清理 tmp 文件（3天前）
    find /tmp -type f -mtime +3 -delete 2>/dev/null || true
    echo "[$(date)] ✓ 清理 /tmp" >> "$LOG"
    
    # 3. 清理 paperclip 日志（14天前）
    find ~/.paperclip/instances/default/data/run-logs -name "*.ndjson" -mtime +14 -delete 2>/dev/null || true
    echo "[$(date)] ✓ 清理 paperclip 日志" >> "$LOG"
    
    # 4. 清理各种缓存备份
    find ~/.cache/memory-dream/backups -type d -mtime +3 -exec rm -rf {} + 2>/dev/null || true
    find ~/.cache -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
    echo "[$(date)] ✓ 清理缓存备份" >> "$LOG"
    
    # 5. Nix 垃圾回收（释放未使用的包）
    nix-collect-garbage -d >> "$LOG" 2>&1 || true
    echo "[$(date)] ✓ Nix 垃圾回收完成" >> "$LOG"
    
    # 6. systemd journal 清理
    sudo journalctl --vacuum-time=7d >> "$LOG" 2>&1 || true
    
    # 清理后检查
    NEW_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
    FREED=$((USAGE - NEW_USAGE))
    echo "[$(date)] ✅ 清理完成，释放 ${FREED}%，当前使用率 ${NEW_USAGE}%" >> "$LOG"
    
    # 发送通知（如果还是超过 90%）
    if [ "$NEW_USAGE" -ge "$THRESHOLD" ]; then
        notify-send "⚠️ 磁盘空间警告" "清理后仍然使用 ${NEW_USAGE}%，建议手动检查大文件" -u critical || true
    fi
else
    echo "[$(date)] ✓ 磁盘使用正常 (${USAGE}%)" >> "$LOG"
fi
