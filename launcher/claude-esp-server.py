#!/usr/bin/env python3
"""
Claude ESP (Extended Session Persistence) Server
实时同步 Claude Code 操作结果到平板浏览器
"""
import json
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uvicorn

app = FastAPI()

# 存储所有连接的 WebSocket 客户端
clients = set()

# Claude 会话历史文件路径
CLAUDE_PROJECT_DIR = Path.home() / ".claude" / "projects"
CURRENT_SESSION = None

class ClaudeSessionHandler(FileSystemEventHandler):
    """监控 Claude 会话文件变化"""
    def on_modified(self, event):
        if event.src_path.endswith('.jsonl'):
            asyncio.create_task(broadcast_update(event.src_path))

async def broadcast_update(file_path):
    """广播更新到所有客户端"""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = json.loads(lines[-1])
                message = format_message(last_line)
                if message:
                    await broadcast(message)
    except Exception as e:
        print(f"Error reading file: {e}")

def format_message(data):
    """格式化消息"""
    try:
        msg_type = data.get('type', '')

        if msg_type == 'assistant':
            content = data.get('content', [])
            text_parts = [c.get('text', '') for c in content if c.get('type') == 'text']
            if text_parts:
                return {'type': 'assistant', 'text': '\n'.join(text_parts)}

        elif msg_type == 'tool_use':
            tool_name = data.get('name', '')
            return {'type': 'tool', 'text': f'🔧 {tool_name}'}

        elif msg_type == 'tool_result':
            content = data.get('content', '')
            if isinstance(content, list):
                content = '\n'.join([c.get('text', '') for c in content if isinstance(c, dict)])
            return {'type': 'result', 'text': str(content)[:500]}

    except Exception as e:
        print(f"Format error: {e}")
    return None

async def broadcast(message):
    """广播消息到所有客户端"""
    if clients:
        disconnected = set()
        for client in clients:
            try:
                await client.send_json(message)
            except:
                disconnected.add(client)
        clients.difference_update(disconnected)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        pass
    finally:
        clients.discard(websocket)

@app.get("/")
async def get_page():
    return HTMLResponse(ESP_HTML)

ESP_HTML = """
<!DOCTYPE html>
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
  --green: #3fb950; --red: #f85149; --yellow: #d29922;
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
.status.disconnected { background: var(--red); animation: none; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.controls { display: flex; gap: 8px; }
.btn {
  padding: 8px 16px; border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface); color: var(--text);
  font-size: 13px; cursor: pointer;
  transition: all 0.15s; touch-action: manipulation;
}
.btn:active {
  background: var(--border); transform: scale(0.95);
}
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
  <div class="msg tool">等待连接...</div>
</div>

<div class="footer">
  <span id="msgCount">0 条消息</span> ·
  <span id="lastUpdate">未更新</span>
</div>

<script>
let autoScroll = true;
let msgCount = 0;
const output = document.getElementById('output');
const status = document.getElementById('status');
let ws = null;

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(protocol + '//' + location.host + '/ws');

  ws.onopen = () => {
    status.className = 'status';
    addMessage('✓ 已连接', 'tool');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    addMessage(data.text, data.type);
  };

  ws.onclose = () => {
    status.className = 'status disconnected';
    addMessage('✗ 连接断开，5秒后重连...', 'result');
    setTimeout(connect, 5000);
  };
}

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

connect();
</script>

</body>
</html>
"""

if __name__ == "__main__":
    print("🚀 Claude ESP Server 启动")
    print("📱 平板访问: http://<主机IP>:9979")
    print("💻 本地访问: http://localhost:9979")

    # 启动文件监控
    observer = Observer()
    handler = ClaudeSessionHandler()
    observer.schedule(handler, str(CLAUDE_PROJECT_DIR), recursive=True)
    observer.start()

    try:
        uvicorn.run(app, host="0.0.0.0", port=9979)
    finally:
        observer.stop()
        observer.join()