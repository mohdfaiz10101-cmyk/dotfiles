#!/usr/bin/env bash
# 紧急磁盘清理 - Layer 4: 一键救命
# 用法: bash ~/launcher/disk-emergency.sh

set -euo pipefail

echo "⚠️ 紧急清理模式启动..."
echo "当前状态:"
df -h / | tail -1

echo ""
echo "1/5 删除所有旧 Nix generation..."
nix-collect-garbage -d 2>&1 || true

echo "2/5 清理所有临时文件..."
find /tmp -type f -delete 2>/dev/null || true

echo "3/5 压缩系统日志..."
sudo journalctl --vacuum-size=100M 2>&1 || true

echo "4/5 清理缓存..."
find /home/charlie/.cache -type f -name "*.log" -delete 2>/dev/null || true
rm -rf /home/charlie/.cache/JetBrains/*/index 2>/dev/null || true

echo "5/5 Docker 清理..."
docker system prune -af 2>/dev/null || true

echo ""
echo "清理完成！最终状态:"
df -h / | tail -1
