#!/usr/bin/env bash
# ============================================================
# 磁盘池自动发现 + 挂载 + 合并脚本
#
# 逻辑：
#   1. blkid 扫描所有分区，找标签以 POOL- 开头的
#   2. 检测已挂载的 POOL 盘（不管挂载点在哪）
#   3. 未挂载的盘按文件系统类型自动挂载到 /mnt/pool-disks/<label>
#   4. MergerFS 合并所有已挂载的 POOL 盘到 /mnt/pool
#
# 特性：
#   - 不绑定 UUID / 设备路径
#   - 支持已存在的挂载点（如 fstab 配置的）
#   - NTFS / ext4 / btrfs 全自动识别
#   - 重装后 rebuild 即恢复
# ============================================================

set -euo pipefail

POOL_MOUNT_BASE="/mnt/pool-disks"
POOL_MERGED="/mnt/pool"
LOG_TAG="disk-pool"
LOCK_FILE="/tmp/disk-pool-$USER.lock"

log() { echo "[disk-pool] $1"; logger -t "$LOG_TAG" "$1"; }

# 获取锁，防止并发
acquire_lock() {
    exec 200>"$LOCK_FILE"
    flock -n 200 || { log "另一个实例正在运行，跳过"; exit 0; }
}

# 扫描所有 POOL- 标签的分区
discover_pool_disks() {
    blkid -o export 2>/dev/null | awk -v RS='\n\n' '/LABEL=POOL-/' | while IFS= read -r block; do
        local dev label fstype
        dev=$(echo "$block" | grep '^DEVNAME=' | cut -d= -f2)
        label=$(echo "$block" | grep '^LABEL=' | cut -d= -f2)
        fstype=$(echo "$block" | grep '^TYPE=' | cut -d= -f2)
        [[ -n "$dev" && -n "$label" ]] && echo "$dev|$label|$fstype"
    done
}

# 检测磁盘是否已挂载（返回挂载点，如果未挂载则返回空）
get_mountpoint() {
    local dev="$1"
    findmnt -n -o TARGET "$dev" 2>/dev/null | head -1
}

# 挂载单个盘
mount_disk() {
    local dev="$1" label="$2" fstype="$3"
    local mountpoint="$POOL_MOUNT_BASE/$label"

    # 检查是否已挂载在其他位置
    local existing_mount
    existing_mount=$(get_mountpoint "$dev")
    if [[ -n "$existing_mount" ]]; then
        log "$label 已挂载在 $existing_mount（跳过重新挂载）"
        return 0
    fi

    # 检查预期挂载点是否已被占用
    if mountpoint -q "$mountpoint" 2>/dev/null; then
        log "$label 已挂载在 $mountpoint"
        return 0
    fi

    mkdir -p "$mountpoint"

    local mount_opts=""
    case "$fstype" in
        ntfs|ntfs3)
            mount_opts="-t ntfs3 -o rw,noatime,uid=1000,gid=100,fmask=0022,dmask=0022"
            ;;
        ext4)
            mount_opts="-t ext4 -o rw,noatime"
            ;;
        btrfs)
            mount_opts="-t btrfs -o rw,noatime,compress=zstd"
            ;;
        exfat)
            mount_opts="-t exfat -o rw,noatime,uid=1000,gid=100"
            ;;
        *)
            mount_opts="-o rw,noatime"
            ;;
    esac

    if mount $mount_opts "$dev" "$mountpoint" 2>/dev/null; then
        log "已挂载: $label ($dev, $fstype) → $mountpoint"
        return 0
    else
        log "挂载失败: $label ($dev, $fstype)"
        return 1
    fi
}

# MergerFS 合并所有已挂载的 POOL 盘
merge_pool() {
    # 收集所有已挂载的 POOL- 标签的磁盘的挂载点
    local pool_dirs=()
    
    while IFS='|' read -r dev label fstype; do
        local mountpoint
        mountpoint=$(get_mountpoint "$dev")
        if [[ -n "$mountpoint" ]]; then
            pool_dirs+=("$mountpoint")
            log "发现 POOL 盘: $label → $mountpoint"
        fi
    done < <(discover_pool_disks)

    if [[ ${#pool_dirs[@]} -eq 0 ]]; then
        log "没有发现已挂载的 POOL 盘，跳过合并"
        return 1
    fi

    # 已合并则先卸载
    if mountpoint -q "$POOL_MERGED" 2>/dev/null; then
        umount "$POOL_MERGED" 2>/dev/null || true
    fi

    mkdir -p "$POOL_MERGED"

    # 构建 MergerFS 挂载路径（用冒号分隔）
    local merged_path
    merged_path=$(IFS=:; echo "${pool_dirs[*]}")

    log "合并路径: $merged_path → $POOL_MERGED"

    # MergerFS 策略：
    #   create = mfs   → 新文件写到剩余空间最多的盘
    #   search = ff    → 搜索文件按首次找到
    #   moveonenospc   → 盘满了自动移到其他盘
    #   cache.files    → 启用文件缓存提升性能
    if mergerfs \
        -o defaults,allow_other,use_ino,category.create=mfs,moveonenospc=true,dropcacheonclose=true,cache.files=partial,minfreespace=10G,fsname=pool \
        "$merged_path" "$POOL_MERGED"; then
        log "✅ MergerFS 合并成功: $POOL_MERGED (包含 ${#pool_dirs[@]} 个盘)"
        return 0
    else
        log "❌ MergerFS 合并失败"
        return 1
    fi
}

# ============================================================
# 主流程
# ============================================================
main() {
    acquire_lock

    if [[ "${1:-}" == "status" ]]; then
        log "========== 磁盘池状态 =========="
        echo ""
        echo "发现的 POOL 盘:"
        discover_pool_disks | while IFS='|' read -r dev label fstype; do
            local mountpoint
            mountpoint=$(get_mountpoint "$dev")
            if [[ -n "$mountpoint" ]]; then
                echo "  ✅ $label ($dev, $fstype) → $mountpoint"
            else
                echo "  ❌ $label ($dev, $fstype) → 未挂载"
            fi
        done
        echo ""
        echo "合并状态:"
        if mountpoint -q "$POOL_MERGED" 2>/dev/null; then
            echo "  ✅ $POOL_MERGED 已合并"
            df -h "$POOL_MERGED" | tail -1
        else
            echo "  ❌ $POOL_MERGED 未合并"
        fi
        return 0
    fi

    log "========== 磁盘池启动 =========="

    # 1. 扫描并挂载所有 POOL 盘
    local mounted_count=0
    while IFS='|' read -r dev label fstype; do
        if mount_disk "$dev" "$label" "$fstype"; then
            ((mounted_count++)) || true
        fi
    done < <(discover_pool_disks)

    # 2. MergerFS 合并
    if merge_pool; then
        log "========== 磁盘池就绪 =========="
    else
        log "========== 磁盘池启动失败 =========="
    fi

    # 显示最终状态
    "$0" status
}

main "$@"
