#!/bin/bash
# 語音輸入腳本 - 按住錄音，鬆開轉文字
# 依賴: whisper-cpp, sox, wl-clipboard

MODEL="${WHISPER_MODEL:-/home/charlie/.local/share/whisper/ggml-base.bin}"
TMPFILE="/tmp/voice-input-$$.wav"

# 下載模型（首次）
if [ ! -f "$MODEL" ]; then
    mkdir -p "$(dirname "$MODEL")"
    echo "首次使用，下載 Whisper base 模型..."
    curl -L "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin" -o "$MODEL"
fi

# 錄音（按 Ctrl+C 停止）
echo "🎤 開始錄音... 按 Ctrl+C 停止"
rec -r 16000 -c 1 -b 16 "$TMPFILE" 2>/dev/null

# 轉文字
if [ -f "$TMPFILE" ]; then
    echo "⏳ 轉換中..."
    RESULT=$(whisper-cli -m "$MODEL" -l auto -f "$TMPFILE" --no-timestamps 2>/dev/null | grep -v "^\[" | sed 's/^ *//')
    rm -f "$TMPFILE"
    
    if [ -n "$RESULT" ]; then
        echo "$RESULT" | wl-copy
        echo "✅ 已複製到剪貼板: $RESULT"
    else
        echo "❌ 未識別到語音"
    fi
fi
