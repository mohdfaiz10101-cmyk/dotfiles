#!/usr/bin/env bash
# 自动磁盘清理脚本 - 每周日执行

set -euo pipefail

LOG="$HOME/.local/log/disk-cleanup.log"
mkdir -p "$(dirname "$LOG")"
echo "[$(date)] 开始磁盘清理" >> "$LOG"

# 1. 清理 tmp 旧文件（7天前）
find /tmp -type f -mtime +7 -delete 2>/dev/null || true

# 2. 清理 paperclip 日志（30天前）
find ~/.paperclip/instances/default/data/run-logs -name "*.ndjson" -mtime +30 -delete 2>/dev/null || true

# 3. 清理 memory-dream 备份（7天前）
find ~/.cache/memory-dream/backups -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

# 4. 清理 systemd journal（保留1个月）- 跳过（需要root权限）
# sudo journalctl --vacuum-time=30d >> "$LOG" 2>&1

# 5. Nix store 垃圾回收（删除未使用的包）- 跳过（需要root权限，避免误删）
# nix-collect-garbage -d >> "$LOG" 2>&1

echo "[$(date)] 清理完成" >> "$LOG"
df -h / >> "$LOG"
