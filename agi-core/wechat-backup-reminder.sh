#!/usr/bin/env bash
# wechat-backup-reminder.sh — 提醒用户手动备份微信聊天记录
# 触发：systemd timer 每3天运行一次
# 输出：Telegram 消息 + KDE 桌面通知

set -euo pipefail

# ─── 配置 ──────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN="8797063873:AAHMK0qy79xqAFS_TxNsIOkEwJSJxq8cixE"
TELEGRAM_CHAT_ID="5036541266"
PROXY="http://127.0.0.1:7890"

# 检查是否已有最近的备份（24小时内有新文件则跳过提醒）
BACKUP_DIR="/mnt/ai/apps/wechat-backup"
STATE_FILE="$BACKUP_DIR/imported/stats.json"

# 检查上次备份时间
if [ -f "$STATE_FILE" ]; then
    LAST_IMPORT=$(python3 -c "
import json, sys
try:
    d = json.load(open('$STATE_FILE'))
    print(d.get('last_import_time', ''))
except: print('')
" 2>/dev/null || echo "")
    if [ -n "$LAST_IMPORT" ]; then
        # 如果24小时内已导入，跳过提醒
        LAST_EPOCH=$(date -d "$LAST_IMPORT" +%s 2>/dev/null || echo 0)
        NOW_EPOCH=$(date +%s)
        DIFF=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))
        if [ "$DIFF" -lt 24 ]; then
            echo "24小时内已有备份导入（${DIFF}小时前），跳过提醒"
            exit 0
        fi
    fi
fi

# ─── 统计信息 ────────────────────────────────────────────────────────────────
STATS="尚未导入过微信数据"
if [ -f "$STATE_FILE" ]; then
    STATS=$(python3 -c "
import json
try:
    d = json.load(open('$STATE_FILE'))
    total = d.get('total_imported', 0)
    last = d.get('last_import_time', '未知')
    contacts = len(d.get('by_talker', {}))
    print(f'已导入 {total} 条消息，{contacts} 个联系人，上次导入: {last[:16]}')
except: print('统计信息读取失败')
" 2>/dev/null || echo "统计信息读取失败")
fi

# ─── 桌面通知 ────────────────────────────────────────────────────────────────
if command -v notify-send &>/dev/null; then
    notify-send -u normal "📱 微信备份提醒" \
        "该备份微信聊天记录了！\n$STATS\n\n导出步骤：微信设置 → 通用 → 聊天记录迁移与备份\n导出后放入 $BACKUP_DIR"
fi

# ─── Telegram 通知 ──────────────────────────────────────────────────────────
MSG="📱 *微信备份提醒*

该备份微信聊天记录了！
$STATS

导出步骤：
1. 打开微信 → 设置 → 通用 → 聊天记录迁移与备份
2. 选择要备份的聊天
3. 导出后放入 \`$BACKUP_DIR\`
4. 运行：\`python3 ~/agi/wechat-learn.py --source all\`"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --proxy "$PROXY" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "
import json
print(json.dumps({
    'chat_id': '$TELEGRAM_CHAT_ID',
    'text': '''$MSG''',
    'parse_mode': 'Markdown'
}))
")" >/dev/null 2>&1

echo "提醒已发送 $(date '+%Y-%m-%d %H:%M')"
