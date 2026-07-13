#!/usr/bin/env bash
# ============================================================
# 桌面自动分类 - 监控项目目录，自动创建桌面快捷方式
# 检测项目类型并归到对应分组
# ============================================================

set -euo pipefail

WATCH_DIRS=("$HOME/Projects" "$HOME/projects" "$HOME/workspace")
DESKTOP_DIR="$HOME/Desktop"
LOG_FILE="$HOME/.local/share/desktop-auto-sort.log"

mkdir -p "$DESKTOP_DIR/开发工具" "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

# 检测项目类型
detect_project_type() {
    local dir="$1"

    # 安卓项目
    if [[ -f "$dir/build.gradle" || -f "$dir/build.gradle.kts" || -f "$dir/AndroidManifest.xml" ]]; then
        echo "安卓项目"
        return
    fi

    # Flutter
    if [[ -f "$dir/pubspec.yaml" ]]; then
        echo "Flutter"
        return
    fi

    # Rust
    if [[ -f "$dir/Cargo.toml" ]]; then
        echo "Rust"
        return
    fi

    # Node.js / Web
    if [[ -f "$dir/package.json" ]]; then
        if grep -q "react\|vue\|angular\|next\|nuxt" "$dir/package.json" 2>/dev/null; then
            echo "Web前端"
        else
            echo "Node.js"
        fi
        return
    fi

    # Python
    if [[ -f "$dir/setup.py" || -f "$dir/pyproject.toml" || -f "$dir/requirements.txt" ]]; then
        echo "Python"
        return
    fi

    # Nix
    if [[ -f "$dir/flake.nix" ]]; then
        echo "Nix"
        return
    fi

    # Go
    if [[ -f "$dir/go.mod" ]]; then
        echo "Go"
        return
    fi

    # Java/Kotlin
    if [[ -f "$dir/pom.xml" || -f "$dir/build.gradle" ]]; then
        echo "Java/Kotlin"
        return
    fi

    # Docker
    if [[ -f "$dir/Dockerfile" || -f "$dir/docker-compose.yml" ]]; then
        echo "Docker"
        return
    fi

    echo "通用项目"
}

# 为项目创建桌面快捷方式
create_shortcut() {
    local dir="$1"
    local name
    name=$(basename "$dir")
    local type
    type=$(detect_project_type "$dir")
    local desktop_file="$DESKTOP_DIR/开发工具/${name}.desktop"

    # 已存在则跳过
    if [[ -f "$desktop_file" ]]; then
        return
    fi

    # 选择图标和打开方式
    local icon="folder-development"
    local exec_cmd="dolphin \"$dir\""

    case "$type" in
        "安卓项目"|"Java/Kotlin")
            icon="android"
            # 优先用 IDEA 打开
            exec_cmd="idea \"$dir\""
            ;;
        "Flutter")
            icon="flutter"
            exec_cmd="code \"$dir\""
            ;;
        "Web前端"|"Node.js")
            icon="text-html"
            exec_cmd="code \"$dir\""
            ;;
        "Python")
            icon="text-x-python"
            exec_cmd="code \"$dir\""
            ;;
        "Rust")
            icon="text-x-rust"
            exec_cmd="code \"$dir\""
            ;;
        "Nix")
            icon="nix-snowflake"
            exec_cmd="code \"$dir\""
            ;;
        *)
            exec_cmd="code \"$dir\""
            ;;
    esac

    cat > "$desktop_file" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=${name} [${type}]
Comment=${type} 项目 - ${dir}
Exec=${exec_cmd}
Icon=${icon}
Terminal=false
Categories=Development;
DESKTOP

    chmod +x "$desktop_file"
    log "新项目: $name ($type) → 桌面快捷方式已创建"
}

# 扫描现有项目
scan_existing() {
    log "扫描现有项目..."
    for watch_dir in "${WATCH_DIRS[@]}"; do
        if [[ ! -d "$watch_dir" ]]; then
            continue
        fi
        for dir in "$watch_dir"/*/; do
            [[ -d "$dir" ]] || continue
            create_shortcut "$dir"
        done
    done
    log "扫描完成"
}

# 监控模式（需要 inotifywait）
watch_mode() {
    # 确保监控目录存在
    for watch_dir in "${WATCH_DIRS[@]}"; do
        mkdir -p "$watch_dir" 2>/dev/null || true
    done

    local existing_dirs=()
    for watch_dir in "${WATCH_DIRS[@]}"; do
        [[ -d "$watch_dir" ]] && existing_dirs+=("$watch_dir")
    done

    if [[ ${#existing_dirs[@]} -eq 0 ]]; then
        log "没有可监控的目录"
        return 1
    fi

    if ! command -v inotifywait &>/dev/null; then
        log "inotifywait 未安装，使用轮询模式（每 30 秒扫描一次）"
        while true; do
            scan_existing
            sleep 30
        done
    else
        log "开始监控: ${existing_dirs[*]}"
        inotifywait -m -e create -e moved_to --format '%w%f' "${existing_dirs[@]}" | while read -r path; do
            if [[ -d "$path" ]]; then
                # 等一下让项目文件创建完
                sleep 2
                create_shortcut "$path"
            fi
        done
    fi
}

case "${1:-scan}" in
    scan)   scan_existing ;;
    watch)  scan_existing; watch_mode ;;
    *)
        echo "用法: $(basename "$0") <命令>"
        echo "  scan    扫描现有项目并创建快捷方式"
        echo "  watch   持续监控新项目（后台运行）"
        ;;
esac
