#!/usr/bin/env bash
# screenshot-translate.sh — 截图 → OCR → 翻译 → 覆盖到图片 → 保存
# 用法: screenshot-translate.sh [源语言] [目标语言]
# 默认: 自动检测 → 中文
# 示例: screenshot-translate.sh en zh   (英→中)
#        screenshot-translate.sh zh en   (中→英)
#        screenshot-translate.sh ja zh   (日→中)

set -euo pipefail

# --- 配置 ---
SAVE_DIR="$HOME/Pictures/Screenshots/Translated"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SCREENSHOT="/tmp/screenshot-translate-${TIMESTAMP}.png"
OUTPUT="${SAVE_DIR}/translated_${TIMESTAMP}.png"
OCR_LANGS="eng+chi_sim+chi_tra+jpn+kor"
SOURCE_LANG="${1:-auto}"
TARGET_LANG="${2:-zh}"
FONT_SIZE=16
FONT_COLOR="red"
BG_COLOR="white"

mkdir -p "$SAVE_DIR"

# --- 1. Spectacle 区域截图（无 GUI，直接保存） ---
spectacle -r -b -n -o "$SCREENSHOT" 2>/dev/null

if [[ ! -f "$SCREENSHOT" ]]; then
    notify-send -u critical "截图翻译" "截图被取消或失败"
    exit 1
fi

notify-send -t 2000 "截图翻译" "正在识别文字..."

# --- 2. OCR 识别（带坐标信息用于覆盖） ---
TEXT=$(tesseract "$SCREENSHOT" stdout -l "$OCR_LANGS" 2>/dev/null | sed '/^\s*$/d')

if [[ -z "$TEXT" ]]; then
    notify-send -u normal "截图翻译" "未识别到文字"
    # 仍然保存原图
    cp "$SCREENSHOT" "$OUTPUT"
    rm -f "$SCREENSHOT"
    exit 0
fi

notify-send -t 2000 "截图翻译" "识别到文字，正在翻译..."

# --- 3. 翻译 ---
if [[ "$SOURCE_LANG" == "auto" ]]; then
    TRANSLATED=$(trans -b -t "$TARGET_LANG" "$TEXT" 2>/dev/null)
else
    TRANSLATED=$(trans -b -s "$SOURCE_LANG" -t "$TARGET_LANG" "$TEXT" 2>/dev/null)
fi

if [[ -z "$TRANSLATED" ]]; then
    notify-send -u normal "截图翻译" "翻译失败，仅保存 OCR 结果"
    TRANSLATED="[翻译失败] $TEXT"
fi

# --- 4. 将翻译结果添加到图片底部 ---
# 获取图片宽度
IMG_WIDTH=$(magick identify -format '%w' "$SCREENSHOT")

# 用 ImageMagick 在图片底部拼接翻译文字
magick "$SCREENSHOT" \
    \( -size "${IMG_WIDTH}x" \
       -background "$BG_COLOR" \
       -fill "$FONT_COLOR" \
       -font "Noto-Sans-CJK-SC" \
       -pointsize "$FONT_SIZE" \
       -gravity NorthWest \
       -interline-spacing 4 \
       caption:"$TRANSLATED" \
    \) \
    -append "$OUTPUT"

# --- 5. 复制翻译文字到剪贴板 ---
echo "$TRANSLATED" | wl-copy

# --- 6. 保存原文+翻译到文本文件 ---
cat > "${OUTPUT%.png}.txt" << TXTEOF
=== 原文 (OCR) ===
$TEXT

=== 翻译 ($SOURCE_LANG → $TARGET_LANG) ===
$TRANSLATED
TXTEOF

# --- 7. 清理临时文件 ---
rm -f "$SCREENSHOT"

# --- 8. 通知用户 ---
# 截取翻译结果前100字符用于通知
PREVIEW="${TRANSLATED:0:100}"
[[ ${#TRANSLATED} -gt 100 ]] && PREVIEW="${PREVIEW}..."

notify-send -i "$OUTPUT" "截图翻译完成" "$PREVIEW

保存到: $OUTPUT"

echo "翻译结果已保存到: $OUTPUT"
echo "翻译文字已复制到剪贴板"
