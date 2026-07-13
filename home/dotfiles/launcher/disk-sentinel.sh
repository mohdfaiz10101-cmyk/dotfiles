#!/usr/bin/env bash
# 磁盘卫兵 v2 - 智能多层清理 + 大目录迁移检测
# 每 5 分钟执行，实时防护根分区爆满

set -euo

LOG="/home/charlie/.local/share/disk-sentinel.log"
MIGRATE_REPORT="/home/charlie/.local/share/disk-migrate-report.txt"
OFFLOAD_BASE="/mnt/pool-disks/POOL-B1/home-offload"
EXT4_OFFLOAD="/mnt/ai/home-offload"
HOME="/home/charlie"
mkdir -p "$(dirname "$LOG")"

USAGE=$(df --output=pcent / | tail -1 | tr -d ' %')
AVAIL=$(df --output=avail / | tail -1 | tr -d ' ')
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ============================================================
# 通用清理函数（从温和到激进分层调用）
# ============================================================

clean_stale_gc_roots() {
    # 清理 result 符号链接（nixos-rebuild 残留）
    if [ -L "$HOME/result" ]; then
        rm -f "$HOME/result" && echo "  removed stale GC root: $HOME/result" >> "$LOG"
    fi
    if [ -L /root/result ] 2>/dev/null; then
        sudo rm -f /root/result && echo "  removed stale GC root: /root/result" >> "$LOG"
    fi
}

