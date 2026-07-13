#!/run/current-system/sw/bin/python3
"""
Claude ESP (Extended Session Persistence) - 简化版
实时同步 Claude Code 操作结果到平板浏览器
只使用 Python 标准库
"""
import json
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os

# Claude 会话历史文件路径
CLAUDE_PROJECT_DIR = Path.home() / ".claude" / "projects"
CURRENT_SESSION_FILE = None
LAST_LINE_COUNT = 0

def find_latest_session():
    """查找最新的会话文件"""
    try:
        jsonl_files = list(CLAUDE_PROJECT_DIR.rglob("*.jsonl"))
        if jsonl_files:
            latest = max(jsonl_files, key=lambda p: p.stat().st_mtime)
            return latest
    except Exception as e:
        print(f"查找会话文件失败: {e}")
    return None

def read_session_updates():
    """读取会话更新"""
    global CURRENT_SESSION_FILE, LAST_LINE_COUNT

    if not CURRENT_SESSION_FILE:
        CURRENT_SESSION_FILE = find_latest_session()
        if not CURRENT_SESSION_FILE:
            return []

    try:
        with open(CURRENT_SESSION_FILE, 'r') as f:
            lines = f.readlines()
            new_lines = lines[LAST_LINE_COUNT:]
            LAST_LINE_COUNT = len(lines)

            messages = []
            for line in new_lines:
                try:
                    data = json.loads(line)
                    msg = format_message(data)
                    if msg:
                        messages.append(msg)
                except:
                    pass
            return messages
    except Exception as e:
        print(f"读取会话失败: {e}")
        return []

def format_message(data):
    """格式化消息"""
    try:
        msg_type = data.get('type', '')

        if msg_type == 'assistant':
            content = data.get('content', [])
            text_parts = []
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'text':
                    text_parts.append(c.get('text', ''))
            if text_parts:
                return {'type': 'assistant', 'text': '\n'.join(text_parts)}

        elif msg_type == 'tool_use':
            tool_name = data.get('name', '')
            return {'type': 'tool', 'text': f'🔧 {tool_name}'}

        elif msg_type == 'tool_result':
            content = data.get('content', '')
            if isinstance(content, list):
                text_parts = []
                for c in content:
                    if isinstance(c, dict):
                        text_parts.append(c.get('text', ''))
                content = '\n'.join(text_parts)
            text = str(content)[:500]
            if text:
                return {'type': 'result', 'text': text}

    except Exception as e:
        pass
    return None

class ESPHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(ESP_HTML.encode('utf-8'))

        elif self.path == '/updates':
            messages = read_session_updates()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(messages).encode('utf-8'))

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # 静默日志

ESP_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Claude ESP</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #e6edf3; --dim: #7d8590; --accent: #58a6ff;
  --green: #3fb950; --red: #f85149;
}
body {
  font-family: "Noto Sans CJK SC", "SF Mono", Consolas, monospace;
  background: var(--bg); color: var(--text);
  padding: 0; overflow: hidden; height: 100vh;
  display: flex; flex-direction: column;
}
.header {
  background: var(--surface); padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}
.title {
  font-size: 16px; font-weight: 600;
  display: flex; align-items: center; gap: 8px;
}
.status {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--green); animation: pulse 2s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.controls { display: flex; gap: 8px; }
.btn {
  padding: 8px 16px; border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface); color: var(--text);
  font-size: 13px; cursor: pointer;
  transition: all 0.15s; touch-action: manipulation;
}
.btn:active { background: var(--border); transform: scale(0.95); }
.output-container {
  flex: 1; overflow-y: auto; padding: 16px;
  -webkit-overflow-scrolling: touch;
  font-size: 14px; line-height: 1.6;
}
.msg {
  padding: 8px 0; white-space: pre-wrap;
  word-wrap: break-word; word-break: break-word;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  margin-bottom: 8px;
}
.msg.assistant { color: var(--text); }
.msg.tool { color: var(--accent); font-weight: 600; }
.msg.result { color: var(--dim); font-size: 12px; }
.footer {
  background: var(--surface); padding: 8px 16px;
  border-top: 1px solid var(--border);
  font-size: 11px; color: var(--dim);
  text-align: center; flex-shrink: 0;
}
</style>
</head>
<body>

<div class="header">
  <div class="title">
    <div class="status" id="status"></div>
    <span>Claude ESP</span>
  </div>
  <div class="controls">
    <button class="btn" onclick="clearOutput()">清空</button>
    <button class="btn" onclick="toggleAutoScroll()">
      <span id="scrollBtn">自动滚动</span>
    </button>
  </div>
</div>

<div class="output-container" id="output">
  <div class="msg tool">正在连接...</div>
</div>

<div class="footer">
  <span id="msgCount">0 条消息</span> ·
  <span id="lastUpdate">未更新</span>
</div>

<script>
let autoScroll = true;
let msgCount = 0;
const output = document.getElementById('output');

function addMessage(text, type = 'assistant') {
  const msg = document.createElement('div');
  msg.className = 'msg ' + type;
  msg.textContent = text;
  output.appendChild(msg);
  msgCount++;
  updateFooter();
  if (autoScroll) {
    output.scrollTop = output.scrollHeight;
  }
}

function clearOutput() {
  output.innerHTML = '<div class="msg tool">已清空</div>';
  msgCount = 0;
  updateFooter();
}

function toggleAutoScroll() {
  autoScroll = !autoScroll;
  document.getElementById('scrollBtn').textContent =
    autoScroll ? '自动滚动' : '手动滚动';
}

function updateFooter() {
  document.getElementById('msgCount').textContent = msgCount + ' 条消息';
  document.getElementById('lastUpdate').textContent =
    new Date().toLocaleTimeString('zh-CN');
}

async function fetchUpdates() {
  try {
    const response = await fetch('/updates');
    const messages = await response.json();
    messages.forEach(msg => addMessage(msg.text, msg.type));
  } catch (e) {
    console.error('获取更新失败:', e);
  }
}

// 每秒轮询一次更新
setInterval(fetchUpdates, 1000);
fetchUpdates();
</script>

</body>
</html>
"""

if __name__ == "__main__":
    PORT = 9980
    print(f"🚀 Claude ESP Server 启动")
    print(f"📱 平板访问: http://<主机IP>:{PORT}")
    print(f"💻 本地访问: http://localhost:{PORT}")
    print(f"📂 监控目录: {CLAUDE_PROJECT_DIR}")
    print()

    server = HTTPServer(('0.0.0.0', PORT), ESPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ 服务器已停止")
