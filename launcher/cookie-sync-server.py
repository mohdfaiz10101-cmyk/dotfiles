#!/usr/bin/env python3
"""
Cookie 同步服务器 - 跨设备登录状态同步
运行: python3 cookie-sync-server.py
端口: 9977
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os
from datetime import datetime

COOKIE_DB = os.path.expanduser("~/.local/share/cookie-sync/cookies.db")

class CookieSyncHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """获取所有 Cookie"""
        if self.path == "/cookies":
            conn = sqlite3.connect(COOKIE_DB)
            cur = conn.cursor()
            cur.execute("SELECT domain, name, value, path, expires, secure, httponly FROM cookies")
            cookies = [{"domain": r[0], "name": r[1], "value": r[2], "path": r[3],
                       "expires": r[4], "secure": bool(r[5]), "httpOnly": bool(r[6])}
                      for r in cur.fetchall()]
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(cookies).encode())

        elif self.path.startswith("/cookies/"):
            domain = self.path.split("/")[-1]
            conn = sqlite3.connect(COOKIE_DB)
            cur = conn.cursor()
            cur.execute("SELECT name, value FROM cookies WHERE domain LIKE ?", (f"%{domain}%",))
            cookies = {r[0]: r[1] for r in cur.fetchall()}
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(cookies).encode())

    def do_POST(self):
        """上传 Cookie"""
        if self.path == "/cookies":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            cookies = json.loads(post_data)

            conn = sqlite3.connect(COOKIE_DB)
            cur = conn.cursor()
            for cookie in cookies:
                cur.execute("""
                    INSERT OR REPLACE INTO cookies
                    (domain, name, value, path, expires, secure, httponly, created)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (cookie["domain"], cookie["name"], cookie["value"],
                     cookie.get("path", "/"), cookie.get("expires", 0),
                     int(cookie.get("secure", False)), int(cookie.get("httpOnly", False)),
                     datetime.now().isoformat()))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "count": len(cookies)}).encode())

def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(COOKIE_DB), exist_ok=True)
    conn = sqlite3.connect(COOKIE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cookies (
            domain TEXT,
            name TEXT,
            value TEXT,
            path TEXT DEFAULT '/',
            expires INTEGER DEFAULT 0,
            secure INTEGER DEFAULT 0,
            httponly INTEGER DEFAULT 0,
            created TEXT,
            PRIMARY KEY (domain, name)
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("🍪 Cookie 同步服务器启动")
    print(f"📍 数据库: {COOKIE_DB}")
    print("🌐 监听端口: 9977")
    print("📡 API 端点:")
    print("   GET  /cookies         - 获取所有 Cookie")
    print("   GET  /cookies/{domain} - 获取指定域名 Cookie")
    print("   POST /cookies         - 上传 Cookie")
    HTTPServer(("0.0.0.0", 9977), CookieSyncHandler).serve_forever()
