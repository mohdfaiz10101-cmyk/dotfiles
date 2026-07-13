#!/usr/bin/env bash
# 以桌面小部件模式启动 启动器
# 无边框窗口，悬浮在桌面上

# 确保服务在运行
if ! lsof -i :9875 &>/dev/null; then
    python3 ~/launcher/launcher-server.py &
    sleep 2
fi

# 用 Firefox 以 WebApp 模式打开（无地址栏无菜单栏）
# 也可以换成 chrome --app=...
if command -v google-chrome-stable &>/dev/null; then
    google-chrome-stable \
        --app=http://127.0.0.1:9875/launcher.html \
        --window-size=420,700 \
        --window-position=50,50 \
        --class="launcher-widget" &
elif command -v floorp &>/dev/null; then
    # Floorp/Firefox 用 SSB 模式
    floorp --ssb=http://127.0.0.1:9875/launcher.html &
else
    firefox http://127.0.0.1:9875/launcher.html &
fi

# 等窗口出现，然后用 KDE 窗口规则设置
sleep 3

# 通过 KWin 脚本设置窗口属性（置底 + 无边框 + 所有桌面）
gdbus call --session \
    --dest org.kde.KWin \
    --object-path /Scripting \
    --method org.kde.kwin.Scripting.loadScript \
    <(cat <<'KWIN_JS'
var clients = workspace.windowList();
for (var i = 0; i < clients.length; i++) {
    var c = clients[i];
    if (c.resourceClass === "launcher-widget" || c.caption.indexOf("启动器") !== -1) {
        c.noBorder = true;
        c.keepBelow = true;
        c.onAllDesktops = true;
        c.skipTaskbar = true;
        c.skipPager = true;
    }
}
KWIN_JS
) "" 2>/dev/null || true

echo "启动器已启动为桌面小部件模式"
echo "提示：右键窗口标题栏 → 更多操作 → 可手动设置："
echo "  - 保持在下方"
echo "  - 无边框"
echo "  - 在所有桌面上显示"
