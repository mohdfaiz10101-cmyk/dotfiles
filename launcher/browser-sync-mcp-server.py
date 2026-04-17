#!/usr/bin/env python3
"""
浏览器 MCP 同步服务器 - 跨设备浏览器状态同步
端口: 9978
功能: 书签、历史、标签页、Cookie、设置等全方位同步
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".local/share/browser-sync/sync.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class BrowserSyncHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """获取同步数据"""
        if self.path == "/sync/all":
            # 获取所有同步数据
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            data = {
                "bookmarks": self._get_bookmarks(cur),
                "history": self._get_history(cur),
                "tabs": self._get_tabs(cur),
                "cookies": self._get_cookies(cur),
                "settings": self._get_settings(cur)
            }

            conn.close()
            self._json_response(data)

        elif self.path.startswith("/sync/"):
            sync_type = self.path.split("/")[-1]
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            if sync_type == "bookmarks":
                data = self._get_bookmarks(cur)
            elif sync_type == "history":
                data = self._get_history(cur)
            elif sync_type == "tabs":
                data = self._get_tabs(cur)
            elif sync_type == "cookies":
                data = self._get_cookies(cur)
            elif sync_type == "settings":
                data = self._get_settings(cur)
            else:
                data = {"error": "Unknown sync type"}

            conn.close()
            self._json_response(data)

    def do_POST(self):
        """上传同步数据"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        if self.path == "/sync/bookmarks":
            self._save_bookmarks(cur, data)
        elif self.path == "/sync/history":
            self._save_history(cur, data)
        elif self.path == "/sync/tabs":
            self._save_tabs(cur, data)
        elif self.path == "/sync/cookies":
            self._save_cookies(cur, data)
        elif self.path == "/sync/settings":
            self._save_settings(cur, data)

        conn.commit()
        conn.close()

        self._json_response({"status": "ok", "timestamp": datetime.now().isoformat()})

    def _get_bookmarks(self, cur):
        cur.execute("SELECT url, title, folder, created FROM bookmarks ORDER BY created DESC")
        return [{"url": r[0], "title": r[1], "folder": r[2], "created": r[3]} for r in cur.fetchall()]

    def _get_history(self, cur):
        cur.execute("SELECT url, title, visit_count, last_visit FROM history ORDER BY last_visit DESC LIMIT 1000")
        return [{"url": r[0], "title": r[1], "visitCount": r[2], "lastVisit": r[3]} for r in cur.fetchall()]

    def _get_tabs(self, cur):
        cur.execute("SELECT device, url, title FROM open_tabs WHERE device = ?", (self._get_device_id(),))
        return [{"url": r[1], "title": r[2]} for r in cur.fetchall()]

    def _get_cookies(self, cur):
        cur.execute("SELECT domain, name, value FROM cookies")
        return [{"domain": r[0], "name": r[1], "value": r[2]} for r in cur.fetchall()]

    def _get_settings(self, cur):
        cur.execute("SELECT key, value FROM settings")
        return {r[0]: r[1] for r in cur.fetchall()}

    def _save_bookmarks(self, cur, bookmarks):
        for bm in bookmarks:
            cur.execute("INSERT OR REPLACE INTO bookmarks (url, title, folder, created) VALUES (?, ?, ?, ?)",
                       (bm["url"], bm["title"], bm.get("folder", ""), bm.get("created", datetime.now().isoformat())))

    def _save_history(self, cur, history):
        for h in history:
            cur.execute("INSERT OR REPLACE INTO history (url, title, visit_count, last_visit) VALUES (?, ?, ?, ?)",
                       (h["url"], h["title"], h.get("visitCount", 1), h.get("lastVisit", datetime.now().isoformat())))

    def _save_tabs(self, cur, tabs):
        device_id = self._get_device_id()
        cur.execute("DELETE FROM open_tabs WHERE device = ?", (device_id,))
        for tab in tabs:
            cur.execute("INSERT INTO open_tabs (device, url, title) VALUES (?, ?, ?)",
                       (device_id, tab["url"], tab["title"]))

    def _save_cookies(self, cur, cookies):
        for c in cookies:
            cur.execute("INSERT OR REPLACE INTO cookies (domain, name, value) VALUES (?, ?, ?)",
                       (c["domain"], c["name"], c["value"]))

    def _save_settings(self, cur, settings):
        for key, value in settings.items():
            cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

    def _get_device_id(self):
        return os.uname().nodename

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            url TEXT PRIMARY KEY,
            title TEXT,
            folder TEXT,
            created TEXT
        );

        CREATE TABLE IF NOT EXISTS history (
            url TEXT PRIMARY KEY,
            title TEXT,
            visit_count INTEGER DEFAULT 1,
            last_visit TEXT
        );

        CREATE TABLE IF NOT EXISTS open_tabs (
            device TEXT,
            url TEXT,
            title TEXT,
            PRIMARY KEY (device, url)
        );

        CREATE TABLE IF NOT EXISTS cookies (
            domain TEXT,
            name TEXT,
            value TEXT,
            PRIMARY KEY (domain, name)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("🌐 浏览器 MCP 同步服务器启动")
    print(f"📁 数据库: {DB_PATH}")
    print("🌐 监听端口: 9978")
    print("")
    print("API 端点:")
    print("  GET  /sync/all       - 获取所有同步数据")
    print("  GET  /sync/bookmarks - 获取书签")
    print("  POST /sync/bookmarks - 上传书签")
    print("  GET  /sync/history   - 获取历史")
    print("  GET  /sync/tabs      - 获取打开的标签页")
    print("  GET  /sync/cookies   - 获取 Cookies")
    HTTPServer(("0.0.0.0", 9978), BrowserSyncHandler).serve_forever()
