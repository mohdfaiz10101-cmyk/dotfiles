#!/bin/bash
# 微信双开启动器

export QT_QPA_PLATFORM=xcb

WECHAT2_HOME="$HOME/.wechat2-home"
mkdir -p "$WECHAT2_HOME/.xwechat" "$WECHAT2_HOME/xwechat_files"

# KDE 勾选对话框（默认两个都勾选）
CHOICES=$(kdialog --checklist "选择要启动的微信" \
  "main"  "微信 · 主号" on \
  "work"  "微信 · 工作号" on \
  2>/dev/null)

# 如果用户取消，默认启动主号
if [ -z "$CHOICES" ]; then
  CHOICES='"main"'
fi

if echo "$CHOICES" | grep -q "main"; then
  env QT_QPA_PLATFORM=xcb QT_SCALE_FACTOR=1.0 QT_FONT_DPI=96 GDK_DPI_SCALE=1.0 QT_IM_MODULE=fcitx XMODIFIERS=@im=fcitx wechat-uos &
fi

if echo "$CHOICES" | grep -q "work"; then
  sleep 2
  env QT_IM_MODULE=fcitx XMODIFIERS=@im=fcitx "$HOME/launcher/wechat-uos-2nd.sh" &
  # 自动改名守护
  (
    sleep 8
    for i in $(seq 1 60); do
      for wid in $(xprop -root _NET_CLIENT_LIST 2>/dev/null | grep -oP '0x[0-9a-f]+'); do
        pid=$(xprop -id "$wid" _NET_WM_PID 2>/dev/null | awk '{print $NF}')
        if [ -n "$pid" ] && grep -q "wechat2-home" /proc/$pid/environ 2>/dev/null; then
          xprop -id "$wid" -set _NET_WM_NAME "微信 · 工作号" 2>/dev/null
        fi
      done
      sleep 5
    done
  ) &
fi
