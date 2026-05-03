#!/usr/bin/env bash
# ============================================================
# Home 大文件自动迁移守护
#
# 逻辑：
#   1. 扫描 ~/ 下超过阈值的大文件/目录
#   2. 排除已迁移（symlink）和黑名单
#   3. 自动迁移到 POOL-D1（ext4，支持权限）
#   4. 创建 symlink 保持原路径
#   5. 记录日志到 ~/.local/log/home-offload.log
#
# 特性：
#   - 最小干扰：只迁移真正大的文件
#   - 安全保留：原路径通过 symlink 完全可用
#   - 幂等运行：已迁移的跳过
#   - 可配置：阈值和黑名单可调
# ============================================================

set -euo pipefail

# 配置
THRESHOLD_MB=200                    # 最小 200MB 才迁移
POOL_TARGET="/mnt/pool-disks/POOL-B1/home-offload"
OFFLOAD_LOG="$HOME/.local/log/home-offload.log"
LOCK_FILE="/tmp/home-offload-$USER.lock"

# 黑名单：永远不迁移的路径（逗号分隔）
BLACKLIST=(
    ".cache"
    ".config"
    ".local"
    ".claude"
    "Projects"
    "projects"
    "Desktop"
    "Documents"
    "Downloads"
    ".ssh"
    ".gnupg"
)

log() {
    local level="$1"
    shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
    echo "$msg"
    mkdir -p "$(dirname "$OFFLOAD_LOG")"
    echo "$msg" >> "$OFFLOAD_LOG"
}

# 获取锁，防止并发
acquire_lock() {
    exec 200>"$LOCK_FILE"
    flock -n 200 || { log "INFO" "另一个实例正在运行，跳过"; exit 0; }
}

# 检查是否在黑名单
is_blacklisted() {
    local name="$1"
    for item in "${BLACKLIST[@]}"; do
        [[ "$name" == "$item" ]] && return 0
    done
    return 1
}

# 检查是否已经是 symlink
is_symlink() {
    [[ -L "$1" ]] && return 0 || return 1
}

# 检查 POOL 是否可用
check_pool_available() {
    if [[ ! -d "$POOL_TARGET" ]]; then
        log "WARN" "POOL 目标不存在，尝试创建: $POOL_TARGET"
        sudo mkdir -p "$POOL_TARGET" && sudo chown charlie:users "$POOL_TARGET" || {
            log "ERROR" "无法创建 POOL 目标，跳过本次运行"
            exit 1
        }
    fi

    # 检查可用空间（需要至少 10GB）
    local available
    available=$(df -P "$POOL_TARGET" 2>/dev/null | tail -1 | awk '{print $4}')
    local available_gb=$((available / 1024 / 1024))
    if [[ $available_gb -lt 10 ]]; then
        log "WARN" "POOL 可用空间不足 10GB，跳过迁移"
        exit 0
    fi
}

# 扫描大文件/目录
scan_large_items() {
    local threshold_kb=$((THRESHOLD_MB * 1024))

    # 扫描 ~/ 下一级目录（隐藏文件+普通文件）
    for item in "$HOME"/* "$HOME"/.*; do
        # 跳过 . 和 ..
        [[ "$item" == "$HOME/." || "$item" == "$HOME/.." ]] && continue
        # 跳过不存在（glob 可能匹配空）
        [[ ! -e "$item" ]] && continue

        local name
        name=$(basename "$item")

        # 跳过黑名单
        is_blacklisted "$name" && continue

        # 跳过已是 symlink
        is_symlink "$item" && continue

        # 获取大小（目录递归计算）
        local size
        size=$(du -sk "$item" 2>/dev/null | cut -f1)

        if [[ $size -ge $threshold_kb ]]; then
            echo "$size|$item"
        fi
    done
}

# 迁移单个项目
migrate_item() {
    local size_kb="$1"
    local source="$2"
    local name
    name=$(basename "$source")
    local target="$POOL_TARGET/$name"

    log "INFO" "开始迁移: $name ($((size_kb / 1024))MB)"

    # 检查目标是否已存在
    if [[ -e "$target" ]]; then
        log "WARN" "目标已存在，跳过: $target"
        return 1
    fi

    # 移动文件
    if mv "$source" "$target"; then
        # 创建 symlink
        if ln -s "$target" "$source"; then
            log "INFO" "✅ 迁移成功: $name"
            return 0
        else
            # symlink 失败，回滚
            log "ERROR" "symlink 创建失败，回滚: $name"
            mv "$target" "$source"
            return 1
        fi
    else
        log "ERROR" "移动失败: $name"
        return 1
    fi
}

# 主流程
main() {
    log "INFO" "=== Home Offload Auto 开始 ==="

    acquire_lock
    check_pool_available

    local items
    items=$(scan_large_items)

    if [[ -z "$items" ]]; then
        log "INFO" "没有发现需要迁移的大文件（阈值: ${THRESHOLD_MB}MB）"
        exit 0
    fi

    log "INFO" "发现 $(echo "$items" | wc -l) 个候选项目"

    # 按大小排序（大的优先）
    echo "$items" | sort -rn -t'|' -k1 | while IFS='|' read -r size_kb item; do
        migrate_item "$size_kb" "$item"
    done

    # 显示当前空间
    local root_used
    root_used=$(df -h / | tail -1 | awk '{print $5}')
    local pool_avail
    pool_avail=$(df -h "$POOL_TARGET" | tail -1 | awk '{print $4}')

    log "INFO" "根分区使用率: $root_used, POOL 可用: $pool_avail"
    log "INFO" "=== Home Offload Auto 完成 ==="
}

main "$@"
