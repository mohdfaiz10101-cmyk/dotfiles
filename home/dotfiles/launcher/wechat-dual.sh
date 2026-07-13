#!/bin/bash
# 微信双开 — 第二个实例使用独立数据目录
export WECHAT_DATA_DIR="$HOME/.xwechat2"
export XWECHAT_FILES_DIR="$HOME/xwechat_files2"

# 通过修改 HOME 的方式隔离数据（微信用 $HOME/.xwechat）
exec env HOME="$HOME/.wechat2-home" \
  QT_SCALE_FACTOR=1.5 QT_FONT_DPI=144 GDK_DPI_SCALE=1.5 \
  wechat-uos "$@"
