#!/bin/bash
# 启动 Claude 待办浮动挂件
# 用 Firefox/Chrome 打开小窗口，KWin 规则控制浮动

WIDGET_URL="http://localhost:9875/todo-widget.html"
WM_CLASS="claude-todo-widget"

# 关闭已有实例
pkill -f "claude-todo-widget" 2>/dev/null
sleep 0.3

# 优先用 Firefox，回退 Chrome
if command -v firefox &>/dev/null; then
    firefox --class="$WM_CLASS" --new-window "$WIDGET_URL" &
elif command -v google-chrome-stable &>/dev/null; then
    google-chrome-stable --app="$WIDGET_URL" --class="$WM_CLASS" --window-size=280,500 &
elif command -v chromium &>/dev/null; then
    chromium --app="$WIDGET_URL" --class="$WM_CLASS" --window-size=280,500 &
fi

echo "待办挂件已启动"
