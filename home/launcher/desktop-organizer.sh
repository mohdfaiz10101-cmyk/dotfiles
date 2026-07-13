#!/usr/bin/env bash
# Desktop Organizer — 定期整理桌面散落文件，.desktop 按 Categories 归类，不移动文件夹
# Usage: desktop-organizer.sh [--dry-run]

DESKTOP="$HOME/Desktop"
DOCS_DIR="$DESKTOP/系统文档"
SCRIPTS_DIR="$DESKTOP/开发工具"
LOG_FILE="$HOME/.local/share/desktop-organizer.log"
APPS_DIR="$HOME/.local/share/applications"

mkdir -p "$DOCS_DIR" "$SCRIPTS_DIR" "$(dirname "$LOG_FILE")" "$APPS_DIR"

# .desktop 分类优先级表: category关键字 → 目标子文件夹名
# 匹配第一个命中的，未命中 → 系统工具
classify_desktop() {
    local file="$1"
    local categories=""
    # 读取 Categories= 行（兼容行首空格、大小写）
    categories=$(grep -iE '^Categories=' "$file" 2>/dev/null | head -1 | cut -d= -f2-)

    # 优先级匹配表: 关键字 → 目标目录
    local -A cat_map=(
        ["AI"]="$DESKTOP/Claude-AI"
        ["IDE"]="$DESKTOP/开发工具"
        ["Network"]="$DESKTOP/网络代理"
        ["Development"]="$DESKTOP/开发工具"
        ["Feed"]="$DESKTOP/社交通讯"
        ["Graphics"]="$DESKTOP/媒体文件"
        ["System"]="$DESKTOP/系统工具"
        ["FileTools"]="$DESKTOP/系统工具"
    )
    local priority=("AI" "IDE" "Network" "Development" "Feed" "Graphics" "System" "FileTools")

    # 按优先级表顺序匹配 categories（确保 AI 优先于 Development 等）
    local IFS=';'
    read -ra cat_arr <<< "$categories"
    for key in "${priority[@]}"; do
        for cat in "${cat_arr[@]}"; do
            if [[ "$cat" == "$key" ]]; then
                echo "${cat_map[$key]}"
                return
            fi
        done
    done

    # 默认归入系统工具
    echo "$DESKTOP/系统工具"
}

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

moved=0
skipped=0
deleted=0

cd "$DESKTOP" || exit 1

# 清理隐藏的临时文件（.swp, .kate-swp, *~）
for swp in .*.swp .*.kate-swp .*~; do
    [[ -f "$swp" ]] || continue
    if $DRY_RUN; then
        log "[DRY] DELETE: $swp"
    else
        rm -f "$swp" && log "[DEL] $swp"
    fi
    ((deleted++))
done

for item in *; do
    # 跳过文件夹
    [[ -d "$item" ]] && continue

    # 跳过 .directory 文件
    [[ "$item" == *.directory ]] && continue

    # 删除 vim/kate 临时文件
    case "$item" in
        *.swp|*.kate-swp|*~)
            if $DRY_RUN; then
                log "[DRY] DELETE: $item"
            else
                rm -f "$item" && log "[DEL] $item"
            fi
            ((deleted++))
            continue
            ;;
    esac

    # .desktop 快捷方式按 Categories 归类
    if [[ "$item" == *.desktop ]]; then
        dest=$(classify_desktop "$item")
        mkdir -p "$dest"
        if [[ -f "$dest/$item" ]]; then
            log "[SKIP] 已存在: $item → $dest/"
            ((skipped++))
            continue
        fi
        if $DRY_RUN; then
            log "[DRY] MOVE: $item → $dest/"
            log "[DRY] LINK: $item → $APPS_DIR/"
        else
            mv -n "$item" "$dest/" && log "[OK] $item → $dest/"
            # 创建软链接到 applications 目录，让 KRunner 能搜到
            ln -sf "$dest/$item" "$APPS_DIR/$item" && log "[OK] 链接: $item → $APPS_DIR/"
        fi
        ((moved++))
        continue
    fi

    # 按扩展名归类普通文件
    dest=""
    case "$item" in
        *.md|*.txt|*.html|*.pdf|*.doc|*.docx)
            dest="$DOCS_DIR"
            ;;
        *.sh|*.bat|*.yml|*.yaml|*.py|*.json|*.toml|*.conf|*.ini)
            dest="$SCRIPTS_DIR"
            ;;
        *)
            # 未知类型跳过
            ((skipped++))
            continue
            ;;
    esac

    # 跳过目标目录已存在的同名文件
    if [[ -f "$dest/$item" ]]; then
        log "[SKIP] 已存在: $item → $dest/"
        ((skipped++))
        continue
    fi

    if $DRY_RUN; then
        log "[DRY] MOVE: $item → $dest/"
    else
        mv -n "$item" "$dest/" && log "[OK] $item → $dest/"
    fi
    ((moved++))
done

log "--- 整理完成: 移动 $moved | 跳过 $skipped | 清理 $deleted ---"
