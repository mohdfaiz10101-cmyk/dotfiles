#!/bin/bash
# Linode VPS - Claude 反向代理一键部署脚本
set -e

echo "开始部署 Claude 反向代理..."

# 1. 安装软件
apt update && apt install -y nginx openssl ufw apache2-utils curl

# 2. 配置防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 3. 生成 SSL 证书
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/claude-proxy.key \
  -out /etc/nginx/ssl/claude-proxy.crt \
  -subj "/C=US/ST=GA/L=ATL/O=Personal/CN=50.116.38.14"

# 4. 创建 Nginx 配置
cat > /etc/nginx/sites-available/claude-proxy <<'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl http2;
    server_name _;
    ssl_certificate /etc/nginx/ssl/claude-proxy.crt;
    ssl_certificate_key /etc/nginx/ssl/claude-proxy.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    auth_basic "Claude Proxy";
    auth_basic_user_file /etc/nginx/.htpasswd;
    location / {
        proxy_pass https://claude.ai;
        proxy_ssl_server_name on;
        proxy_set_header Host claude.ai;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
        proxy_buffering off;
        proxy_cache off;
    }
}
EOF

# 5. 创建认证密码
echo "claude:$(openssl passwd -apr1 kb9qr6fuop)" > /etc/nginx/.htpasswd

# 6. 启用配置
ln -sf /etc/nginx/sites-available/claude-proxy /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 7. 测试并启动
nginx -t
systemctl restart nginx
systemctl enable nginx

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo "访问地址: https://50.116.38.14"
echo "用户名: claude"
echo "密码: kb9qr6fuop"
echo ""
