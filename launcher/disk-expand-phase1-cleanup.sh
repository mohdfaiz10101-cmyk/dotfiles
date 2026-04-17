#!/bin/bash
# ============================================================
# 阶段 1：在线清理（在当前 NixOS 中执行）
# 目标：清理垃圾 + 迁移非必要数据到 POOL-D1
# 预计释放：~5-7G
# ============================================================
set -euo pipefail

TARGET="/mnt/pool-disks/POOL-D1/home-offload"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[Phase1]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[FAIL]${NC} $1"; }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  阶段 1：在线清理 + 数据迁移"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
df -h / | tail -1
echo ""

# 检查目标盘
if [ ! -d "$TARGET" ]; then
    mkdir -p "$TARGET"
fi

if ! mountpoint -q /mnt/pool-disks/POOL-D1 2>/dev/null; then
    err "POOL-D1 未挂载！请先执行 disk-pool-mount.sh"
    exit 1
fi

# ---- 1. 清理 /root 垃圾（~1.9G）----
log "清理 /root 缓存（JetBrains/浏览器缓存，~1.9G）"
sudo rm -rf /root/.cache/JetBrains 2>/dev/null && log "  删除 /root/.cache/JetBrains (653M)" || true
sudo rm -rf /root/.cache/mozilla 2>/dev/null && log "  删除 /root/.cache/mozilla (114M)" || true
sudo rm -rf /root/.cache/epiphany 2>/dev/null && log "  删除 /root/.cache/epiphany (106M)" || true
sudo rm -rf /root/.config/JetBrains 2>/dev/null && log "  删除 /root/.config/JetBrains (511M)" || true
sudo rm -rf /root/.config/mozilla 2>/dev/null && log "  删除 /root/.config/mozilla (73M)" || true
sudo rm -rf /root/.config/chromium 2>/dev/null && log "  删除 /root/.config/chromium (8M)" || true
sudo rm -rf /root/.floorp 2>/dev/null && log "  删除 /root/.floorp (51M)" || true
sudo rm -rf /root/Documents 2>/dev/null && log "  删除 /root/Documents (142M)" || true

# ---- 2. 清理 /opt/docker-data 残留（~2.3G）----
# Docker data-root 已在 /mnt/ai/docker，/opt/docker-data 是旧残留
log "清理 /opt/docker-data 旧残留（~2.3G）"
if [ -d /opt/docker-data ] && [ "$(docker info 2>/dev/null | grep 'Docker Root Dir' | awk '{print $NF}')" != "/opt/docker-data" ]; then
    sudo rm -rf /opt/docker-data && log "  删除 /opt/docker-data (2.3G)"
else
    warn "  /opt/docker-data 仍在使用，跳过"
fi

# ---- 3. 清理 /var/lib/systemd coredump（可能很大）----
log "清理 systemd coredump 和 journal"
sudo journalctl --vacuum-size=100M 2>/dev/null && log "  journal 压缩到 100M" || true
sudo rm -rf /var/lib/systemd/coredump/* 2>/dev/null && log "  清理 coredump" || true

# ---- 4. 迁移 /home/charlie 大文件到 POOL-D1 ----
log "迁移 /home/charlie 大文件到 POOL-D1"

# .vscode (889M) → 不迁移（IDE 需要）
# .cursor (325M) → 迁移 + 符号链接
if [ -d /home/charlie/.cursor ] && [ ! -L /home/charlie/.cursor ]; then
    rsync -a /home/charlie/.cursor/ "$TARGET/.cursor/" 2>/dev/null
    rm -rf /home/charlie/.cursor
    ln -s "$TARGET/.cursor" /home/charlie/.cursor
    log "  迁移 .cursor (325M) → POOL-D1 + symlink"
fi

# .npm-global (267M) → 迁移 + 符号链接
if [ -d /home/charlie/.npm-global ] && [ ! -L /home/charlie/.npm-global ]; then
    rsync -a /home/charlie/.npm-global/ "$TARGET/.npm-global/" 2>/dev/null
    rm -rf /home/charlie/.npm-global
    ln -s "$TARGET/.npm-global" /home/charlie/.npm-global
    log "  迁移 .npm-global (267M) → POOL-D1 + symlink"
fi

# .cache-ext4 (169M) → 直接删除（缓存可重建）
if [ -d /home/charlie/.cache-ext4 ]; then
    rm -rf /home/charlie/.cache-ext4
    log "  删除 .cache-ext4 (169M)"
fi

# .npm-cache (114M) → 直接删除（缓存可重建）
if [ -d /home/charlie/.npm-cache ]; then
    rm -rf /home/charlie/.npm-cache
    log "  删除 .npm-cache (114M)"
fi

# ide-backup-archive (66M) → 迁移
if [ -d /home/charlie/ide-backup-archive ] && [ ! -L /home/charlie/ide-backup-archive ]; then
    rsync -a /home/charlie/ide-backup-archive/ "$TARGET/ide-backup-archive/" 2>/dev/null
    rm -rf /home/charlie/ide-backup-archive
    ln -s "$TARGET/ide-backup-archive" /home/charlie/ide-backup-archive
    log "  迁移 ide-backup-archive (66M) → POOL-D1 + symlink"
fi

# .codex (26M) → 迁移 + 符号链接
if [ -d /home/charlie/.codex ] && [ ! -L /home/charlie/.codex ]; then
    rsync -a /home/charlie/.codex/ "$TARGET/.codex/" 2>/dev/null
    rm -rf /home/charlie/.codex
    ln -s "$TARGET/.codex" /home/charlie/.codex
    log "  迁移 .codex (26M) → POOL-D1 + symlink"
fi

# ---- 5. Nix GC ----
log "运行 nix garbage collection"
sudo nix-collect-garbage --delete-older-than 1d 2>/dev/null | tail -1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  阶段 1 完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
df -h / | tail -1
echo ""
echo "下一步：从 USB 启动 LiveCD → 执行阶段 2（GParted 扩容）"
echo "脚本位置：桌面图标 → 自动扩容脚本"
