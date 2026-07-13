#!/usr/bin/env bash
# 自动 Cookie 同步脚本 - 每5分钟同步一次浏览器 Cookie

COOKIE_SERVER="http://192.168.123.1:9977"
FIREFOX_PROFILE=$(find ~/.mozilla/firefox -name "*.default*" -type d | head -1)
CHROME_PROFILE="$HOME/.config/google-chrome/Default"

sync_firefox_cookies() {
    if [ -f "$FIREFOX_PROFILE/cookies.sqlite" ]; then
        echo "[$(date)] 同步 Firefox Cookies..."
        sqlite3 "$FIREFOX_PROFILE/cookies.sqlite" \
            "SELECT host, name, value, path, expiry, isSecure, isHttpOnly FROM moz_cookies" \
            | while IFS='|' read -r domain name value path expires secure httponly; do
                curl -s -X POST "$COOKIE_SERVER/cookies" \
                    -H "Content-Type: application/json" \
                    -d "[{\"domain\":\"$domain\",\"name\":\"$name\",\"value\":\"$value\",\"path\":\"$path\",\"expires\":$expires,\"secure\":$secure,\"httpOnly\":$httponly}]"
            done
        echo "✅ Firefox Cookies 已上传"
    fi
}

sync_chrome_cookies() {
    if [ -f "$CHROME_PROFILE/Cookies" ]; then
        echo "[$(date)] 同步 Chrome Cookies..."
        # Chrome Cookies 需要解密，暂时跳过
        echo "⚠️ Chrome Cookie 同步需要解密，暂时跳过"
    fi
}

while true; do
    sync_firefox_cookies
    sleep 300  # 每5分钟同步一次
done