clean_appimage_cache() {
    if [ -d "$HOME/.cache-local/appimage-run" ]; then
        local size
        size=$(du -sm "$HOME/.cache-local/appimage-run" 2>/dev/null | cut -f1)
        if [ "${size:-0}" -gt 500 ]; then
            rm -rf "$HOME/.cache-local/appimage-run"/*
            echo "  cleared AppImage cache (${size}M)" >> "$LOG"
        fi
    fi
}

clean_docker_unused() {
    if command -v docker &>/dev/null; then
        local reclaimed
        reclaimed=$(docker image prune -f 2>/dev/null | grep "reclaimed" || echo "0B")
        echo "  docker image prune: $reclaimed" >> "$LOG"
    fi
}

clean_nix_user_profiles() {
    # 清理用户 nix profile 的旧 generations
    nix profile wipe-history --older-than 3d 2>/dev/null || true
}

clean_tmp_aggressive() {
    find /tmp -maxdepth 2 -type d -name "mcp-pw-*" -mtime +1 -exec rm -rf {} + 2>/dev/null || true
    find /tmp -maxdepth 2 -type d -name "nix-shell-*" -mtime +1 -exec rm -rf {} + 2>/dev/null || true
    find /tmp -type f -mtime +1 -delete 2>/dev/null || true
}

clean_nix_generations() {
    local age="${1:-3d}"
    nix-collect-garbage --delete-older-than "$age" >> "$LOG" 2>&1 || true
}

# ============================================================
# 大目录自动检测（迁移建议）
# ============================================================

detect_large_dirs() {
    # 扫描 home 下直接子目录和 .* 目录，找出 >500M 且不在 offload 的
    local report_needed=false
    local report_content=""

    # 迁移目标：ext4 优先（支持 symlink），NTFS 仅用于无 symlink 的目录
    local EXT4_TARGET="$EXT4_OFFLOAD"
    local NTFS_TARGET="$OFFLOAD_BASE/auto-migrate"

    while IFS=$'\t' read -r size dir; do
        local dirname
        dirname=$(basename "$dir")

        # 跳过已知必须在本地的目录
        case "$dirname" in
            .nix-*|.local|.config|.claude|.ssh|.gnupg|Desktop|Documents|launcher|agi) continue ;;
        esac

        # 检查是否已是符号链接（已迁移）
        [ -L "$dir" ] && continue

        # 检查两个 offload 目标中是否已存在
        [ -d "$EXT4_TARGET/$dirname" ] && continue
        [ -d "$NTFS_TARGET/$dirname" ] && continue

        local size_mb
        size_mb=$(echo "$size" | sed 's/M//')
        if [ "${size_mb:-0}" -gt 500 ]; then
            report_needed=true

            # 检测目录内是否含 symlink → 决定推荐目标
            local symlink_count
            symlink_count=$(find "$dir" -maxdepth 3 -type l 2>/dev/null | head -5 | wc -l)
            local target_hint
            if [ "$symlink_count" -gt 0 ]; then
                target_hint="→ ext4 ($EXT4_TARGET) [含 symlink，NTFS 不兼容]"
            else
                target_hint="→ NTFS ($NTFS_TARGET) 或 ext4 ($EXT4_TARGET)"
            fi
            report_content+="  ${size}MB  $dir  $target_hint\n"
        fi
    done < <(du -sm "$HOME"/.* "$HOME"/* 2>/dev/null | sort -rn | awk 'NR<=20')

    if [ "$report_needed" = true ]; then
        {
            echo "=== 大目录迁移建议 $(date '+%Y-%m-%d %H:%M') ==="
            echo "以下目录 >500M 在根分区，建议迁移:"
            echo ""
            echo -e "$report_content"
            echo "迁移命令:"
            echo "  # 含 symlink（venv/conda/mamba/node_modules）→ 必须用 ext4"
            echo "  mv <dir> $EXT4_TARGET/ && ln -s $EXT4_TARGET/<dirname> <original-path>"
            echo ""
            echo "  # 无 symlink → NTFS 或 ext4 均可"
            echo "  mv <dir> $NTFS_TARGET/ && ln -s $NTFS_TARGET/<dirname> <original-path>"
        } > "$MIGRATE_REPORT"
        echo "  [MIGRATE] 发现可迁移大目录，详见 $MIGRATE_REPORT" >> "$LOG"
    fi
}

# ============================================================
# 主逻辑：分级响应
# ============================================================

if [ "$USAGE" -ge 95 ]; then
    echo "[$TIMESTAMP] CRITICAL: ${USAGE}% (avail: ${AVAIL}K) - 全量清理" >> "$LOG"
    clean_stale_gc_roots
    clean_appimage_cache
    clean_docker_unused
    clean_nix_user_profiles
    clean_tmp_aggressive
    clean_nix_generations "1d"
    # 紧急时额外清理 journal
    sudo journalctl --vacuum-size=50M >> "$LOG" 2>&1 || true
    notify-send -u critical "磁盘紧急 ${USAGE}%" "已执行全量清理。剩余 $((AVAIL/1024))M" || true

elif [ "$USAGE" -ge 90 ]; then
    echo "[$TIMESTAMP] WARNING: ${USAGE}% (avail: ${AVAIL}K) - 标准清理" >> "$LOG"
    clean_stale_gc_roots
    clean_appimage_cache
    clean_docker_unused
    clean_nix_user_profiles
    clean_tmp_aggressive
    clean_nix_generations "3d"
    notify-send -u normal "磁盘警告 ${USAGE}%" "已清理缓存+旧包。剩余 $((AVAIL/1024))M" || true

elif [ "$USAGE" -ge 85 ]; then
    echo "[$TIMESTAMP] NOTICE: ${USAGE}% (avail: ${AVAIL}K)" >> "$LOG"
    # 85% 只做轻量清理 + 检测
    clean_stale_gc_roots
    detect_large_dirs
    notify-send -u low "磁盘提醒 ${USAGE}%" "根分区接近阈值，已扫描可迁移目录" || true

else
    # 健康状态：每小时静默记录一次
    MIN=$(date '+%M')
    if [ "$MIN" -lt 5 ]; then
        echo "[$TIMESTAMP] OK: ${USAGE}% (avail: ${AVAIL}K)" >> "$LOG"
    fi
    # 每天 3:00 左右执行一次大目录扫描
    HOUR=$(date '+%H')
    if [ "$HOUR" = "03" ] && [ "$MIN" -lt 5 ]; then
        detect_large_dirs
    fi
fi

# 日志轮转：保留最近 500 行
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 1000 ]; then
    tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
