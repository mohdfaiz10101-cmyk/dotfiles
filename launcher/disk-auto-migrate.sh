#!/usr/bin/env bash
# ============================================================
# 磁盘自动迁移服务
# 监控磁盘使用率，自动将文件从快满的盘迁移到空闲盘
#
# 你的磁盘布局：
#   /           (NVMe 90G)   — 系统盘，保持精简
#   /mnt/ai     (100G loop)  — AI 模型和 Docker
#   /mnt/data   (932G HDD)   — 用户数据
#   /mnt/storage_1.8t (1.8T) — 大容量存储
#   另有 3.6T 和未挂载盘可扩展
#
# 迁移策略：
#   系统盘满 → 大文件移到 /mnt/data
#   /mnt/data 满 → 旧文件移到 /mnt/storage_1.8t
#   /mnt/ai 满 → 旧模型移到 /mnt/data
# ============================================================

set -euo pipefail

LOG_FILE="$HOME/.local/share/disk-migrate.log"
THRESHOLD=85  # 使用率超过 85% 触发迁移
DRY_RUN=false

mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

# 获取磁盘使用率百分比
get_usage() {
    df "$1" 2>/dev/null | awk 'NR==2 {gsub(/%/,""); print $5}'
}

# 获取可用空间 (KB)
get_avail() {
    df "$1" 2>/dev/null | awk 'NR==2 {print $4}'
}

# 查找大文件
find_large_files() {
    local dir="$1" min_size="${2:-100M}"
    find "$dir" -maxdepth 3 -type f -size +${min_size} -printf '%s %T@ %p\n' 2>/dev/null | \
        sort -rn | head -20
}

# 查找最旧的文件
find_oldest_files() {
    local dir="$1" min_size="${2:-50M}"
    find "$dir" -maxdepth 3 -type f -size +${min_size} -printf '%T@ %s %p\n' 2>/dev/null | \
        sort -n | head -20
}

# 安全迁移文件（保留目录结构）
migrate_file() {
    local src="$1" dest_base="$2"
    local src_base="$3"  # 源根目录，用于计算相对路径
    local rel_path="${src#$src_base}"
    local dest="$dest_base$rel_path"
    local dest_dir
    dest_dir=$(dirname "$dest")

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[预览] 迁移: $src → $dest ($(du -sh "$src" 2>/dev/null | awk '{print $1}'))"
        return
    fi

    mkdir -p "$dest_dir"

    # rsync 保留权限和时间戳
    if rsync -a --remove-source-files "$src" "$dest" 2>/dev/null; then
        # 创建符号链接指向新位置（保持旧路径可用）
        ln -sf "$dest" "$src" 2>/dev/null || true
        log "已迁移: $src → $dest"
    else
        log "迁移失败: $src"
    fi
}

# 策略 1: 系统盘 / 快满 → 大文件移到 /mnt/data
migrate_system_disk() {
    local usage
    usage=$(get_usage "/")
    log "系统盘 / 使用率: ${usage}%"

    if [[ "$usage" -lt "$THRESHOLD" ]]; then
        log "系统盘正常，无需迁移"
        return
    fi

    log "系统盘使用率超过 ${THRESHOLD}%，开始迁移大文件..."

    # 迁移 ~/Downloads 中的大文件
    if [[ -d "$HOME/Downloads" ]]; then
        while IFS=' ' read -r size mtime filepath; do
            [[ -n "$filepath" ]] || continue
            migrate_file "$filepath" "/mnt/data/migrated" "$HOME"
            # 每迁移一个文件检查一次
            usage=$(get_usage "/")
            if [[ "$usage" -lt 75 ]]; then
                log "系统盘已降到 ${usage}%，停止迁移"
                return
            fi
        done < <(find_large_files "$HOME/Downloads" "50M")
    fi

    # 迁移 ~/.cache 中的大文件
    if [[ -d "$HOME/.cache" ]]; then
        while IFS=' ' read -r size mtime filepath; do
            [[ -n "$filepath" ]] || continue
            migrate_file "$filepath" "/mnt/data/migrated" "$HOME"
            usage=$(get_usage "/")
            [[ "$usage" -lt 75 ]] && return
        done < <(find_large_files "$HOME/.cache" "100M")
    fi

    # 迁移 ~/Documents 中的大文件
    if [[ -d "$HOME/Documents" ]]; then
        while IFS=' ' read -r size mtime filepath; do
            [[ -n "$filepath" ]] || continue
            migrate_file "$filepath" "/mnt/data/migrated" "$HOME"
            usage=$(get_usage "/")
            [[ "$usage" -lt 75 ]] && return
        done < <(find_large_files "$HOME/Documents" "100M")
    fi
}

