#!/run/current-system/sw/bin/python3
"""
平板控制面板 API 服务器
提供命令执行和状态检查接口
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import subprocess
import os
import sqlite3
from pathlib import Path

AGENT_DB = Path.home() / ".local" / "lib" / "agent-orchestrator" / "agent_tasks.db"
AGENT_STATUS = Path.home() / ".cache" / "agent-orchestrator-status.json"
PATROL_STATUS = Path.home() / ".cache" / "agent-patrol-status.json"


def query_agent_db(sql, params=()):
    try:
        db = sqlite3.connect(str(AGENT_DB), timeout=5)
        db.row_factory = sqlite3.Row
        rows = db.execute(sql, params).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


class TabletControlHandler(SimpleHTTPRequestHandler):
    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def do_POST(self):
        if self.path == '/api/agent/tasks':
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length))
            title = body.get('title', '').strip()
            if not title:
                self._json_response({"error": "title required"}, 400)
                return
            try:
                db = sqlite3.connect(str(AGENT_DB), timeout=5)
                cursor = db.execute(
                    "INSERT INTO tasks (title, description, complexity, priority, source) VALUES (?, ?, ?, ?, ?)",
                    (title, body.get('description', ''), body.get('complexity', 'medium'),
                     body.get('priority', 5), 'tablet')
                )
                task_id = cursor.lastrowid
                db.commit()
                db.close()
                self._json_response({"id": task_id, "title": title})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if self.path == '/api/agent/control':
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length))
            action = body.get('action', '')
            try:
                if action == 'start':
                    subprocess.run(['systemctl', '--user', 'start', 'agent-orchestrator'], timeout=10)
                elif action == 'stop':
                    subprocess.run(['systemctl', '--user', 'stop', 'agent-orchestrator'], timeout=10)
                elif action == 'restart':
                    subprocess.run(['systemctl', '--user', 'restart', 'agent-orchestrator'], timeout=10)
                elif action == 'patrol':
                    subprocess.Popen(['python3', str(Path.home() / '.local/lib/agent-orchestrator/patrol.py'), '--once'])
                else:
                    self._json_response({"error": "unknown action"}, 400)
                    return
                self._json_response({"ok": True, "action": action})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if self.path == '/api/exec':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            cmd = data.get('command', '')

            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True,
                    text=True, timeout=10
                )
                output = result.stdout or result.stderr or 'Command executed'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'output': output[:500]
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': str(e)
                }).encode())

    def do_GET(self):
        if self.path == '/api/agent/tasks':
            rows = query_agent_db(
                "SELECT id, title, assigned_to, status, complexity, priority, error_count, created_at, finished_at "
                "FROM tasks ORDER BY status='running' DESC, status='pending' DESC, priority ASC LIMIT 50"
            )
            self._json_response(rows)
            return

        if self.path == '/api/agent/status':
            data = {}
            if AGENT_STATUS.exists():
                try:
                    data = json.loads(AGENT_STATUS.read_text())
                except Exception:
                    pass
            self._json_response(data)
            return

        if self.path == '/api/agent/patrol':
            data = {}
            if PATROL_STATUS.exists():
                try:
                    data = json.loads(PATROL_STATUS.read_text())
                except Exception:
                    pass
            self._json_response(data)
            return

        if self.path.startswith('/api/agent/log/'):
            task_id = self.path.split('/')[-1]
            rows = query_agent_db(
                "SELECT * FROM agent_log WHERE task_id=? ORDER BY created_at DESC LIMIT 20",
                (task_id,)
            )
            self._json_response(rows)
            return

        if self.path == '/api/status':
            services = {
                'hyperchat': self.check_service('hyperchat'),
                'launcher': self.check_port(9875),
                'syncthing': self.check_port(8384),
                'cockpit': self.check_port(9090),
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(services).encode())

        elif self.path == '/api/ping-windows':
            result = subprocess.run(
                'ping -c 1 -W 1 192.168.123.136',
                shell=True, capture_output=True
            )
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'online': result.returncode == 0
            }).encode())

        else:
            super().do_GET()

    def check_service(self, name):
        result = subprocess.run(
            f'systemctl --user is-active {name}',
            shell=True, capture_output=True, text=True
        )
        return result.stdout.strip() == 'active'

    def check_port(self, port):
        result = subprocess.run(
            f'curl -s http://localhost:{port} >/dev/null 2>&1',
            shell=True
        )
        return result.returncode == 0

if __name__ == '__main__':
    os.chdir('/home/charlie/launcher/public')
    server = HTTPServer(('0.0.0.0', 9876), TabletControlHandler)
    print('平板控制面板运行在: http://localhost:9876/tablet-control.html')
    server.serve_forever()
