#!/run/current-system/sw/bin/bash
# git-backup.sh — 全系统 Git 备份
# 覆盖所有 ~/ 下的 git 仓库，自动 commit + push
# 路径: ~/bin/git-backup.sh (git tracked by dotfiles)

set -uo pipefail
LOG_DIR="$HOME/.local/state/git-backup"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/git-backup-$(date +%Y%m%d).log"
DATE=$(date '+%Y-%m-%d %H:%M')
OK=0; FAIL=0; SKIP=0; LOCAL=0

log() { echo "$*" | tee -a "$LOG"; }

backup_repo() {
    local path="$1" desc="$2"

    if [ ! -d "$path/.git" ]; then
        log "[SKIP] $desc — 非 git 仓库"; ((SKIP++)); return
    fi

    cd "$path" 2>/dev/null || { log "[FAIL] $desc — 无法进入目录"; ((FAIL++)); return; }

    # 检查有无remote
    local remote
    remote=$(git remote get-url origin 2>/dev/null || echo "")
    if [ -z "$remote" ]; then
        has_remote=false
    else
        has_remote=true
        # HTTPS → SSH
        if [[ "$remote" == https://github.com/* ]]; then
            git remote set-url origin "git@github.com:${remote#https://github.com/}" 2>/dev/null || true
        fi
    fi

    # 检查变更
    local changes
    changes=$(git status --porcelain 2>/dev/null || true)
    if [ -z "$changes" ]; then
        if $has_remote; then
            log "[SKIP] $desc — 无变更"; ((SKIP++))
        else
            log "[SKIP] $desc — 无变更(无remote)"; ((SKIP++))
        fi
        return
    fi

    local count
    count=$(echo "$changes" | wc -l)

    git add -A 2>/dev/null || true
    git commit -m "${DATE} 自动备份（${count} 个文件变更）" 2>/dev/null || true

    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

    if ! $has_remote; then
        log "[LOCAL] $desc → $branch (${count}文件) — 无remote未推送"; ((LOCAL++))
        return
    fi

    # push（允许 Everything up-to-date）
    local push_out
    push_out=$(git push origin "$branch" 2>&1) || {
        if echo "$push_out" | grep -q "Everything up-to-date"; then
            log "[OK] $desc → $branch (${count}文件,已是最新)"; ((OK++))
        else
            log "[FAIL] $desc → $branch push失败: $(echo "$push_out" | tail -1)"; ((FAIL++))
        fi
        return
    }
    log "[OK] $desc → $branch (${count}文件)"; ((OK++))
}

log "=== Git 备份开始 $DATE ==="

# 核心配置（必须有 GitHub remote）
backup_repo ~/dotfiles                "dotfiles(核心配置)"
backup_repo ~/dotfiles/agi-core       "agi-core(AGI核心)"
backup_repo ~/ai-config-sync          "ai-config-sync"
backup_repo /etc/nixos                "NixOS系统配置"

# 开发项目
backup_repo ~/nixos-dev               "NixOS开发"
backup_repo ~/claude-router-plugin    "Claude路由插件"
backup_repo ~/ccm-cli                 "CCM CLI"
backup_repo ~/balance-trigger         "余额触发器"
backup_repo ~/free-claude-api-pool    "Free Claude API"
backup_repo ~/pets/playground         "宠物项目"
backup_repo ~/docker/deepwiki-open    "DeepWiki Docker"

# 文档/知识
backup_repo ~/Documents/Obsidian      "Obsidian笔记"
backup_repo ~/Desktop                 "桌面文件"
backup_repo ~/cline-workspace         "Cline工作区"
backup_repo ~/.openclaw/workspace     "OpenClaw工作区"

# 项目（已有 GitHub remote）
backup_repo ~/launcher               "launcher(服务管理)"
backup_repo ~/hub                    "hub(API服务)"

# 已确认的遗留非git目录（不报SKIP）
# ~/agi ~/crewai-project 非git — 仅数据目录

log "=== 完成: OK=$OK SKIP=$SKIP LOCAL=$LOCAL FAIL=$FAIL ==="

# 桌面通知
if [ "$FAIL" -gt 0 ]; then
    notify-send "Git备份完成 ⚠️" "成功:$OK 跳过:$SKIP 失败:$FAIL" --app-name="GitBackup" -t 5000 2>/dev/null || true
else
    notify-send "Git备份完成" "成功:$OK 跳过:$SKIP" --app-name="GitBackup" -t 3000 2>/dev/null || true
fi

# 复制到桌面
mkdir -p ~/Desktop/日志/操作记录/
cp "$LOG" ~/Desktop/日志/操作记录/git-backup-$(date +%Y%m%d).log 2>/dev/null || true