# 策略 2: /mnt/data 快满 → 旧文件移到 /mnt/storage_1.8t
migrate_data_disk() {
    local usage
    usage=$(get_usage "/mnt/data")
    log "/mnt/data 使用率: ${usage}%"

    if [[ "$usage" -lt "$THRESHOLD" ]]; then
        log "/mnt/data 正常，无需迁移"
        return
    fi

    if [[ ! -d "/mnt/storage_1.8t" ]]; then
        log "目标盘 /mnt/storage_1.8t 未挂载，跳过"
        return
    fi

    log "/mnt/data 使用率超过 ${THRESHOLD}%，开始迁移旧文件..."

    while IFS=' ' read -r mtime size filepath; do
        [[ -n "$filepath" ]] || continue
        migrate_file "$filepath" "/mnt/storage_1.8t/migrated" "/mnt/data"
        usage=$(get_usage "/mnt/data")
        if [[ "$usage" -lt 75 ]]; then
            log "/mnt/data 已降到 ${usage}%，停止迁移"
            return
        fi
    done < <(find_oldest_files "/mnt/data" "100M")
}

# 策略 3: /mnt/ai 快满 → 旧模型移到 /mnt/data
migrate_ai_disk() {
    local usage
    usage=$(get_usage "/mnt/ai")
    log "/mnt/ai 使用率: ${usage}%"

    if [[ "$usage" -lt "$THRESHOLD" ]]; then
        log "/mnt/ai 正常，无需迁移"
        return
    fi

    log "/mnt/ai 使用率超过 ${THRESHOLD}%，开始迁移..."

    # 迁移旧的 Docker 镜像层（最大的文件优先）
    while IFS=' ' read -r size mtime filepath; do
        [[ -n "$filepath" ]] || continue
        migrate_file "$filepath" "/mnt/data/ai-archive" "/mnt/ai"
        usage=$(get_usage "/mnt/ai")
        [[ "$usage" -lt 75 ]] && return
    done < <(find_large_files "/mnt/ai" "200M")
}

# 状态报告
cmd_status() {
    echo "━━━━━━━━━━ 磁盘状态 ━━━━━━━━━━"
    echo ""
    printf "%-20s %6s %10s %10s\n" "挂载点" "使用率" "已用" "可用"
    echo "─────────────────────────────────────────────"
    for mp in "/" "/mnt/ai" "/mnt/data" "/mnt/storage_1.8t"; do
        if mountpoint -q "$mp" 2>/dev/null || [[ "$mp" == "/" ]]; then
            local info
            info=$(df -h "$mp" 2>/dev/null | awk 'NR==2 {print $5, $3, $4}')
            local pct used avail
            pct=$(echo "$info" | awk '{print $1}')
            used=$(echo "$info" | awk '{print $2}')
            avail=$(echo "$info" | awk '{print $3}')

            local warn=""
            local pct_num=${pct//%/}
            [[ "$pct_num" -ge 85 ]] && warn=" ⚠️"
            [[ "$pct_num" -ge 95 ]] && warn=" 🔴"

            printf "%-20s %6s %10s %10s%s\n" "$mp" "$pct" "$used" "$avail" "$warn"
        fi
    done
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 显示迁移日志最后几行
    if [[ -f "$LOG_FILE" ]]; then
        echo ""
        echo "最近迁移记录:"
        tail -5 "$LOG_FILE"
    fi
}

# 主逻辑
case "${1:-status}" in
    run)
        log "========== 开始磁盘自动迁移 =========="
        migrate_system_disk
        migrate_data_disk
        migrate_ai_disk
        log "========== 迁移完成 =========="
        ;;
    dry-run|preview)
        DRY_RUN=true
        log "========== 预览模式（不实际迁移）=========="
        migrate_system_disk
        migrate_data_disk
        migrate_ai_disk
        ;;
    status|s)
        cmd_status
        ;;
    watch)
        log "启动持续监控模式（每 10 分钟检查一次）"
        while true; do
            "$0" run
            sleep 600
        done
        ;;
    *)
        echo "用法: $(basename "$0") <命令>"
        echo "  status     查看磁盘状态"
        echo "  dry-run    预览迁移（不实际执行）"
        echo "  run        立即执行迁移"
        echo "  watch      持续监控模式"
        ;;
esac
