#!/usr/bin/env python3
"""
APK 自动更新服务器
端口: 9876
用法: python3 apk-update-server.py
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path

APK_DIR = Path.home() / "apk-releases"
APK_DIR.mkdir(exist_ok=True)

class APKUpdateHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APK_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/version.json":
            # 获取最新 APK 信息
            apk_files = sorted(APK_DIR.glob("*.apk"), key=lambda x: x.stat().st_mtime, reverse=True)

            if apk_files:
                latest = apk_files[0]
                version_info = {
                    "versionCode": 1,
                    "versionName": "1.0.0",
                    "downloadUrl": f"http://192.168.123.1:9876/{latest.name}",
                    "fileSize": latest.stat().st_size,
                    "changelog": "初始版本\n- 内置代理节点\n- 支持 Poe、Gemini、Claude\n- 默认打开微信网页版\n- 自动更新功能"
                }
            else:
                version_info = {
                    "versionCode": 0,
                    "versionName": "0.0.0",
                    "downloadUrl": "",
                    "changelog": "暂无可用版本"
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(version_info, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

if __name__ == "__main__":
    print("📱 APK 更新服务器启动")
    print(f"📁 APK 目录: {APK_DIR}")
    print("🌐 监听端口: 9876")
    print("📡 版本检查: http://localhost:9876/version.json")
    print("📦 APK 下载: http://localhost:9876/<apk文件名>")
    print("")
    print("提示: 将构建好的 APK 放到", APK_DIR, "目录")
    HTTPServer(("0.0.0.0", 9876), APKUpdateHandler).serve_forever()
