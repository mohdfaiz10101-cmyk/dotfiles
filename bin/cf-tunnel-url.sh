#!/run/current-system/sw/bin/bash
# 获取 Cloudflare Tunnel URL 并推送到 Telegram
TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | tail -1)
if [ -z "$TUNNEL_URL" ]; then
    # 尝试从 cloudflared 状态获取
    TUNNEL_URL=$(curl -s http://localhost:4040/status 2>/dev/null | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | head -1)
fi

if [ -n "$TUNNEL_URL" ]; then
    echo "OpenCode 临时访问地址: <a href=\"$TUNNEL_URL\">$TUNNEL_URL</a>" | /home/charlie/bin/.notify-venv/bin/python3 ~/bin/notify-telegram.py P1 "Cloudflare Tunnel"
else
    echo "Tunnel URL 未找到" | python3 ~/bin/notify-telegram.py P1 "Tunnel 异常"
fi
