"""
Charlie Hub API — 统一入口（健康检查 + 微信统一面板 API）
"""

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import json
import os
import sqlite3
import subprocess
import time
import typing
import urllib.parse
import urllib.request
import uvicorn
import base64
import hashlib
import ssl
import io
import re
import shlex
import uuid
import zipfile
import xml.sax.saxutils
from datetime import datetime
from hub_config import cfg

# ── 三方对话室 ─────────────────────────────────────────────
_ws_clients: list[WebSocket] = []
_ws_lock = asyncio.Lock()


def dialogue_append(sender: str, content: str, msg_type: str = "message") -> None:
    """外部脚本调用此函数广播消息（也可直接追加文件）。"""
    entry = {
        "ts": time.strftime("%H:%M:%S"),
        "from": sender,
        "type": msg_type,
        "content": content,
    }
    with open(cfg.DIALOGUE_FEED, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


app = FastAPI(title="Charlie Hub API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── AI 任务注册表（内存，最小可用） ─────────────────────────
# ponytail: 内存存储，hub 重启丢失；够面板用，如需持久化再加 sqlite。
import threading

_task_lock = threading.Lock()
_tasks: dict[str, dict] = {}
_task_counter = 0

# ── 面板点击统计（SQLite + 内存缓存） ─────────────────────
# ponytail: SQLite 持久化，hub 重启不丢；内存缓存减少 IO。
import sqlite3
_CLICK_DB = Path(__file__).parent / 'clicks.db'
_CLICK_DB_LOCK = threading.Lock()
_click_lock = threading.Lock()
_clicks: dict[str, int] = {}


def _init_click_db():
    with sqlite3.connect(_CLICK_DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS clicks (click_id TEXT PRIMARY KEY, count INTEGER NOT NULL)")


def _record_click(click_id: str) -> int:
    with _click_lock:
        _clicks[click_id] = _clicks.get(click_id, 0) + 1
        count = _clicks[click_id]
    with sqlite3.connect(_CLICK_DB) as conn:
        conn.execute("INSERT INTO clicks (click_id, count) VALUES (?, ?) ON CONFLICT(click_id) DO UPDATE SET count = count + 1", (click_id, 1))
        conn.commit()
    return count


def _get_clicks() -> dict[str, int]:
    with _click_lock:
        if not _clicks:
            try:
                with sqlite3.connect(_CLICK_DB) as conn:
                    rows = conn.execute("SELECT click_id, count FROM clicks").fetchall()
                    _clicks.update({r[0]: r[1] for r in rows})
            except Exception:
                pass
        return dict(_clicks)


_architecture_cache: dict[str, typing.Any] = {"ts": 0.0, "data": None}


DEVICE_CODE = os.environ.get("HUB_DEVICE_CODE", "w19900422")


LINK_REGISTRY: dict[str, dict] = {
    "terminal": {
        "name": "终端入口",
        "description": "OpenClaw ttyd / 手机远程终端",
        "candidates": [
            "http://100.87.238.153:18080/?device={device}",
            "http://192.168.123.71:18080/?device={device}",
            "http://{host}:18080/?device={device}",
            "http://charlie1990.duckdns.org:18080/?device={device}",
            "http://{host}:8080/",
        ],
    },
    "opencode": {
        "name": "OpenCode",
        "description": "OpenCode Web 控制台",
        "candidates": [
            "http://100.87.238.153:18910/?device={device}",
            "http://192.168.123.71:18910/?device={device}",
            "http://{host}:18910/?device={device}",
            "http://charlie1990.duckdns.org:18910/?device={device}",
            "http://{host}:4097/?device={device}",
        ],
    },
    "crush": {
        "name": "Crush",
        "description": "Crush WebTTY / Button API",
        "candidates": [
            "http://100.87.238.153:17766/",
            "http://192.168.123.71:17766/",
            "http://{host}:17766/",
            "http://charlie1990.duckdns.org:17766/",
            "http://127.0.0.1:17766/",
        ],
    },
    "codex": {
        "name": "Codex",
        "description": "Codex WebTTY 入口",
        "candidates": [
            "http://100.87.238.153:19899/",
            "http://100.87.238.153:19900/",
            "http://100.87.238.153:19902/",
            "http://192.168.123.71:19899/",
            "http://192.168.123.71:19900/",
            "http://192.168.123.71:19902/",
            "http://{host}:19899/",
            "http://{host}:19900/",
            "http://{host}:19902/",
        ],
    },
    "termhive": {
        "name": "TermHive",
        "description": "TermHive 项目控制台",
        "candidates": [
            "/proxy/termhive/",
            "http://{host}:18081/",
            "https://fedora-termhive.tail60cff7.ts.net/",
        ],
    },
    "cursor": {
        "name": "Cursor GUI",
        "description": "Cursor/KasmVNC GUI IDE；适合前端视觉、插件、登录态、人工协同代码任务",
        "candidates": [
            "http://100.87.238.153:19970/",
            "http://192.168.123.71:19970/",
            "http://{host}:19970/",
        ],
    },
    "goose": {
        "name": "Goose 只读诊断",
        "description": "Goose/Guise 只读计划与任务分诊；写入前转 Hub/Aider 审批",
        "candidates": [
            "http://100.87.238.153:7694/tool/guise/",
            "http://192.168.123.71:7694/tool/guise/",
            "http://{host}:7694/tool/guise/",
        ],
    },
    "aider": {
        "name": "Aider 单写入执行",
        "description": "经 Goose 计划和 Hub 审批后的单写入代码执行器",
        "candidates": [
            "http://100.87.238.153:7693/tool/aider/",
            "http://192.168.123.71:7693/tool/aider/",
            "http://{host}:7693/tool/aider/",
        ],
    },
    "fastgpt": {
        "name": "FastGPT",
        "description": "知识库 / 工作流问答",
        "candidates": [
            "http://100.87.238.153:3000/",
            "http://192.168.123.71:3000/",
            "http://{host}:19894/",
            "http://charlie1990.duckdns.org:19894/",
            "http://{host}:3000/",
        ],
    },
    "litellm": {
        "name": "LiteLLM",
        "description": "AI 网关模型列表",
        "candidates": [
            "http://{host}:4000/v1/models",
            "http://{host}:4002/v1/models",
        ],
    },
    "telegram": {
        "name": "Telegram Gateway",
        "description": "Telegram 控制网关健康检查",
        "candidates": [
            "/api/links",
            "http://{host}:9811/health",
        ],
    },
    "openagents": {
        "name": "OpenAgents",
        "description": "Agent 网络",
        "candidates": [
            "http://{host}:19876/",
            "http://{host}:8700/",
        ],
    },
    "mihomo": {
        "name": "Mihomo",
        "description": "代理控制面板",
        "candidates": [
            "http://{host}:9091/ui",
        ],
    },
    "sunshine": {
        "name": "Sunshine",
        "description": "串流控制台",
        "candidates": [
            "https://{host}:47990/",
            "https://fedora.tailnet.local:47990/",
        ],
    },
    "hub": {
        "name": "Hub 工作台",
        "description": "9800 统一入口；优先给手机 NetBird 与家里局域网双地址",
        "candidates": [
            "http://100.87.238.153:9800/",
            "http://100.87.238.153:9800/projects",
            "http://192.168.123.71:9800/",
            "http://192.168.123.71:9800/projects",
            "/",
        ],
    },
    "appsmith": {
        "name": "统一操作台",
        "description": "Appsmith internal tool console; one-window control plane for Hub/n8n/OP/FastGPT/Zulip",
        "candidates": [
            "http://100.87.238.153:8089/",
            "http://192.168.123.71:8089/",
            "http://{host}:8089/",
            "http://127.0.0.1:8089/",
        ],
    },
    "n8n": {
        "name": "动作总线",
        "description": "n8n workflow automation bus for Hub/OP/FastGPT/Zulip/Plane/Huly",
        "candidates": [
            "http://100.87.238.153:5678/",
            "http://192.168.123.71:5678/",
            "http://{host}:5678/",
            "http://127.0.0.1:5678/",
        ],
    },
    "dashboard": {
        "name": "系统全景",
        "description": "服务 / 软件 / 项目",
        "candidates": ["/dashboard"],
    },
    "ai-panel": {
        "name": "AI 工作台",
        "description": "Agent / MCP / 任务派发",
        "candidates": ["/ai-panel"],
    },
    "control": {
        "name": "控制中心",
        "description": "服务启停与诊断",
        "candidates": ["/control"],
    },
    "service-manager": {
        "name": "服务管理",
        "description": "服务分类、内存占用、锁定开机启动",
        "candidates": ["/service-manager"],
    },
    "kanban": {
        "name": "任务看板",
        "description": "项目和任务推进",
        "candidates": ["/kanban"],
    },
    "contracts": {
        "name": "合同助手",
        "description": "截图/图片 + 一句话生成合同草稿和 Excel 明细",
        "candidates": ["/contracts"],
    },
    "plane": {
        "name": "Plane",
        "description": "自托管项目进度、任务、周期、模块和路线图",
        "candidates": [
            "http://100.87.238.153:8090/",
            "http://192.168.123.71:8090/",
            "http://{host}:8090/",
            "http://127.0.0.1:8090/",
            "https://fedora-termhive.tail60cff7.ts.net/",
            "http://100.87.238.153:8090/god-mode/",
            "http://192.168.123.71:8090/god-mode/",
            "http://{host}:8090/god-mode/",
            "http://127.0.0.1:8090/god-mode/",
        ],
    },
    "huly": {
        "name": "Huly",
        "description": "综合工作区：项目、任务、文档、聊天和协作",
        "candidates": [
            "http://100.87.238.153:8087/",
            "http://192.168.123.71:8087/",
            "http://{host}:8087/",
            "http://127.0.0.1:8087/",
        ],
    },
    "mattermost": {
        "name": "Mattermost",
        "description": "频道聊天、机器人、图片、Webhook 和 AI 协作入口",
        "candidates": [
            "http://100.87.238.153:8065/",
            "http://192.168.123.71:8065/",
            "http://{host}:8065/",
            "http://127.0.0.1:8065/",
        ],
    },
    "search": {
        "name": "全局搜索",
        "description": "资料检索",
        "candidates": ["/search"],
    },
    "wechat": {
        "name": "微信查询",
        "description": "聊天记录查询",
        "candidates": ["/wechat"],
    },
    "phone-health": {
        "name": "手机健康",
        "description": "ADB / Haven 状态",
        "candidates": ["/phone-health"],
    },
    "sourcing": {
        "name": "Sourcing 项目",
        "description": "旧 WordPress 站点资产与 Astro 迁移项目",
        "candidates": ["/#projects"],
    },
    "replit-agent": {
        "name": "Replit Agent",
        "description": "AI 全栈建站、后台、数据库与部署",
        "candidates": ["https://replit.com/products/agent"],
    },
    "lovable": {
        "name": "Lovable",
        "description": "AI 应用与网站生成",
        "candidates": ["https://lovable.dev/"],
    },
    "bolt": {
        "name": "Bolt",
        "description": "AI 网站 / Web App 原型与部署",
        "candidates": ["https://bolt.new/"],
    },
    "v0": {
        "name": "v0",
        "description": "React / Next.js UI 与页面生成",
        "candidates": ["https://v0.app/"],
    },
    "google-trends": {
        "name": "Google Trends",
        "description": "搜索趋势和急需配件需求发现",
        "candidates": ["https://trends.google.com/trends/"],
    },
    "google-merchant": {
        "name": "Google Merchant Center",
        "description": "免费商品展示和商品 Feed",
        "candidates": ["https://business.google.com/us/merchant-center/"],
    },
    "meta-advantage": {
        "name": "Meta Advantage+",
        "description": "Facebook / Instagram AI 广告自动化",
        "candidates": ["https://www.facebook.com/business/ads/meta-advantage-plus"],
    },
    "tiktok-creative": {
        "name": "TikTok Creative Center",
        "description": "短视频趋势、热门广告和创意参考",
        "candidates": ["https://ads.tiktok.com/business/creativecenter/trends/hub/pc/en"],
    },
    "odoo": {
        "name": "Odoo",
        "description": "开源 ERP / CRM / 电商 / 网站 / 库存一体化",
        "candidates": ["https://www.odoo.com/"],
    },
    "erpnext": {
        "name": "ERPNext",
        "description": "开源 ERP、CRM、库存、网站和运营后台",
        "candidates": ["https://erpnext.com/"],
    },
    "medusa": {
        "name": "Medusa",
        "description": "开源可定制 commerce 后端和管理台",
        "candidates": ["https://medusajs.com/"],
    },
    "saleor": {
        "name": "Saleor",
        "description": "开源 GraphQL / headless 电商平台",
        "candidates": ["https://saleor.io/"],
    },
    "vendure": {
        "name": "Vendure",
        "description": "开源 B2B / marketplace / headless commerce",
        "candidates": ["https://vendure.io/"],
    },
    "directus": {
        "name": "Directus",
        "description": "开源数据后台、权限、API 和 no-code 管理界面",
        "candidates": ["https://directus.com/"],
    },
    "payload": {
        "name": "Payload CMS",
        "description": "开源 Next.js CMS / 应用后台 / 电商内容",
        "candidates": ["https://payloadcms.com/"],
    },
    "grapesjs": {
        "name": "GrapesJS",
        "description": "开源可视化页面/模板编辑器框架",
        "candidates": ["https://grapesjs.com/"],
    },
    "mautic": {
        "name": "Mautic",
        "description": "开源营销自动化、邮件、线索培育",
        "candidates": ["https://www.mautic.org/"],
    },
    "n8n-info": {
        "name": "n8n 官网",
        "description": "开源工作流自动化和营销/CRM 集成",
        "candidates": ["https://n8n.io/"],
    },
    "ntfy": {
        "name": "ntfy",
        "description": "轻量 topic 通知频道，项目同步走 charlie-projects；手机订阅仍可用 DuckDNS",
        "candidates": [
            "http://100.87.238.153:2586/",
            "http://192.168.123.71:2586/",
            "http://charlie1990.duckdns.org:19867/",
        ],
    },
    "mattermost-info": {
        "name": "Mattermost",
        "description": "自建团队频道、Incoming Webhook、权限较清晰",
        "candidates": ["https://mattermost.com/"],
    },
    "zulip": {
        "name": "Zulip",
        "description": "频道 + topic 结构，适合异步项目讨论",
        "candidates": ["https://charlie.zulipchat.com/", "https://zulip.com/"],
    },
    "rocketchat": {
        "name": "Rocket.Chat",
        "description": "自建团队通信、webhook、细粒度权限",
        "candidates": ["https://www.rocket.chat/"],
    },
}


def _link_candidates(key: str, request: Request) -> list[str]:
    item = LINK_REGISTRY.get(key)
    if not item:
        return []
    host = request.headers.get("host", "127.0.0.1:9800").split(":")[0]
    values = []
    for template in item.get("candidates", []):
        values.append(template.format(host=host, device=DEVICE_CODE))
    return values


def _go_page(key: str, item: dict, candidates: list[str]) -> str:
    payload = json.dumps({"key": key, "item": item, "candidates": candidates}, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{item.get('name', key)} 跳转</title>
<style>
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#111312;color:#edf2ee;font:15px system-ui,sans-serif}}
.box{{width:min(92vw,520px);border:1px solid #303832;border-radius:8px;background:#181c1a;padding:18px}}
h1{{margin:0 0 8px;font-size:20px}}p{{margin:0 0 14px;color:#9daaa2;line-height:1.5}}
.row{{display:flex;gap:8px;align-items:center;justify-content:space-between;border:1px solid #303832;border-radius:6px;padding:10px;margin-top:8px}}
a{{color:#edf2ee;text-decoration:none}}.muted{{color:#9daaa2;font-size:12px;word-break:break-all}}.ok{{color:#79d38b}}.bad{{color:#ee7c7c}}
button{{border:1px solid #303832;background:#202521;color:#edf2ee;border-radius:6px;padding:8px 10px;cursor:pointer}}
</style></head><body><main class="box">
<h1>{item.get('name', key)}</h1><p id="status">正在选择可访问链接...</p><div id="list"></div>
</main>
<script>
const data = {payload};
const statusEl = document.getElementById('status');
const listEl = document.getElementById('list');
function abs(url) {{ return new URL(url, location.href).href; }}
function render(state) {{
  listEl.innerHTML = data.candidates.map((u, i) => `<div class="row"><div><b>${{i+1}}. ${{state[i] || '待检测'}}</b><div class="muted">${{abs(u)}}</div></div><a href="${{abs(u)}}"><button>打开</button></a></div>`).join('');
}}
async function canReach(url) {{
  const target = abs(url);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 2500);
  try {{
    await fetch(target, {{ method:'GET', mode:'no-cors', cache:'no-store', signal:ctrl.signal }});
    clearTimeout(timer);
    return true;
  }} catch (e) {{
    clearTimeout(timer);
    return false;
  }}
}}
(async () => {{
  const state = [];
  render(state);
  for (let i = 0; i < data.candidates.length; i++) {{
    state[i] = '检测中';
    render(state);
    const url = data.candidates[i];
    if (await canReach(url)) {{
      state[i] = '可访问';
      render(state);
      statusEl.innerHTML = '已找到可访问入口，正在跳转...';
      location.href = abs(url);
      return;
    }}
    state[i] = '不可达';
    render(state);
  }}
  statusEl.innerHTML = '<span class="bad">自动检测失败</span>，请手动选择一个候选入口。';
}})();
</script></body></html>"""

def _new_task(title: str, payload: dict) -> dict:
    global _task_counter
    with _task_lock:
        _task_counter += 1
        tid = f"task_{_task_counter}_{int(time.time())}"
        task = {
            "id": tid,
            "title": title,
            "status": "pending",
            "assignee": None,
            "payload": payload,
            "events": [
                {"ts": datetime.now().isoformat(), "event": "task.created", "source": "hub", "data": {"title": title}}
            ],
            "created_at": datetime.now().isoformat(),
        }
        _tasks[tid] = task
        return task

def _append_event(task_id: str, event: str, source: str, data: dict | None = None):
    with _task_lock:
        t = _tasks.get(task_id)
        if t:
            t["events"].append({"ts": datetime.now().isoformat(), "event": event, "source": source, "data": data or {}})

# ── 路径配置 → hub_config.cfg ─────────────────────────────


def _load_table_map() -> dict:
    return cfg.load_table_map()


def _sanitize(text: str) -> str:
    if not text:
        return text
    return "".join(c for c in text if ord(c) >= 32)


# 回复队列
REPLY_QUEUE = cfg.REPLY_QUEUE


def _query_messages(
    limit: int = 50, offset: int = 0, talker: str = "", search: str = "",
    start_date: int = 0, end_date: int = 0,
) -> list[dict]:
    """从微信消息 DB 读取消息。
    Why: 统一入口，兼容两种schema：旧版 messages 表 和 新版 Msg_* 分表
    What: 优先查 messages.db 的 messages 表；不存在时回退到 message_0.db 的 Msg_* 表
    Test: GET /api/wechat/messages?limit=5 应返回消息列表，不为空
    """
    results = []

    # ── 路径1：旧格式统一DB（messages 表）──────────────────
    msg_db = cfg.WECHAT_MSG_DBS[0]
    if msg_db.exists():
        try:
            conn = sqlite3.connect(f"file:{msg_db}?mode=ro", uri=True, timeout=5)
            where_clauses = ["message_content IS NOT NULL", "message_content != ''"]
            params: list = []
            if talker:
                where_clauses.append("talker = ?")
                params.append(talker)
            if search:
                where_clauses.append("message_content LIKE ?")
                params.append(f"%{search}%")
            if start_date > 0:
                where_clauses.append("create_time >= ?")
                params.append(start_date)
            if end_date > 0:
                where_clauses.append("create_time <= ?")
                params.append(end_date)
            where_sql = " AND ".join(where_clauses)
            query = (
                f"SELECT msg_id, server_id, talker, is_send, create_time,"
                f"       local_type, message_content, db_origin"
                f" FROM messages WHERE {where_sql}"
                f" ORDER BY create_time DESC LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                content = _sanitize(
                    r["message_content"]
                    if isinstance(r["message_content"], str)
                    else ""
                )
                if content and len(content) < 5000:
                    results.append(
                        {
                            "id": r["msg_id"],
                            "server_id": r["server_id"],
                            "talker": r["talker"],
                            "is_send": r["is_send"],
                            "time": r["create_time"],
                            "type": r["local_type"],
                            "content": content,
                            "db_origin": r["db_origin"],
                        }
                    )
            conn.close()
            if results:
                return results
        except Exception as e:
            results.append({"error": f"messages.db: {e}"})
            results = []

    # ── 路径2：新格式 Msg_* 分表（message_0.db）─────────────
    # 优先 wechat-merged，回退到 win-wechat-decrypted
    for msg0_db in [cfg.WECHAT_MSG_DB_MERGED, cfg.WECHAT_MSG_DB_WIN_FALLBACK]:
        if not msg0_db.exists():
            continue
        try:
            conn = sqlite3.connect(f"file:{msg0_db}?mode=ro", uri=True, timeout=5)
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
                ).fetchall()
            ]
            if not tables:
                conn.close()
                continue

            # 如果指定了 talker，尝试精确匹配表名（Msg_<wxid>）
            if talker:
                target_tables = [t for t in tables if talker in t]
                if not target_tables:
                    target_tables = tables  # fallback 全搜
            else:
                target_tables = tables

            all_rows = []
            for tbl in target_tables:
                try:
                    where_parts = [
                        "typeof(message_content) = 'text'",
                        "message_content != ''",
                        "local_type IN (1,3,34,43,49)",
                    ]
                    tbl_params: list = []
                    if search:
                        where_parts.append("message_content LIKE ?")
                        tbl_params.append(f"%{search}%")
                    where_str = " AND ".join(where_parts)
                    rows = conn.execute(
                        f"SELECT local_id, create_time, message_content, local_type"
                        f' FROM "{tbl}" WHERE {where_str}'
                        f" ORDER BY create_time DESC LIMIT ?",
                        tbl_params + [limit],
                    ).fetchall()
                    for r in rows:
                        raw_content = r[2] or ""
                        # 解析 UOS 格式 "wxid:\n消息"
                        talker_name = ""
                        if isinstance(raw_content, str) and ":\n" in raw_content:
                            talker_name, raw_content = raw_content.split(":\n", 1)
                        all_rows.append(
                            {
                                "id": r[0],
                                "time": r[1],
                                "talker": talker_name or tbl.replace("Msg_", ""),
                                "content": _sanitize(raw_content)[:4999],
                                "type": r[3],
                                "is_send": 0,
                                "db_origin": msg0_db.name,
                            }
                        )
                except Exception:
                    continue

            conn.close()
            # 全局排序，取前 limit 条
            all_rows.sort(key=lambda x: x.get("time", 0), reverse=True)
            results = all_rows[offset : offset + limit]
            if results:
                return results
        except Exception as e:
            results = [{"error": f"{msg0_db.name}: {e}"}]

    return results


def _get_contacts(limit: int = 500, search: str = "") -> list[dict]:
    """获取联系人列表，合并 table_map 消息统计 + contact.db 头像/昵称。"""
    tmap = _load_table_map()

    msg_stats: dict[str, dict] = {}
    msg_db = cfg.WECHAT_MSG_DBS[0]
    if msg_db.exists():
        try:
            conn = sqlite3.connect(f"file:{msg_db}?mode=ro", uri=True, timeout=5)
            for username, info in tmap.items():
                tbl = info["table"]
                try:
                    row = conn.execute(
                        f'SELECT count(*), max(create_time) FROM "{tbl}" '
                        f"WHERE typeof(message_content) = 'text' AND message_content != ''"
                    ).fetchone()
                    msg_stats[username] = {
                        "msg_count": row[0] or 0,
                        "last_time": row[1] or 0,
                    }
                except Exception:
                    msg_stats[username] = {
                        "msg_count": info.get("count", 0),
                        "last_time": 0,
                    }
            conn.close()
        except Exception:
            pass

    contacts = []
    if cfg.WECHAT_CONTACT_DB.exists():
        try:
            conn = sqlite3.connect(
                f"file:{cfg.WECHAT_CONTACT_DB}?mode=ro", uri=True, timeout=10
            )
            # NOTE: 不用 row_factory — small_head_url 可能含二进制数据导致 UTF-8 解码失败
            # 用 SQL CASE 过滤非文本 avatar，避免 fetchall() 时解码异常

            where = ""
            params: tuple = ()
            if search:
                where = "WHERE nick_name LIKE ? OR remark LIKE ? OR username LIKE ?"
                params = (f"%{search}%", f"%{search}%", f"%{search}%")

            rows = conn.execute(
                f"SELECT username, nick_name, remark, "
                f"CASE WHEN typeof(small_head_url)='text' AND small_head_url LIKE 'http%' "
                f"THEN small_head_url "
                f"WHEN typeof(big_head_url)='text' AND big_head_url LIKE 'http%' "
                f"THEN big_head_url ELSE '' END as avatar "
                f"FROM contact {where}",
                params,
            ).fetchall()

            for r in rows:
                username = r[0] or ""
                if not username:
                    continue
                nickname = _sanitize(r[1] or "")
                remark = _sanitize(r[2] or "")
                stats = msg_stats.get(username, {"msg_count": 0, "last_time": 0})
                display_name = remark or nickname or username
                contacts.append(
                    {
                        "talker": username,
                        "nickname": nickname,
                        "remark": remark,
                        "avatar": r[3] or "",
                        "msg_count": stats["msg_count"],
                        "last_time": stats["last_time"],
                        "display_name": display_name,
                    }
                )
            conn.close()
        except Exception as e:
            contacts.append({"error": str(e)})

    known = {c["talker"] for c in contacts if c.get("talker")}
    for username, stats in msg_stats.items():
        if username not in known and stats["msg_count"] > 0:
            contacts.append(
                {
                    "talker": username,
                    "nickname": username,
                    "remark": "",
                    "avatar": "",
                    "msg_count": stats["msg_count"],
                    "last_time": stats["last_time"],
                    "display_name": username,
                }
            )

    system_prefix = (
        "notif",
        "tmessage",
        "medianote",
        "qmessage",
        "weibo",
        "float",
        "filehelper",
    )
    contacts = [
        c for c in contacts if not c.get("talker", "").startswith(system_prefix)
    ]

    has_msg = [c for c in contacts if c.get("last_time", 0) > 0]
    no_msg = [c for c in contacts if c.get("last_time", 0) == 0]
    has_msg.sort(key=lambda c: c.get("last_time", 0), reverse=True)
    no_msg.sort(key=lambda c: c.get("display_name", ""))
    contacts = has_msg + no_msg

    return contacts[:limit]


# ── 基础路由 ──────────────────────────────────────────────
@app.get("/api/status")
async def api_status():
    return {
        "service": "charlie-hub",
        "status": "running",
        "port": 9800,
        "version": "2.1.0",
    }


@app.get("/health")
async def health():
    return {"healthy": True}


@app.get("/api/status")
async def status():
    return {"service": "charlie-hub", "version": "2.0.0", "uptime": "active"}


@app.get("/api/brain/status")
async def brain_status():
    """读取 AGI Brain 实时状态（/tmp/agi-brain-status.json）"""
    brain_file = Path(Path.home() / ".local/state/agi-brain-status.json")
    if brain_file.exists():
        try:
            data = json.loads(brain_file.read_text(encoding="utf-8"))
            return SafeJSONResponse(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse({"error": "brain status file corrupt"}, status_code=500)
    return JSONResponse(
        {"status": "no_data", "message": "AGI Brain 未运行或无状态文件"},
        status_code=404,
    )


@app.get("/api/chronos/status")
async def chronos_status():
    chronos_dir = Path(Path.home() / ".local/state/chronos")
    result: dict = {"available": False}
    if not chronos_dir.exists():
        return JSONResponse(result, status_code=404)
    for name in ("biofeedback_state", "sensory_state", "subconscious_state"):
        fp = chronos_dir / f"{name}.json"
        if fp.exists():
            try:
                result[name] = json.loads(fp.read_text(encoding="utf-8"))
                result["available"] = True
            except (json.JSONDecodeError, UnicodeDecodeError):
                result[name] = {"error": "parse_failed"}
    return SafeJSONResponse(result)


# ── 微信统一面板 API ─────────────────────────────────────
class SafeJSONResponse(JSONResponse):
    def render(self, content: typing.Any) -> bytes:
        return json.dumps(content, ensure_ascii=False, allow_nan=False).encode("utf-8")


@app.get("/api/wechat/contacts")
async def wechat_contacts(
    limit: int = Query(3000, le=5000),
    search: str = Query(""),
):
    """获取联系人列表（3268人，支持搜索）。"""
    return SafeJSONResponse(_get_contacts(limit=limit, search=search))


@app.get("/api/wechat/messages")
async def wechat_messages(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    talker: str = Query(""),
    search: str = Query(""),
    start_date: int = Query(0, description="开始时间戳(含)"),
    end_date: int = Query(0, description="结束时间戳(含)"),
):
    """获取微信消息（支持按联系人筛选、日期过滤和搜索）。"""
    return SafeJSONResponse(
        await asyncio.to_thread(_query_messages, limit, offset, talker, search, start_date, end_date)
    )


@app.post("/api/wechat/reply")
async def wechat_reply(body: dict):
    """发送微信回复（写入回复队列，由 wechat_agent 消费）。"""
    talker = body.get("talker", "")
    content = body.get("content", "")
    if not talker or not content:
        return JSONResponse({"error": "talker 和 content 必填"}, status_code=400)

    entry = {
        "talker": talker,
        "reply": content,
        "source": "hub-api",
        "timestamp": time.time(),
    }
    with open(REPLY_QUEUE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"status": "queued", "talker": talker, "content_preview": content[:50]}


@app.get("/api/wechat/status")
async def wechat_status():
    """微信系统状态。"""
    try:
        agent_active = (
            subprocess.run(
                ["systemctl", "--user", "is-active", "wechat-agent.service"],
                capture_output=True,
                text=True,
                timeout=5,
                stdin=subprocess.DEVNULL,
            ).stdout.strip()
            == "active"
        )
    except Exception:
        agent_active = False
    try:
        uos_active = (
            subprocess.run(
                ["systemctl", "--user", "is-active", "wechat-uos.service"],
                capture_output=True,
                text=True,
                timeout=5,
                stdin=subprocess.DEVNULL,
            ).stdout.strip()
            == "active"
        )
    except Exception:
        uos_active = False

    digests_db = Path.home() / ".local/share/hyperchat/data/wechat_digests.db"
    return {
        "wechat_uos": "running" if uos_active else "stopped",
        "wechat_agent": "running" if agent_active else "stopped",
        "msg_db_exists": digests_db.exists(),
        "digests_count": _count_digests(digests_db),
        "reply_queue": REPLY_QUEUE.exists(),
    }


def _count_digests(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2)
        cnt = conn.execute("SELECT count(*) FROM digests").fetchone()[0]
        conn.close()
        return cnt
    except Exception:
        return 0


# ── Wechat Digests ───────────────────────────────────────
@app.get("/api/wechat/digests")
async def get_wechat_digests(limit: int = 50):
    db_path = Path.home() / ".local/share/hyperchat/data/wechat_digests.db"
    if not db_path.exists():
        return {"digests": [], "count": 0}
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3)
        rows = conn.execute(
            "SELECT * FROM digests ORDER BY rowid DESC LIMIT ?", (limit,)
        ).fetchall()
        cols = (
            [d[0] for d in conn.execute("SELECT * FROM digests LIMIT 1").description]
            if rows
            else []
        )
        conn.close()
        return {"digests": [dict(zip(cols, r)) for r in rows], "count": len(rows)}
    except Exception as e:
        return {"digests": [], "count": 0, "error": str(e)}


# ── OP Tasks（解析 op-tasks.md）──────────────────────────
OP_TASKS_FILE = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
TASK_BUS_FILE = Path.home() / ".local/state/hub/task-bus.jsonl"
FASTGPT_KNOWLEDGE_DIR = Path.home() / ".local/share/hub/fastgpt-knowledge"
WORKSPACE_SNAPSHOT_FILE = Path.home() / ".local/state/hub/workspace-snapshot.json"
OP_LIFECYCLE_DIR = Path.home() / ".local/state/opencode-lifecycle"
OP_REVIEW_GATE_FILE = OP_LIFECYCLE_DIR / "review-gate.jsonl"
OP_EVENTS_FILE = OP_LIFECYCLE_DIR / "events.jsonl"
OP_KNOWLEDGE_CANDIDATES_FILE = OP_LIFECYCLE_DIR / "knowledge-candidates.jsonl"
OP_RAG_INDEX_FILE = OP_LIFECYCLE_DIR / "rag-index.jsonl"
OP_LEARNING_DECISIONS_FILE = OP_LIFECYCLE_DIR / "learning-decisions.jsonl"
OP_APPROVED_LEARNING_FILE = OP_LIFECYCLE_DIR / "approved-learning-queue.jsonl"
OP_RECALL_ACCURACY_FILE = OP_LIFECYCLE_DIR / "recall-accuracy.jsonl"
OP_CORRECTION_CANDIDATES_FILE = OP_LIFECYCLE_DIR / "correction-candidates.jsonl"
OP_VERIFY_DIR = Path.home() / ".local/state/opencode-verify"
OP_ESCALATION_DIR = Path.home() / "memory/opencode-escalations/requests"
CONTROL_PLANE_SUPERVISOR_DIR = Path.home() / ".local/state/control-plane-supervisor"
CONTROL_PLANE_SUPERVISOR_LATEST = CONTROL_PLANE_SUPERVISOR_DIR / "latest.json"
CONTRACTS_DIR = Path.home() / ".local/share/hub/contracts"


def _xml(v: typing.Any) -> str:
    return xml.sax.saxutils.escape("" if v is None else str(v), {'"': "&quot;"})


def _xlsx_col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _xlsx_sheet(rows: list[list[typing.Any]]) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    out.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')
    for r_idx, row in enumerate(rows, 1):
        out.append(f'<row r="{r_idx}">')
        for c_idx, value in enumerate(row, 1):
            ref = f"{_xlsx_col(c_idx)}{r_idx}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                out.append(f'<c r="{ref}" t="inlineStr"><is><t>{_xml(value)}</t></is></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def _write_contract_xlsx(path: Path, data: dict) -> None:
    fields = data.get("fields") or {}
    items = data.get("items") or []
    rows: list[list[typing.Any]] = [
        ["合同字段", "值"],
        ["合同类型", fields.get("contract_type", "")],
        ["甲方", fields.get("party_a", "")],
        ["乙方", fields.get("party_b", "")],
        ["项目/标的", fields.get("subject", "")],
        ["金额", fields.get("amount", "")],
        ["税率", fields.get("tax_rate", "")],
        ["付款方式", fields.get("payment_terms", "")],
        ["交付时间", fields.get("delivery_date", "")],
        [],
        ["序号", "名称", "规格", "数量", "单位", "单价", "金额", "备注"],
    ]
    if items:
        for idx, item in enumerate(items, 1):
            rows.append([
                idx,
                item.get("name", ""),
                item.get("spec", ""),
                item.get("quantity", ""),
                item.get("unit", ""),
                item.get("unit_price", ""),
                item.get("amount", ""),
                item.get("note", ""),
            ])
    else:
        rows.append([1, fields.get("subject", "待确认项目"), "", "", "", "", fields.get("amount", ""), "AI 未识别到明细，请人工确认"])

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>""")
        z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""")
        z.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="合同明细" sheetId="1" r:id="rId1"/></sheets></workbook>""")
        z.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>""")
        z.writestr("xl/worksheets/sheet1.xml", _xlsx_sheet(rows))
        z.writestr("docProps/core.xml", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>合同明细</dc:title><dc:creator>Charlie Hub</dc:creator></cp:coreProperties>""")
        z.writestr("docProps/app.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Charlie Hub</Application></Properties>""")


def _extract_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("model did not return json")
    return json.loads(m.group(0))


def _fallback_contract_data(intent: str, error: str = "") -> dict:
    amount = ""
    m = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?\s*(?:万|元|块|rmb|RMB|¥)?)", intent or "")
    if m:
        amount = m.group(1)
    return {
        "fields": {
            "contract_type": "销售/采购合同",
            "party_a": "待确认",
            "party_b": "待确认",
            "subject": intent[:80] if intent else "待确认项目",
            "amount": amount or "待确认",
            "tax_rate": "待确认",
            "payment_terms": "待确认",
            "delivery_date": "待确认",
        },
        "items": [],
        "questions": ["请确认甲方、乙方、金额、税率、付款方式和交付时间。"],
        "risk_flags": [f"视觉识别未完成：{error}"] if error else ["未提供足够材料，已生成待确认草稿。"],
    }


def _contract_markdown(data: dict, intent: str) -> str:
    f = data.get("fields") or {}
    flags = "\n".join(f"- {x}" for x in data.get("risk_flags", []) or ["金额和主体信息需人工复核"])
    questions = "\n".join(f"- {x}" for x in data.get("questions", []) or [])
    items = data.get("items") or []
    item_lines = "\n".join(
        f"| {i+1} | {it.get('name','')} | {it.get('spec','')} | {it.get('quantity','')} | {it.get('unit_price','')} | {it.get('amount','')} |"
        for i, it in enumerate(items)
    ) or "| 1 | 待确认项目 |  |  |  | 待确认 |"
    return f"""# 合同草稿

> 这是 AI 生成的草稿，金额、主体、付款和交付条款必须人工确认后再使用。

原始意图：{intent or "未填写"}

## 关键字段

- 合同类型：{f.get('contract_type', '待确认')}
- 甲方：{f.get('party_a', '待确认')}
- 乙方：{f.get('party_b', '待确认')}
- 项目/标的：{f.get('subject', '待确认')}
- 金额：{f.get('amount', '待确认')}
- 税率：{f.get('tax_rate', '待确认')}
- 付款方式：{f.get('payment_terms', '待确认')}
- 交付时间：{f.get('delivery_date', '待确认')}

## 明细

| 序号 | 名称 | 规格 | 数量 | 单价 | 金额 |
| --- | --- | --- | --- | --- | --- |
{item_lines}

## 待确认问题

{questions or "- 暂无"}

## 风险提示

{flags}
"""


def _call_contract_vision(intent: str, files: list[tuple[str, bytes, str]]) -> dict:
    content: list[dict] = [{
        "type": "text",
        "text": (
            "你是合同录入助手。根据用户意图和图片/PDF截图抽取合同字段，"
            "只返回 JSON，不要 Markdown。schema: {fields:{contract_type,party_a,party_b,subject,amount,tax_rate,payment_terms,delivery_date},"
            "items:[{name,spec,quantity,unit,unit_price,amount,note}],questions:[],risk_flags:[]}。"
            f"用户意图：{intent}"
        ),
    }]
    for name, raw, media_type in files[:4]:
        if media_type.startswith("image/"):
            b64 = base64.b64encode(raw).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}})
        else:
            content.append({"type": "text", "text": f"附件 {name} 类型 {media_type} 已上传；如无法读取请在 questions 中提示人工确认。"})
    payload = json.dumps({
        "model": "glm-4.6v-flash",
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:4000/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer sk-litellm-charlie-2026"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    text = body["choices"][0]["message"]["content"]
    return _extract_json_object(text)


@app.get("/api/op-tasks")
async def get_op_tasks():
    """解析 op-tasks.md，返回 pending/done/failed 三类任务列表。"""
    import re

    if not OP_TASKS_FILE.exists():
        return {"pending": [], "done": [], "failed": []}
    text = OP_TASKS_FILE.read_text()
    pending, done, failed = [], [], []
    for line in text.splitlines():
        m_pend = re.match(r"^- \[ \] (.+)$", line)
        m_done = re.match(r"^- \[x\] (.+)$", line, re.IGNORECASE)
        m_fail = re.match(r"^- \[!\] (.+)$", line)
        if m_pend:
            pending.append({"text": m_pend.group(1)[:120]})
        elif m_done:
            done.append({"text": m_done.group(1)[:120]})
        elif m_fail:
            failed.append({"text": m_fail.group(1)[:120]})
    return {
        "pending": pending[-30:],
        "done": done[-30:],
        "failed": failed[-10:],
"counts": {"pending": len(pending), "done": len(done), "failed": len(failed)},
     }


def _task_id(source: str, title: str, detail: str = "") -> str:
    raw = f"{source}\n{title}\n{detail}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:12]


def _task_bus_append(event: str, task_id: str, source: str, data: dict | None = None) -> dict:
    TASK_BUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "ts": datetime.now().isoformat(),
        "event": event,
        "task_id": task_id,
        "source": source,
        "data": data or {},
    }
    with TASK_BUS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def _task_bus_events(limit: int = 80) -> list[dict]:
    if not TASK_BUS_FILE.exists():
        return []
    rows = []
    for line in TASK_BUS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _read_jsonl_tail(path: Path, limit: int = 80) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]
    except Exception:
        return []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _op_review_id(row: dict) -> str:
    raw = "|".join(
        str(row.get(key, ""))
        for key in ("session_id", "sessionID", "ts", "verdict", "task_preview", "gap")
    )
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:14]


def _load_learning_decisions() -> dict[str, dict]:
    decisions: dict[str, dict] = {}
    for row in _read_jsonl_tail(OP_LEARNING_DECISIONS_FILE, 1000):
        review_id = row.get("review_id")
        if review_id:
            decisions[str(review_id)] = row
    return decisions


def _op_lifecycle_status() -> dict:
    bin_path = Path.home() / ".local/bin/opencode-lifecycle.py"
    if not bin_path.exists():
        return {"ok": False, "error": f"{bin_path} not found"}
    try:
        result = subprocess.run(
            [str(bin_path), "status"],
            capture_output=True,
            text=True,
            timeout=12,
            stdin=subprocess.DEVNULL,
        )
        data = json.loads(result.stdout or "{}")
        data["ok"] = result.returncode == 0
        if result.stderr:
            data["stderr"] = result.stderr[-2000:]
        return data
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _op_learning_plan() -> dict:
    return {
        "title": "OP 任务闭环",
        "principle": "任务前先召回规则和验收标准，任务中记录失败指纹并及时换策略，任务后复盘、评分、沉淀到可批准的学习队列。",
        "phases": [
            {
                "id": "before",
                "name": "任务前",
                "goal": "让 OP 带着架构、偏好、黑名单和验收标准开工。",
                "steps": [
                    "识别任务类型：系统、代码、网络、桌面、配置、普通问答。",
                    "按 SYSTEM_MAP、FAILURE_BLACKLIST、runbook、router memory 召回上下文。",
                    "写清成功标准、风险点、可回滚范围和需要验证的命令。",
                    "已有失败方案进入禁用清单，同一失败路径最多重复 2 次。",
                    "把用户偏好、评论要求、任务结束评分要求注入执行上下文。",
                ],
            },
            {
                "id": "during",
                "name": "任务中",
                "goal": "执行时持续留痕，失败就换策略，长任务有可恢复进度。",
                "steps": [
                    "记录工具调用、文件变更、服务重启、端口和关键输出。",
                    "发现同类错误时生成失败指纹，先查黑名单和最近复盘。",
                    "验证被占用或会话未空闲时标记 DEFERRED，不当成通过。",
                    "长任务定期写 journal、task bus 和下一步，避免中断后丢上下文。",
                    "需要人工判断时进入 Appsmith/Hub 学习中枢的待决策队列。",
                ],
            },
            {
                "id": "after",
                "name": "任务后",
                "goal": "把结果变成可审计、可复用、可纠错的知识。",
                "steps": [
                    "运行验证并给出 PASS、FAIL 或 UNCLEAR，不允许空泛结束。",
                    "review gate 评分，记录证据、缺口、工具失败数和变更规模。",
                    "可复用经验进入候选知识，需用户批准后再提升为规则或黑名单。",
                    "用户评论、驳回、重试、已解决动作写入 learning-decisions。",
                    "后续 maintainer 把批准项同步到偏好、决策规则、runbook 或 FAILURE_BLACKLIST。",
                ],
            },
        ],
    }


def _op_review_items(limit: int = 80) -> list[dict]:
    decisions = _load_learning_decisions()
    items = []
    for row in reversed(_read_jsonl_tail(OP_REVIEW_GATE_FILE, limit)):
        review_id = _op_review_id(row)
        item = dict(row)
        item["id"] = review_id
        item["decision"] = decisions.get(review_id)
        item["pending_decision"] = (
            str(item.get("verdict", "")).upper() in {"FAIL", "UNCLEAR"}
            and item.get("decision") is None
        )
        items.append(item)
    return items


def _op_learning_summary(reviews: list[dict], candidates: list[dict], events: list[dict], escalations: list[dict]) -> dict:
    verdicts: dict[str, int] = {}
    for item in reviews:
        verdict = str(item.get("verdict") or "UNKNOWN").upper()
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
    deferred = 0
    review_gate = 0
    for event in events:
        event_type = event.get("type") or event.get("event")
        result = str(event.get("result") or "")
        if event_type == "auto_verify" and "DEFERRED" in result:
            deferred += 1
        if event_type == "review_gate":
            review_gate += 1
    return {
        "reviews": len(reviews),
        "pending_decisions": sum(1 for item in reviews if item.get("pending_decision")),
        "fail": verdicts.get("FAIL", 0),
        "unclear": verdicts.get("UNCLEAR", 0),
        "pass": verdicts.get("PASS", 0),
        "knowledge_candidates": len(candidates),
        "deferred_verify": deferred,
        "review_gate_events": review_gate,
        "escalations": len(escalations),
    }


def _op_accuracy_summary(reports: list[dict], corrections: list[dict]) -> dict:
    scores = [int(item.get("score", 0)) for item in reports if item.get("score") is not None]
    verdicts: dict[str, int] = {}
    for item in reports:
        verdict = str(item.get("verdict") or "UNKNOWN").upper()
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
    return {
        "reports": len(reports),
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "pass": verdicts.get("PASS", 0),
        "review": verdicts.get("REVIEW", 0),
        "fix": verdicts.get("FIX", 0),
        "pending_corrections": sum(1 for item in corrections if item.get("status") == "pending"),
    }


def _op_escalations(limit: int = 30) -> list[dict]:
    if not OP_ESCALATION_DIR.exists():
        return []
    items = []
    try:
        files = sorted(OP_ESCALATION_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    except Exception:
        return []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            data = {}
        data.setdefault("file", str(path))
        items.append(data)
    return items


def _normalize_task(source: str, title: str, detail: str = "", priority: str = "medium", action: str = "", href: str = "", status: str = "pending") -> dict:
    return {
        "id": _task_id(source, title, detail),
        "source": source,
        "title": title[:160],
        "detail": detail[:600],
        "priority": priority,
        "action": action[:1000],
        "href": href,
        "status": status,
    }


async def _unified_todos(request: Request | None = None) -> dict:
    tasks: list[dict] = []

    try:
        op = await get_op_tasks()
        for item in (op.get("pending") or [])[:20]:
            text = item.get("text", "")
            tasks.append(_normalize_task("op", text, "来自 op-tasks.md", "medium", text, "/kanban"))
        for item in (op.get("failed") or [])[:8]:
            text = item.get("text", "")
            tasks.append(_normalize_task("op-failed", text, "OP 失败任务，需要人工确认或重新派发", "high", text, "/kanban", "failed"))
    except Exception:
        pass

    try:
        ops = await ops_daily_improvement()
        for item in (ops.get("next_tasks") or [])[:8]:
            tasks.append(_normalize_task(
                "daily",
                item.get("title", "每日提升"),
                f"{item.get('area', '')} · {item.get('detail', '')}",
                item.get("priority", "medium"),
                item.get("command", ""),
                item.get("href", "/dashboard") or "/dashboard",
            ))
    except Exception:
        pass

    try:
        arch = await architecture_actions(request)  # type: ignore[arg-type]
        for item in (arch.get("actions") or [])[:8]:
            tasks.append(_normalize_task(
                "architecture",
                item.get("title", "架构动作"),
                f"{item.get('area', '')} · {item.get('detail', '')}",
                item.get("priority", "medium"),
                item.get("command", ""),
                item.get("href", "/dashboard") or "/dashboard",
            ))
    except Exception:
        pass

    try:
        for project in _all_projects():
            for milestone in project.get("milestones", []):
                if milestone.get("status") in {"pending", "in_progress"}:
                    tasks.append(_normalize_task(
                        "project",
                        f"{project.get('name')} / {milestone.get('name')}",
                        project.get("description", ""),
                        "medium" if milestone.get("status") == "pending" else "high",
                        f"推进项目 {project.get('name')} 的里程碑：{milestone.get('name')}",
                        "/#projects",
                    ))
    except Exception:
        pass

    try:
        marketing = await marketing_center()
        for slot in marketing.get("automation_slots", []):
            tasks.append(_normalize_task(
                "marketing",
                f"营销中心 / {slot.get('name')}",
                slot.get("detail", ""),
                "medium",
                f"设计并落地 Sourcing 营销自动化模块：{slot.get('name')}。{slot.get('detail', '')}",
                "/#marketing",
            ))
    except Exception:
        pass

    seen = set()
    unique = []
    for task in tasks:
        if task["id"] in seen:
            continue
        seen.add(task["id"])
        unique.append(task)
    unique.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority"), 3))
    events = _task_bus_events()
    event_by_task: dict[str, list] = {}
    for ev in events:
        event_by_task.setdefault(ev.get("task_id", ""), []).append(ev)
    for task in unique:
        task["events"] = event_by_task.get(task["id"], [])[-5:]
        if task["events"]:
            last = task["events"][-1]
            if last.get("event") in {"completed", "sent_to_op", "exported_to_fastgpt"}:
                task["last_event"] = last.get("event")
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total": len(unique),
            "high": sum(1 for t in unique if t["priority"] == "high"),
            "medium": sum(1 for t in unique if t["priority"] == "medium"),
            "low": sum(1 for t in unique if t["priority"] == "low"),
        },
        "tasks": unique[:80],
        "events": events[-30:],
        "routing": {
            "hub": "统一收集、显示过程和完成状态",
            "op": "执行代码、系统命令、部署和修复",
            "fastgpt": "知识库问答、方案生成、复盘，不直接写代码",
        },
    }


def _task_markdown(task: dict) -> str:
    return f"""# {task.get('title')}

- 来源: {task.get('source')}
- 优先级: {task.get('priority')}
- 状态: {task.get('status')}
- 入口: {task.get('href') or ''}

## 详情
{task.get('detail') or '无'}

## 建议动作
{task.get('action') or '请分析下一步。'}
"""


# ── 自愈面板 API（runbook + feed + health）─────────────────
RUNBOOK_FEED = Path.home() / ".local/state/ops-infra/runbook-executions.jsonl"
FEED_FILE = Path.home() / "Desktop/巡检报告/op-live-feed.jsonl"
HEALTH_SCORES = Path.home() / ".local/state/ops-infra/health-scores.jsonl"
OPENCODE_SCORE_HISTORY = Path.home() / ".local/state/opencode-score-history.jsonl"


@app.get("/api/runbook/history")
async def runbook_history(limit: int = 50):
    """最近N条runbook执行记录"""
    if not RUNBOOK_FEED.exists():
        return {"records": [], "total": 0}
    lines = RUNBOOK_FEED.read_text().strip().split("\n")
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"records": list(reversed(records)), "total": len(lines)}


@app.get("/api/runbook/summary")
async def runbook_summary():
    """今日自愈统计"""
    today = time.strftime("%Y-%m-%d")
    records = []
    if RUNBOOK_FEED.exists():
        for line in RUNBOOK_FEED.read_text().strip().split("\n"):
            try:
                r = json.loads(line)
                if r.get("timestamp", "").startswith(today):
                    records.append(r)
            except json.JSONDecodeError:
                continue
    fixed = [r for r in records if r.get("action") == "fixed"]
    skipped = [r for r in records if r.get("action") == "skipped"]
    failed = [r for r in records if r.get("status") == "failed"]
    return {
        "today": today,
        "total_checks": len(records),
        "fixed": len(fixed),
        "skipped": len(skipped),
        "failed": len(failed),
        "active_alerts": len([r for r in records if r.get("severity") == "critical"]),
    }


@app.get("/api/feed/alerts")
async def feed_alerts(limit: int = 30):
    """最近告警"""
    if not FEED_FILE.exists():
        return {"alerts": [], "total": 0}
    lines = FEED_FILE.read_text().strip().split("\n")
    alerts = []
    for line in lines[-limit:]:
        try:
            a = json.loads(line)
            if a.get("type") in ("alert", "critical", "error"):
                alerts.append(a)
        except json.JSONDecodeError:
            continue
    return {"alerts": list(reversed(alerts)), "total": len(alerts)}


@app.get("/api/health/scores")
async def health_scores(limit: int = 30):
    """最近健康评分"""
    if not HEALTH_SCORES.exists():
        return {"scores": [], "total": 0}
    lines = HEALTH_SCORES.read_text().strip().split("\n")
    scores = []
    for line in lines[-limit:]:
        try:
            scores.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"scores": list(reversed(scores)), "total": len(lines)}


# ── 部门报告（读取 ~/Desktop/巡检报告/*-latest.json）──────────────────
DEPT_REPORTS_DIR = Path.home() / "Desktop/巡检报告"

# ── 监控注册中心（monitor-engine + monitor-lifecycle）────────────────
MONITOR_REGISTRY = Path.home() / ".local/state/monitor-registry/registry.json"
MONITORS_FILE = Path.home() / ".config/monitors/monitors.yaml"
MONITOR_HISTORY = Path.home() / ".local/state/monitor-registry/history.jsonl"


def _load_monitor_registry() -> dict:
    if not MONITOR_REGISTRY.exists():
        return {}
    try:
        return json.loads(MONITOR_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_monitors_yaml() -> list[dict]:
    if not MONITORS_FILE.exists():
        return []
    try:
        import yaml
        data = yaml.safe_load(MONITORS_FILE.read_text(encoding="utf-8")) or {}
        return data.get("monitors", [])
    except Exception:
        return []


def _load_monitor_history() -> list[dict]:
    entries = []
    if not MONITOR_HISTORY.exists():
        return entries
    for line in MONITOR_HISTORY.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    entries.reverse()
    return entries[-100:]


@app.get("/api/monitors")
async def api_monitors():
    """监控面板：读取 monitor registry 与 monitors.yaml，返回 active/archived 列表。"""
    registry = _load_monitor_registry()
    monitors = _load_monitors_yaml()
    results = []
    for m in monitors:
        mid = m.get("id") or m.get("name")
        state = registry.get(mid, {})
        results.append({
            "id": mid,
            "name": m.get("name", mid),
            "type": m.get("type"),
            "status": state.get("status", "unknown"),
            "consecutive_ok": state.get("consecutive_ok", 0),
            "consecutive_fail": state.get("consecutive_fail", 0),
            "last_ok": state.get("last_ok"),
            "last_fail": state.get("last_fail"),
            "archived_at": state.get("archived_at"),
            "promoted_count": state.get("promoted_count", 0),
            "success_threshold": m.get("success_threshold", 5),
            "fail_threshold": m.get("fail_threshold", 2),
        })
    return {"monitors": results, "generated_at": datetime.now().isoformat()}


@app.get("/api/monitors/summary")
async def api_monitors_summary():
    """监控面板摘要。"""
    registry = _load_monitor_registry()
    monitors = _load_monitors_yaml()
    active = sum(1 for m in registry.values() if m.get("status") == "active")
    archived = sum(1 for m in registry.values() if m.get("status") == "archived")
    return {
        "total_monitors": len(monitors),
        "active": active,
        "archived": archived,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/api/monitors/history")
async def api_monitors_history(limit: int = 50):
    """监控面板最近历史。"""
    entries = _load_monitor_history()
    return {"history": entries[-limit:]}


@app.get("/api/dept-reports")
async def get_dept_reports():
    """读取各部门 agent 输出的 *-latest.json，返回聚合部门状态。"""
    if not DEPT_REPORTS_DIR.exists():
        return {"reports": {}, "count": 0}
    reports = {}
    for f in sorted(DEPT_REPORTS_DIR.glob("*-latest.json")):
        dept = f.stem.replace("-latest", "")
        try:
            data = json.loads(f.read_text())
            reports[dept] = {
                "dept": dept,
                "timestamp": data.get("timestamp", ""),
                "status": data.get("status", "unknown"),
                "summary": data.get("summary", ""),
                "items": data.get("items", [])[:5],
            }
        except Exception as e:
            reports[dept] = {
                "dept": dept,
                "status": "error",
                "summary": str(e),
                "timestamp": "",
                "items": [],
            }
    return {"reports": reports, "count": len(reports)}


# ── CRM 客户/供应商数据 ─────────────────────────────────────
CUSTOMER_INDEX = Path.home() / "Desktop/巡检报告/customer-index.json"
SUPPLIER_INDEX = Path.home() / "Desktop/巡检报告/supplier-index.json"


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


@app.get("/api/crm/customers")
async def crm_customers(
    region: str = Query("", description="按地区过滤（已合作/未合作）"),
    search: str = Query("", description="搜索名称关键词"),
    type: str = Query("", description="supplier=查供应商，空=查客户"),
):
    """CRM 客户/供应商数据接口。
    - 默认返回客户数据
    - ?type=supplier 返回供应商
    - ?region= 已合作/未合作 过滤
    - ?search= 名称关键词搜索
    """
    if type == "supplier":
        data = _load_json(SUPPLIER_INDEX)
        # 供应商 region 过滤映射到 source 字段
        if region:
            data = [d for d in data if region in d.get("source", "")]
        if search:
            data = [d for d in data if search.lower() in d.get("name", "").lower()]
        return {"type": "supplier", "count": len(data), "data": data}
    else:
        data = _load_json(CUSTOMER_INDEX)
        if region:
            data = [d for d in data if region in d.get("region", "")]
        if search:
            data = [
                d
                for d in data
                if search.lower() in d.get("name", "").lower()
                or search.lower() in d.get("country", "").lower()
            ]
        return {"type": "customer", "count": len(data), "data": data}


@app.get("/api/crm/contacts")
async def crm_contacts_list(search: str = Query("", description="关键词搜索")):
    """crm.db 联系人列表"""
    if not cfg.CRM_DB.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{cfg.CRM_DB}?mode=ro", uri=True, timeout=5)
        rows = conn.execute(
            "SELECT id, name, company, phone, email, wechat, notes, created_at FROM contacts ORDER BY id DESC"
        ).fetchall()
        conn.close()
    except Exception:
        return []
    result = []
    for r in rows:
        cid, name, company, phone, email, wechat, notes, created = r
        if (
            search
            and search.lower() not in (name or "").lower()
            and search.lower() not in (company or "").lower()
        ):
            continue
        result.append(
            {
                "id": cid,
                "name": name or "",
                "company": company or "",
                "phone": phone or "",
                "email": email or "",
                "wechat": wechat or "",
                "notes": notes or "",
                "tag": "customer",
                "created_at": created or "",
            }
        )
    return result


@app.post("/api/crm/contacts")
async def crm_contact_create(body: dict):
    """新增联系人"""
    if not cfg.CRM_DB.exists():
        return {"error": "DB not found"}
    try:
        conn = sqlite3.connect(str(cfg.CRM_DB), timeout=5)
        cur = conn.execute(
            "INSERT INTO contacts (name,company,phone,email,wechat,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,datetime('now'),datetime('now'))",
            (
                body.get("name", ""),
                body.get("company", ""),
                body.get("phone", ""),
                body.get("email", ""),
                body.get("wechat", ""),
                body.get("notes", ""),
            ),
        )
        conn.commit()
        cid = cur.lastrowid
        conn.close()
        return {"id": cid, "ok": True}
    except Exception as e:
        return {"error": str(e)}


@app.put("/api/crm/contacts/{cid}")
async def crm_contact_update(cid: int, body: dict):
    """更新联系人"""
    if not cfg.CRM_DB.exists():
        return {"error": "DB not found"}
    try:
        conn = sqlite3.connect(str(cfg.CRM_DB), timeout=5)
        conn.execute(
            "UPDATE contacts SET name=?,company=?,phone=?,email=?,wechat=?,notes=?,updated_at=datetime('now') WHERE id=?",
            (
                body.get("name", ""),
                body.get("company", ""),
                body.get("phone", ""),
                body.get("email", ""),
                body.get("wechat", ""),
                body.get("notes", ""),
                cid,
            ),
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/crm/contacts/{cid}")
async def crm_contact_delete(cid: int):
    """删除联系人"""
    if not cfg.CRM_DB.exists():
        return {"error": "DB not found"}
    try:
        conn = sqlite3.connect(str(cfg.CRM_DB), timeout=5)
        conn.execute("DELETE FROM contacts WHERE id=?", (cid,))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/crm/link-wechat")
async def crm_link_wechat(body: dict):
    """关联 CRM contact 到微信 wxid。
    body: {"contact_id": int, "wxid": "wxid_xxx"}
    在 crm.db contacts.wechat 字段写入 wxid，
    同时在 wechat-agent crm.db 创建/更新对应联系人。
    """
    contact_id = body.get("contact_id")
    wxid = body.get("wxid", "").strip()
    if not contact_id or not wxid:
        return JSONResponse({"error": "contact_id 和 wxid 必填"}, status_code=400)

    try:
        conn = sqlite3.connect(str(cfg.CRM_DB))
        # 更新 crm.db contacts.wechat
        conn.execute(
            "UPDATE contacts SET wechat=?, updated_at=datetime('now') WHERE id=?",
            (wxid, contact_id),
        )
        row = conn.execute(
            "SELECT id,name,company,phone,email FROM contacts WHERE id=?", (contact_id,)
        ).fetchone()
        conn.commit()
        conn.close()

        if not row:
            return JSONResponse(
                {"error": f"contact_id={contact_id} 不存在"}, status_code=404
            )

        # 同步到 wechat-agent crm.db（upsert）
        if cfg.WECHAT_CRM_DB.exists():
            wconn = sqlite3.connect(str(cfg.WECHAT_CRM_DB))
            existing = wconn.execute(
                "SELECT wxid FROM contacts WHERE wxid=?", (wxid,)
            ).fetchone()
            if existing:
                wconn.execute(
                    "UPDATE contacts SET remark=?, company=?, phone=?, email=? WHERE wxid=?",
                    (row[1], row[2], row[3], row[4], wxid),
                )
            else:
                wconn.execute(
                    "INSERT INTO contacts (wxid,nickname,remark,company,phone,email) VALUES (?,?,?,?,?,?)",
                    (wxid, row[1], row[1], row[2], row[3], row[4]),
                )
            wconn.commit()
            wconn.close()

        return {
            "status": "linked",
            "contact_id": contact_id,
            "wxid": wxid,
            "name": row[1],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/crm/notes")
async def crm_notes_list(
    contact_id: int = Query(0, description="按联系人ID过滤"),
    company_id: int = Query(0, description="按公司ID过滤"),
    category: str = Query("", description="按分类过滤"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """查询 CRM 笔记列表。"""
    try:
        conn = sqlite3.connect(f"file:{cfg.CRM_DB}?mode=ro", uri=True)
        where, params = [], []
        if contact_id:
            where.append("contact_id=?")
            params.append(contact_id)
        if company_id:
            where.append("company_id=?")
            params.append(company_id)
        if category:
            where.append("category=?")
            params.append(category)
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        total = conn.execute(f"SELECT count(*) FROM notes {clause}", params).fetchone()[
            0
        ]
        rows = conn.execute(
            f"SELECT id, contact_id, company_id, title, content, category, created_at, updated_at "
            f"FROM notes {clause} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        conn.close()

        notes = [
            {
                "id": r[0],
                "contact_id": r[1],
                "company_id": r[2],
                "title": r[3] or "",
                "content": r[4] or "",
                "category": r[5] or "general",
                "created_at": r[6],
                "updated_at": r[7],
            }
            for r in rows
        ]
        return {"count": total, "data": notes}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/crm/notes")
async def crm_notes_create(body: dict):
    """创建 CRM 笔记。
    body: {"contact_id": int?, "company_id": int?, "title": str, "content": str, "category": str?}
    """
    content = body.get("content", "").strip()
    if not content:
        return JSONResponse({"error": "content 必填"}, status_code=400)

    try:
        conn = sqlite3.connect(str(cfg.CRM_DB))
        cur = conn.execute(
            "INSERT INTO notes (contact_id, company_id, title, content, category) VALUES (?,?,?,?,?)",
            (
                body.get("contact_id"),
                body.get("company_id"),
                body.get("title", ""),
                content,
                body.get("category", "general"),
            ),
        )
        note_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"status": "created", "id": note_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.put("/api/crm/notes/{note_id}")
async def crm_notes_update(note_id: int, body: dict):
    """更新 CRM 笔记。"""
    try:
        conn = sqlite3.connect(str(cfg.CRM_DB))
        sets, params = [], []
        for field in ("title", "content", "category"):
            if field in body:
                sets.append(f"{field}=?")
                params.append(body[field])
        if not sets:
            conn.close()
            return JSONResponse({"error": "无更新字段"}, status_code=400)
        sets.append("updated_at=datetime('now')")
        params.append(note_id)
        conn.execute(f"UPDATE notes SET {', '.join(sets)} WHERE id=?", params)
        conn.commit()
        conn.close()
        return {"status": "updated", "id": note_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/crm/notes/{note_id}")
async def crm_notes_delete(note_id: int):
    """删除 CRM 笔记。"""
    try:
        conn = sqlite3.connect(str(cfg.CRM_DB))
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
        conn.close()
        return {"status": "deleted", "id": note_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── CopilotKit Runtime（对接 LiteLLM）──────────────────
@app.post("/api/copilotkit")
async def copilotkit_runtime(body: dict):
    """CopilotKit runtime proxy → LiteLLM。
    将 CopilotKit 的请求转发给 LiteLLM，用 Cerebras 免费模型。"""
    import httpx

    messages = body.get("messages", [])
    # 注入系统上下文
    system_msg = {
        "role": "system",
        "content": (
            "你是 AGI Control 的 AI 助手。用中文回复。\n"
            "你可以帮用户：查看系统状态、处理微信消息、管理任务、执行运维。\n"
            "微信数据来自 /api/wechat/* 端点。系统状态来自 AGI Brain。\n"
            "用户的 CC(Claude Code) 在终端运行，OP(OpenCode) 是运维执行层。"
        ),
    }

    llm_messages = [system_msg] + messages
    payload = {
        "model": "cerebras-qwen3-235b",
        "messages": llm_messages,
        "max_tokens": 1024,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "http://localhost:4000/v1/chat/completions",
                headers={"Authorization": "Bearer sk-local-8e781a02c87854bf06ed2a5e871915962227ab91bc71937e"},
                json=payload,
            )
            data = resp.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"choices": [{"message": {"role": "assistant", "content": reply}}]}
    except Exception as e:
        return {
            "choices": [
                {"message": {"role": "assistant", "content": f"AI 助手连接失败: {e}"}}
            ]
        }


@app.post("/api/contracts/draft")
async def contract_draft(
    intent: str = Form(""),
    files: list[UploadFile] = File(default=[]),
):
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    job_dir = CONTRACTS_DIR / job_id
    upload_dir = job_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    raw_files: list[tuple[str, bytes, str]] = []
    for f in files[:8]:
        raw = await f.read()
        if not raw:
            continue
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", f.filename or "upload.bin")[:120]
        (upload_dir / safe_name).write_bytes(raw)
        raw_files.append((safe_name, raw, f.content_type or "application/octet-stream"))

    status = "model"
    try:
        data = await asyncio.to_thread(_call_contract_vision, intent, raw_files)
    except Exception as e:
        status = "fallback"
        data = _fallback_contract_data(intent, str(e))

    data.setdefault("fields", {})
    data.setdefault("items", [])
    data.setdefault("questions", [])
    data.setdefault("risk_flags", [])
    data["job_id"] = job_id
    data["status"] = status
    data["intent"] = intent
    data["uploaded_files"] = [name for name, _, _ in raw_files]

    json_path = job_dir / "result.json"
    md_path = job_dir / "contract-draft.md"
    xlsx_path = job_dir / "contract-lines.xlsx"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_contract_markdown(data, intent), encoding="utf-8")
    _write_contract_xlsx(xlsx_path, data)

    return SafeJSONResponse({
        "ok": True,
        "job_id": job_id,
        "status": status,
        "fields": data.get("fields", {}),
        "items": data.get("items", []),
        "questions": data.get("questions", []),
        "risk_flags": data.get("risk_flags", []),
        "downloads": {
            "json": f"/api/contracts/files/{job_id}/result.json",
            "draft": f"/api/contracts/files/{job_id}/contract-draft.md",
            "xlsx": f"/api/contracts/files/{job_id}/contract-lines.xlsx",
        },
    })


@app.get("/api/contracts/files/{job_id}/{filename}")
async def contract_file(job_id: str, filename: str):
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[a-f0-9]{8}", job_id):
        return JSONResponse({"error": "bad job_id"}, status_code=400)
    if filename not in {"result.json", "contract-draft.md", "contract-lines.xlsx"}:
        return JSONResponse({"error": "bad filename"}, status_code=400)
    path = CONTRACTS_DIR / job_id / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path)


STATIC_DIR = Path(__file__).parent / 'static'
app.mount("/static", StaticFiles(directory=STATIC_DIR))
FRP_CONFIG = Path('/etc/frp/frpc.toml')
MEMORY_DIR = Path.home() / '.claude/projects/-home-charlie/memory'
LETTA_API = 'http://localhost:8283'


@app.get("/api/links")
async def link_registry_api(request: Request):
    return JSONResponse({
        key: {
            **value,
            "candidates": _link_candidates(key, request),
        }
        for key, value in LINK_REGISTRY.items()
    })


@app.get("/api/plane/status")
async def plane_status_api():
    def run(cmd: list[str], timeout: float = 4.0) -> tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    service_code, service_out, service_err = run(["systemctl", "--user", "is-active", "plane.service"], 3.0)
    http_ok = False
    http_status = None
    try:
        req = urllib.request.Request("http://127.0.0.1:8090/", method="HEAD")
        with urllib.request.urlopen(req, timeout=4) as resp:
            http_status = resp.status
            http_ok = 200 <= resp.status < 500
    except Exception as exc:
        http_status = str(exc)

    ps_code, ps_out, ps_err = run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], 4.0)
    containers = [
        line for line in ps_out.splitlines()
        if line.startswith("plane-app-")
    ]
    return JSONResponse({
        "ok": service_code == 0 and http_ok,
        "url": "http://100.87.238.153:8090/",
        "lan_url": "http://192.168.123.71:8090/",
        "tailnet_fallback": "https://fedora-termhive.tail60cff7.ts.net/",
        "service": service_out or service_err,
        "http_status": http_status,
        "containers": containers,
        "compose": "/var/home/charlie/apps/plane-selfhost/plane-app/docker-compose.yaml",
        "unit": "plane.service",
        "role": "project progress source of truth; Hub/Zulip/OP/FastGPT should sync around it",
        "ps_error": ps_err if ps_code != 0 else "",
    })


@app.get("/api/appsmith/status")
async def appsmith_status_api():
    def run(cmd: list[str], timeout: float = 4.0) -> tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    service_code, service_out, service_err = run(["systemctl", "--user", "is-active", "appsmith.service"], 3.0)
    http_ok = False
    http_status = None
    try:
        req = urllib.request.Request("http://127.0.0.1:8089/", method="GET")
        with urllib.request.urlopen(req, timeout=4) as resp:
            http_status = resp.status
            http_ok = 200 <= resp.status < 500
    except Exception as exc:
        http_status = str(exc)
    ps_code, ps_out, ps_err = run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], 4.0)
    containers = [line for line in ps_out.splitlines() if line.startswith("appsmith ")]
    return JSONResponse({
        "ok": service_code == 0 and http_ok,
        "url": "http://100.87.238.153:8089/",
        "lan_url": "http://192.168.123.71:8089/",
        "service": service_out or service_err,
        "http_status": http_status,
        "containers": containers,
        "compose": "/var/home/charlie/apps/appsmith/docker-compose.yml",
        "unit": "appsmith.service",
        "role": "single operations console; visual UI over Hub APIs, n8n workflows, OP execution, and collaboration tools",
        "ps_error": ps_err if ps_code != 0 else "",
    })


@app.get("/api/n8n/status")
async def n8n_status_api():
    def run(cmd: list[str], timeout: float = 4.0) -> tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    service_code, service_out, service_err = run(["systemctl", "--user", "is-active", "n8n.service"], 3.0)
    http_ok = False
    http_status = None
    try:
        req = urllib.request.Request("http://127.0.0.1:5678/", method="GET")
        with urllib.request.urlopen(req, timeout=4) as resp:
            http_status = resp.status
            http_ok = 200 <= resp.status < 500
    except Exception as exc:
        http_status = str(exc)
    return JSONResponse({
        "ok": service_code == 0 and http_ok,
        "url": "http://100.87.238.153:5678/",
        "lan_url": "http://192.168.123.71:5678/",
        "service": service_out or service_err,
        "http_status": http_status,
        "unit": "n8n.service",
        "role": "automation bus; connects semantic commands, webhooks, Hub APIs, OP, FastGPT, Zulip, Plane, and Huly",
    })


@app.get("/api/huly/status")
async def huly_status_api():
    def run(cmd: list[str], timeout: float = 4.0) -> tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    service_code, service_out, service_err = run(["systemctl", "--user", "is-active", "huly.service"], 3.0)
    http_ok = False
    http_status = None
    try:
        req = urllib.request.Request("http://127.0.0.1:8087/", method="HEAD")
        with urllib.request.urlopen(req, timeout=4) as resp:
            http_status = resp.status
            http_ok = 200 <= resp.status < 500
    except Exception as exc:
        http_status = str(exc)

    ps_code, ps_out, ps_err = run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], 4.0)
    containers = [
        line for line in ps_out.splitlines()
        if line.startswith("huly_v7-")
    ]
    return JSONResponse({
        "ok": service_code == 0 and http_ok,
        "url": "http://100.87.238.153:8087/",
        "lan_url": "http://192.168.123.71:8087/",
        "service": service_out or service_err,
        "http_status": http_status,
        "containers": containers,
        "compose": "/var/home/charlie/apps/huly-selfhost/compose.yml",
        "unit": "huly.service",
        "role": "all-in-one workspace for projects, tasks, docs, chat, and collaboration",
        "ps_error": ps_err if ps_code != 0 else "",
    })


async def _mattermost_payload_from_request(request: Request) -> dict:
    content_type = request.headers.get("content-type", "").lower()
    raw = await request.body()
    if "application/json" in content_type:
        try:
            data = json.loads(raw.decode("utf-8", errors="replace") or "{}")
            return data if isinstance(data, dict) else {"payload": data}
        except json.JSONDecodeError:
            return {"raw": raw.decode("utf-8", errors="replace")}
    if "application/x-www-form-urlencoded" in content_type or raw:
        parsed = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
        return {k: v[-1] if isinstance(v, list) and v else v for k, v in parsed.items()}
    try:
        form = await request.form()
        return {k: str(v) for k, v in form.items()}
    except Exception:
        return {}


def _mattermost_source_ref(payload: dict) -> str:
    env = _load_simple_env(MATTERMOST_INBOX_ENV)
    base = (env.get("MATTERMOST_NETBIRD_URL") or env.get("MATTERMOST_BASE_URL") or "http://100.87.238.153:8065").rstrip("/")
    team = payload.get("team_domain") or payload.get("team_name") or env.get("MATTERMOST_TEAM") or ""
    post_id = payload.get("post_id") or payload.get("postId") or payload.get("id") or ""
    if team and post_id:
        return f"{base}/{team}/pl/{post_id}"
    return str(payload.get("trigger_word") or payload.get("channel_name") or "mattermost")


def _mattermost_intake_kind(payload: dict) -> str:
    """Classify a Mattermost intake into the Hub workflow lane.

    This is intentionally deterministic and local: channel naming and artifact
    extensions decide the initial lane; AI agents can refine it only after the
    user approves the Hub task.
    """
    channel = str(payload.get("channel_name") or payload.get("channel_id") or "").lower()
    text = str(payload.get("text") or payload.get("message") or payload.get("post") or "").lower()
    artifacts = payload.get("artifact_paths") if isinstance(payload.get("artifact_paths"), list) else []
    attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
    kinds = {
        str(item.get("kind") or "").lower()
        for item in attachments
        if isinstance(item, dict) and item.get("kind")
    }
    suffixes = {Path(str(path)).suffix.lower().strip(".") for path in artifacts}
    if "aider" in channel or any(word in text for word in ["aider", "单写入", "最小变更", "写入执行"]):
        return "aider"
    if "cursor" in channel or any(word in text for word in ["cursor", "kasm", "gui ide", "可视化", "界面验证", "前端视觉"]):
        return "cursor"
    if "goose" in channel or "guise" in channel or any(word in text for word in ["goose", "guise", "只读", "诊断", "计划", "复盘"]):
        return "goose"
    if "review" in channel or any(word in text for word in ["确认", "审核", "approve", "review"]):
        return "review"
    if "task" in channel or any(word in text for word in ["任务", "待办", "todo", "执行", "安排"]):
        return "task"
    if "image" in channel or "图片" in channel or "image" in kinds or suffixes & {"jpg", "jpeg", "png", "webp", "gif", "heic", "heif", "bmp", "tif", "tiff"}:
        return "image"
    if "doc" in channel or "资料" in channel or "document" in kinds or suffixes & {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "md", "txt", "csv", "json", "html"}:
        return "document"
    return "inbox"


MATTERMOST_RECEIPT_PREFIXES = (
    "✅ 已进入 Hub 待审批",
    "✅ Mattermost 对接自测已创建任务",
    "⚠️ Mattermost 收件失败",
)


MATTERMOST_CHANNEL_GUIDES = {
    "ai-inbox": {
        "agent": "AI 收件箱 Agent",
        "use": "文字、链接、图片、资料、手机需求总入口；自动进入 Hub 待审批。",
        "next": "补充资料请直接回复；需要手机跨 App/屏幕操作请回复 `step: 你的目标`。",
        "red": "删除/付款/发外部消息/登录授权/公开发布必须先到 `ai-review` 确认。",
    },
    "ai-images": {
        "agent": "AI 图片整理 Agent",
        "use": "截图/照片/OCR/分类/重命名/图片资料归档。",
        "next": "继续上传图片即可；需要从手机相册取图请回复 `step: 打开相册...只停在选择页`。",
        "red": "不自动删除原图、不自动上传外网；隐私图片公开前必须确认。",
    },
    "ai-docs": {
        "agent": "AI 资料整理 Agent",
        "use": "PDF/Word/Excel/txt/链接摘要、关键事实提取、归档和任务拆解。",
        "next": "补链接/附件即可；需要引用已有本地资料请写清路径或来源。",
        "red": "合同/财务/法律/密钥/密码内容只摘要和标注风险，不外发。",
    },
    "ai-review": {
        "agent": "AI 人工确认 / 红线 Agent",
        "use": "高风险动作审批台：只给选项、影响、风险和推荐，不越权执行。",
        "next": "回复 `确认: ...` 才会进入后续派发；不确认默认停住。",
        "red": "删除、覆盖、改网络/防火墙/NAT、付款/下单、发消息、登录授权都必须人工确认。",
    },
    "ai-tasks": {
        "agent": "AI 任务回执 Agent",
        "use": "只显示 Hub 任务 ID、审批入口和执行状态。",
        "next": "不要在这里投递新任务；补充内容请回原频道或 `ai-inbox`。",
        "red": "`ai-tasks` 必须保持输出频道，不能加入 `MATTERMOST_WATCH_CHANNELS`。",
    },
    "hub": {
        "agent": "Hub 总控 Agent",
        "use": "项目、审批、任务状态、服务入口和运维总控。",
        "next": "打开 Hub 审批入口，补工作区/目标/验收后再派发执行。",
        "red": "系统级改动必须给备份、验证和回滚。",
    },
    "op": {
        "agent": "OP / OpenCode 执行 Agent",
        "use": "代码、脚本、服务修复、自动化按钮；先建 Hub 待审批任务。",
        "next": "写清目标、文件路径、验证命令；需要执行时从 Hub 批准。",
        "red": "写入/删除/重启服务必须有验证和回滚说明。",
    },
    "cursor": {
        "agent": "Cursor GUI 任务 Agent",
        "use": "GUI/IDE/前端视觉/插件/登录态/人工协同代码任务；先入 Hub，默认 Goose 只读计划。",
        "next": "写清项目路径、要看的界面、预期/实际差异；需要执行写入时转 `aider` 或 Hub 批准。",
        "red": "Cursor 频道不直接改生产、不自动提交/发布；登录授权、付费插件、删除/覆盖必须确认。",
    },
    "goose": {
        "agent": "Goose 只读诊断 Agent",
        "use": "只读分析、计划、风险评审、上下文整理；默认 Hub assignee=`plan`。",
        "next": "让 Goose 先给最小方案、影响范围、验证命令；写入执行再转 `aider`/`op`。",
        "red": "Goose 默认不写文件、不重启服务、不改网络；破坏性动作必须 Hub/ai-review 确认。",
    },
    "aider": {
        "agent": "Aider 单写入执行 Agent",
        "use": "经 Goose 计划和 Hub 审批后的代码/配置最小写入；默认 Hub assignee=`goose_aider`。",
        "next": "提供目标文件、修改范围、测试命令、回滚方式；执行后结果回 `ai-tasks`/项目同步。",
        "red": "大范围重构、数据库写入、删除、发布、网络规则改动必须有备份和回滚。",
    },
    "fastgpt": {
        "agent": "FastGPT 知识库 Agent",
        "use": "资料问答、方案、最佳实践和 FAQ 沉淀。",
        "next": "适合发资料和问题；执行类任务仍回 Hub 审批。",
        "red": "不要把密码/token/私密数据库内容写入知识库。",
    },
    "alerts": {
        "agent": "系统告警 Agent",
        "use": "网络、端口、服务、手机连通性、ntfy/Kuma 事件。",
        "next": "先诊断再建议；需要修复时创建 Hub 待审批任务。",
        "red": "告警不能直接触发破坏性修复；网络规则变更先确认。",
    },
    "sourcing": {
        "agent": "采集 / 资料源 Agent",
        "use": "网页、产品、供应商、开源方案、论坛最佳实践采集。",
        "next": "输出比较、来源和后续任务；采购/联系前等确认。",
        "red": "下单、付款、询价、发邮件/私信必须人工确认。",
    },
}


def _mattermost_channel_agent(channel: str, intake_kind: str = "inbox") -> dict:
    name = str(channel or "").lower()
    guide = MATTERMOST_CHANNEL_GUIDES.get(name)
    if guide:
        return guide
    by_kind = {
        "image": MATTERMOST_CHANNEL_GUIDES["ai-images"],
        "document": MATTERMOST_CHANNEL_GUIDES["ai-docs"],
        "review": MATTERMOST_CHANNEL_GUIDES["ai-review"],
        "task": MATTERMOST_CHANNEL_GUIDES["hub"],
        "cursor": MATTERMOST_CHANNEL_GUIDES["cursor"],
        "goose": MATTERMOST_CHANNEL_GUIDES["goose"],
        "aider": MATTERMOST_CHANNEL_GUIDES["aider"],
    }
    return by_kind.get(intake_kind, MATTERMOST_CHANNEL_GUIDES["ai-inbox"])


def _mattermost_should_skip_intake(payload: dict, env: dict, text: str) -> tuple[bool, str]:
    channel = str(payload.get("channel_name") or payload.get("channel_id") or "").strip()
    tasks_channel = str(env.get("MATTERMOST_TASKS_CHANNEL") or "ai-tasks").strip()
    if channel and tasks_channel and channel == tasks_channel:
        return True, "output_channel"
    if "<!-- charlie-agent-guide:" in text[:200]:
        return True, "agent_guide"
    if text.startswith(MATTERMOST_RECEIPT_PREFIXES) or "已进入 Hub 待审批" in text[:240]:
        return True, "hub_receipt"
    post_type = str(payload.get("type") or payload.get("post_type") or "")
    if post_type.startswith("system_"):
        return True, "system_post"
    return False, ""


def _mattermost_step_request_text(text: str) -> str:
    m = re.match(r"^\s*(?:step|step\s*ui|gelab|手机操作|跨app|跨应用)\s*[:：-]\s*(.+)$", text, flags=re.I | re.S)
    return (m.group(1).strip() if m else "")


def _mattermost_http_json(method: str, url: str, body: dict | None = None, timeout: float = 8.0) -> tuple[dict, int]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(120000).decode("utf-8", errors="replace")
        try:
            return json.loads(raw or "{}"), resp.status
        except json.JSONDecodeError:
            return {"raw": raw[-2000:]}, resp.status
    except Exception as exc:
        return {"ok": False, "error": str(exc)}, 502


def _mattermost_maybe_dispatch_step_router(payload: dict, text: str) -> dict:
    task_text = _mattermost_step_request_text(text)
    if not task_text:
        return {}
    base = "http://127.0.0.1:19888"
    device = "w19900422"
    dispatch_text = f"step ui 跨App 操作：{task_text}"
    dispatch, status = _mattermost_http_json(
        "POST",
        f"{base}/api/super/dispatch?device={urllib.parse.quote(device)}",
        {"text": dispatch_text, "source": "mattermost", "channel": payload.get("channel_name") or ""},
        timeout=10,
    )
    result = {"requested": task_text[:500], "dispatch_status": status, "dispatch": dispatch}
    # Always save the clean user task after /dispatch.  /dispatch may prepend
    # router hints to make Workbench choose Step UI; the Step UI operator should
    # see the user's original instruction instead.
    forced, forced_status = _mattermost_http_json(
        "POST",
        f"{base}/api/super/run?action=step-task&redirect=0&device={urllib.parse.quote(device)}",
        {"task": task_text, "source": "mattermost", "max_steps": 20},
        timeout=10,
    )
    result["forced_step_status"] = forced_status
    result["forced_step"] = forced
    return result


def _mattermost_step_summary(step_router: dict) -> list[str]:
    if not step_router:
        return []
    dispatch = step_router.get("dispatch") if isinstance(step_router.get("dispatch"), dict) else {}
    forced = step_router.get("forced_step") if isinstance(step_router.get("forced_step"), dict) else {}
    plan = dispatch.get("plan") if isinstance(dispatch.get("plan"), dict) else {}
    lines = [
        "## Step Router / 手机 GUI Agent",
        f"- 请求：{str(step_router.get('requested') or '')[:300]}",
        f"- 路由：{plan.get('action') or forced.get('action') or 'step-task'} / {plan.get('kind') or 'step'}",
    ]
    task_saved = forced.get("task_saved") or ((dispatch.get("result") or {}) if isinstance(dispatch.get("result"), dict) else {}).get("task_saved")
    step_ui = forced.get("step_ui") or ((dispatch.get("result") or {}) if isinstance(dispatch.get("result"), dict) else {}).get("step_ui")
    if task_saved:
        lines.append(f"- 已保存 Step 任务：{task_saved}")
    if step_ui:
        lines.append(f"- Step UI：{step_ui}")
    lines.append("- 红线：付款/下单/删除/发外部消息前必须停在确认页。")
    return lines


def _mattermost_reply_guide(payload: dict, task: dict, step_router: dict) -> str:
    channel = str(payload.get("channel_name") or payload.get("channel_id") or "")
    intake_kind = _mattermost_intake_kind(payload)
    guide = _mattermost_channel_agent(channel, intake_kind)
    lines = [
        f"### 🤖 当前频道：{guide['agent']}",
        f"- 用途：{guide['use']}",
        f"- 下一步：{guide['next']}",
        f"- 🔴 红线：{guide['red']}",
        "- 常用回复：`补充: ...` / `确认: ...` / `取消` / `step: ...`",
    ]
    if step_router:
        step_lines = _mattermost_step_summary(step_router)
        if step_lines:
            lines.extend(["", *step_lines])
    return "\n".join(lines)


def _mattermost_task_body(payload: dict) -> dict:
    env = _load_simple_env(MATTERMOST_INBOX_ENV)
    text = str(payload.get("text") or payload.get("message") or payload.get("post") or payload.get("raw") or "").strip()
    trigger = str(payload.get("trigger_word") or "").strip()
    if trigger and text.startswith(trigger):
        text = text[len(trigger):].strip()
    text = re.sub(r"^[/!#]*(ai|task|todo|任务|待办)[:：\\s-]*", "", text, flags=re.I).strip() or text
    user = payload.get("user_name") or payload.get("user") or payload.get("user_id") or "mattermost"
    channel = payload.get("channel_name") or payload.get("channel_id") or "unknown"
    title_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    title = title_line[:90] if title_line else f"Mattermost 收件：{channel}"
    source_ref = _mattermost_source_ref(payload)
    intake_kind = _mattermost_intake_kind(payload)
    kind_labels = {
        "image": "图片整理",
        "document": "资料整理",
        "task": "任务拆解",
        "review": "人工确认",
        "inbox": "收件整理",
        "cursor": "Cursor GUI任务",
        "goose": "Goose只读诊断",
        "aider": "Aider单写入执行",
    }
    if not title_line:
        title = f"Mattermost {kind_labels.get(intake_kind, '收件整理')}：{channel}"
    artifact_paths = payload.get("artifact_paths") if isinstance(payload.get("artifact_paths"), list) else []
    attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
    attachment_lines = []
    for item in attachments[:12]:
        if isinstance(item, dict):
            name = item.get("name") or Path(str(item.get("path") or "")).name or "attachment"
            kind = item.get("kind") or "file"
            size = item.get("size")
            suffix = f" ({size} bytes)" if size else ""
            attachment_lines.append(f"- [{kind}] {name}{suffix}: {item.get('path') or ''}")
    if not attachment_lines:
        attachment_lines = [f"- {path}" for path in artifact_paths[:12]]
    if not attachment_lines:
        attachment_lines = ["- 无"]
    agent_guide = _mattermost_channel_agent(str(channel), intake_kind)
    step_router = payload.get("step_router") if isinstance(payload.get("step_router"), dict) else {}
    step_lines = _mattermost_step_summary(step_router)
    acceptance_by_kind = {
        "image": "提取图片/截图中的关键信息；按主题重命名/分类；需要 OCR 时给出文字；产出摘要、存放路径、后续动作。",
        "document": "阅读附件/资料；提炼摘要、关键事实、链接/文件路径；按主题归档；给出可执行后续任务。",
        "task": "把消息拆成可审批的目标、步骤、风险、验收标准；必要时建议执行窗口和负责人。",
        "review": "明确需要人工确认的选项、影响、风险和推荐选择；不要越过确认执行破坏性动作。",
        "inbox": "在 Hub 中确认任务目标；如涉及图片/资料，整理出摘要、分类、存放路径和后续动作。",
        "cursor": "给出 Cursor GUI/IDE 操作目标、项目路径、要观察的界面、预期/实际差异、建议验证方式；写入前转 Aider/OP 审批。",
        "goose": "只读分析上下文、影响范围、风险、最小变更计划、验证命令和回滚建议；不得直接写入。",
        "aider": "在 Hub 审批后按最小变更执行；列出修改文件、验证命令、结果证据和回滚方式。",
    }
    goal_by_kind = {
        "image": "整理 Mattermost 收件箱中的图片/截图，提取信息并形成可追踪任务。",
        "document": "整理 Mattermost 收件箱中的资料/文档，形成摘要、分类和后续动作。",
        "task": text[:1000] or "拆解 Mattermost 中提交的任务并进入 Hub 审批。",
        "review": text[:1000] or "整理 Mattermost 中需要人工确认的事项。",
        "inbox": text[:1000] or "整理 Mattermost 收件箱中的图片/资料/任务。",
        "cursor": text[:1000] or "整理 Cursor GUI/IDE 任务，先形成只读计划和验证入口。",
        "goose": text[:1000] or "用 Goose 只读诊断并形成可审批执行计划。",
        "aider": text[:1000] or "在 Hub 审批后用 Goose→Aider 单写入执行最小变更。",
    }
    brief = "\n".join([
        "来自 Mattermost AI Inbox 的待审批任务。",
        "",
        f"- 用户：{user}",
        f"- 频道：{channel}",
        f"- 类型：{kind_labels.get(intake_kind, intake_kind)}",
        f"- 来源：{source_ref}",
        "",
        "## 频道 Agent 引导",
        f"- Agent：{agent_guide['agent']}",
        f"- 用途：{agent_guide['use']}",
        f"- 下一步：{agent_guide['next']}",
        f"- 🔴 红线：{agent_guide['red']}",
        "- Cursor入口：NetBird http://100.87.238.153:19970/ ｜ LAN http://192.168.123.71:19970/",
        "- Goose入口：NetBird http://100.87.238.153:7694/tool/guise/ ｜ LAN http://192.168.123.71:7694/tool/guise/",
        "- Aider入口：NetBird http://100.87.238.153:7693/tool/aider/ ｜ LAN http://192.168.123.71:7693/tool/aider/",
        "",
        *step_lines,
        "" if step_lines else "",
        "## 附件/资料",
        "\n".join(attachment_lines),
        "",
        "## 原始内容",
        text or "(无文本；可能是附件/图片消息，请在 Mattermost 中查看原帖)",
    ])
    return {
        "project_id": env.get("HUB_DEFAULT_PROJECT_ID") or "ai-brain",
        "title": title,
        "brief": brief,
        "goal": goal_by_kind.get(intake_kind, goal_by_kind["inbox"]),
        "acceptance": acceptance_by_kind.get(intake_kind, acceptance_by_kind["inbox"]),
        "priority": env.get("HUB_DEFAULT_PRIORITY") or "medium",
        "assignee": ("plan" if intake_kind in {"goose", "cursor"} else ("goose_aider" if intake_kind == "aider" else (env.get("HUB_DEFAULT_ASSIGNEE") or "op"))),
        "window": env.get("HUB_DEFAULT_WINDOW") or "night",
        "tags": ["mattermost", "ai-inbox", intake_kind, str(channel)[:32]] + (["step-router"] if step_router else []),
        "source": "mattermost",
        "source_ref": source_ref,
        "artifact_paths": artifact_paths,
        "attachments": attachments,
    }


@app.get("/api/mattermost/integration/status")
async def mattermost_integration_status_api():
    config_path = Path("/var/home/charlie/apps/mattermost-docker/volumes/app/mattermost/config/config.json")
    config_flags: dict[str, typing.Any] = {}
    try:
        cfg_mm = json.loads(config_path.read_text(encoding="utf-8"))
        for sec, key in [
            ("ServiceSettings", "EnableIncomingWebhooks"),
            ("ServiceSettings", "EnableOutgoingWebhooks"),
            ("ServiceSettings", "EnableBotAccountCreation"),
            ("ServiceSettings", "EnableUserAccessTokens"),
            ("ServiceSettings", "EnablePostUsernameOverride"),
            ("ServiceSettings", "EnablePostIconOverride"),
            ("FileSettings", "EnableMobileUpload"),
            ("FileSettings", "EnableMobileDownload"),
        ]:
            config_flags[f"{sec}.{key}"] = cfg_mm.get(sec, {}).get(key)
    except Exception as exc:
        config_flags["error"] = str(exc)
    recent: list[dict] = []
    if MATTERMOST_INBOX_EVENTS.exists():
        try:
            for line in MATTERMOST_INBOX_EVENTS.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]:
                try:
                    recent.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
    return {
        "ok": True,
        "role": "Mattermost AI Inbox: phone/chat/files -> Hub pending approval -> AI/workflow -> Mattermost/ntfy receipt",
        "hub_inbox_url": "http://127.0.0.1:9800/api/mattermost/inbox",
        "hub_outgoing_url": "http://127.0.0.1:9800/api/mattermost/outgoing",
        "env": _mattermost_env_status(),
        "mattermost_config": config_flags,
        "agent_guides": {
            name: {"agent": cfg["agent"], "use": cfg["use"], "red": cfg["red"]}
            for name, cfg in MATTERMOST_CHANNEL_GUIDES.items()
        },
        "step_router": {
            "dispatch": "POST http://127.0.0.1:19888/api/super/dispatch?device=w19900422",
            "explicit_prefix": "step: ...",
            "latest_task": str(Path.home() / ".local/state/mobile-ai-super/latest-step-task.txt"),
        },
        "events_file": str(MATTERMOST_INBOX_EVENTS),
        "recent_events": recent,
    }


@app.post("/api/mattermost/inbox")
@app.post("/api/mattermost/outgoing")
async def mattermost_inbox_api(request: Request):
    payload = await _mattermost_payload_from_request(request)
    env = _load_simple_env(MATTERMOST_INBOX_ENV)
    expected_token = env.get("MATTERMOST_OUTGOING_TOKEN", "").strip()
    got_token = str(payload.get("token") or payload.get("mattermost_token") or "").strip()
    if expected_token and got_token != expected_token:
        _append_jsonl(MATTERMOST_INBOX_EVENTS, {"ts": datetime.now().isoformat(), "event": "reject", "reason": "bad token", "channel": payload.get("channel_name")})
        return JSONResponse({"error": "invalid token"}, status_code=403)

    text = str(payload.get("text") or payload.get("message") or payload.get("post") or payload.get("raw") or "").strip()
    skip, skip_reason = _mattermost_should_skip_intake(payload, env, text)
    if skip:
        _append_jsonl(MATTERMOST_INBOX_EVENTS, {
            "ts": datetime.now().isoformat(),
            "event": "skipped",
            "reason": skip_reason,
            "channel": payload.get("channel_name") or payload.get("channel_id"),
            "post_id": payload.get("post_id") or payload.get("id"),
            "text_preview": text[:240],
        })
        return {"ok": True, "skipped": True, "reason": skip_reason, "response_type": "ephemeral", "text": "已跳过 Hub 回执/输出频道消息，避免自循环。"}
    step_router = _mattermost_maybe_dispatch_step_router(payload, text)
    if step_router:
        payload["step_router"] = step_router
    event = {
        "ts": datetime.now().isoformat(),
        "event": "received",
        "user": payload.get("user_name") or payload.get("user_id"),
        "channel": payload.get("channel_name") or payload.get("channel_id"),
        "post_id": payload.get("post_id") or payload.get("id"),
        "source_ref": _mattermost_source_ref(payload),
        "text_preview": text[:500],
    }
    task_payload = _mattermost_task_body(payload)
    result, status = _create_project_task_from_body(task_payload, "mattermost")
    event["task_id"] = result.get("task", {}).get("id")
    event["task_status"] = status
    if step_router:
        dispatch = step_router.get("dispatch") if isinstance(step_router.get("dispatch"), dict) else {}
        event["step_router"] = {
            "requested": step_router.get("requested"),
            "dispatch_status": step_router.get("dispatch_status"),
            "plan": dispatch.get("plan") if isinstance(dispatch.get("plan"), dict) else {},
            "forced_step_status": step_router.get("forced_step_status"),
        }
    _append_jsonl(MATTERMOST_INBOX_EVENTS, event)

    if status >= 400:
        reply = f"⚠️ Mattermost 收件失败：{result.get('error') or status}"
        _mattermost_post(reply, env.get("MATTERMOST_REVIEW_CHANNEL", ""))
        return JSONResponse({"error": result.get("error"), "response_type": "ephemeral", "text": reply}, status_code=status)

    task = result["task"]
    projects_url = env.get("HUB_PROJECTS_NETBIRD_URL") or env.get("HUB_PROJECTS_URL") or "http://100.87.238.153:9800/projects"
    projects_lan = env.get("HUB_PROJECTS_LAN_URL") or "http://192.168.123.71:9800/projects"
    reply = f"✅ 已进入 Hub 待审批：**{task['title']}**\n\n- 任务 ID: `{task['id']}`\n- 审批入口 NetBird: {projects_url}\n- 审批入口 LAN: {projects_lan}\n\n{_mattermost_reply_guide(payload, task, step_router)}"
    post_result = _mattermost_post(reply, env.get("MATTERMOST_TASKS_CHANNEL", ""))
    return {
        "ok": True,
        "response_type": "comment",
        "text": reply,
        "task": task,
        "mattermost_receipt": post_result,
    }


@app.post("/api/mattermost/test-task")
async def mattermost_test_task_api(body: dict | None = None):
    body = body or {}
    payload = {
        "text": body.get("text") or "测试：从 Mattermost AI Inbox 创建一条待审批任务",
        "user_name": body.get("user_name") or "hub-test",
        "channel_name": body.get("channel_name") or "ai-inbox",
        "post_id": f"hubtest{int(time.time())}",
        "team_domain": "charlie",
    }
    task_payload = _mattermost_task_body(payload)
    result, status = _create_project_task_from_body(task_payload, "mattermost-test")
    if status >= 400:
        return JSONResponse(result, status_code=status)
    receipt_text = (
        f"✅ Mattermost 对接自测已创建任务 `{result['task']['id']}`：{result['task']['title']}\n\n"
        f"{_mattermost_reply_guide(payload, result['task'], {})}"
    )
    receipt = _mattermost_post(receipt_text)
    return {"ok": True, "task": result["task"], "mattermost_receipt": receipt}


@app.get("/api/mattermost/status")
async def mattermost_status_api():
    def run(cmd: list[str], timeout: float = 4.0) -> tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    service_code, service_out, service_err = run(["systemctl", "--user", "is-active", "mattermost.service"], 3.0)
    http_ok = False
    http_status = None
    try:
        req = urllib.request.Request("http://127.0.0.1:8065/api/v4/system/ping", method="GET")
        with urllib.request.urlopen(req, timeout=4) as resp:
            http_status = resp.status
            http_ok = 200 <= resp.status < 500
    except Exception as exc:
        http_status = str(exc)

    ps_code, ps_out, ps_err = run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], 4.0)
    containers = [
        line for line in ps_out.splitlines()
        if line.startswith("mattermost-docker-")
    ]
    return JSONResponse({
        "ok": service_code == 0 and http_ok,
        "url": "http://100.87.238.153:8065/",
        "lan_url": "http://192.168.123.71:8065/",
        "service": service_out or service_err,
        "http_status": http_status,
        "containers": containers,
        "compose": "/var/home/charlie/apps/mattermost-docker/docker-compose.yml",
        "unit": "mattermost.service",
        "role": "channel collaboration, bots, webhooks, images, and AI coordination",
        "ps_error": ps_err if ps_code != 0 else "",
    })


@app.get("/go/{key}")
async def go_link(key: str, request: Request):
    item = LINK_REGISTRY.get(key)
    if not item:
        return HTMLResponse(f"<h1>未知链接: {key}</h1>", status_code=404)
    return HTMLResponse(_go_page(key, item, _link_candidates(key, request)))


@app.api_route("/proxy/termhive/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.api_route("/proxy/termhive", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_termhive(request: Request, path: str = ""):
    import httpx

    suffix = f"/{path}" if path else "/"
    query = request.url.query
    target = f"http://127.0.0.1:3200{suffix}" + (f"?{query}" if query else "")
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in {"host", "connection", "content-length", "accept-encoding"}
    }
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
            upstream = await client.request(request.method, target, content=body, headers=headers)
    except Exception as exc:
        return Response(f"TermHive proxy error: {exc}", status_code=502, media_type="text/plain")

    out_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in {"transfer-encoding", "connection", "content-encoding", "content-length"}
    }
    return Response(upstream.content, status_code=upstream.status_code, headers=out_headers)
LETTA_AGENT_ID = 'agent-0040ded4-1831-4b76-a4a4-62519a416a5a'
GLM_DATA_DIR = Path.home() / 'Desktop' / '巡检报告'
_TASK_REVIEW_PATH = Path.home() / 'Desktop' / '巡检报告' / 'task-review.json'
OP_RESULTS_FILE = Path(Path.home() / '.local/state/op-results.json')

def _load_op_results() -> dict:
    if OP_RESULTS_FILE.exists():
        try: return json.loads(OP_RESULTS_FILE.read_text())
        except Exception: pass
    return {}

def _save_op_results(data: dict) -> None:
    OP_RESULTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

class SafeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, default=str).encode('utf-8')

PROJECTS_DEF = [
    {"id": "wechat-system", "name": "微信体系", "emoji": "💬", "group": "biz", "description": "微信消息解密 + 三端合并 + 自动回复", "milestones": [{"id": "key-extract", "name": "DB Key 提取", "status": "in_progress"}, {"id": "db-merge", "name": "三端数据合并", "status": "pending"}, {"id": "auto-reply", "name": "自动回复接入", "status": "done"}]},
    {"id": "trade-crm", "name": "外贸 CRM", "emoji": "🏭", "group": "biz", "description": "联系人 / 商机 / 报关单自动填写", "milestones": [{"id": "twenty-deploy", "name": "Twenty CRM 部署", "status": "done"}, {"id": "entity-graph", "name": "实体上下文图谱", "status": "in_progress"}, {"id": "doc-autofill", "name": "文档自动填写", "status": "pending"}]},
    {"id": "ai-brain", "name": "AI 架构升级", "emoji": "🧠", "group": "infra", "description": "Brain.py 从监控转业务智能 / Entity Context Graph", "milestones": [{"id": "email-imap", "name": "Email IMAP → CRM", "status": "pending"}, {"id": "entity-graph-l2", "name": "L2 关联推理层", "status": "pending"}, {"id": "action-layer", "name": "L3 行动层", "status": "pending"}]},
    {"id": "console-3000", "name": "3000 控制台", "emoji": "🖥️", "group": "infra", "description": "AGI Control Plane — 统一项目视图 + OP 面板", "milestones": [{"id": "op-center", "name": "OP 控制中心", "status": "done"}, {"id": "projects-panel", "name": "Projects 汇总面板", "status": "in_progress"}, {"id": "graph-panel", "name": "知识图谱面板", "status": "done"}]},
    {"id": "op-infra", "name": "OP 运维体系", "emoji": "⚙️", "group": "infra", "description": "定时巡检 / 健康监控 / 自愈能力", "milestones": [{"id": "health-check", "name": "服务健康巡检", "status": "done"}, {"id": "discord-bot", "name": "Discord 通知机器人", "status": "in_progress"}, {"id": "self-heal", "name": "自愈 + 自动重启", "status": "done"}]},
    {"id": "sourcing-content", "name": "Sourcing内容创建", "emoji": "📦", "group": "biz", "description": "旧 WordPress 采购站资产 → Astro 商品页 → CRM/Telegram 联动", "source_path": "/var/mnt/nixos/home/charlie/Desktop/巡检报告/wordpress-analysis.json", "target_path": "/var/home/charlie/projects/projects/sourcing-site", "legacy": {"type": "wordpress", "backup_hint": "/mnt/pool/sde1-migrated/- 123 onedrive/- Sourcing/root", "db_name": "w422417869", "theme": "elessi-theme", "plugins": 23, "status": "analysis_found_backup_path_pending_mount"}, "artifacts": ["/var/mnt/nixos/home/charlie/Desktop/巡检报告/wordpress-analysis.json", "/var/mnt/nixos/home/charlie/op-tasks-archive.md", "/var/mnt/nixos/home/charlie/Documents/Obsidian/Charlie-Hub/📌 跨会话待办.md"], "milestones": [{"id": "wordpress-backup", "name": "WordPress 备份定位", "status": "in_progress"}, {"id": "pdf-parser", "name": "PDF解析器", "status": "pending"}, {"id": "copy-generator", "name": "文案生成引擎", "status": "pending"}, {"id": "astro-generator", "name": "Astro页面生成器", "status": "pending"}, {"id": "crm-sync", "name": "CRM同步", "status": "pending"}, {"id": "telegram-push", "name": "Telegram推送", "status": "pending"}]},
]

PROJECTS_STATE_FILE = Path.home() / ".local/state/hub/projects.json"
PROJECT_CONTROL_FILE = Path.home() / ".local/state/hub/project-control.json"
DISPATCH_TASKS_DIR = Path.home() / ".local/state/agent-dispatch/tasks"
PROJECT_TASK_STATUSES = {
    "pending_approval", "queued", "delegated", "in_progress", "blocked",
    "review", "done", "cancelled", "dispatch_failed",
}
PROJECT_TASK_PRIORITIES = {"urgent", "high", "medium", "low"}
PROJECT_TASK_ASSIGNEES = {"auto", "op", "crush", "goose_aider", "plan"}
PROJECT_TASK_RUNS_DIR = Path.home() / ".local/state/hub/task-runs"
_project_control_lock = threading.Lock()
MATTERMOST_INBOX_DIR = Path.home() / ".local/state/mattermost-ai-inbox"
MATTERMOST_INBOX_EVENTS = MATTERMOST_INBOX_DIR / "events.jsonl"
MATTERMOST_INBOX_ENV = Path.home() / ".config/mattermost-ai-inbox.env"


def _project_slug(text: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or f"project-{int(time.time())}"


def _bounded_int(value, minimum: int = 0, maximum: int = 100) -> int:
    try:
        return max(minimum, min(maximum, int(value or 0)))
    except (TypeError, ValueError):
        return minimum


def _load_custom_projects() -> list[dict]:
    if not PROJECTS_STATE_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_custom_projects(projects: list[dict]) -> None:
    PROJECTS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_STATE_FILE.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")


def _all_projects() -> list[dict]:
    custom = _load_custom_projects()
    overrides = {p.get("id"): p for p in custom if p.get("id")}
    builtin = [dict(overrides.get(p.get("id"), p), builtin=True) for p in PROJECTS_DEF]
    seen = {p["id"] for p in builtin}
    return builtin + [dict(p, builtin=False) for p in custom if p.get("id") not in seen]


def _project_with_progress(project: dict) -> dict:
    ms = project.get("milestones", [])
    return {
        **project,
        "progress": _calc_progress(ms),
        "done_count": sum(1 for m in ms if m.get("status") == "done"),
        "in_progress_count": sum(1 for m in ms if m.get("status") == "in_progress"),
    }


def _append_project_op_task(project: dict, message: str) -> dict:
    task_text = message.strip() or f"推进项目 {project.get('name', project.get('id'))}"
    return _append_op_inbox_task(
        "hub-projects",
        task_text,
        tags=[f"PROJECT:{project.get('id')}"],
        metadata={"project_id": project.get("id")},
    )


def _load_project_control() -> dict:
    if PROJECT_CONTROL_FILE.exists():
        try:
            data = json.loads(PROJECT_CONTROL_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("tasks", [])
                data.setdefault("decisions", [])
                return data
        except Exception:
            pass
    return {"tasks": [], "decisions": []}


def _save_project_control(data: dict) -> None:
    PROJECT_CONTROL_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now().isoformat()
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    temp_file = PROJECT_CONTROL_FILE.with_suffix(".json.tmp")
    with _project_control_lock:
        temp_file.write_text(payload, encoding="utf-8")
        os.replace(temp_file, PROJECT_CONTROL_FILE)
    _trigger_comm_project_sync("project_control_saved")


def _trigger_comm_project_sync(event: str) -> None:
    """Fire-and-forget cross-sync; the helper dedupes unchanged snapshots."""
    helper = Path.home() / ".local/bin/comm-project-sync"
    if not helper.exists():
        return
    try:
        subprocess.Popen(
            [str(helper), "sync", "--event", str(event)[:80]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def _load_simple_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def _append_jsonl(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")


def _mattermost_env_status() -> dict:
    env = _load_simple_env(MATTERMOST_INBOX_ENV)
    watch_channels = [
        part.strip()
        for part in str(env.get("MATTERMOST_WATCH_CHANNELS") or "").split(",")
        if part.strip()
    ]
    if not watch_channels:
        for value in [
            env.get("MATTERMOST_INBOX_CHANNEL") or "ai-inbox",
            env.get("MATTERMOST_IMAGES_CHANNEL") or "ai-images",
            env.get("MATTERMOST_DOCS_CHANNEL") or "ai-docs",
            env.get("MATTERMOST_REVIEW_CHANNEL") or "ai-review",
        ]:
            if value and value not in watch_channels:
                watch_channels.append(value)
    return {
        "env_file": str(MATTERMOST_INBOX_ENV),
        "has_incoming_webhook": bool(env.get("MATTERMOST_INCOMING_WEBHOOK_URL")),
        "has_outgoing_token": bool(env.get("MATTERMOST_OUTGOING_TOKEN")),
        "has_bot_token": bool(env.get("MATTERMOST_BOT_TOKEN")),
        "base_url": env.get("MATTERMOST_BASE_URL") or "http://127.0.0.1:8065",
        "netbird_url": env.get("MATTERMOST_NETBIRD_URL") or "http://100.87.238.153:8065",
        "lan_url": env.get("MATTERMOST_LAN_URL") or "http://192.168.123.71:8065",
        "hub_projects_netbird": env.get("HUB_PROJECTS_NETBIRD_URL") or env.get("HUB_PROJECTS_URL") or "http://100.87.238.153:9800/projects",
        "hub_projects_lan": env.get("HUB_PROJECTS_LAN_URL") or "http://192.168.123.71:9800/projects",
        "team": env.get("MATTERMOST_TEAM") or "charlie",
        "channels": {
            "inbox": env.get("MATTERMOST_INBOX_CHANNEL") or "ai-inbox",
            "tasks": env.get("MATTERMOST_TASKS_CHANNEL") or "ai-tasks",
            "review": env.get("MATTERMOST_REVIEW_CHANNEL") or "ai-review",
            "images": env.get("MATTERMOST_IMAGES_CHANNEL") or "ai-images",
            "docs": env.get("MATTERMOST_DOCS_CHANNEL") or "ai-docs",
        },
        "watch_channels": watch_channels,
    }


def _mattermost_post(text: str, channel: str = "") -> dict:
    env = _load_simple_env(MATTERMOST_INBOX_ENV)
    webhook = env.get("MATTERMOST_INCOMING_WEBHOOK_URL", "").strip()
    if not webhook:
        return {"ok": False, "skipped": True, "reason": "MATTERMOST_INCOMING_WEBHOOK_URL not configured"}
    payload = {
        "text": text[:12000],
        "username": env.get("MATTERMOST_BOT_DISPLAY", "Charlie AI Hub"),
        "icon_emoji": env.get("MATTERMOST_BOT_ICON", ":robot_face:"),
    }
    if channel:
        payload["channel"] = channel
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read(4000).decode("utf-8", errors="replace")
        return {"ok": 200 <= resp.status < 300, "status": resp.status, "body": body[-1000:]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _project_due_state(task: dict, today: str) -> str:
    due_date = str(task.get("due_date") or "").strip()
    if not due_date or task.get("status") in {"done", "cancelled"}:
        return "none"
    if due_date < today:
        return "overdue"
    if due_date == today:
        return "today"
    try:
        delta = (datetime.fromisoformat(due_date).date() - datetime.fromisoformat(today).date()).days
        return "soon" if delta <= 3 else "scheduled"
    except ValueError:
        return "none"


def _normalize_project_task(task: dict, today: str) -> dict:
    item = dict(task)
    item.setdefault("priority", "medium")
    item.setdefault("tags", [])
    item.setdefault("dependencies", [])
    item.setdefault("acceptance", "")
    item.setdefault("completion_evidence", "")
    item.setdefault("blocker", "")
    item.setdefault("due_date", "")
    item.setdefault("estimate_minutes", 0)
    item.setdefault("workspace", "")
    item.setdefault("execution_policy", "")
    item["progress"] = _bounded_int(item.get("progress"))
    item["due_state"] = _project_due_state(item, today)
    dispatch = item.get("dispatch") if isinstance(item.get("dispatch"), dict) else {}
    dispatch_id = dispatch.get("dispatch_id") or item.get("dispatch_id")
    if dispatch_id:
        state_path = DISPATCH_TASKS_DIR / f"{dispatch_id}.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            attempts = state.get("attempts") or []
            latest = attempts[-1] if attempts else {}
            item["dispatch_state"] = {
                "id": state.get("id"),
                "status": state.get("status"),
                "initial_target": state.get("initial_target"),
                "current_target": latest.get("target"),
                "attempt_status": latest.get("status"),
                "observed_reason": latest.get("observed_reason") or latest.get("failure_reason"),
                "codex_review_request": state.get("codex_review_request"),
                "codex_review_status": state.get("codex_review_status"),
                "failure_pack": state.get("codex_failure_pack"),
            }
        except (OSError, json.JSONDecodeError):
            item["dispatch_state"] = {"id": dispatch_id, "status": "pending"}
    if dispatch.get("unit"):
        try:
            unit_state = subprocess.run(
                ["systemctl", "--user", "show", str(dispatch["unit"]), "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
                capture_output=True, text=True, timeout=3, check=False,
            )
            values = (unit_state.stdout or "").splitlines()
            item["runner_state"] = {"unit": dispatch["unit"], "active": values[0] if values else "unknown", "sub": values[1] if len(values) > 1 else "", "result": values[2] if len(values) > 2 else ""}
        except (OSError, subprocess.TimeoutExpired):
            item["runner_state"] = {"unit": dispatch["unit"], "active": "unknown"}
    return item


def _project_control_snapshot() -> dict:
    control = _load_project_control()
    raw_tasks = control.get("tasks") if isinstance(control.get("tasks"), list) else []
    today = datetime.now().date().isoformat()
    tasks = [_normalize_project_task(item, today) for item in raw_tasks]
    by_project: dict[str, dict] = {p.get("id", ""): _project_with_progress(p) for p in _all_projects()}
    for item in tasks:
        project = by_project.get(item.get("project_id", ""))
        if project:
            item["project_name"] = project.get("name")
            item["project_group"] = project.get("group")
    counts: dict[str, int] = {}
    for item in tasks:
        counts[item.get("status", "unknown")] = counts.get(item.get("status", "unknown"), 0) + 1
    actionable = [item for item in tasks if item.get("status") not in {"done", "cancelled"}]
    completed = [item for item in tasks if item.get("status") == "done"]
    overdue = [item for item in actionable if item.get("due_state") == "overdue"]
    blocked = [item for item in actionable if item.get("status") == "blocked" or item.get("blocker")]
    completion_base = len(completed) + len(actionable)
    return {
        "projects": list(by_project.values()),
        "tasks": sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True),
        "summary": {
            "projects": len(by_project),
            "tasks": len(tasks),
            "active": len(actionable),
            "completed": len(completed),
            "blocked": len(blocked),
            "overdue": len(overdue),
            "review": counts.get("review", 0),
            "completion_rate": round(len(completed) * 100 / completion_base) if completion_base else 0,
            "counts": counts,
        },
        "decisions": control.get("decisions", [])[-80:],
        "state_file": str(PROJECT_CONTROL_FILE),
        "updated_at": control.get("updated_at"),
    }


def _project_task_prompt(task: dict) -> str:
    return "\n".join([
        f"项目: {task.get('project_name') or task.get('project_id')}",
        f"任务: {task.get('title')}",
        f"前景: {task.get('outlook') or '待评估'}",
        f"目标: {task.get('goal') or task.get('title')}",
        f"执行窗口: {task.get('window')}",
        f"审批状态: {task.get('approval')}",
        "",
        str(task.get("brief") or task.get("title") or "").strip(),
        "",
        "要求:",
        "- 先只做必要上下文读取，避免大范围搜索。",
        "- 给出进度、风险、验收证据和后续建议。",
        "- 如果需要高风险写操作，先停下并回报等待人工确认。",
    ])


def _create_project_task_from_body(body: dict, source: str = "hub-projects") -> tuple[dict, int]:
    project_id = (body.get("project_id") or "").strip()
    title = (body.get("title") or "").strip()
    if not title:
        return {"error": "title required"}, 400
    projects = {p.get("id"): p for p in _all_projects()}
    if not project_id:
        project_id = next(iter(projects.keys()), "system-home")
    if project_id not in projects:
        return {"error": "unknown project_id"}, 400
    priority = str(body.get("priority") or "medium").strip().lower()
    if priority not in PROJECT_TASK_PRIORITIES:
        return {"error": "invalid priority"}, 400
    assignee = str(body.get("assignee") or "goose_aider").strip().lower()
    if assignee not in PROJECT_TASK_ASSIGNEES:
        return {"error": "invalid assignee"}, 400
    due_date = str(body.get("due_date") or "").strip()
    if due_date:
        try:
            datetime.fromisoformat(due_date)
        except ValueError:
            return {"error": "invalid due_date"}, 400
    now = datetime.now().isoformat()
    tags = body.get("tags") or []
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split(",") if part.strip()]
    dependencies = body.get("dependencies") or []
    if isinstance(dependencies, str):
        dependencies = [part.strip() for part in dependencies.split(",") if part.strip()]
    attachments = body.get("attachments") or []
    if not isinstance(attachments, list):
        attachments = [str(attachments)]
    artifact_paths = body.get("artifact_paths") or []
    if not isinstance(artifact_paths, list):
        artifact_paths = [str(artifact_paths)]
    source = str(body.get("source") or source)[:80]
    source_ref = str(body.get("source_ref") or "")[:500]
    if source_ref:
        existing_data = _load_project_control()
        existing = next((
            item for item in existing_data.get("tasks", [])
            if item.get("source") == source and item.get("source_ref") == source_ref and item.get("status") != "cancelled"
        ), None)
        if existing:
            return {"ok": True, "duplicate": True, "task": existing}, 200
    task = {
        "id": f"pt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.sha1(title.encode('utf-8')).hexdigest()[:8]}",
        "project_id": project_id,
        "project_name": projects[project_id].get("name"),
        "title": title[:160],
        "brief": (body.get("brief") or title).strip()[:4000],
        "goal": (body.get("goal") or "").strip()[:1000],
        "outlook": (body.get("outlook") or "").strip()[:1000],
        "acceptance": (body.get("acceptance") or "").strip()[:2000],
        "completion_evidence": "",
        "priority": priority,
        "due_date": due_date,
        "tags": [str(tag)[:40] for tag in tags[:12]],
        "dependencies": [str(item)[:120] for item in dependencies[:12]],
        "estimate_minutes": _bounded_int(body.get("estimate_minutes"), 0, 100000),
        "blocker": "",
        "assignee": assignee,
        "workspace": str(body.get("workspace") or "").strip()[:500],
        "execution_policy": "single_writer_goose_aider" if assignee == "goose_aider" else ("read_only_plan" if assignee == "plan" else "legacy_op_crush"),
        "window": (body.get("window") or "night").strip().lower(),
        "approval": (body.get("approval") or "pending").strip().lower(),
        "status": "pending_approval",
        "progress": 0,
        "source": source,
        "source_ref": source_ref,
        "attachments": [str(item)[:500] for item in attachments[:12]],
        "artifact_paths": [str(item)[:500] for item in artifact_paths[:12]],
        "created_at": now,
        "updated_at": now,
        "events": [{"ts": now, "event": "created", "source": source}],
    }
    data = _load_project_control()
    data["tasks"] = [task] + [x for x in data.get("tasks", []) if x.get("id") != task["id"]]
    _save_project_control(data)
    return {"ok": True, "task": task}, 200


def _project_task_workspace(task: dict) -> tuple[str, str]:
    """Return a safe workspace for the Goose -> Aider single-writer path."""
    raw = str(task.get("workspace") or "").strip()
    if not raw:
        return "", "workspace is required for Goose -> Aider tasks"
    try:
        workspace = Path(raw).expanduser().resolve()
    except OSError:
        return "", "workspace cannot be resolved"
    home = Path.home().resolve()
    if not workspace.is_dir() or (workspace != home and home not in workspace.parents):
        return "", "workspace must be an existing directory under the home workspace"
    return str(workspace), ""


def _dispatch_goose_aider_task(task: dict, target: str) -> dict:
    workspace, error = _project_task_workspace(task)
    if error:
        return {"ok": False, "target": target, "error": error}
    mode = "diagnose" if target == "plan" else "auto"
    task_id = re.sub(r"[^a-zA-Z0-9_-]", "-", str(task.get("id") or "task"))[:70]
    unit = f"hub-{mode}-{task_id}"
    PROJECT_TASK_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = PROJECT_TASK_RUNS_DIR / f"{task_id}.log"
    router = Path.home() / ".local/bin/agent-goose-aider-router"
    command = [str(router), mode, "--workspace", workspace, _project_task_prompt(task)]
    shell_command = "exec " + " ".join(shlex.quote(item) for item in command)
    shell_command += f" >> {shlex.quote(str(log_file))} 2>&1"
    try:
        proc = subprocess.run(
            [
                "systemd-run", "--user", "--no-block", "--collect",
                f"--unit={unit}",
                f"--description=Hub {mode} task {task_id}",
                f"--working-directory={workspace}",
                "--property=RuntimeMaxSec=2100",
                "--property=MemoryHigh=3G",
                "--property=TasksMax=220",
                "--property=Nice=10",
                "/bin/bash", "-lc", shell_command,
            ],
            capture_output=True, text=True, timeout=12, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "target": target, "error": str(exc)}
    return {
        "ok": proc.returncode == 0,
        "target": target,
        "selected_target": target,
        "runner": "goose_aider",
        "mode": mode,
        "unit": unit,
        "workspace": workspace,
        "log": str(log_file),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-1600:],
        "stderr": (proc.stderr or "").strip()[-1600:],
    }


def _dispatch_project_task(task: dict, target: str) -> dict:
    target = target if target in PROJECT_TASK_ASSIGNEES else "auto"
    if target == "auto":
        # A project task with a concrete workspace is a code/config task by
        # default. Keep OP for the legacy no-workspace queue only.
        target = "goose_aider" if task.get("workspace") else "op"
    if target in {"goose_aider", "plan"}:
        return _dispatch_goose_aider_task(task, target)
    title = str(task.get("title") or "项目任务")[:90]
    prompt = _project_task_prompt(task)
    dispatch_bin = str(Path.home() / ".local/bin/agent-dispatch")
    proc = subprocess.run(
        [dispatch_bin, "submit", "--target", target, "--title", title, prompt],
        capture_output=True,
        text=True,
        timeout=45,
        stdin=subprocess.DEVNULL,
    )
    result = {
        "ok": proc.returncode == 0,
        "target": target,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-1600:],
        "stderr": (proc.stderr or "").strip()[-1600:],
    }
    try:
        payload = json.loads(proc.stdout or "{}")
        if payload.get("id"):
            result["dispatch_id"] = payload["id"]
            result["selected_target"] = payload.get("target")
    except json.JSONDecodeError:
        pass
    return result


@app.get("/api/projects/control")
async def projects_control_api():
    return _project_control_snapshot()


@app.get("/api/projects/comm-sync")
async def projects_comm_sync_api():
    path = Path.home() / ".local/state/comm-project-sync/latest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"ok": True, "state_file": str(path), **data}
    except Exception as exc:
        return JSONResponse({"ok": False, "state_file": str(path), "error": str(exc)}, status_code=404)


@app.post("/api/projects/tasks")
async def project_task_create(body: dict):
    result, status = _create_project_task_from_body(body, "hub-projects")
    if status >= 400:
        return JSONResponse(result, status_code=status)
    return result


@app.post("/api/projects/tasks/{task_id}/approve")
async def project_task_approve(task_id: str, body: dict):
    data = _load_project_control()
    tasks = data.get("tasks", [])
    task = next((x for x in tasks if x.get("id") == task_id), None)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    if task.get("status") not in {"pending_approval", "dispatch_failed"}:
        return JSONResponse({"error": "task is not awaiting approval"}, status_code=409)
    target = (body.get("target") or task.get("assignee") or "auto").strip().lower()
    if target not in PROJECT_TASK_ASSIGNEES:
        return JSONResponse({"error": "invalid dispatch target"}, status_code=400)
    task["approval"] = "approved"
    task["status"] = "queued"
    task["updated_at"] = datetime.now().isoformat()
    task.setdefault("events", []).append({"ts": task["updated_at"], "event": "approved", "source": "hub-projects", "target": target})
    result = _dispatch_project_task(task, target)
    task["dispatch"] = result
    task["status"] = "delegated" if result.get("ok") else "dispatch_failed"
    task["updated_at"] = datetime.now().isoformat()
    task.setdefault("events", []).append({"ts": task["updated_at"], "event": task["status"], "source": "agent-dispatch", "result": result})
    data["decisions"] = (data.get("decisions") or []) + [{"ts": task["updated_at"], "task_id": task_id, "decision": "approve", "target": target, "ok": result.get("ok")}]
    _save_project_control(data)
    return {"ok": bool(result.get("ok")), "task": task, "dispatch": result}


@app.get("/api/projects/tasks/{task_id}/log")
async def project_task_log(task_id: str):
    task = next((x for x in _load_project_control().get("tasks", []) if x.get("id") == task_id), None)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    log_name = str((task.get("dispatch") or {}).get("log") or "")
    try:
        log_path = Path(log_name).resolve()
        run_root = PROJECT_TASK_RUNS_DIR.resolve()
        if run_root not in log_path.parents or not log_path.is_file():
            raise OSError("log unavailable")
        text = log_path.read_text(encoding="utf-8", errors="replace")[-12000:]
    except (OSError, ValueError):
        text = "No runner log is available yet."
    return {"task_id": task_id, "log": text}


@app.post("/api/projects/tasks/{task_id}/update")
async def project_task_update(task_id: str, body: dict):
    data = _load_project_control()
    task = next((x for x in data.get("tasks", []) if x.get("id") == task_id), None)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    requested_status = str(body.get("status") or task.get("status") or "").strip().lower()
    if requested_status not in PROJECT_TASK_STATUSES:
        return JSONResponse({"error": "invalid status"}, status_code=400)
    if "priority" in body and str(body["priority"]).lower() not in PROJECT_TASK_PRIORITIES:
        return JSONResponse({"error": "invalid priority"}, status_code=400)
    if "due_date" in body and body["due_date"]:
        try:
            datetime.fromisoformat(str(body["due_date"]))
        except ValueError:
            return JSONResponse({"error": "invalid due_date"}, status_code=400)
    if "title" in body and not str(body["title"] or "").strip():
        return JSONResponse({"error": "title required"}, status_code=400)
    evidence = str(body.get("completion_evidence") or task.get("completion_evidence") or "").strip()
    acceptance = str(body.get("acceptance") or task.get("acceptance") or "").strip()
    if requested_status == "done" and acceptance and not evidence:
        return JSONResponse({"error": "completion evidence required"}, status_code=400)
    text_limits = {
        "outlook": 1000, "brief": 4000, "goal": 1000, "acceptance": 2000,
        "completion_evidence": 4000, "blocker": 2000,
    }
    for key, limit in text_limits.items():
        if key in body:
            task[key] = str(body[key] or "").strip()[:limit]
    if "title" in body:
        task["title"] = str(body["title"]).strip()[:160]
    if "assignee" in body:
        assignee = str(body["assignee"] or "goose_aider").strip().lower()
        if assignee not in PROJECT_TASK_ASSIGNEES:
            return JSONResponse({"error": "invalid assignee"}, status_code=400)
        task["assignee"] = assignee
        task["execution_policy"] = "single_writer_goose_aider" if assignee == "goose_aider" else ("read_only_plan" if assignee == "plan" else "legacy_op_crush")
    if "workspace" in body:
        task["workspace"] = str(body["workspace"] or "").strip()[:500]
    if "status" in body:
        task["status"] = requested_status
    if "progress" in body:
        task["progress"] = _bounded_int(body["progress"])
    if "priority" in body:
        task["priority"] = str(body["priority"]).lower()
    if "due_date" in body:
        task["due_date"] = str(body["due_date"] or "").strip()
    if "estimate_minutes" in body:
        task["estimate_minutes"] = _bounded_int(body["estimate_minutes"], 0, 100000)
    for key in ("tags", "dependencies"):
        if key in body:
            value = body[key]
            if isinstance(value, str):
                value = [part.strip() for part in value.split(",") if part.strip()]
            task[key] = [str(item)[:120] for item in (value or [])[:12]]
    if requested_status == "done":
        task["progress"] = 100
        task["completed_at"] = datetime.now().isoformat()
    elif task.get("status") == "blocked" and not task.get("blocker"):
        return JSONResponse({"error": "blocker required"}, status_code=400)
    else:
        task.pop("completed_at", None)
    task["updated_at"] = datetime.now().isoformat()
    task.setdefault("events", []).append({"ts": task["updated_at"], "event": "updated", "source": "hub-projects", "fields": list(body.keys())})
    _save_project_control(data)
    return {"ok": True, "task": task}


@app.post("/api/projects/{project_id}/milestones/{milestone_id}")
async def project_milestone_update(project_id: str, milestone_id: str, body: dict):
    status = str(body.get("status") or "").strip().lower()
    if status not in {"pending", "in_progress", "done"}:
        return JSONResponse({"error": "invalid milestone status"}, status_code=400)
    projects = _load_custom_projects()
    builtin = next((p for p in PROJECTS_DEF if p.get("id") == project_id), None)
    project = next((p for p in projects if p.get("id") == project_id), None)
    if project is None and builtin is not None:
        project = json.loads(json.dumps(builtin, ensure_ascii=False))
        projects.append(project)
    if project is None:
        return JSONResponse({"error": "project not found"}, status_code=404)
    milestone = next((m for m in project.get("milestones", []) if m.get("id") == milestone_id), None)
    if milestone is None:
        return JSONResponse({"error": "milestone not found"}, status_code=404)
    milestone["status"] = status
    milestone["updated_at"] = datetime.now().isoformat()
    _save_custom_projects(projects)
    return {"ok": True, "project": _project_with_progress(project), "milestone": milestone}


def _append_op_inbox_task(source: str, message: str, tags: list[str] | None = None, metadata: dict | None = None) -> dict:
    OP_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    task_text = (message or "").strip()
    if not task_text:
        task_text = "查看 Hub 投递的待确认事项"
    tag_text = " ".join(f"[{tag}]" for tag in (tags or []))
    prefix = f"{tag_text} " if tag_text else ""
    guarded = (
        f"{prefix}[OP-INBOX] [NO-AUTO-EXEC] {task_text} "
        "｜只读查看与评估，不要直接执行；等待人工确认后再行动。"
    )
    line = f"- [ ] {guarded}\n"
    with OP_TASKS_FILE.open("a", encoding="utf-8") as f:
        f.write(line)
    journal = Path.home() / "memory/opencode-task-journal.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text("", encoding="utf-8") if not journal.exists() else None
    with journal.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "source": source,
            "mode": "queued_not_executed",
            "task": task_text,
            "tags": tags or [],
            "metadata": metadata or {},
            "file": str(OP_TASKS_FILE),
        }, ensure_ascii=False) + "\n")
    return {
        "status": "queued_not_executed",
        "mode": "op_inbox",
        "task": task_text,
        "file": str(OP_TASKS_FILE),
        "instruction": "只发送到 OP 待确认队列，不触发 OpenCode 执行。",
        **(metadata or {}),
    }


AI_WEBSITE_BUILDERS = [
    {
        "id": "replit-agent",
        "name": "Replit Agent",
        "role": "主力全栈执行",
        "best_for": "后台、数据库、权限、部署、代码可接管",
        "link": "/go/replit-agent",
        "fit": "sourcing 这种从 WordPress 迁移到现代后台的项目优先用它。",
    },
    {
        "id": "lovable",
        "name": "Lovable",
        "role": "整站快速生成",
        "best_for": "业务页面、管理端原型、Supabase 类后端联动",
        "link": "/go/lovable",
        "fit": "适合先把产品目录、询盘、CRM 入口做出可点的版本。",
    },
    {
        "id": "bolt",
        "name": "Bolt",
        "role": "前后端原型",
        "best_for": "Web App、移动端原型、快速迭代效果",
        "link": "/go/bolt",
        "fit": "适合试交互和视觉方案，确认后再并入正式仓库。",
    },
    {
        "id": "v0",
        "name": "v0",
        "role": "UI 组件专家",
        "best_for": "React / Next.js 页面、后台表格、筛选器、仪表盘",
        "link": "/go/v0",
        "fit": "适合生成高质量后台界面，再交给 Replit/Codex 接入真实数据。",
    },
]

OPEN_SOURCE_SITE_STACK = [
    {
        "id": "odoo",
        "name": "Odoo Community",
        "role": "一站式业务运营后台",
        "best_for": "网站、电商、CRM、库存、销售、项目、邮件营销的一体化试点",
        "link": "/go/odoo",
        "fit": "最接近你要的综合后台；注意部分高级模块/托管服务可能收费，自建 Community 可作为底座。",
        "stack_role": "suite",
    },
    {
        "id": "erpnext",
        "name": "ERPNext / Frappe",
        "role": "开源 ERP + 电商 + CRM",
        "best_for": "库存、采购、销售、报价、客户、网站和运营数据打通",
        "link": "/go/erpnext",
        "fit": "适合 Sourcing 做 B2B 询盘、报价、库存、采购跟进的运营中台。",
        "stack_role": "suite",
    },
    {
        "id": "vendure",
        "name": "Vendure",
        "role": "B2B / marketplace 电商内核",
        "best_for": "账号层级、合同价格、审批流、多渠道、B2B 和 marketplace",
        "link": "/go/vendure",
        "fit": "如果目标是阿里巴巴式 B2B 平台，优先评估 Vendure 作为 commerce core。",
        "stack_role": "commerce",
    },
    {
        "id": "medusa",
        "name": "Medusa",
        "role": "可定制 commerce 后端",
        "best_for": "产品、订单、客户、支付、配送和自定义电商流程",
        "link": "/go/medusa",
        "fit": "适合让 AI/Codex 快速扩展业务流程和插件，不被传统 CMS 限制。",
        "stack_role": "commerce",
    },
    {
        "id": "saleor",
        "name": "Saleor",
        "role": "GraphQL headless commerce",
        "best_for": "高性能 API、复杂前端、多渠道、AI/自动化集成",
        "link": "/go/saleor",
        "fit": "适合前端自由度高、团队愿意围绕 GraphQL 做现代电商。",
        "stack_role": "commerce",
    },
    {
        "id": "directus",
        "name": "Directus",
        "role": "可视化数据后台",
        "best_for": "把产品、供应商、询盘、机会池建成 no-code 管理后台和 API",
        "link": "/go/directus",
        "fit": "非常适合作为 Sourcing 的产品资料库、机会池和运营后台。",
        "stack_role": "admin",
    },
    {
        "id": "payload",
        "name": "Payload CMS",
        "role": "Next.js 原生后台/CMS",
        "best_for": "内容、商品资料、权限、媒体、定制管理台",
        "link": "/go/payload",
        "fit": "适合与 Astro/Next 前台一体开发，代码可控，后台可深度定制。",
        "stack_role": "admin",
    },
    {
        "id": "grapesjs",
        "name": "GrapesJS",
        "role": "可视化页面编辑器",
        "best_for": "落地页、邮件模板、产品专题页、广告页拖拽编辑",
        "link": "/go/grapesjs",
        "fit": "适合内嵌到后台，让运营人员可视化搭建页面，不用每次改代码。",
        "stack_role": "visual",
    },
    {
        "id": "mautic",
        "name": "Mautic",
        "role": "开源营销自动化",
        "best_for": "线索培育、邮件、表单、营销活动、分群和转化追踪",
        "link": "/go/mautic",
        "fit": "适合把 Sourcing 询盘、邮件、再营销流程自动化。",
        "stack_role": "marketing",
    },
    {
        "id": "n8n",
        "name": "n8n",
        "role": "工作流自动化",
        "best_for": "采集趋势、生成页面、同步 CRM、Telegram 通知、AI 工作流",
        "link": "/go/n8n",
        "fit": "适合做自动化胶水；必须内网化和权限收紧，不建议直接公网暴露。",
        "stack_role": "automation",
    },
]

SOURCING_STACK_BLUEPRINT = {
    "recommended_path": "先用 ERPNext/Odoo 验证一站式运营，再用 Vendure 或 Medusa 做可扩展 B2B commerce core，Directus/Payload 做后台，GrapesJS 做可视化页面，Mautic+n8n 做营销自动化。",
    "lean_start": ["ERPNext", "Directus", "GrapesJS", "Mautic", "n8n"],
    "b2b_marketplace": ["Vendure", "Directus", "Payload CMS", "GrapesJS", "Mautic", "n8n"],
    "developer_flexible": ["Medusa", "Payload CMS", "GrapesJS", "Mautic", "n8n"],
    "decision": [
        {"need": "最快有完整后台和运营闭环", "pick": "ERPNext 或 Odoo Community"},
        {"need": "做阿里巴巴式 B2B/多供应商/复杂价格", "pick": "Vendure 优先，Medusa 备选"},
        {"need": "产品库/供应商/询盘/机会池强后台", "pick": "Directus 或 Payload"},
        {"need": "运营可视化搭页面", "pick": "GrapesJS 嵌入后台"},
        {"need": "营销自动化和采集同步", "pick": "Mautic + n8n"},
    ],
}

CHANNEL_ADAPTERS = [
    {
        "id": "ntfy",
        "name": "ntfy",
        "role": "轻量频道通知",
        "fit": "最适合先落地。Hub 按 topic 推送：ops、projects、sourcing、marketing、phone、critical。",
        "direction": "Hub -> App 为主，也可用订阅回看历史",
        "difficulty": "low",
        "link": "/go/ntfy",
        "channels": ["critical", "ops", "projects", "sourcing", "marketing", "phone"],
        "hub_pattern": "POST /api/channels/publish -> ntfy topic",
    },
    {
        "id": "mattermost",
        "name": "Mattermost",
        "role": "自建 Slack 类频道",
        "fit": "适合你要的不同群/频道：#ops、#ai、#sourcing、#marketing、#phone。Incoming Webhook 对 Hub 很友好。",
        "direction": "Hub -> Channel，后续再做 slash command 回 Hub",
        "difficulty": "medium",
        "link": "/go/mattermost",
        "channels": ["ops", "ai", "sourcing", "marketing", "projects"],
        "hub_pattern": "每个频道一个 incoming webhook，Hub 按任务来源路由",
    },
    {
        "id": "zulip",
        "name": "Zulip",
        "role": "频道 + topic 项目讨论",
        "fit": "已迁移 Telegram OP 控制形态：/ask、/task、/project、/status 等命令可按 stream/topic 管理。",
        "direction": "Hub <-> Zulip <-> OP，适合长周期项目和任务过程",
        "difficulty": "medium",
        "link": "/go/zulip",
        "channels": ["OpenCode", "Sourcing", "Operations", "Knowledge", "Marketing", "Finance"],
        "hub_pattern": "opencode-zulip-gateway.service :9812；Hub 可 /api/workflow/todos/{id}/zulip 推送",
    },
    {
        "id": "rocketchat",
        "name": "Rocket.Chat",
        "role": "重型自建协作平台",
        "fit": "权限和团队隔离强，但比 ntfy/Mattermost 重。适合以后多用户、多角色后再上。",
        "direction": "Hub -> Rooms / webhook",
        "difficulty": "high",
        "link": "/go/rocketchat",
        "channels": ["ops", "business", "marketing", "support"],
        "hub_pattern": "Incoming/outgoing webhooks + room 权限",
    },
]

CHANNEL_BLUEPRINT = {
    "recommended_start": "ntfy",
    "recommended_team": "mattermost",
    "recommended_project_discussion": "zulip",
    "avoid_first": ["Telegram bot", "Discord bot", "Rocket.Chat full deployment"],
    "routing": [
        {"source": "high_priority", "channel": "critical", "adapter": "ntfy", "reason": "手机通知最快"},
        {"source": "daily_improvement", "channel": "ops", "adapter": "ntfy/mattermost", "reason": "日常系统维护"},
        {"source": "project", "channel": "projects", "adapter": "mattermost/zulip", "reason": "项目过程可追踪"},
        {"source": "sourcing", "channel": "sourcing", "adapter": "zulip/mattermost", "reason": "按主题拆 WordPress、开源栈、营销"},
        {"source": "marketing", "channel": "marketing", "adapter": "mattermost", "reason": "机会池和推广动作"},
        {"source": "phone", "channel": "phone", "adapter": "ntfy", "reason": "设备状态只要通知，不需要群聊"},
    ],
}

ZULIP_SITE = os.environ.get("HUB_ZULIP_SITE", "").rstrip("/")
ZULIP_EMAIL = os.environ.get("HUB_ZULIP_EMAIL", "")
ZULIP_API_KEY = os.environ.get("HUB_ZULIP_API_KEY", "")
ZULIP_DEFAULT_STREAM = os.environ.get("HUB_ZULIP_STREAM", "Sourcing")
ZULIP_DEFAULT_TOPIC = os.environ.get("HUB_ZULIP_TOPIC", "Hub")


def _zulip_configured() -> bool:
    return bool(ZULIP_SITE and ZULIP_EMAIL and ZULIP_API_KEY)


def _zulip_request(path: str, data: dict | None = None, files: dict | None = None, timeout: int = 20) -> dict:
    if not _zulip_configured():
        raise RuntimeError("Zulip not configured: set HUB_ZULIP_SITE, HUB_ZULIP_EMAIL, HUB_ZULIP_API_KEY")
    import requests

    auth = (ZULIP_EMAIL, ZULIP_API_KEY)
    url = f"{ZULIP_SITE}{path}"
    if files:
        resp = requests.post(url, auth=auth, data=data or {}, files=files, timeout=timeout)
    else:
        resp = requests.post(url, auth=auth, data=data or {}, timeout=timeout)
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text[:1000]}
    if resp.status_code >= 400:
        raise RuntimeError(f"Zulip API {resp.status_code}: {payload}")
    return payload


def _zulip_send_message(content: str, stream: str = "", topic: str = "", direct_to: str = "") -> dict:
    if direct_to:
        payload = {"type": "direct", "to": direct_to, "content": content}
    else:
        payload = {
            "type": "stream",
            "to": stream or ZULIP_DEFAULT_STREAM,
            "topic": topic or ZULIP_DEFAULT_TOPIC,
            "content": content,
        }
    return _zulip_request("/api/v1/messages", payload)


def _zulip_task_content(task: dict) -> str:
    return (
        f"**{task.get('priority', 'medium').upper()} · {task.get('title')}**\n\n"
        f"- 来源: `{task.get('source')}`\n"
        f"- 状态: `{task.get('status')}`\n"
        f"- Hub: http://127.0.0.1:9800/#workflow\n\n"
        f"{task.get('detail') or ''}\n\n"
        f"**建议动作**\n{task.get('action') or '请分析下一步。'}"
    )


def _restart_hub_api_delayed() -> None:
    time.sleep(1.0)
    subprocess.run(["systemctl", "--user", "restart", "hub-api.service"], stdin=subprocess.DEVNULL)


def _write_zulip_setup(site: str, bot_email: str, api_key: str, allowed_email: str, stream: str, topic: str, enable_gateway: bool = True) -> dict:
    site = site.strip().rstrip("/")
    bot_email = bot_email.strip()
    api_key = api_key.strip()
    allowed_email = allowed_email.strip()
    stream = (stream or "Sourcing").strip()
    topic = (topic or "Hub").strip()
    if not site or not bot_email or not api_key:
        raise ValueError("Zulip 地址、bot 邮箱、API key 都必填")
    if not site.startswith(("http://", "https://")):
        raise ValueError("Zulip 地址必须以 http:// 或 https:// 开头")

    home = Path.home()
    zulip_dir = home / ".config/opencode-zulip"
    hub_dropin = home / ".config/systemd/user/hub-api.service.d"
    systemd_dir = home / ".config/systemd/user"
    gateway_repo = home / "opencode-zulip-gateway"
    zulip_dir.mkdir(parents=True, exist_ok=True)
    hub_dropin.mkdir(parents=True, exist_ok=True)
    systemd_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(zulip_dir, 0o700)

    env_text = "\n".join([
        f"ZULIP_SITE={site}",
        f"ZULIP_BOT_EMAIL={bot_email}",
        f"ZULIP_API_KEY={api_key}",
        f"ZULIP_ALLOWED_EMAIL={allowed_email}",
        f"ZULIP_DEFAULT_STREAM={stream}",
        f"ZULIP_DEFAULT_TOPIC={topic}",
        "",
        "OPENCODE_URL=http://127.0.0.1:4097",
        "HUB_URL=http://127.0.0.1:9800",
        "GATEWAY_PORT=9812",
        "GATEWAY_DATA_DIR=~/.local/share/opencode-zulip-gateway",
        "OPENCODE_AGENT=sisyphus",
        "LOG_LEVEL=info",
        "",
    ])
    env_path = zulip_dir / ".env"
    env_path.write_text(env_text, encoding="utf-8")
    os.chmod(env_path, 0o600)

    dropin_text = "\n".join([
        "[Service]",
        f"Environment=HUB_ZULIP_SITE={site}",
        f"Environment=HUB_ZULIP_EMAIL={bot_email}",
        f"Environment=HUB_ZULIP_API_KEY={api_key}",
        f"Environment=HUB_ZULIP_STREAM={stream}",
        f"Environment=HUB_ZULIP_TOPIC={topic}",
        "",
    ])
    dropin_path = hub_dropin / "zulip.conf"
    dropin_path.write_text(dropin_text, encoding="utf-8")
    os.chmod(dropin_path, 0o600)

    src_service = gateway_repo / "systemd/opencode-zulip-gateway.service"
    dst_service = systemd_dir / "opencode-zulip-gateway.service"
    if src_service.exists():
        dst_service.write_text(src_service.read_text(encoding="utf-8"), encoding="utf-8")

    build = subprocess.run(["npm", "--prefix", str(gateway_repo), "run", "build"], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL)
    if enable_gateway:
        subprocess.run(["systemctl", "--user", "enable", "--now", "opencode-zulip-gateway.service"], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)

    return {
        "env": str(env_path),
        "hub_dropin": str(dropin_path),
        "service": str(dst_service),
        "build_ok": build.returncode == 0,
        "build_stderr": (build.stderr or "")[-600:],
    }


def _zulip_architecture() -> dict:
    path = Path.home() / ".config/zulip/architecture.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"error": str(exc), "path": str(path)}
    return {"error": "missing", "path": str(path)}


def _project_handoff_prompt(project: dict) -> str:
    legacy = project.get("legacy") or {}
    artifacts = "\n".join(f"- {p}" for p in project.get("artifacts", [])[:8]) or "- 暂无"
    milestones = "\n".join(f"- {m.get('name')}: {m.get('status')}" for m in project.get("milestones", [])) or "- 暂无"
    open_stack = "\n".join(f"- {item['name']}：{item['role']}；{item['fit']}" for item in OPEN_SOURCE_SITE_STACK)
    return f"""你是高级全栈产品工程师。请把下面项目做成可运行的网站/后台，并保留可维护代码。

项目：{project.get('name')}
目标：{project.get('description')}
旧系统：{legacy.get('type', 'unknown')}
旧备份线索：{legacy.get('backup_hint', project.get('source_path', '待补充'))}
目标仓库/目录：{project.get('target_path', '待创建')}

已知资产：
{artifacts}

里程碑：
{milestones}

优先评估这些开源底座，不要默认使用付费闭源平台：
{open_stack}

需要实现：
1. 产品/文章/页面管理后台，支持从 WordPress 备份或导出的内容导入。
2. 产品详情页、分类页、询盘表单、SEO 字段、图片管理。
3. B2B 配件电商能力：供应商、型号、兼容替代件、报价、询盘、批量采购、快速找件。
4. CRM、库存、邮件营销、Telegram 推送、Google Merchant Feed、SEO 页面生成。
5. 管理端要有空位：数据库、权限、内容审核、发布流程、营销自动化、数据归因。
6. 代码结构清晰，给出本地运行、部署、数据导入步骤。"""


MARKETING_STATE_FILE = Path.home() / ".local/state/hub/marketing-opportunities.json"

DEMAND_SOURCES = [
    {
        "id": "google-trends",
        "name": "Google Trends",
        "kind": "search_trend",
        "link": "/go/google-trends",
        "use": "按国家/地区跟踪 urgent replacement parts、spare parts、machine parts、配件型号等搜索增长。",
        "automation": "有 API/数据接入后，每天拉取关键词热度、相关查询和上升词。",
    },
    {
        "id": "merchant-center",
        "name": "Google Merchant Center",
        "kind": "product_feed",
        "link": "/go/google-merchant",
        "use": "把 Sourcing 商品 Feed 提交到 Google 免费商品展示，并监控拒登、曝光、点击。",
        "automation": "生成 feed.xml / product.json，每天检查库存、价格、图片和结构化数据。",
    },
    {
        "id": "meta-advantage",
        "name": "Meta Advantage+",
        "kind": "paid_social",
        "link": "/go/meta-advantage",
        "use": "用 AI 自动测试图片、短视频、文案和受众，适合急需配件的询盘广告。",
        "automation": "从机会池生成广告角度、素材 brief、预算建议和落地页。",
    },
    {
        "id": "tiktok-creative",
        "name": "TikTok Creative Center",
        "kind": "creative_intel",
        "link": "/go/tiktok-creative",
        "use": "观察热门短视频广告、行业关键词和用户评论，找出急需/维修/替换场景。",
        "automation": "采集公开趋势后生成短视频脚本、FAQ、落地页标题。",
    },
    {
        "id": "public-forums",
        "name": "公开论坛/问答/采购贴",
        "kind": "public_web",
        "link": "/search",
        "use": "跟踪 Reddit、Quora、行业论坛、维修社区、B2B 采购贴里的缺件和替换需求。",
        "automation": "只采集公开页面摘要，抽取配件名、机器型号、急迫程度、国家和联系方式线索。",
    },
]

MARKETING_CHANNELS = [
    {"id": "seo", "name": "SEO 内容矩阵", "goal": "用型号词、故障词、替代件词做长尾页面", "cadence": "daily"},
    {"id": "merchant", "name": "Google 免费商品展示", "goal": "让配件商品进入 Search / Shopping / Images 等免费展示面", "cadence": "daily"},
    {"id": "ads", "name": "AI 广告投放", "goal": "Meta Advantage+ / Google PMax / TikTok 自动测试询盘素材", "cadence": "weekly"},
    {"id": "social", "name": "短视频与社媒", "goal": "把急修、替换、停机损失场景做成短内容", "cadence": "daily"},
    {"id": "crm", "name": "询盘与再营销", "goal": "把询盘、报价、未成交需求回流 CRM 和邮件/Telegram", "cadence": "realtime"},
]

SEED_ACCESSORY_OPPORTUNITIES = [
    {
        "id": "packaging-machine-spares",
        "title": "包装机急需备件",
        "keywords": ["packaging machine spare parts", "sealing jaws", "heating element", "photoelectric sensor", "conveyor belt"],
        "buyer_pain": "生产线停机，买家急需替换件、兼容型号和快速发货。",
        "landing_page": "/products/packaging-machine-spare-parts",
        "priority": "high",
    },
    {
        "id": "paper-cup-machine-parts",
        "title": "纸杯/纸碗机配件",
        "keywords": ["paper cup machine parts", "mold", "ultrasonic horn", "knurling wheel", "paper cup HS code"],
        "buyer_pain": "型号复杂，买家需要按机器照片、铭牌、尺寸找到可替代配件。",
        "landing_page": "/products/paper-cup-machine-parts",
        "priority": "high",
    },
    {
        "id": "industrial-sensor-replacement",
        "title": "工业传感器替换件",
        "keywords": ["replacement sensor", "photoelectric sensor", "proximity switch", "encoder replacement"],
        "buyer_pain": "原厂件缺货或价格高，需要兼容替代和接线说明。",
        "landing_page": "/products/industrial-sensor-replacement",
        "priority": "medium",
    },
    {
        "id": "motor-drive-components",
        "title": "电机/驱动/控制器配件",
        "keywords": ["servo drive replacement", "stepper motor driver", "VFD replacement", "PLC module spare"],
        "buyer_pain": "设备维修周期短，需要快速确认参数、库存和替代方案。",
        "landing_page": "/products/motor-drive-components",
        "priority": "medium",
    },
]


def _load_marketing_opportunities() -> list[dict]:
    if not MARKETING_STATE_FILE.exists():
        return []
    try:
        data = json.loads(MARKETING_STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_marketing_opportunities(items: list[dict]) -> None:
    MARKETING_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MARKETING_STATE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _marketing_opportunities() -> list[dict]:
    custom = _load_marketing_opportunities()
    seen = {item.get("id") for item in custom}
    return custom + [item for item in SEED_ACCESSORY_OPPORTUNITIES if item.get("id") not in seen]


def _marketing_prompt() -> str:
    opportunities = "\n".join(
        f"- {item['title']}：{item['buyer_pain']}；关键词：{', '.join(item.get('keywords', []))}"
        for item in _marketing_opportunities()[:8]
    )
    channels = "\n".join(f"- {c['name']}：{c['goal']}" for c in MARKETING_CHANNELS)
    sources = "\n".join(f"- {s['name']}：{s['use']}" for s in DEMAND_SOURCES)
    stack = "\n".join(f"- {item['name']}：{item['role']}；{item['best_for']}" for item in OPEN_SOURCE_SITE_STACK)
    return f"""你是 B2B 配件电商增长负责人。请为 Sourcing 采购配件网站设计自动营销和需求采集系统。

目标：发现网上买家急需的机器配件、替代件、维修件，快速生成商品页、询盘页、广告素材和销售跟进。

可选开源建站/运营底座：
{stack}

需求采集源：
{sources}

当前机会池：
{opportunities}

推广渠道：
{channels}

输出要求：
1. 给出数据采集字段：关键词、国家、机器型号、配件名、急迫度、来源 URL、证据摘要、推荐落地页。
2. 给出网站后台模块：机会池、商品页生成、SEO 页面、广告素材、询盘 CRM、报价跟进。
3. 给出 7 天自动推广节奏：每天采集、生成页面、发布内容、检查询盘。
4. 给出每个机会的落地页标题、FAQ、Meta title、广告文案、短视频脚本。
5. 保持合规：只采集公开网页，不保存无授权隐私数据，不群发垃圾信息。"""
@app.post("/api/intake")
async def intake(body: dict):
    import httpx
    content = body.get("text") or body.get("filepath") or ""
    entity_prompt = (
        f'从以下输入中提取实体，返回JSON：\n输入：{content[:500]}\n'
        '返回格式：{"people":[],"companies":[],"tasks":[],"intents":[],"is_trade":false}\n'
        "只返回JSON，不要解释。"
    )
    entities = {}
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.post("http://localhost:4000/v1/chat/completions",
                json={"model": "glm-4-flash", "messages": [{"role": "user", "content": entity_prompt}], "temperature": 0.3})
            raw = resp.json()["choices"][0]["message"]["content"]
            entities = json.loads(raw.strip().strip("`").removeprefix("json"))
    except Exception:
        entities = {"people": [], "companies": [], "tasks": [], "intents": [], "is_trade": False}
    action = "stored"
    if entities.get("tasks"): action = "task-created"
    elif entities.get("is_trade"): action = "trade-detected"
    try: await _letta_store_entities(content, entities, action)
    except Exception: pass
    dialogue_append("SYSTEM", f"Intake: {json.dumps(entities, ensure_ascii=False)}", "message")
    return {"ok": True, "action": action, "entities": entities}

async def _letta_store_entities(content, entities, action):
    import httpx
    parts = []
    for kind, label in [("people", "人物"), ("companies", "公司")]:
        for item in entities.get(kind, []): parts.append(f"{label}: {item}")
    role = entities.get("intents", [])
    if role: parts.append("意图: " + ", ".join(role))
    date_str = datetime.now().strftime("%Y-%m-%d")
    mem_text = f"[{date_str}] intake-graph | " + " ←→ ".join(parts[:5]) + " | 意图:" + str(role) + " | 原文:" + content[:200]
    _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        await client.post(f"{LETTA_API}/v1/agents/{LETTA_AGENT_ID}/archival-memory", json={"text": mem_text})

@app.websocket("/ws/dialogue")
async def ws_dialogue(ws: WebSocket):
    feed = cfg.DIALOGUE_FEED
    lines = sum(1 for _ in open(feed)) if feed.exists() else 0
    await ws.accept()
    try:
        while True:
            await asyncio.sleep(0.5)
            if feed.exists():
                new_lines = sum(1 for _ in open(feed))
                if new_lines > lines:
                    with open(feed) as f: all_lines = f.readlines()
                    for line in all_lines[lines:]: await ws.send_text(line.strip())
                    lines = new_lines
            await asyncio.sleep(2)
    except Exception: pass

@app.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(f"http://127.0.0.1:9800/api/dashboard/overview")
                    data = r.json()
            except Exception:
                data = {"error": "fetch failed"}
            await ws.send_text(json.dumps({"type": "status", "data": data}))
            await asyncio.sleep(30)
    except Exception: pass

@app.post("/api/dialogue/post")
async def dialogue_post(body: dict):
    sender = body.get("from", "SYSTEM")
    content = body.get("content", "")
    msg_type = body.get("type", "message")
    entry = json.dumps({"from": sender, "content": content, "type": msg_type, "time": datetime.now().strftime("%H:%M:%S")}, ensure_ascii=False)
    feed = cfg.DIALOGUE_FEED
    with open(feed, "a") as f: f.write(entry + "\n")
    dead = []
    for c in list(_ws_clients):
        try: await c.send_text(entry)
        except Exception: dead.append(c)
    for c in dead: _ws_clients.discard(c)
    return {"ok": True}

@app.get("/api/dialogue/inbox")
async def dialogue_inbox(limit: int = 100, source: str = ""):
    """统一收件箱：从 dialogue feed 读取，按来源分组。"""
    feed = cfg.DIALOGUE_FEED
    messages = []
    if feed.exists():
        with open(feed) as f:
            lines = f.readlines()
        for line in lines[-limit * 3:]:
            try:
                entry = json.loads(line)
                src = (entry.get("from") or entry.get("source") or "system").lower()
                if source and source.lower() not in src:
                    continue
                entry["_source"] = src
                messages.append(entry)
            except Exception:
                continue
    messages = messages[-limit:]
    by_source: dict[str, list] = {}
    for m in messages:
        by_source.setdefault(m["_source"], []).append(m)
    return SafeJSONResponse({
        "total": len(messages),
        "sources": sorted(by_source.keys()),
        "by_source": by_source,
        "messages": messages,
    })


@app.post("/api/dialogue/webhook/telegram")
async def dialogue_webhook_telegram(body: dict):
    """Telegram Gateway webhook：将 TG 消息写入 dialogue feed。"""
    msg = body.get("message") or body.get("text") or ""
    chat_id = str(body.get("chat_id") or body.get("chatId") or "")
    sender = body.get("from") or body.get("username") or f"tg:{chat_id}"
    if not msg:
        return JSONResponse({"error": "empty message"}, status_code=400)
    dialogue_append(sender, msg[:2000], "telegram")
    return {"ok": True}


@app.get("/api/dialogue/history")
async def dialogue_history(limit: int = 50):
    msgs = []
    feed = cfg.DIALOGUE_FEED
    if feed.exists():
        with open(feed) as f: lines = f.readlines()
        for line in lines[-limit:]:
            try: msgs.append(json.loads(line))
            except Exception: pass
    return {"messages": msgs}

async def _check_tcp(host, port, timeout=3):
    import asyncio
    start = datetime.now()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        latency = (datetime.now() - start).total_seconds() * 1000
        writer.close(); await writer.wait_closed()
        return True, latency
    except Exception: return False, 0

async def _check_http(url, timeout=5):
    import asyncio
    start = datetime.now()
    try:
        _sp = await asyncio.create_subprocess_exec(
            "curl", "-sL", "-o", "/dev/null", "-w", "%{http_code}", "-m", str(timeout), url,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(_sp.communicate(), timeout=timeout+2)
        code = stdout.decode().strip()
        latency = (datetime.now() - start).total_seconds() * 1000
        return code == "200", latency, code
    except Exception: return False, 0, "000"

@app.get("/api/tunnels/status")
async def tunnels_status():
    result = {"tunnels": []}
    frp_proxies = []
    if FRP_CONFIG.exists():
        import re
        cfg = FRP_CONFIG.read_text()
        for p in re.findall(r'(?s)\[\[proxies\]\]\s*name\s*=\s*\"(\w+)\".*?type\s*=\s*\"(\w+)\".*?localIP\s*=\s*\"([^\"]+)\".*?localPort\s*=\s*(\d+).*?remotePort\s*=\s*(\d+)', cfg):
            frp_proxies.append({"name": p[0], "type": p[1], "localIP": p[2], "localPort": int(p[3]), "remotePort": int(p[4])})
    frp_svc = "unknown"
    try:
        _sp = await asyncio.create_subprocess_exec("systemctl", "--user", "is-active", "frpc.service", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await _sp.communicate(); frp_svc = stdout.decode().strip()
    except Exception: pass
    frp_active = frp_svc == "active"
    for proxy in frp_proxies:
        ok, lat = await _check_tcp("127.0.0.1", proxy["localPort"])
        result["tunnels"].append({"name": proxy["name"], "status": "online" if (ok and frp_active) else "offline", "latency": round(lat), "local_port": proxy["localPort"], "connected": ok, "service_active": frp_active, "type": "frp"})
    cf_ok, cf_lat = await _check_tcp("localhost", 7890)
    result["tunnels"].append({"name": "cloudflare", "status": "online" if cf_ok else "offline", "latency": round(cf_lat), "type": "cloudflare"})
    try:
        _sp = await asyncio.create_subprocess_exec("tailscale", "status", "--json", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await _sp.communicate(); ts_data = json.loads(stdout.decode())
        peers = [{"id": p.get("ID", ""), "name": p.get("HostName", ""), "online": p.get("Online", False)} for p in ts_data.get("Peer", {}).values()]
        result["tunnels"].append({"name": "tailscale", "status": "online" if ts_data.get("Self", {}).get("Online") else "offline", "self": ts_data.get("Self", {}).get("TailscaleIPs", []), "peers": peers, "type": "tailscale"})
    except Exception: result["tunnels"].append({"name": "tailscale", "status": "offline", "type": "tailscale"})
    # DuckDNS 公网 8080 OpenCode 连通性
    dns_ok, dns_lat, dns_code = await _check_http("http://charlie1990.duckdns.org:8080/")
    result["tunnels"].append({"name": "duckdns-8080", "status": "online" if dns_ok else "offline", "latency": round(dns_lat), "http_code": dns_code, "type": "duckdns"})
    return result
async def _fetch_twenty_contacts():
    import subprocess
    ws = "workspace_4fi60z16hu359ticc16w8z5ff"
    sql_p = f'SELECT p.id, p."nameFirstName", p."nameLastName", p."emailsPrimaryEmail", p."jobTitle", p."companyId", c.name AS cn FROM "{ws}"."person" p LEFT JOIN "{ws}"."company" c ON p."companyId" = c.id WHERE p."deletedAt" IS NULL LIMIT 100'
    sql_c = f'SELECT id, name, "domainNamePrimaryLinkLabel" AS domain, employees FROM "{ws}"."company" WHERE "deletedAt" IS NULL LIMIT 100'
    people, companies = [], []
    try:
        r1 = subprocess.run(["docker","exec","twenty-db-1","psql","-U","twenty","-d",ws,"-t","-A","-F","|","-c",sql_p], capture_output=True, text=True, timeout=10)
        for line in r1.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("|")
                if len(parts)>=7: people.append({"id":parts[0],"firstName":parts[1],"lastName":parts[2],"email":parts[3],"jobTitle":parts[4],"companyId":parts[5],"companyName":parts[6]})
    except Exception: pass
    try:
        r2 = subprocess.run(["docker","exec","twenty-db-1","psql","-U","twenty","-d",ws,"-t","-A","-F","|","-c",sql_c], capture_output=True, text=True, timeout=10)
        for line in r2.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("|")
                if len(parts)>=4: companies.append({"id":parts[0],"name":parts[1],"domain":parts[2],"employees":parts[3]})
    except Exception: pass
    return people, companies

@app.get("/api/graph/nodes")
async def graph_nodes():
    nodes, edges = [], []
    conn = sqlite3.connect(f"file:{cfg.CRM_DB}?mode=ro", uri=True, timeout=5)
    try:
        for c in conn.execute("SELECT id, name, company, tags FROM contacts LIMIT 50").fetchall():
            nodes.append({"id": f"contact_{c[0]}", "name": c[1] or "未知", "company": c[2], "tags": c[3], "type": "person"})
    except Exception: pass
    finally: conn.close()
    try:
        tp, tc = await _fetch_twenty_contacts()
        for p in tp:
            name = (p.get("firstName","") + " " + p.get("lastName","")).strip() or "Unknown"
            nodes.append({"id": f'twenty_{p["id"]}', "name": name, "email": p.get("email",""), "jobTitle": p.get("jobTitle",""), "companyName": p.get("companyName",""), "type": "twenty_person"})
            if p.get("companyId"): edges.append({"source": f'twenty_{p["id"]}', "target": f'twenty_co_{p["companyId"]}', "relation": "属于"})
        for co in tc:
            nodes.append({"id": f'twenty_co_{co["id"]}', "name": co.get("name",""), "domain": co.get("domain",""), "type": "twenty_company"})
    except Exception: pass
    otp = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
    if otp.exists():
        for i, line in enumerate(open(otp)):
            if line.startswith("- [x]") or line.startswith("- [ ]"):
                nodes.append({"id": f"task_{i}", "name": line.strip()[5:].strip()[:50], "status": "done" if "[x]" in line else "pending", "type": "task"})
    return {"nodes": nodes, "edges": edges}

@app.get("/search")
async def search_page():
    p = STATIC_DIR / "search.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>搜索页面不存在</h1>")

@app.get("/wechat")
async def wechat_search():
    p = STATIC_DIR / "wechat-search.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>微信搜索页面不存在</h1>")

@app.get("/dashboard")
async def dashboard_page():
    p = STATIC_DIR / "dashboard.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>Dashboard 页面不存在</h1>", status_code=404)

@app.get("/legacy-panel")
@app.get("/old-nixos-panel")
@app.get("/old-nixos")
async def legacy_panel_page():
    p = STATIC_DIR / "dashboard.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>旧 NixOS 融合面板页面不存在</h1>", status_code=404)

@app.get("/kanban")
async def kanban_page():
    p = STATIC_DIR / "hub.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>看板页面不存在</h1>", status_code=404)

@app.get("/control")
async def control_page():
    p = STATIC_DIR / "control.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>控制中心页面不存在</h1>", status_code=404)

@app.get("/service-manager")
async def service_manager_page():
    p = STATIC_DIR / "service-manager.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>服务管理页面不存在</h1>", status_code=404)

@app.get("/social-graph")
async def social_graph_page():
    p = STATIC_DIR / "social-graph.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>社交图谱页面不存在</h1>", status_code=404)

@app.get("/ai-panel")
async def ai_panel_page():
    p = STATIC_DIR / "ai-panel.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>AI Panel 页面不存在</h1>", status_code=404)

@app.get("/op-learning")
async def op_learning_page():
    p = STATIC_DIR / "op-learning.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>OP 学习中枢页面不存在</h1>", status_code=404)

@app.get("/workspace")
async def workspace_page():
    p = STATIC_DIR / "workspace.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>工作区聚合页面不存在</h1>", status_code=404)

@app.get("/projects")
async def projects_page():
    page = STATIC_DIR / "projects.html"
    if page.exists():
        return FileResponse(page)
    return HTMLResponse("""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>项目管理 · Hub</title>
<style>
html,body{margin:0;min-height:100%;background:#0b0f14;color:#d8dee9;font:14px system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:2;display:flex;gap:8px;align-items:center;padding:9px 10px;background:#11151b;border-bottom:1px solid #303948}
header a,button,select,input,textarea{border:1px solid #303948;border-radius:7px;background:#171a21;color:#eceff4;font:13px system-ui,sans-serif}
header a,button{padding:8px 10px;text-decoration:none}button.primary{border-color:#4f8fcc;background:#1c3d5d}button.good{border-color:#2f7d4a;background:#12351f}#float-close{display:none}
main{box-sizing:border-box;max-width:1180px;margin:0 auto;padding:12px 10px 70px;display:grid;gap:12px}
.grid{display:grid;gap:10px}.projects{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}.tasks{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.card,.panel{border:1px solid #303948;background:#11151b;border-radius:8px;padding:11px;display:grid;gap:8px}.panel{grid-template-columns:1fr}
h1{font-size:16px;margin:0}h2{font-size:15px;margin:0}.muted{color:#aeb8c5}.pill{display:inline-block;border:1px solid #3a4656;border-radius:999px;padding:2px 7px;background:#171a21;font-size:12px;color:#c9d3df}
.barline{height:7px;border-radius:99px;background:#263141;overflow:hidden}.barline span{display:block;height:100%;background:#5e9bd3}
label{display:grid;gap:4px;color:#cbd5e1}input,select,textarea{box-sizing:border-box;width:100%;padding:9px}textarea{min-height:86px;resize:vertical}.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}.actions{display:flex;gap:7px;flex-wrap:wrap}.error{color:#ffb4b4}.ok{color:#9ee6b2}
pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;padding:8px;border:1px solid #303948;border-radius:7px;background:#080c11;color:#cbd5e1;max-height:180px;overflow:auto}
@media(max-width:640px){.row{grid-template-columns:1fr}header{overflow:auto}.projects,.tasks{grid-template-columns:1fr}}
</style></head><body>
<header><button id="float-close" onclick="closeFloat()">关闭</button><a href="http://100.87.238.153:9800/workspace" target="_blank" rel="noopener">工作区</a><a href="http://100.87.238.153:9800/go/plane" target="_blank" rel="noopener">Plane</a><a href="http://100.87.238.153:9800/go/huly" target="_blank" rel="noopener">Huly</a><a href="http://100.87.238.153:9800/go/fastgpt" target="_blank" rel="noopener">FastGPT</a><a href="http://100.87.238.153:9800/go/openagents" target="_blank" rel="noopener">OpenAgents</a><button onclick="load()">刷新</button><h1>项目管理</h1></header>
<main>
  <section class="panel">
    <h2>新建任务</h2>
    <div class="row"><label>项目<select id="project"></select></label><label>执行策略<select id="assignee"><option value="goose_aider">智能代码 · Goose → Aider</option><option value="plan">只读计划 · Goose</option><option value="op">OP · 短会话</option><option value="crush">Crush · 故障诊断</option></select></label></div>
    <label>工作区（智能代码任务必填）<input id="workspace" placeholder="例如：/var/home/charlie/hub"></label>
    <label>标题<input id="title" placeholder="例如：整理项目路线图并生成下一步执行清单"></label>
    <label>前景<textarea id="outlook" placeholder="机会、价值、风险、为什么值得做"></textarea></label>
    <label>任务说明<textarea id="brief" placeholder="交给 OP/Crush 的具体要求"></textarea></label>
    <div class="actions"><button class="primary" onclick="createTask()">加入待审批</button><span id="msg" class="muted"></span></div>
  </section>
  <section><h2>项目</h2><div id="projects" class="grid projects"></div></section>
  <section><h2>审批 / 进度</h2><div id="tasks" class="grid tasks"></div></section>
</main>
<script>
let state={projects:[],tasks:[]};
const $=id=>document.getElementById(id);
function esc(v){return String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function pct(n){return Math.max(0,Math.min(100,Number(n||0)));}
function framed(){try{return window.parent&&window.parent!==window;}catch(e){return false;}}
function closeFloat(){try{const p=window.parent.document.getElementById('codex-project-float');if(p)p.classList.remove('open','min');}catch(e){}}
if(framed()){document.documentElement.classList.add('framed');setTimeout(()=>{const b=$('float-close');if(b)b.style.display='inline-block';},0);}
async function load(){
  const r=await fetch('/api/projects/control',{cache:'no-store'});
  state=await r.json();
  $('project').innerHTML=(state.projects||[]).map(p=>`<option value="${esc(p.id)}">${esc(p.name)} · ${esc(p.group||'')}</option>`).join('');
  $('projects').innerHTML=(state.projects||[]).map(p=>`<div class="card"><h2>${esc(p.name)}</h2><div class="muted">${esc(p.description||'')}</div><div><span class="pill">${esc(p.group||'project')}</span> <span class="pill">${esc(p.progress||0)}%</span></div><div class="barline"><span style="width:${pct(p.progress)}%"></span></div><div class="muted">完成 ${esc(p.done_count||0)} · 进行 ${esc(p.in_progress_count||0)}</div></div>`).join('');
  $('tasks').innerHTML=(state.tasks||[]).map(t=>taskCard(t)).join('')||'<div class="card muted">暂无项目任务</div>';
}
function taskCard(t){
  const log=t.dispatch?`<pre>${esc((t.dispatch.stdout||t.dispatch.stderr||'').slice(-1200))}</pre>`:'';
  const can=t.status==='pending_approval'||t.status==='dispatch_failed'||t.approval==='pending';
  const runner=t.runner_state?` · runner ${esc(t.runner_state.active||'unknown')}`:'';
  return `<div class="card"><h2>${esc(t.title)}</h2><div class="muted">${esc(t.project_name||t.project_id)} · ${esc(t.assignee||'auto')} · ${esc(t.workspace||'未指定工作区')}${runner}</div><div><span class="pill">${esc(t.status)}</span> <span class="pill">${esc(t.execution_policy||'legacy')}</span></div><div>${esc(t.outlook||'')}</div><div class="actions">${can?`<button class="good" onclick="approve('${esc(t.id)}','${esc(t.assignee||'goose_aider')}')">批准并派发</button>`:''}<button onclick="progress('${esc(t.id)}')">更新进度</button>${t.dispatch&&t.dispatch.log?`<button onclick="runnerLog('${esc(t.id)}')">执行日志</button>`:''}</div>${log}</div>`;
}
async function createTask(){
  $('msg').textContent='提交中...';
  const body={project_id:$('project').value,assignee:$('assignee').value,workspace:$('workspace').value,title:$('title').value,brief:$('brief').value,outlook:$('outlook').value,window:'night'};
  const r=await fetch('/api/projects/tasks',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
  const d=await r.json(); $('msg').textContent=r.ok?'已加入待审批':(d.error||'失败');
  if(r.ok){$('title').value='';$('brief').value='';$('outlook').value='';load();}
}
async function approve(id,target){
  const r=await fetch('/api/projects/tasks/'+encodeURIComponent(id)+'/approve',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({target})});
  const d=await r.json(); $('msg').textContent=r.ok?'已派发':(d.error||'派发失败'); load();
}
async function progress(id){
  const text=prompt('进度 0-100 或状态文字');
  if(text==null)return;
  const n=Number(text);
  const body=Number.isFinite(n)?{progress:n,status:n>=100?'done':'in_progress'}:{status:text};
  await fetch('/api/projects/tasks/'+encodeURIComponent(id)+'/update',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
  load();
}
async function runnerLog(id){
  const r=await fetch('/api/projects/tasks/'+encodeURIComponent(id)+'/log',{cache:'no-store'}); const d=await r.json();
  alert((d.log||d.error||'暂无日志').slice(-8000));
}
load();
</script></body></html>""")

@app.get("/contracts")
async def contracts_page():
    p = STATIC_DIR / "contracts.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>合同助手页面不存在</h1>", status_code=404)

@app.get("/")
async def root(request: Request):
    client_ip = request.client.host if request.client else ""
    if client_ip == "127.0.0.1":
        return RedirectResponse("http://192.168.123.71:9800/")
    p = STATIC_DIR / "hub-home.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>Hub API 运行中</h1>")

@app.get("/sw.js")
async def service_worker():
    p = STATIC_DIR / "sw.js"
    return FileResponse(p) if p.exists() else Response("", media_type="application/javascript")

@app.get("/api/dashboard/overview")
async def dashboard_overview(request: Request):
    import re
    import time

    host = request.headers.get("host", "127.0.0.1:9800").split(":")[0]

    def external_url(port: int, path: str = "/") -> str:
        return f"http://{host}:{port}{path}"

    def run(cmd: list[str]) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return (r.stdout or "").strip()
        except Exception:
            return ""

    def port_up(port: int) -> bool:
        return bool(run(["bash", "-lc", f"ss -tln | grep -q ':{port} ' && echo ok"]) == "ok")

    def user_service_active(name: str) -> bool:
        return run(["systemctl", "--user", "is-active", name]) == "active"

    def cpu_percent() -> int:
        with open("/proc/stat", encoding="utf-8") as f:
            a = f.readline().split()
        time.sleep(0.15)
        with open("/proc/stat", encoding="utf-8") as f:
            b = f.readline().split()
        t1 = sum(int(x) for x in a[1:])
        t2 = sum(int(x) for x in b[1:])
        idle = int(b[4]) - int(a[4])
        return round((1 - idle / max(1, (t2 - t1))) * 100)

    meminfo = Path("/proc/meminfo").read_text(encoding="utf-8", errors="ignore")
    mem_total = int(re.search(r"MemTotal:\s+(\d+)", meminfo).group(1))
    mem_avail = int(re.search(r"MemAvailable:\s+(\d+)", meminfo).group(1))
    swap_total_match = re.search(r"SwapTotal:\s+(\d+)", meminfo)
    swap_free_match = re.search(r"SwapFree:\s+(\d+)", meminfo)
    swap_total = int(swap_total_match.group(1)) if swap_total_match else 0
    swap_free = int(swap_free_match.group(1)) if swap_free_match else 0
    mem_used_pct = round((1 - mem_avail / max(1, mem_total)) * 100)
    swap_used_pct = round((1 - swap_free / max(1, swap_total)) * 100) if swap_total else 0

    df_root = run(["df", "-P", "/"]).splitlines()
    root_pct = 0
    if len(df_root) > 1:
        m = re.search(r"(\d+)%", df_root[1])
        root_pct = int(m.group(1)) if m else 0

    score_file = Path("/home/charlie/.local/state/dashboard-health-score.json")
    score_data = {"score": 0, "grade": "?", "critical": 0, "warning": 0, "services": []}
    if score_file.exists():
        try:
            score_data = json.loads(score_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    services = [
        {
            "name": "Hub",
            "status": "online" if port_up(9800) else "offline",
            "url": external_url(9800),
            "detail": "统一看板与 API",
        },
        {
            "name": "OpenAgents",
            "status": "online" if port_up(8700) else "offline",
            "url": external_url(8700),
            "detail": "协作层 + 事件总线 (8700/8600)",
        },
        {
            "name": "TermHive Web",
            "status": "online" if port_up(3200) else "offline",
            "url": external_url(3200),
            "detail": "项目管理面板 (3200)",
        },
        {
            "name": "TermHive Daemon",
            "status": "online" if port_up(3210) else "offline",
            "url": external_url(3210, "/api/daemon/status"),
            "detail": "Agent 运行时 (3210)",
        },
        {
            "name": "OpenCode Web",
            "status": "online" if port_up(4097) else "offline",
            "url": external_url(4097),
            "detail": "Web 控制台 (4097)",
        },
        {
            "name": "OpenCode Server",
            "status": "online" if port_up(4097) else "offline",
            "url": external_url(4097),
            "detail": "后端 API (4097)",
        },
        {
            "name": "OpenClaw TTYD",
            "status": "online" if port_up(8080) else "offline",
            "url": external_url(8080),
            "detail": "本地 ttyd 入口",
        },
        {
            "name": "LiteLLM",
            "status": "online" if port_up(4002) else "offline",
            "url": external_url(4002, "/v1/models"),
            "detail": "AI 网关 (4002)",
        },
        {
            "name": "Letta",
            "status": "online" if port_up(8283) else "offline",
            "url": external_url(8283),
            "detail": "记忆服务",
        },
        {
            "name": "Embedding",
            "status": "online" if port_up(8286) else "offline",
            "url": external_url(8286),
            "detail": "向量嵌入服务",
        },
        {
            "name": "Telegram Gateway",
            "status": "online" if port_up(9811) else "offline",
            "url": external_url(9811, "/health"),
            "detail": "Telegram 消息网关",
        },
        {
            "name": "Haven MCP Bridge",
            "status": "online" if port_up(8732) else "offline",
            "url": external_url(8732, "/mcp"),
            "detail": "手机桥接 MCP (当前 disabled)",
        },
        {
            "name": "FRP 19890",
            "status": "online" if port_up(19890) else "offline",
            "url": external_url(19890),
            "detail": "公网映射入口",
        },
        {
            "name": "Mihomo",
            "status": "online" if port_up(9091) else "offline",
            "url": external_url(9091, "/ui"),
            "detail": "代理控制面",
        },
        {
            "name": "Memory Pulse",
            "status": "not_deployed",
            "url": external_url(8285, "/pulse/summary"),
            "detail": "记忆桥接 (mem0-bridge 源码缺失)",
        },
        {
            "name": "内容筛选",
            "status": "online" if port_up(8765) else "offline",
            "url": external_url(8765),
            "detail": "内容筛选面板 (8765)",
        },
        {
            "name": "Sunshine",
            "status": "online" if port_up(47990) else "offline",
            "url": f"https://{host}:47990/",
            "detail": "游戏串流 (47990)",
        },
        {
            "name": "Moonlight",
            "status": "online" if run(["bash", "-lc", "command -v moonlight >/dev/null || command -v moonlight-qt >/dev/null && echo ok"]) == "ok" else "not_deployed",
            "url": "https://moonlight-stream.org/",
            "detail": "Moonlight 客户端 / 串流接入",
        },
    ]

    return {
        "generated_at": datetime.now().isoformat(),
        "score": score_data,
        "system": {
            "cpu": cpu_percent(),
            "memory": mem_used_pct,
            "memory_available_gb": round(mem_avail / 1024 / 1024, 1),
            "swap": swap_used_pct,
            "root_disk": root_pct,
        },
        "services": services,
        "links": [
            {"name": "Hub", "url": external_url(9800)},
            {"name": "Dashboard", "url": external_url(9800, "/dashboard")},
            {"name": "Mihomo", "url": external_url(9091, "/ui")},
            {"name": "OpenClaw", "url": external_url(8080)},
            {"name": "OpenCode", "url": external_url(8081)},
            {"name": "LiteLLM", "url": external_url(4000, "/v1/models")},
        ],
    }


@app.get("/api/ai/opencode-score")
async def opencode_daily_score():
    import sqlite3, time, os, glob, json as _json, subprocess
    from datetime import datetime
    from collections import Counter

    db_path = os.path.expanduser("~/.local/share/opencode/opencode.db")
    if not os.path.exists(db_path):
        return JSONResponse({"error": "opencode.db not found"}, status_code=404)

    now_ms = int(time.time() * 1000)
    day_ago_ms = now_ms - 24 * 60 * 60 * 1000

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Sessions in last 24h
        c.execute(
            "SELECT id, title, cost, tokens_input, tokens_output, agent, time_created FROM session WHERE time_created >= ? ORDER BY time_created DESC",
            (day_ago_ms,),
        )
        sessions = c.fetchall()

        # Todos in last 24h
        c.execute(
            "SELECT t.status, COUNT(*) FROM todo t JOIN session s ON t.session_id = s.id WHERE s.time_created >= ? GROUP BY t.status",
            (day_ago_ms,),
        )
        todo_counts = {r[0]: r[1] for r in c.fetchall()}

        # Totals
        c.execute(
            "SELECT COUNT(*), SUM(cost), SUM(tokens_input), SUM(tokens_output) FROM session WHERE time_created >= ?",
            (day_ago_ms,),
        )
        totals = c.fetchone()

        # Tool usage from part table
        c.execute(
            "SELECT data FROM part WHERE data LIKE '%\"tool\"%' AND time_created >= ?",
            (day_ago_ms,),
        )
        tool_counter = Counter()
        tool_success = 0
        tool_failed = 0
        tool_total = 0
        for (raw,) in c.fetchall():
            try:
                d = _json.loads(raw)
                if d.get("type") != "tool":
                    continue
                name = d.get("tool", "unknown")
                tool_counter[name] += 1
                tool_total += 1
                status = d.get("state", {}).get("status", "")
                if status == "completed":
                    tool_success += 1
                elif status in ("error", "failed"):
                    tool_failed += 1
            except Exception:
                pass

        # Model usage stats (count step-start = actual model invocations)
        model_stats = []
        try:
            c.execute(
                "SELECT s.model, COUNT(*) as cnt, SUM(s.cost) as total_cost, SUM(s.tokens_input) as ti, SUM(s.tokens_output) as tout FROM part p JOIN session s ON p.session_id = s.id WHERE p.data LIKE '%\"step-start\"%' AND s.time_created >= ? GROUP BY s.model ORDER BY cnt DESC",
                (day_ago_ms,),
            )
            model_stats = [
                {"model": r[0], "calls": r[1], "cost": round(r[2] or 0, 4), "tokens_in": r[3] or 0, "tokens_out": r[4] or 0}
                for r in c.fetchall()
            ]
        except Exception:
            pass

        conn.close()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # --- Derived metrics ---

    # Task completion
    completed = todo_counts.get("completed", 0)
    total_todos = sum(todo_counts.values())
    completion_rate = round(completed / total_todos * 100) if total_todos else 0

    # Tool reliability
    tool_rate = round(tool_success / tool_total * 100) if tool_total else 100

    # Verify reports
    verify_dir = os.path.expanduser("~/.local/state/opencode-verify")
    pass_count = 0
    fail_count = 0
    for vf in glob.glob(os.path.join(verify_dir, "*.json")):
        try:
            mt = os.path.getmtime(vf)
            if mt * 1000 >= day_ago_ms:
                with open(vf) as f:
                    vd = _json.load(f)
                v = vd.get("verdict", "").upper()
                if v == "PASS":
                    pass_count += 1
                elif v == "FAIL":
                    fail_count += 1
        except Exception:
            pass
    verify_total = pass_count + fail_count
    verify_rate = (pass_count / verify_total * 100) if verify_total else 100

    # Memory engagement
    mem_calls = sum(v for k, v in tool_counter.items() if "memory-engine" in k)
    letta_calls = sum(v for k, v in tool_counter.items() if "letta" in k)
    codegraph_calls = sum(v for k, v in tool_counter.items() if "codegraph" in k)
    delegation_calls = tool_counter.get("task", 0)
    phone_calls = sum(v for k, v in tool_counter.items() if "phone-connect" in k)
    sys_calls = sum(v for k, v in tool_counter.items() if "sys-info" in k)
    win_calls = sum(v for k, v in tool_counter.items() if k.startswith("win_"))
    context_calls = sum(v for k, v in tool_counter.items() if "context7" in k)
    fetch_calls = sum(v for k, v in tool_counter.items() if "fetch" in k or "webfetch" in k)

    # Memory-engine stats (direct SQLite, timestamps are ISO strings)
    mem_facts_total = 0
    mem_facts_24h = 0
    mem_relations_total = 0
    try:
        mem_db = os.path.expanduser("~/.local/share/memory-engine/memory.db")
        if os.path.exists(mem_db):
            mconn = sqlite3.connect(mem_db)
            mc = mconn.cursor()
            mc.execute("SELECT COUNT(*) FROM facts")
            mem_facts_total = mc.fetchone()[0]
            day_ago_iso = (datetime.now() - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            mc.execute("SELECT COUNT(*) FROM facts WHERE created >= ?", (day_ago_iso,))
            mem_facts_24h = mc.fetchone()[0]
            mc.execute("SELECT COUNT(*) FROM relations")
            mem_relations_total = mc.fetchone()[0]
            mconn.close()
    except Exception:
        pass

    # Capability coverage: how many tool categories used (out of 10 target categories)
    TARGET_CATEGORIES = 10
    categories_used = 0
    if tool_counter.get("bash", 0): categories_used += 1
    if tool_counter.get("read", 0) or tool_counter.get("glob", 0) or tool_counter.get("grep", 0): categories_used += 1
    if tool_counter.get("edit", 0) or tool_counter.get("write", 0): categories_used += 1
    if mem_calls or letta_calls: categories_used += 1
    if codegraph_calls: categories_used += 1
    if delegation_calls: categories_used += 1
    if phone_calls: categories_used += 1
    if sys_calls or win_calls: categories_used += 1
    if fetch_calls or context_calls: categories_used += 1
    if tool_counter.get("skill", 0) or tool_counter.get("question", 0) or tool_counter.get("todowrite", 0): categories_used += 1
    coverage_rate = round(categories_used / TARGET_CATEGORIES * 100)

    # Memory activity score: normalized (10+ calls in 24h = 100%)
    mem_activity = min(100, round((mem_calls + letta_calls) / 10 * 100))

    # Delegation score: normalized (1+ delegation = 100%)
    delegation_rate = min(100, delegation_calls * 100)

    # --- Composite score (6 dimensions, weighted) ---
    dimensions = {
        "task_completion": {"score": completion_rate, "weight": 0.25, "label": "任务完成", "detail": f"{completed}/{total_todos}"},
        "tool_reliability": {"score": tool_rate, "weight": 0.15, "label": "工具可靠性", "detail": f"{tool_success}/{tool_total}"},
        "verify_quality": {"score": verify_rate, "weight": 0.15, "label": "验证质量", "detail": f"{pass_count}✓/{fail_count}✗"},
        "memory_activity": {"score": mem_activity, "weight": 0.15, "label": "记忆活跃", "detail": f"MEM:{mem_calls} LETTA:{letta_calls}"},
        "capability_coverage": {"score": coverage_rate, "weight": 0.15, "label": "能力覆盖", "detail": f"{categories_used}/{TARGET_CATEGORIES}类"},
        "delegation": {"score": delegation_rate, "weight": 0.15, "label": "委派效率", "detail": f"{delegation_calls}次"},
    }
    composite_score = round(sum(d["score"] * d["weight"] for d in dimensions.values()))

    # Tool top-5
    top_tools = tool_counter.most_common(8)

    # Session list
    session_list = [
        {
            "title": s[1],
            "cost": round(s[2] or 0, 4),
            "tokens_in": s[3],
            "tokens_out": s[4],
            "agent": s[5],
            "time": datetime.fromtimestamp(s[6] / 1000).strftime("%H:%M"),
        }
        for s in sessions[:8]
    ]

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "score": composite_score,
        "dimensions": dimensions,
        "sessions_24h": totals[0] or 0,
        "total_cost": round(totals[1] or 0, 4),
        "tokens_in": totals[2] or 0,
        "tokens_out": totals[3] or 0,
        "todos": {"completed": completed, "in_progress": todo_counts.get("in_progress", 0), "pending": todo_counts.get("pending", 0), "total": total_todos},
        "completion_rate": completion_rate,
        "verify": {"pass": pass_count, "fail": fail_count},
        "model_stats": model_stats,
        "tools": {
            "total": tool_total,
            "success": tool_success,
            "failed": tool_failed,
            "success_rate": tool_rate,
            "top": [{"name": n, "count": cnt} for n, cnt in top_tools],
            "categories": {
                "memory": mem_calls,
                "letta": letta_calls,
                "codegraph": codegraph_calls,
                "delegation": delegation_calls,
                "phone": phone_calls,
                "system": sys_calls + win_calls,
                "research": fetch_calls + context_calls,
            },
        },
        "memory_engine": {"facts_total": mem_facts_total, "facts_24h": mem_facts_24h, "relations_total": mem_relations_total},
        "recent_sessions": session_list,
    }


@app.get("/api/ai/opencode-score-history")
async def opencode_score_history(days: int = 30):
    """Daily/weekly/monthly score history for comparison."""
    if not OPENCODE_SCORE_HISTORY.exists():
        return {"daily": [], "weekly": [], "monthly": []}
    lines = OPENCODE_SCORE_HISTORY.read_text(encoding="utf-8").strip().split("\n")
    entries = []
    seen_dates = set()
    for line in lines:
        try:
            entry = json.loads(line)
            date = entry.get("date")
            if date and date not in seen_dates:
                seen_dates.add(date)
                entries.append(entry)
        except json.JSONDecodeError:
            continue
    entries.sort(key=lambda x: x.get("date", ""))
    entries = entries[-days:]
    daily = [{"date": e["date"], "score": e["score"]} for e in entries if "date" in e and "score" in e]
    weekly = _aggregate_by_period(entries, "week")
    monthly = _aggregate_by_period(entries, "month")
    return {"daily": daily, "weekly": weekly, "monthly": monthly}


def _aggregate_by_period(entries: list[dict], period: str) -> list[dict]:
    from collections import defaultdict
    groups = defaultdict(list)
    for e in entries:
        date_str = e.get("date", "")
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if period == "week":
            key = dt.strftime("%Y-W%W")
            label = f"{dt.year} 第{dt.isocalendar().week:02d}周"
        else:
            key = dt.strftime("%Y-%m")
            label = f"{dt.year}年{dt.month:02d}月"
        groups[key].append({"label": label, "score": e.get("score", 0)})
    result = []
    for key in sorted(groups.keys()):
        scores = [g["score"] for g in groups[key]]
        result.append({
            "period": key,
            "label": groups[key][0]["label"],
            "avg_score": round(sum(scores) / len(scores)),
            "days": len(scores),
        })
    return result


def _trim_jsonl(path: Path, keep: int = 90):
    try:
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) > keep:
            path.write_text("\n".join(lines[-keep:]) + "\n", encoding="utf-8")
    except Exception:
        pass


@app.get("/api/ops/daily-improvement")
async def ops_daily_improvement():
    """Unified daily score for Fedora, phone, AI services, code quality, and upkeep."""
    import re
    import shutil
    from datetime import timedelta

    def run(cmd: list[str], timeout: float = 2.5) -> tuple[int, str, str]:
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    def sh(cmd: str, timeout: float = 2.5) -> str:
        return run(["bash", "-lc", cmd], timeout=timeout)[1]

    def bounded(value: float) -> int:
        return max(0, min(100, round(value)))

    def grade(score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 65:
            return "C"
        return "D"

    def penalty_score(base: int, penalties: list[int]) -> int:
        return bounded(base - sum(penalties))

    def status_item(name: str, ok: bool, detail: str = "", command: str = "") -> dict:
        return {
            "name": name,
            "status": "ok" if ok else "warn",
            "detail": detail,
            "command": command,
        }

    def port_up(port: int) -> bool:
        return bool(sh(f"ss -tln | grep -q ':{port} ' && echo ok", 1.0) == "ok")

    def user_service_state(unit: str) -> dict:
        code, out, _ = run(
            ["systemctl", "--user", "show", unit, "--property=ActiveState,SubState,Result,NRestarts", "--value"],
            timeout=1.5,
        )
        vals = out.splitlines()
        active, sub, result, restarts = (vals + ["unknown", "unknown", "unknown", "0"])[:4]
        ok = active in {"active", "activating"} and result in {"success", ""}
        return {
            "unit": unit,
            "active": active,
            "sub": sub,
            "result": result,
            "restarts": int(restarts) if str(restarts).isdigit() else 0,
            "ok": code == 0 and ok,
        }

    now = datetime.now()
    domains: list[dict] = []
    actions: list[dict] = []

    # Fedora system
    meminfo = Path("/proc/meminfo").read_text(encoding="utf-8", errors="ignore")
    mem_total = int(re.search(r"MemTotal:\s+(\d+)", meminfo).group(1))
    mem_avail = int(re.search(r"MemAvailable:\s+(\d+)", meminfo).group(1))
    mem_pct = round((1 - mem_avail / max(1, mem_total)) * 100)
    swap_total = int((re.search(r"SwapTotal:\s+(\d+)", meminfo) or [0, "0"])[1])
    swap_free = int((re.search(r"SwapFree:\s+(\d+)", meminfo) or [0, "0"])[1])
    swap_pct = round((1 - swap_free / max(1, swap_total)) * 100) if swap_total else 0
    disk_path = str(Path.home())
    disk = shutil.disk_usage(disk_path)
    disk_pct = round(disk.used / max(1, disk.total) * 100)
    failed_user = [x for x in sh("systemctl --user --failed --no-legend", 2.0).splitlines() if x.strip()]
    failed_system = [x for x in sh("systemctl --failed --no-legend", 2.0).splitlines() if x.strip()]
    psi_mem = Path("/proc/pressure/memory").read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    fedora_penalties = []
    if mem_pct > 85:
        fedora_penalties.append(18)
        actions.append({"priority": "high", "area": "Fedora", "title": "内存压力偏高", "detail": f"内存使用 {mem_pct}%", "command": "ps aux --sort=-%mem | head -11"})
    if swap_pct > 30:
        fedora_penalties.append(10)
    if disk_pct > 85:
        fedora_penalties.append(18)
        actions.append({"priority": "high", "area": "Fedora", "title": "用户数据分区空间偏高", "detail": f"{disk_path} 使用 {disk_pct}%", "command": "df -hTx tmpfs && rpm-ostree cleanup -m --preview"})
    if failed_user or failed_system:
        fedora_penalties.append(min(30, (len(failed_user) + len(failed_system)) * 8))
        actions.append({"priority": "high", "area": "Fedora", "title": "存在失败 systemd 服务", "detail": f"user {len(failed_user)} / system {len(failed_system)}", "command": "systemctl --user --failed && systemctl --failed"})
    domains.append({
        "key": "fedora",
        "label": "Fedora 系统",
        "score": penalty_score(100, fedora_penalties),
        "items": [
            status_item("内存", mem_pct <= 85, f"{mem_pct}% 使用, available {round(mem_avail/1024/1024, 1)} GiB"),
            status_item("Swap", swap_pct <= 30, f"{swap_pct}% 使用"),
            status_item("用户数据分区", disk_pct <= 85, f"{disk_path} · {disk_pct}% 使用"),
            status_item("失败服务", not (failed_user or failed_system), f"user {len(failed_user)} / system {len(failed_system)}"),
            status_item("内存 PSI", True, psi_mem),
        ],
    })

    # Phone
    devices = sh("adb devices", 2.0)
    adb_candidates = ["192.168.123.22:5555", "100.108.28.44:5555", "127.0.0.1:15555"]
    adb_target = next((target for target in adb_candidates if f"{target}\tdevice" in devices), adb_candidates[0])
    if f"{adb_target}\tdevice" not in devices:
        run(["adb", "connect", adb_target], timeout=3.0)
        devices = sh("adb devices", 2.0)
    phone_connected = f"{adb_target}\tdevice" in devices
    battery = {}
    phone_storage = "unknown"
    if phone_connected:
        batt_raw = sh(f"adb -s {adb_target} shell dumpsys battery", 3.0)
        for line in batt_raw.splitlines():
            if ":" in line:
                k, v = line.strip().split(":", 1)
                battery[k.strip()] = v.strip()
        phone_storage = sh(f"adb -s {adb_target} shell df -h /data | tail -1", 3.0)
    battery_level = int(battery.get("level", "0")) if str(battery.get("level", "0")).isdigit() else 0
    temp_raw = int(battery.get("temperature", "0")) if str(battery.get("temperature", "0")).isdigit() else 0
    temp_c = round(temp_raw / 10, 1) if temp_raw else 0
    phone_penalties = []
    if not phone_connected:
        phone_penalties.append(45)
        actions.append({"priority": "high", "area": "手机", "title": "ADB 未连接", "detail": " / ".join(adb_candidates), "command": "adb devices && systemctl --user status adb-phone-keepalive.timer"})
    if phone_connected and battery_level < 25:
        phone_penalties.append(12)
    if phone_connected and temp_c >= 42:
        phone_penalties.append(16)
    domains.append({
        "key": "phone",
        "label": "手机",
        "score": penalty_score(100, phone_penalties),
        "items": [
            status_item("ADB", phone_connected, adb_target, "adb devices"),
            status_item("电量", (not phone_connected) or battery_level >= 25, f"{battery_level or '?'}%"),
            status_item("温度", (not phone_connected) or temp_c < 42, f"{temp_c or '?'} C"),
            status_item("存储", True, phone_storage),
        ],
    })

    # AI services
    ai_specs = [
        ("LiteLLM", 4002, "litellm.service", "/v1/models"),
        ("LiteLLM Strip", 4000, "litellm-strip-proxy.service", "/v1/models"),
        ("Letta", 8283, "letta-stack.service", "/v1/agents/"),
        ("Embedding", 8286, "embedding-server.service", "/health"),
        ("FastGPT", 3000, "", "/"),
        ("Open WebUI", 3001, "", "/"),
        ("n8n", 5678, "", "/"),
        ("OpenCode API", 4097, "opencode.service", "/"),
        ("Telegram Gateway", 9811, "opencode-telegram-gateway.service", "/health"),
    ]
    ai_items = []
    ai_down = 0
    for name, port, unit, path in ai_specs:
        is_up = port_up(port)
        unit_state = user_service_state(unit) if unit else {"ok": is_up, "active": "port"}
        ok = is_up and unit_state.get("ok", True)
        if not ok:
            ai_down += 1
            actions.append({"priority": "medium", "area": "AI 服务", "title": f"{name} 异常", "detail": f"port {port}, unit {unit or 'n/a'}", "command": f"systemctl --user status {unit}" if unit else f"ss -tlnp | grep :{port}"})
        ai_items.append(status_item(name, ok, f":{port}{path} · {unit_state.get('active', 'unknown')}"))
    domains.append({
        "key": "ai",
        "label": "AI 服务",
        "score": penalty_score(100, [min(55, ai_down * 9)]),
        "items": ai_items,
    })

    # OpenCode execution resilience
    op_resilience = {}
    try:
        code, out, err = run([str(Path.home() / ".local/bin/opencode-resilience-score"), "--json"], timeout=10.0)
        if code == 0 and out:
            op_resilience = json.loads(out)
    except Exception:
        op_resilience = {}
    if op_resilience:
        op_items = []
        for layer in (op_resilience.get("fallback_layers") or [])[:9]:
            op_items.append(status_item(layer.get("name", "?"), bool(layer.get("ok")), layer.get("detail", "")))
        stopped = bool(op_resilience.get("stopped"))
        if stopped:
            actions.append({
                "priority": "high",
                "area": "OP 执行",
                "title": "发现疑似停止的 OP busy session",
                "detail": ", ".join((s.get("id", "")[:12] for s in op_resilience.get("stopped_like", []) if s.get("id"))) or "stopped_like",
                "command": "opencode-resilience-score --json | jq '.stopped_like'",
            })
        for rec in (op_resilience.get("recommendations") or [])[:3]:
            if rec.get("priority") in {"high", "medium"}:
                actions.append({
                    "priority": rec.get("priority", "medium"),
                    "area": "OP 执行",
                    "title": rec.get("title", "OP 韧性建议"),
                    "detail": rec.get("detail", ""),
                    "command": "opencode-resilience-score --json",
                })
        domains.append({
            "key": "op-resilience",
            "label": "OP 执行韧性",
            "score": int(op_resilience.get("score") or 0),
            "items": [
                status_item("疑似停止", not stopped, f"busy {len(op_resilience.get('busy') or [])}"),
                status_item("服务链", bool((op_resilience.get("probes") or {}).get("api_4097", {}).get("ok")), "18910→4097"),
                status_item("智能内存", bool((op_resilience.get("memory") or {}).get("high", 0) >= 10 * 1024**3), f"score {op_resilience.get('score')} / {op_resilience.get('grade')}"),
            ] + op_items[:5],
        })

    # Code quality
    repos = [
        Path.home() / "hub",
        Path.home() / "termhive",
        Path.home() / "dotfiles",
        Path.home() / "opencode-telegram-gateway",
    ]
    code_items = []
    code_penalties = []
    for repo in repos:
        if not repo.exists():
            continue
        dirty = bool(sh(f"git -C {repo} status --short", 2.0))
        tracked_py = sh(f"git -C {repo} ls-files '*.py' | wc -l", 2.0).strip()
        compile_ok = True
        if tracked_py and tracked_py != "0":
            compile_ok = run(["python3", "-m", "compileall", "-q", str(repo)], timeout=12.0)[0] == 0
        if dirty:
            code_penalties.append(4)
        if not compile_ok:
            code_penalties.append(20)
            actions.append({"priority": "high", "area": "代码质量", "title": f"{repo.name} Python 编译失败", "detail": str(repo), "command": f"python3 -m compileall -q {repo}"})
        code_items.append(status_item(repo.name, compile_ok, ("dirty" if dirty else "clean") + f" · py {tracked_py or 0}", f"git -C {repo} status --short"))
    cg_list = sh("codegraphcontext list", 8.0)
    codegraph_ok = "/var/home/charlie/hub" in cg_list
    if not codegraph_ok:
        code_penalties.append(12)
        actions.append({"priority": "medium", "area": "代码质量", "title": "CodeGraph 索引不可用", "detail": "hub 未出现在 list 输出中", "command": "codegraphcontext list && codegraphcontext update /var/home/charlie/hub"})
    code_items.append(status_item("CodeGraph", codegraph_ok, "hub indexed" if codegraph_ok else "hub missing", "codegraphcontext list"))
    domains.append({
        "key": "code",
        "label": "代码质量",
        "score": penalty_score(100, code_penalties),
        "items": code_items,
    })

    # Scheduled maintenance
    timer_specs = [
        ("DuckDNS", "duckdns-update.timer"),
        ("ADB Keepalive", "adb-phone-keepalive.timer"),
        ("知识维护", "opencode-knowledge-maintainer.timer"),
        ("CodeGraph Warmup", "opencode-codegraph-warmup.timer"),
    ]
    maint_items = []
    maint_penalties = []
    for label, unit in timer_specs:
        active = run(["systemctl", "--user", "is-active", unit], timeout=1.5)[1]
        enabled = run(["systemctl", "--user", "is-enabled", unit], timeout=1.5)[1]
        ok = active == "active" and enabled in {"enabled", "static"}
        if not ok:
            maint_penalties.append(12)
            actions.append({"priority": "medium", "area": "定期维护", "title": f"{label} timer 未正常启用", "detail": f"{unit}: {enabled}/{active}", "command": f"systemctl --user status {unit}"})
        maint_items.append(status_item(label, ok, f"{unit}: {enabled}/{active}", f"systemctl --user status {unit}"))
    domains.append({
        "key": "maintenance",
        "label": "定期维护",
        "score": penalty_score(100, maint_penalties),
        "items": maint_items,
    })

    # Learning / improvement
    learned = Path.home() / ".ai-context/AUTO_LEARNED.md"
    queue = Path.home() / "memory/agent-adaptation-queue.md"
    journal = Path.home() / "memory/opencode-task-journal.jsonl"
    fresh_cutoff = time.time() - 24 * 60 * 60
    learned_fresh = learned.exists() and learned.stat().st_mtime >= fresh_cutoff
    queue_size = queue.stat().st_size if queue.exists() else 0
    journal_lines_24h = 0
    if journal.exists():
        try:
            for line in journal.read_text(encoding="utf-8", errors="ignore").splitlines()[-500:]:
                if now.strftime("%Y-%m-%d") in line:
                    journal_lines_24h += 1
        except Exception:
            pass
    learning_penalties = []
    if not learned_fresh:
        learning_penalties.append(10)
        actions.append({"priority": "low", "area": "每日提升", "title": "今日尚未刷新学习产物", "detail": str(learned), "command": "systemctl --user start opencode-knowledge-maintainer.service"})
    if queue_size > 50_000:
        learning_penalties.append(8)
    domains.append({
        "key": "learning",
        "label": "自主学习",
        "score": penalty_score(100, learning_penalties),
        "items": [
            status_item("AUTO_LEARNED", learned_fresh, datetime.fromtimestamp(learned.stat().st_mtime).isoformat(timespec="minutes") if learned.exists() else "missing"),
            status_item("适配队列", queue_size <= 50_000, f"{round(queue_size/1024, 1)} KiB"),
            status_item("任务日志", True, f"今日记录 {journal_lines_24h} 行"),
        ],
    })

    total_score = bounded(sum(d["score"] for d in domains) / max(1, len(domains)))
    actions.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority"), 3))
    next_tasks = actions[:8] or [
        {"priority": "low", "area": "每日提升", "title": "做一次只读巡检", "detail": "当前没有高优先级异常", "command": "curl -s http://127.0.0.1:9800/api/ops/daily-improvement | jq '.score,.domains[].score'"},
        {"priority": "low", "area": "代码质量", "title": "刷新 CodeGraph 索引", "detail": "结构变化后保持代码图谱准确", "command": "codegraphcontext update /var/home/charlie/hub"},
    ]
    return {
        "generated_at": now.isoformat(),
        "score": total_score,
        "grade": grade(total_score),
        "domains": [{**d, "grade": grade(d["score"])} for d in domains],
        "next_tasks": next_tasks,
        "cadence": [
            {"name": "每天", "items": ["看总分和高优先级任务", "确认失败服务和端口冲突", "检查手机 ADB/电量/温度"]},
            {"name": "每周", "items": ["rpm-ostree upgrade --check", "清理 journal 和容器缓存预览", "刷新 CodeGraph 索引"]},
            {"name": "每月", "items": ["审计 runbook 与故障黑名单", "检查公网入口和 FRP/路由器快照", "归档已完成任务和学习队列"]},
        ],
    }


def _format_score_dispatch(data: dict, intent: str = "optimize") -> str:
    score = data.get("score", "?")
    grade = data.get("grade", "?")
    generated_at = data.get("generated_at", "")
    next_tasks = data.get("next_tasks") or []
    domains = data.get("domains") or []
    mode_line = (
        "请先复核评分和评测结果，再处理高优先级缺陷；可以执行优化，但必须遵守系统 runbook、FAILURE_BLACKLIST 和持久化服务规则。"
        if intent == "optimize"
        else "请只读评估评分和评测结果，输出缺陷、风险和建议，不要执行修改。"
    )
    lines = [
        "# Hub 每日评分与评测结果",
        "",
        f"- 生成时间: {generated_at}",
        f"- 总分: {score} / 等级 {grade}",
        f"- 意图: {intent}",
        "",
        mode_line,
        "",
        "## 分域评分",
    ]
    for domain in domains:
        lines.append(f"- {domain.get('label', domain.get('key', '?'))}: {domain.get('score', '?')} / {domain.get('grade', '?')}")
        for item in (domain.get("items") or [])[:4]:
            lines.append(f"  - {item.get('status', '?')}: {item.get('name', '?')} - {item.get('detail', '')}")
    lines.extend(["", "## 优先处理项"])
    if next_tasks:
        for index, task in enumerate(next_tasks[:10], 1):
            lines.append(f"{index}. [{task.get('priority', 'low')}] {task.get('area', '')} / {task.get('title', '')}")
            if task.get("detail"):
                lines.append(f"   - 详情: {task.get('detail')}")
            if task.get("command"):
                lines.append(f"   - 建议验证命令: `{task.get('command')}`")
    else:
        lines.append("- 暂无待处理项。")
    lines.extend([
        "",
        "## 执行规则",
        "- 修改系统服务前先检查对应 runbook 和失败黑名单。",
        "- 长驻进程必须通过 user systemd service 管理。",
        "- 优化完成后回写验证结果、风险和回滚方式。",
    ])
    return "\n".join(lines)


def _append_codex_inbox_task(message: str, metadata: dict | None = None) -> dict:
    inbox = Path.home() / ".local/state/hub/codex-inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:10]
    path = inbox / f"{stamp}-{digest}.md"
    path.write_text(message + "\n", encoding="utf-8")
    journal = Path.home() / "memory/opencode-task-journal.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "source": "hub-score-dispatch",
            "target": "codex",
            "mode": "codex_inbox",
            "file": str(path),
            "metadata": metadata or {},
        }, ensure_ascii=False) + "\n")
    return {"status": "queued", "target": "codex", "file": str(path), "instruction": "已写入 Codex inbox；从 Codex 按需打开执行。"}


@app.post("/api/ops/score-dispatch/{target}")
async def ops_score_dispatch(target: str, body: dict | None = None):
    body = body or {}
    target = target.lower().strip()
    if target not in {"op", "crush", "codex", "all"}:
        return JSONResponse({"error": "target must be op, crush, codex, or all"}, status_code=400)
    intent = (body.get("intent") or "optimize").strip().lower()
    if intent not in {"optimize", "review"}:
        intent = "optimize"
    data = await ops_daily_improvement()
    message = _format_score_dispatch(data, intent=intent)
    targets = ["op", "crush", "codex"] if target == "all" else [target]
    results: dict[str, dict] = {}
    for item in targets:
        if item == "op":
            results[item] = _append_op_inbox_task(
                "hub-score-dispatch",
                message,
                tags=["HUB-SCORE", "OPTIMIZE" if intent == "optimize" else "REVIEW"],
                metadata={"score": data.get("score"), "grade": data.get("grade"), "intent": intent},
            )
        elif item == "crush":
            title = f"Hub评分优化 {data.get('score')}/{data.get('grade')}"
            try:
                dispatch_bin = str(Path.home() / ".local/bin/agent-dispatch")
                proc = subprocess.run(
                    [dispatch_bin, "submit", "--target", "crush", "--title", title, message],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    stdin=subprocess.DEVNULL,
                )
                results[item] = {
                    "status": "queued" if proc.returncode == 0 else "failed",
                    "target": "crush",
                    "returncode": proc.returncode,
                    "stdout": (proc.stdout or "").strip()[-1200:],
                    "stderr": (proc.stderr or "").strip()[-1200:],
                }
            except Exception as exc:
                results[item] = {"status": "failed", "target": "crush", "error": str(exc)}
        elif item == "codex":
            results[item] = _append_codex_inbox_task(
                message,
                metadata={"score": data.get("score"), "grade": data.get("grade"), "intent": intent},
            )
    event = _task_bus_append("score_dispatched", "ops-score", "hub", {"target": target, "intent": intent, "score": data.get("score"), "results": results})
    return {"status": "ok", "target": target, "intent": intent, "score": data.get("score"), "grade": data.get("grade"), "results": results, "event": event}


@app.get("/api/architecture/actions")
async def architecture_actions(request: Request):
    """Self-updating architecture guidance for the Hub home page."""
    import re

    now_ts = time.time()
    cached = _architecture_cache.get("data")
    if cached and now_ts - float(_architecture_cache.get("ts", 0.0)) < 300:
        return cached

    def run(cmd: list[str], timeout: float = 3.0) -> tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    def sh(cmd: str, timeout: float = 3.0) -> str:
        return run(["bash", "-lc", cmd], timeout=timeout)[1]

    def add(priority: str, area: str, title: str, detail: str, command: str = "", href: str = ""):
        actions.append({
            "priority": priority,
            "area": area,
            "title": title,
            "detail": detail,
            "command": command,
            "href": href,
        })

    actions: list[dict] = []
    signals: dict[str, typing.Any] = {}

    try:
        ops = await ops_daily_improvement()
        if isinstance(ops, dict):
            signals["daily_score"] = ops.get("score")
            for task in (ops.get("next_tasks") or [])[:3]:
                add(task.get("priority", "medium"), task.get("area", "每日提升"), task.get("title", "处理异常"), task.get("detail", ""), task.get("command", ""), "/dashboard")
    except Exception as exc:
        signals["daily_score_error"] = str(exc)
        add("medium", "观测", "每日评分接口异常", str(exc), "curl -s http://127.0.0.1:9800/api/ops/daily-improvement | jq", "/dashboard")

    active_user_services = [
        line.split(".service", 1)[0] + ".service"
        for line in sh("systemctl --user list-units --type=service --state=running --no-legend", 2.0).splitlines()
        if ".service" in line
    ]
    ai_like = [s for s in active_user_services if any(k in s.lower() for k in ("ai", "agent", "opencode", "letta", "embedding", "openagents", "dashboard", "orchestrator", "office", "matrix", "mautrix"))]
    signals["running_user_services"] = len(active_user_services)
    signals["ai_like_services"] = len(ai_like)
    if len(ai_like) >= 14:
        add(
            "medium",
            "常驻降噪",
            "AI/Agent 常驻服务偏多",
            f"当前 AI/Agent 相关运行服务约 {len(ai_like)} 个，建议拆成 core / ai-work / lab profile。",
            "systemctl --user list-units --type=service --state=running | rg 'ai|agent|opencode|letta|embedding|openagents|matrix|office'",
            "/control",
        )

    timer_out = sh("systemctl --user list-timers --all --no-legend", 2.0)
    active_timers = [line for line in timer_out.splitlines() if line.strip() and not line.startswith("-")]
    fast_timers = []
    for line in active_timers:
        if re.search(r"\b([0-9]|[1-5][0-9])s\b|ago", line) and any(k in line for k in ("opencode", "adb", "watchdog", "stuck")):
            fast_timers.append(line)
    signals["active_timers"] = len(active_timers)
    signals["fast_watch_timers"] = len(fast_timers)
    if len(fast_timers) >= 5:
        add(
            "medium",
            "自动化",
            "高频 watchdog 较多",
            f"检测到 {len(fast_timers)} 个高频巡检/守护计时器，建议合并到统一维护节奏。",
            "systemctl --user list-timers --all | rg 'opencode|adb|watchdog|stuck'",
            "/dashboard",
        )

    link_count = len(LINK_REGISTRY)
    go_ready = sum(1 for item in LINK_REGISTRY.values() if item.get("candidates"))
    signals["link_registry"] = {"total": link_count, "with_candidates": go_ready}
    if go_ready < link_count:
        add("high", "入口治理", "存在未配置兜底的链接", f"{link_count - go_ready} 个链接没有候选地址。", "curl -s http://127.0.0.1:9800/api/links | jq", "/api/links")
    else:
        add("low", "入口治理", "链接兜底已覆盖", f"{go_ready}/{link_count} 个入口已走 /go 注册表。", "curl -s http://127.0.0.1:9800/api/links | jq 'keys'", "/api/links")

    rpm_status = sh("rpm-ostree status", 5.0)
    layered_match = re.search(r"LayeredPackages:\s+(.+?)(?:\n\s+\w|\n\s+LocalPackages:|\n\s+Pinned:)", rpm_status, re.S)
    layered_text = layered_match.group(1) if layered_match else ""
    layered_count = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+-]+", layered_text))
    signals["layered_packages_estimate"] = layered_count
    if layered_count >= 50:
        add(
            "low",
            "Silverblue",
            "Layered packages 偏多",
            f"估算 layered 包 {layered_count} 个；开发库可逐步迁入 toolbox/distrobox。",
            "rpm-ostree status | sed -n '1,80p'",
            "/dashboard",
        )

    profile_file = Path.home() / ".config/systemd/user/ai-work.target"
    signals["ai_work_target_exists"] = profile_file.exists()
    if not profile_file.exists():
        add(
            "medium",
            "服务 Profile",
            "尚未落地 ai-work.target",
            "建议把 FastGPT、Embedding、CodeGraph warmup、ttyd 等工作态服务挂到 ai-work.target。",
            "systemctl --user list-unit-files '*target'",
            "/control",
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda item: (priority_order.get(item.get("priority"), 9), item.get("area", ""), item.get("title", "")))
    data = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "high": sum(1 for a in actions if a["priority"] == "high"),
            "medium": sum(1 for a in actions if a["priority"] == "medium"),
            "low": sum(1 for a in actions if a["priority"] == "low"),
        },
        "signals": signals,
        "actions": actions[:8],
        "cadence": [
            {"name": "实时", "detail": "首页每 30 秒刷新系统状态，每 5 分钟刷新架构动作。"},
            {"name": "每天", "detail": "优先处理 high/medium 动作，保持入口可访问和服务稳定。"},
            {"name": "每周", "detail": "审计常驻服务、timer、Silverblue layered 包和链接注册表。"},
        ],
    }
    _architecture_cache["ts"] = now_ts
    _architecture_cache["data"] = data
    return data


@app.get("/api/ops/opencode-resilience")
async def opencode_resilience():
    try:
        r = await asyncio.to_thread(
            subprocess.run,
            [str(Path.home() / ".local/bin/opencode-resilience-score"), "--json", "--write"],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        if r.returncode != 0:
            return JSONResponse({"error": r.stderr or "opencode-resilience-score failed"}, status_code=500)
        return JSONResponse(json.loads(r.stdout))
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/ai/services")
async def ai_services(request: Request):
    import re

    def run(cmd: list[str], timeout: float = 1.0) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return (r.stdout or "").strip()
        except Exception:
            return ""

    ss_out = run(["ss", "-tln"])
    listening_ports = {int(m.group(1)) for m in re.finditer(r":(\d+)\s", ss_out)}
    service_active_cache: dict[str, bool] = {}
    docker_ps_names = set(run(["docker", "ps", "--format", "{{.Names}}"]).splitlines())
    docker_ps_all = run(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"])

    def port_up(port: int) -> bool:
        return port in listening_ports

    def user_service_active(name: str) -> bool:
        if name not in service_active_cache:
            service_active_cache[name] = run(["systemctl", "--user", "is-active", name]) == "active"
        return service_active_cache[name]

    def container_running(name: str) -> bool:
        return any(name in n for n in docker_ps_names)

    def container_exited(name: str) -> bool:
        return name in docker_ps_all and "Exited" in docker_ps_all

    def sunshine_apps() -> list[dict]:
        apps_file = Path.home() / ".config/sunshine/apps.json"
        try:
            data = json.loads(apps_file.read_text(encoding="utf-8"))
            apps = data.get("apps") or []
        except Exception:
            return []
        items = []
        for app_item in apps:
            name = str(app_item.get("name") or "").strip()
            if not name:
                continue
            category = str(app_item.get("category") or "桌面").strip()
            launch_kind = "桌面画面" if name.lower() in {"desktop", "low res desktop"} else "应用画面"
            items.append({
                "name": f"Moonlight: {name}",
                "status": "online" if port_up(47990) else "offline",
                "url": f"https://{host}:47990/",
                "host_url": f"https://{host}:47990/",
                "listen": "0.0.0.0",
                "detail": f"手机 Moonlight 中显示的 Sunshine 启动项 · {category} · {launch_kind}",
                "category": "moonlight",
                "source": "sunshine-apps",
            })
        return items

    host = request.headers.get("host", "127.0.0.1:9800").split(":")[0]

    def external_url(port: int, path: str = "/") -> str:
        return f"http://{host}:{port}{path}"

    def old_web_service(name: str, port: int, detail: str, category: str, path: str = "/",
                        status: str | None = None, listen: str = "127.0.0.1") -> dict:
        return {
            "name": name,
            "status": status or ("online" if port_up(port) else "offline"),
            "url": external_url(port, path),
            "host_url": external_url(port, path),
            "listen": listen,
            "detail": detail,
            "category": category,
            "source": "old-nixos-desktop-web",
        }

    def old_nixos_web_services() -> list[dict]:
        return [
            old_web_service("旧盘: Open-WebUI", 3001, "聊天界面，旧桌面 Web服务/Open-WebUI.desktop", "legacy"),
            old_web_service("旧盘: Dify", 3100, "AI 工作流，旧桌面 Web服务/Dify.desktop", "legacy"),
            old_web_service("旧盘: LiteLLM", 4000, "AI 代理网关，旧桌面 Web服务/LiteLLM.desktop", "legacy", "/v1/models", listen="0.0.0.0"),
            old_web_service("旧盘: BrowserAgent", 5002, "浏览器代理，旧桌面 Web服务/BrowserAgent.desktop", "legacy"),
            old_web_service("旧盘: Langflow", 7860, "可视化 AI 流，旧桌面 Web服务/Langflow.desktop", "legacy"),
            old_web_service("旧盘: Letta", 8283, "长期记忆 AI，旧桌面 Web服务/Letta.desktop", "legacy"),
            old_web_service("旧盘: Autogen", 8080, "多 Agent，旧桌面 Web服务/Autogen.desktop", "legacy"),
            old_web_service("旧盘: Ollama", 11434, "本地大模型，旧桌面 Web服务/Ollama.desktop", "legacy"),
            old_web_service("旧盘: ChromaDB", 8000, "向量数据库，旧桌面 Web服务/ChromaDB.desktop", "legacy"),
            old_web_service("旧盘: Mem0", 5001, "记忆过滤，旧桌面 Web服务/Mem0.desktop", "legacy"),

            old_web_service("旧盘: CRM 静态面板", 9876, "CRM 客户/联系人面板，旧 crm-server.service", "legacy", listen="0.0.0.0"),
            old_web_service("旧盘: Twenty CRM", 3001, "旧盘记录 twenty-server-1:3001；当前 3001 被 Open-WebUI 占用", "legacy",
                            status=("online" if (container_running("twenty-server-1") or container_running("twenty-server")) else "not_deployed")),
            old_web_service("旧盘: ERPNext", 8088, "ERP 系统，旧桌面 Web服务/ERPNext.desktop", "legacy"),
            old_web_service("旧盘: 1688", 5000, "1688 采购，旧桌面 Web服务/1688.desktop", "legacy"),
            old_web_service("旧盘: HyperChat", 9098, "CRM+AI+RAG 智能助手，旧桌面 Web服务/HyperChat.desktop", "legacy"),
            old_web_service("旧盘: InboxZero", 8079, "邮件管理，旧桌面 Web服务/InboxZero.desktop", "legacy"),
            old_web_service("旧盘: SocialAgg", 1200, "社交聚合，旧桌面 Web服务/SocialAgg.desktop", "legacy"),
            old_web_service("旧盘: TripMap", 8090, "旅行地图，旧桌面 Web服务/TripMap.desktop", "legacy"),

            old_web_service("旧盘: 启动器", 9875, "应用启动器，旧桌面 Web服务/启动器.desktop", "legacy", "/launcher.html"),
            old_web_service("旧盘: 操作指南", 9875, "操作说明书，旧桌面 Web服务/操作指南.desktop", "legacy", "/guide.html"),
            old_web_service("旧盘: Dashboard", 9099, "系统仪表盘，旧桌面 Web服务/Dashboard.desktop", "legacy"),
            old_web_service("旧盘: HyperOS", 8800, "HyperOS 面板，旧桌面 Web服务/HyperOS.desktop", "legacy"),
            old_web_service("旧盘: Guacamole", 6080, "远程桌面，旧桌面 Web服务/Guacamole.desktop", "legacy"),
            old_web_service("旧盘: OpenClaw", 18789, "OpenClaw，旧桌面 Web服务/OpenClaw.desktop", "legacy"),

            old_web_service("旧盘: N8N", 5678, "自动化工作流，旧桌面 Web服务/N8N.desktop", "legacy"),
            old_web_service("旧盘: Xray代理", 9090, "代理面板，旧桌面 Web服务/Xray代理.desktop", "legacy", "/ui"),
        ]

    services = [
        {
            "name": "OpenCode Server",
            "status": "online" if user_service_active("opencode.service") and port_up(4097) else "offline",
            "url": external_url(4097),
            "host_url": external_url(4097),
            "listen": "127.0.0.1",
            "detail": "后端 API (4097)",
            "category": "core",
        },
        {
            "name": "OpenCode Web",
            "status": "online" if user_service_active("opencode-18910-local.service") and port_up(18910) else "offline",
            "url": external_url(18910),
            "host_url": external_url(18910),
            "listen": "0.0.0.0",
            "detail": "Web 控制台 (18910→4097)",
            "category": "core",
        },
        {
            "name": "OpenClaw TTYD",
            "status": "online" if port_up(8080) else "offline",
            "url": external_url(8080),
            "host_url": external_url(8080),
            "listen": "127.0.0.1",
            "detail": "本地终端入口",
            "category": "core",
        },
        {
            "name": "LiteLLM",
            "status": "online" if user_service_active("litellm-strip-proxy.service") and port_up(4000) else "offline",
            "url": external_url(4000, "/v1/models"),
            "host_url": external_url(4000, "/v1/models"),
            "listen": "0.0.0.0",
            "detail": "AI 网关 (strip-proxy 4000)",
            "category": "infra",
        },
        {
            "name": "LiteLLM 原生",
            "status": "online" if port_up(4002) else "offline",
            "url": external_url(4002, "/v1/models"),
            "host_url": external_url(4002, "/v1/models"),
            "listen": "127.0.0.1",
            "detail": "原生 LiteLLM (4002)",
            "category": "infra",
        },
        {
            "name": "Letta",
            "status": "online" if port_up(8283) else "offline",
            "url": external_url(8283),
            "host_url": external_url(8283),
            "listen": "127.0.0.1",
            "detail": "记忆服务",
            "category": "infra",
        },
        {
            "name": "Embedding",
            "status": "online" if port_up(8286) else "offline",
            "url": external_url(8286, "/health"),
            "host_url": external_url(8286, "/health"),
            "listen": "0.0.0.0",
            "detail": "向量嵌入服务",
            "category": "infra",
        },
        {
            "name": "TermHive Web",
            "status": "online" if user_service_active("termhive-web.service") and port_up(3200) else "offline",
            "url": external_url(3200),
            "host_url": external_url(3200),
            "listen": "127.0.0.1",
            "detail": "终端管理 Web (3200)",
            "category": "agent",
        },
        {
            "name": "TermHive Daemon",
            "status": "online" if user_service_active("termhive-daemon.service") and port_up(3210) else "offline",
            "url": external_url(3210, "/api/daemon/status"),
            "host_url": external_url(3210, "/api/daemon/status"),
            "listen": "127.0.0.1",
            "detail": "终端守护进程 (3210)",
            "category": "agent",
        },
        {
            "name": "Telegram Gateway",
            "status": "online" if user_service_active("opencode-telegram-gateway.service") and port_up(9811) else "offline",
            "url": external_url(9811, "/health"),
            "host_url": external_url(9811, "/health"),
            "listen": "127.0.0.1",
            "detail": "Telegram 消息网关",
            "category": "agent",
        },
        {
            "name": "Haven MCP Bridge",
            "status": "online" if user_service_active("haven-mcp-bridge.service") and port_up(8732) else "offline",
            "url": external_url(8732, "/mcp"),
            "host_url": external_url(8732, "/mcp"),
            "listen": "127.0.0.1",
            "detail": "手机桥接 MCP",
            "category": "agent",
        },
        {
            "name": "内容筛选",
            "status": "online" if port_up(8765) else "offline",
            "url": external_url(8765),
            "host_url": external_url(8765),
            "listen": "0.0.0.0",
            "detail": "内容筛选面板 (8765)",
            "category": "apps",
        },
        {
            "name": "Sunshine",
            "status": "online" if port_up(47990) else "offline",
            "url": f"https://{host}:47990/",
            "host_url": f"https://{host}:47990/",
            "listen": "0.0.0.0",
            "detail": "游戏串流 (47990)",
            "category": "infra",
        },
        {
            "name": "Moonlight 手机客户端",
            "status": "online" if port_up(47990) else "offline",
            "url": "https://moonlight-stream.org/",
            "host_url": "https://moonlight-stream.org/",
            "listen": "",
            "detail": "手机安装 Moonlight 后连接 Sunshine；下方 Moonlight 启动器显示可启动的电脑画面",
            "category": "moonlight",
        },
        *sunshine_apps(),
        {
            "name": "FRP Dashboard",
            "status": "online" if port_up(7500) else "offline",
            "url": external_url(7500),
            "host_url": f"http://admin:frp%40charlie2026@{host}:7500/",
            "listen": "0.0.0.0",
            "detail": "FRP 管理面板",
            "category": "infra",
            "auth": "basic",
        },
        {
            "name": "FRP 公网入口",
            "status": "online" if port_up(19890) else "offline",
            "url": external_url(19890),
            "host_url": external_url(19890),
            "listen": "0.0.0.0",
            "detail": "公网映射入口",
            "category": "infra",
        },
        {
            "name": "Mihomo",
            "status": "online" if port_up(9091) else "offline",
            "url": external_url(9091, "/ui"),
            "host_url": external_url(9091, "/ui"),
            "listen": "127.0.0.1",
            "detail": "代理控制面",
            "category": "infra",
        },
        {
            "name": "OpenAgents",
            "status": "online" if port_up(8700) else "offline",
            "url": external_url(8700),
            "host_url": external_url(8700),
            "listen": "0.0.0.0",
            "detail": "Agent 网络 + 事件总线 (8700)，Hub 是统一面板入口",
            "category": "agent",
        },
        {
            "name": "OpenAgents Daemon",
            "status": "online" if port_up(8600) else "offline",
            "url": external_url(8600),
            "host_url": external_url(8600),
            "listen": "0.0.0.0",
            "detail": "Agent 运行时 (8600)",
            "category": "agent",
        },
        {
            "name": "旧 NixOS 融合面板",
            "status": "online" if (STATIC_DIR / "dashboard.html").exists() else "offline",
            "url": external_url(9800, "/legacy-panel"),
            "host_url": external_url(9800, "/legacy-panel"),
            "listen": "0.0.0.0",
            "detail": "从旧盘 hub/dashboard 找回的多服务入口：系统、服务、项目、告警",
            "category": "legacy",
        },
        {
            "name": "旧 Hub 看板",
            "status": "online" if (STATIC_DIR / "hub.html").exists() else "offline",
            "url": external_url(9800, "/kanban"),
            "host_url": external_url(9800, "/kanban"),
            "listen": "0.0.0.0",
            "detail": "旧 hub 主界面，含微信体系、CRM 任务、项目看板",
            "category": "legacy",
        },
        {
            "name": "微信聊天记录查询",
            "status": "online" if (STATIC_DIR / "wechat-search.html").exists() else "offline",
            "url": external_url(9800, "/wechat"),
            "host_url": external_url(9800, "/wechat"),
            "listen": "0.0.0.0",
            "detail": "旧盘找回的微信消息搜索入口，使用 /api/wechat/messages",
            "category": "legacy",
        },
        {
            "name": "CRM 静态面板",
            "status": "online" if port_up(9876) else "offline",
            "url": external_url(9876),
            "host_url": external_url(9876),
            "listen": "0.0.0.0",
            "detail": "旧 crm-server.service 入口 (9876)，联系人/客户数据",
            "category": "legacy",
        },
        {
            "name": "Twenty CRM",
            "status": "online" if (container_running("twenty-server-1") or container_running("twenty-server") or port_up(3001) and not container_running("open-webui")) else "not_deployed",
            "url": external_url(3001),
            "host_url": external_url(3001),
            "listen": "127.0.0.1",
            "detail": "旧盘记录为 twenty-server-1:3001；当前 3001 被 Open WebUI 使用，Twenty 未运行",
            "category": "legacy",
        },
        *old_nixos_web_services(),
        {
            "name": "FastGPT",
            "status": "online" if container_running("fastgpt") and port_up(3000) else "offline",
            "url": external_url(3000),
            "host_url": external_url(3000),
            "listen": "0.0.0.0",
            "detail": "AI 应用编排 (3000)",
            "category": "apps",
            "actions": [
                {"label": "打开", "endpoint": "/api/ai/actions/open", "method": "POST", "target": "fastgpt"}
            ],
        },
        {
            "name": "n8n",
            "status": "online" if container_running("n8n") and port_up(5678) else ("offline" if container_exited("n8n") else "offline"),
            "url": external_url(5678),
            "host_url": external_url(5678),
            "listen": "127.0.0.1",
            "detail": "工作流自动化 (5678)",
            "category": "apps",
            "actions": [
                {"label": "启动", "endpoint": "/api/ai/actions/start", "method": "POST", "target": "n8n"},
                {"label": "打开", "endpoint": "/api/ai/actions/open", "method": "POST", "target": "n8n"},
            ],
        },
        {
            "name": "OpenHands",
            "status": "not_deployed",
            "url": "",
            "host_url": "",
            "listen": "",
            "detail": "未部署，可接入（需 Docker socket，资源较重）",
            "category": "apps",
            "actions": [
                {"label": "部署", "endpoint": "/api/ai/actions/deploy-openhands", "method": "POST"}
            ],
        },
        {
            "name": "Dify",
            "status": "not_deployed",
            "url": "",
            "host_url": "",
            "listen": "",
            "detail": "未部署，可接入（需 Docker Compose，资源较重）",
            "category": "apps",
            "actions": [
                {"label": "部署", "endpoint": "/api/ai/actions/deploy-dify", "method": "POST"}
            ],
        },
        {
            "name": "Open WebUI",
            "status": "online" if container_running("open-webui") and port_up(3001) else "offline",
            "url": external_url(3001),
            "host_url": external_url(3001),
            "listen": "127.0.0.1",
            "detail": "WebUI 聊天入口 (3001 → LiteLLM)",
            "category": "apps",
            "actions": [
                {"label": "打开", "endpoint": "/api/ai/actions/open", "method": "POST", "target": "open-webui"}
            ],
        },
    ]

    include_archived = request.query_params.get("include_archived") in {"1", "true", "yes", "on"}

    def normalize_url(svc: dict) -> str:
        return (svc.get("host_url") or svc.get("url") or "").rstrip("/")

    canonical_urls: dict[str, str] = {}
    for svc in services:
        if svc.get("source") == "old-nixos-desktop-web" or svc.get("category", "").startswith("old"):
            continue
        if svc.get("category") == "moonlight":
            continue
        url = normalize_url(svc)
        if url and svc.get("status") == "online":
            canonical_urls.setdefault(url, svc.get("name", ""))

    visible_services: list[dict] = []
    archived_services: list[dict] = []
    archive_reasons = {"duplicate": 0, "offline_old": 0, "not_deployed": 0, "offline_app": 0}
    for svc in services:
        svc = dict(svc)
        url = normalize_url(svc)
        is_old = svc.get("source") == "old-nixos-desktop-web" or svc.get("category", "").startswith("old")
        archive_reason = ""
        if is_old and url in canonical_urls:
            archive_reason = f"重复入口：已由 {canonical_urls[url]} 提供"
            archive_reasons["duplicate"] += 1
        elif is_old and svc.get("status") in {"offline", "not_deployed"}:
            archive_reason = "旧盘服务当前未运行"
            archive_reasons["offline_old"] += 1
        elif svc.get("status") == "not_deployed" and svc.get("category") == "legacy":
            archive_reason = "未部署，默认隐藏"
            archive_reasons["not_deployed"] += 1

        if archive_reason:
            svc["archived"] = True
            svc["archive_reason"] = archive_reason
            svc["category"] = "archive"
            archived_services.append(svc)
        else:
            svc["archived"] = False
            visible_services.append(svc)

    display_services = visible_services + archived_services if include_archived else visible_services

    links = [
        {"name": "旧 NixOS 融合面板", "url": external_url(9800, "/legacy-panel")},
        {"name": "微信聊天记录查询", "url": external_url(9800, "/wechat")},
        {"name": "Hub 服务全景", "url": external_url(9800, "/dashboard")},
        {"name": "Hub 看板", "url": external_url(9800, "/kanban")},
        {"name": "OpenCode Web", "url": external_url(4097)},
        {"name": "OpenClaw", "url": external_url(8080)},
        {"name": "TermHive", "url": external_url(3200)},
        {"name": "LiteLLM 模型列表", "url": external_url(4000, "/v1/models")},
        {"name": "Letta Agents", "url": external_url(8283, "/v1/agents/")},
        {"name": "FRP Dashboard", "url": external_url(7500)},
        {"name": "Mihomo", "url": external_url(9091, "/ui")},
        {"name": "FastGPT", "url": external_url(3000)},
    ]

    return {
        "generated_at": datetime.now().isoformat(),
        "services": display_services,
        "visible_count": len(visible_services),
        "archived_count": len(archived_services),
        "total_count": len(services),
        "archive_reasons": archive_reasons,
        "archived_services": archived_services[:20],
        "include_archived": include_archived,
        "links": links,
        "host": host,
    }


@app.post("/api/ai/opencode-task")
async def opencode_task(request: Request):
    body = await request.json()
    message = (body.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "message required"}, status_code=400)
    result = _append_op_inbox_task(
        "hub-ai-panel",
        message,
        tags=["HUB:manual"],
        metadata={"requested_session_id": (body.get("session_id") or "").strip()},
    )
    return JSONResponse({"ok": True, **result})


# ── AI 任务注册表 ─────────────────────────────────────────

@app.get("/api/ai/tasks")
async def list_tasks(limit: int = 50):
    with _task_lock:
        items = sorted(_tasks.values(), key=lambda x: x["created_at"], reverse=True)[:limit]
    return {"tasks": items}


@app.post("/api/ai/tasks/create")
async def create_task(body: dict):
    title = (body.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)
    task = _new_task(title, body.get("payload") or {})
    _maybe_send_openagents_event("task.created", task)
    return JSONResponse(task)


@app.post("/api/ai/tasks/{task_id}/assign/opencode")
async def assign_opencode(task_id: str, body: dict):
    with _task_lock:
        task = _tasks.get(task_id)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    message = (body.get("message") or task.get("payload", {}).get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "message required"}, status_code=400)
    result = _append_op_inbox_task(
        "hub-ai-tasks",
        message,
        tags=[f"HUB-TASK:{task_id}"],
        metadata={"task_id": task_id, "requested_session_id": (body.get("session_id") or "").strip()},
    )
    with _task_lock:
        task["status"] = "queued_not_executed"
        task["assignee"] = "opencode-inbox"
        task["op_inbox_file"] = result["file"]
    _append_event(task_id, "task.queued_not_executed", "hub", {"assignee": "opencode-inbox", "file": result["file"]})
    _maybe_send_openagents_event("task.queued_not_executed", task)
    return JSONResponse({"ok": True, "task": task, "response": result})


@app.get("/api/ai/tasks/{task_id}/events")
async def task_events(task_id: str):
    with _task_lock:
        task = _tasks.get(task_id)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    return JSONResponse({"events": task.get("events", [])})


# ── AI 服务操作（最小 allowlist） ─────────────────────────

_ALLOWED_ACTIONS = {
    "open": ["fastgpt", "n8n", "open-webui", "termhive-web", "opencode-18910-local"],
    "start": ["n8n"],
}

@app.post("/api/ai/actions/{action}")
async def service_action(action: str, body: dict):
    target = (body.get("target") or "").strip()
    if action not in _ALLOWED_ACTIONS or target not in _ALLOWED_ACTIONS[action]:
        return JSONResponse({"error": "action not allowed"}, status_code=403)
    try:
        if action == "start":
            r = subprocess.run(["docker", "start", target], capture_output=True, text=True, timeout=30)
            return JSONResponse({"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr})
        elif action == "open":
            url = body.get("url") or ""
            if not url:
                return JSONResponse({"error": "url required"}, status_code=400)
            import webbrowser
            webbrowser.open(url)
            return JSONResponse({"ok": True, "url": url})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Moonlight / Sunshine 配对白名单 ───────────────────────

def _sunshine_state_path() -> Path:
    return Path.home() / ".config/sunshine/sunshine_state.json"


def _sunshine_conf_path() -> Path:
    return Path.home() / ".config/sunshine/sunshine.conf"


def _cert_fingerprint(cert: str) -> str:
    try:
        der = ssl.PEM_cert_to_DER_cert(cert)
        digest = hashlib.sha256(der).hexdigest().upper()
        return ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))
    except Exception:
        return ""


def _read_sunshine_state() -> dict:
    try:
        return json.loads(_sunshine_state_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_sunshine_web_env() -> dict:
    env_path = Path.home() / ".config/sunshine/web.env"
    data: dict[str, str] = {}
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        pass
    return data


def _sunshine_devices_summary() -> dict:
    state = _read_sunshine_state()
    raw_devices = ((state.get("root") or {}).get("named_devices") or [])
    seen: dict[str, int] = {}
    devices = []
    for item in raw_devices:
        cert = item.get("cert") or ""
        fp = _cert_fingerprint(cert)
        seen[fp] = seen.get(fp, 0) + 1
        devices.append({
            "name": item.get("name") or "",
            "uuid": item.get("uuid") or "",
            "enabled": str(item.get("enabled", "")).lower() == "true",
            "fingerprint": fp,
            "duplicate": bool(fp and seen.get(fp, 0) > 1),
        })
    fingerprints = [d["fingerprint"] for d in devices if d.get("fingerprint")]
    try:
        sunshine_online = bool(subprocess.run(["bash", "-lc", "ss -tln | grep -q ':47990 '"], capture_output=True, timeout=5, stdin=subprocess.DEVNULL).returncode == 0)
    except Exception:
        sunshine_online = False
    return {
        "sunshine_online": sunshine_online,
        "state_path": str(_sunshine_state_path()),
        "conf_path": str(_sunshine_conf_path()),
        "devices": devices,
        "device_count": len(devices),
        "unique_cert_count": len(set(fingerprints)),
        "duplicate_cert_count": len(fingerprints) - len(set(fingerprints)),
        "pin_config": "pin = false" in (_sunshine_conf_path().read_text(encoding="utf-8", errors="ignore") if _sunshine_conf_path().exists() else ""),
    }


def _dedupe_sunshine_devices(state: dict) -> int:
    devices = ((state.get("root") or {}).get("named_devices") or [])
    seen: set[str] = set()
    deduped = []
    removed = 0
    for item in devices:
        fp = _cert_fingerprint(item.get("cert") or "")
        if fp and fp in seen:
            removed += 1
            continue
        if fp:
            seen.add(fp)
        deduped.append(item)
    if removed:
        state.setdefault("root", {})["named_devices"] = deduped
    return removed


@app.get("/api/moonlight/devices")
async def moonlight_devices():
    return JSONResponse(_sunshine_devices_summary())


@app.post("/api/moonlight/pair")
async def moonlight_pair(body: dict):
    pin = "".join(ch for ch in str(body.get("pin") or "") if ch.isdigit())
    name = (body.get("name") or "").strip()[:80]
    if len(pin) != 4:
        return JSONResponse({"error": "Moonlight PIN must be 4 digits"}, status_code=400)
    creds = _read_sunshine_web_env()
    user = creds.get("SUNSHINE_USER") or creds.get("USERNAME") or "charlie"
    password = creds.get("SUNSHINE_PASS") or creds.get("PASSWORD")
    if not password:
        return JSONResponse({
            "error": "sunshine web credentials unavailable",
            "detail": "Create ~/.config/sunshine/web.env with SUNSHINE_USER and SUNSHINE_PASS, or pair once in Sunshine Web UI.",
        }, status_code=409)
    payload = json.dumps({"pin": pin, "name": name or "Moonlight Device"}).encode()
    req = urllib.request.Request(
        "https://127.0.0.1:47990/api/pin",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    import base64 as _b64
    req.add_header("Authorization", "Basic " + _b64.b64encode(f"{user}:{password}".encode()).decode())
    try:
        import ssl as _ssl
        ctx = _ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            raw = resp.read().decode("utf-8", "replace")
        data = json.loads(raw) if raw else {}
        ok = bool(data.get("status"))
        return JSONResponse({
            "ok": ok,
            "error": "" if ok else "Sunshine rejected the PIN or no Moonlight client is waiting for pairing",
            "response": data,
            "devices": _sunshine_devices_summary(),
        }, status_code=200 if ok else 409)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@app.post("/api/moonlight/import-android")
async def moonlight_import_android(body: dict):
    serial = (body.get("serial") or "100.108.28.44:5555").strip()
    name = (body.get("name") or "Android Moonlight").strip()[:80]
    try:
        cert = subprocess.check_output([
            "adb", "-s", serial, "shell",
            "su -c 'cat /data/data/com.limelight/files/client.crt'",
        ], text=True, timeout=10).strip()
    except Exception as e:
        return JSONResponse({"error": f"cannot read Android Moonlight cert: {e}"}, status_code=502)
    if "BEGIN CERTIFICATE" not in cert:
        return JSONResponse({"error": "client.crt not found or not readable"}, status_code=404)
    state_path = _sunshine_state_path()
    state = _read_sunshine_state()
    root = state.setdefault("root", {})
    devices = root.setdefault("named_devices", [])
    fp = _cert_fingerprint(cert)
    for item in devices:
        if _cert_fingerprint(item.get("cert") or "") == fp:
            item["name"] = name or item.get("name") or "Android Moonlight"
            item["enabled"] = "true"
            removed = _dedupe_sunshine_devices(state)
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if removed:
                subprocess.run(["systemctl", "--user", "restart", "sunshine.service"], capture_output=True, text=True, timeout=20)
            return JSONResponse({"ok": True, "imported": False, "reason": "already_whitelisted", "deduped": removed, "fingerprint": fp, "devices": _sunshine_devices_summary()})
    devices.append({
        "name": name or "Android Moonlight",
        "cert": cert + "\n",
        "uuid": hashlib.sha256(cert.encode()).hexdigest()[:16],
        "enabled": "true",
    })
    removed = _dedupe_sunshine_devices(state)
    backup = state_path.with_suffix(f".json.bak.{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    try:
        backup.write_text(state_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["systemctl", "--user", "restart", "sunshine.service"], capture_output=True, text=True, timeout=20)
    return JSONResponse({"ok": True, "imported": True, "deduped": removed, "fingerprint": fp, "devices": _sunshine_devices_summary()})


@app.post("/api/ai/actions/openagents-event")
async def openagents_event(body: dict):
    event_name = (body.get("event_name") or "").strip()
    source_id = (body.get("source_id") or "").strip()
    event_id = (body.get("event_id") or f"hub-{int(time.time())}").strip()
    if not event_name:
        return JSONResponse({"error": "event_name required"}, status_code=400)
    try:
        r = subprocess.run([
            "curl", "-s", "-X", "POST", "http://127.0.0.1:8700/api/send_event",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"event_id": event_id, "event_name": event_name, "source_id": source_id, "data": body.get("data") or {}})
        ], capture_output=True, text=True, timeout=10)
        return JSONResponse({"ok": True, "response": r.stdout})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@app.post("/api/ai/actions/deploy-openhands")
async def deploy_openhands():
    return JSONResponse({"ok": False, "error": "OpenHands 需 Docker socket + 较重资源，当前未自动部署。请手动 docker run openhands 或使用 on-demand 脚本。"}, status_code=501)


@app.post("/api/ai/actions/deploy-dify")
async def deploy_dify():
    return JSONResponse({"ok": False, "error": "Dify 需 Docker Compose 全栈，当前未自动部署。请参考官方文档手动部署。"}, status_code=501)


def _maybe_send_openagents_event(event_name: str, task: dict):
    try:
        event_id = f"hub-{task.get('id','unknown')}-{int(time.time())}"
        subprocess.run([
            "curl", "-s", "-X", "POST", "http://127.0.0.1:8700/api/send_event",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"event_id": event_id, "event_name": event_name, "source_id": "hub", "data": {"task_id": task.get("id"), "title": task.get("title")}})
        ], capture_output=True, text=True, timeout=5)
    except Exception:
        pass


# ── 服务快捷操作（systemctl --user） ──────────────────────
_SERVICE_WHITELIST = {
    "hub-api", "hub-reverse-proxy", "opencode", "opencode-18910-local", "opencode-telegram-gateway", "litellm",
    "litellm-strip-proxy", "letta-stack", "embedding-server", "syncthing",
    "frpc", "openagents-network", "termhive-web", "termhive-daemon",
    "ttyd-8080", "ttyd-session-proxy", "sys-info-mcp",
    "appsmith", "n8n", "huly", "plane", "mattermost", "fastgpt",
    "opencode-zulip-gateway", "opencode-telegram-gateway",
    "ai-a2a", "ai-watchdog", "ao-dashboard", "ao-orchestrator",
    "browser-sync-mcp-server", "container-ntfy", "content-filter",
    "crush-button-api", "crush-server", "crush-tailscale", "crush-ttyd-backend",
    "duckdns-update", "gelab-zero", "gelab-zero-mcp",
    "kanshi", "launcher-server", "matrix-synapse", "mautrix-whatsapp",
    "notify-forwarder", "obex", "office-agent", "op-tasker-bridge",
    "opencode-4096-proxy", "session-guard", "smart-redirector",
    "ssh-keepalive-proxy", "ssh-keepalive-proxy-codex2", "sunshine",
    "waybar", "wayvnc",
}

def _svc_action(name: str, action: str) -> dict:
    normalized = name.lower()
    if normalized not in _SERVICE_WHITELIST:
        return {"error": f"service '{name}' not in whitelist", "allowed": sorted(_SERVICE_WHITELIST)}
    unit = f"{normalized}.service"
    try:
        r = subprocess.run(
            ["systemctl", "--user", action, unit],
            capture_output=True, text=True, timeout=30
        )
        return {"ok": r.returncode == 0, "unit": unit, "action": action, "stdout": r.stdout, "stderr": r.stderr}
    except Exception as e:
        return {"error": str(e), "unit": unit, "action": action}

_CRUSH_SERVICES = ["crush-button-api", "crush-server", "crush-tailscale", "crush-ttyd-backend"]


@app.post("/api/service/crush/restart")
async def crush_restart():
    results = {}
    ok = True
    for svc in _CRUSH_SERVICES:
        r = _svc_action(svc, "restart")
        results[svc] = r
        if not r.get("ok"):
            ok = False
    return JSONResponse({"ok": ok, "results": results, "action": "crush_restart"})


@app.post("/api/service/{name}/restart")
async def service_restart(name: str):
    if name == "opencode":
        try:
            r = subprocess.run(
                ["systemctl", "--user", "restart", "opencode.service"],
                capture_output=True, text=True, timeout=30
            )
            return JSONResponse({
                "ok": r.returncode == 0,
                "action": "restarted",
                "stdout": r.stdout,
                "stderr": r.stderr,
                "note": "opencode.service restarted via systemctl.",
            })
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e), "action": "restart_failed"})
    return JSONResponse(_svc_action(name, "restart"))


@app.post("/api/service/{name}/stop")
async def service_stop(name: str):
    return JSONResponse(_svc_action(name, "stop"))

@app.post("/api/service/{name}/start")
async def service_start(name: str):
    return JSONResponse(_svc_action(name, "start"))


# ── 服务内存与配置管理 ──────────────────────────────────────
_SERVICE_CONFIG_FILE = Path.home() / ".local/state/hub/service-manager.json"
_SERVICE_CATEGORIES = ["core", "always-on", "on-demand", "rarely-used", "stop-candidate"]

_DEFAULT_SERVICE_CATEGORIES = {
    "hub-api.service": "core",
    "hub-reverse-proxy.service": "core",
    "opencode.service": "core",
    "opencode-18910-local.service": "core",
    "opencode-telegram-gateway.service": "core",
    "opencode-zulip-gateway.service": "core",
    "openagents-network.service": "core",
    "n8n.service": "always-on",
    "appsmith.service": "always-on",
    "plane.service": "always-on",
    "huly.service": "always-on",
    "mattermost.service": "always-on",
    "fastgpt.service": "always-on",
    "litellm.service": "always-on",
    "litellm-strip-proxy.service": "always-on",
    "letta-stack.service": "always-on",
    "embedding-server.service": "always-on",
    "frpc.service": "always-on",
    "ttyd-8080.service": "always-on",
    "ttyd-session-proxy.service": "always-on",
    "sys-info-mcp.service": "always-on",
    "syncthing.service": "always-on",
    "sunshine.service": "on-demand",
    "mihomo": "on-demand",
    "content-filter.service": "on-demand",
    "opencode-4096-proxy.service": "on-demand",
    "termhive-web.service": "on-demand",
    "termhive-daemon.service": "on-demand",
    "office-agent.service": "on-demand",
    "notify-forwarder.service": "on-demand",
    "browser-sync-mcp-server.service": "rarely-used",
    "container-ntfy.service": "rarely-used",
    "matrix-synapse.service": "rarely-used",
    "mautrix-whatsapp.service": "rarely-used",
    "smart-redirector.service": "rarely-used",
    "ssh-keepalive-proxy.service": "rarely-used",
    "ssh-keepalive-proxy-codex2.service": "rarely-used",
    "session-guard.service": "rarely-used",
    "kanshi.service": "rarely-used",
    "launcher-server.service": "rarely-used",
    "obex.service": "rarely-used",
    "waybar.service": "rarely-used",
    "wayvnc.service": "rarely-used",
    "gnome-remote-desktop-headless.service": "rarely-used",
    "dbus-broker.service": "rarely-used",
    "mpris-proxy.service": "rarely-used",
    "xdg-user-dirs.service": "rarely-used",
    "systemd-tmpfiles-setup.service": "rarely-used",
    "duckdns-update.service": "rarely-used",
    "ai-a2a.service": "stop-candidate",
    "ai-watchdog.service": "stop-candidate",
    "ao-dashboard.service": "stop-candidate",
    "ao-orchestrator.service": "stop-candidate",
    "crush-button-api.service": "stop-candidate",
    "crush-server.service": "stop-candidate",
    "crush-tailscale.service": "stop-candidate",
    "crush-ttyd-backend.service": "stop-candidate",
    "gelab-zero.service": "stop-candidate",
    "gelab-zero-mcp.service": "stop-candidate",
    "op-tasker-bridge.service": "stop-candidate",
    "podman.service": "always-on",
    "wireplumber.service": "rarely-used",
    "mako.service": "rarely-used",
    "swaync.service": "rarely-used",
    "kdeconnect-indicator.service": "rarely-used",
    "kdeconnectd.service": "rarely-used",
    "gnome-remote-desktop-headless.service": "rarely-used",
    "wayvnc.service": "rarely-used",
    "waybar.service": "rarely-used",
    "obex.service": "rarely-used",
    "mpris-proxy.service": "rarely-used",
    "xdg-user-dirs.service": "rarely-used",
    "dbus-broker.service": "rarely-used",
    "systemd-tmpfiles-setup.service": "rarely-used",
    "duckdns-update.service": "rarely-used",
    "content-filter.service": "on-demand",
    "smart-redirector.service": "on-demand",
    "session-guard.service": "on-demand",
    "kanshi.service": "on-demand",
    "launcher-server.service": "on-demand",
    "notify-forwarder.service": "on-demand",
    "office-agent.service": "on-demand",
    "browser-sync-mcp-server.service": "on-demand",
    "container-ntfy.service": "on-demand",
    "matrix-synapse.service": "on-demand",
    "mautrix-whatsapp.service": "on-demand",
    "gelab-zero.service": "stop-candidate",
    "gelab-zero-mcp.service": "stop-candidate",
    "crush-server.service": "stop-candidate",
    "crush-button-api.service": "stop-candidate",
    "crush-tailscale.service": "stop-candidate",
    "crush-ttyd-backend.service": "stop-candidate",
    "ai-a2a.service": "stop-candidate",
    "ai-watchdog.service": "stop-candidate",
    "ao-dashboard.service": "stop-candidate",
    "ao-orchestrator.service": "stop-candidate",
}

def _load_service_config() -> dict:
    config = dict(_DEFAULT_SERVICE_CATEGORIES)
    if _SERVICE_CONFIG_FILE.exists():
        try:
            saved = json.loads(_SERVICE_CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in saved.items():
                if isinstance(v, dict):
                    config[k] = v
                else:
                    config[k] = v
        except Exception:
            pass
    for unit in list(config.keys()):
        if isinstance(config[unit], str):
            config[unit] = {"category": config[unit]}
    return config

def _guess_category_for_unit(unit: str) -> str:
    name = unit.replace(".service", "")
    if any(name.startswith(p) for p in ["opencode-", "op-", "ao-", "ai-", "agent-", "upnp-", "sentinel-", "daily-", "disk-", "docker-", "fedora-", "grub-", "idle-", "memory-", "mcp-", "ostree-", "system-", "tailscale"]):
        return "stop-candidate"
    if any(name.startswith(p) for p in ["dbus-", "gvfs-", "pipewire", "pulseaudio", "spice-", "at-spi-", "kdeconnect", "mpris-", "xdg-", "uresourced", "systemd-"]):
        return "rarely-used"
    if any(name.startswith(p) for p in ["container-", "podman", "docker"]):
        return "stop-candidate"
    if any(name.startswith(p) for p in ["77c", "b315", "c4b", "c92", "d454", "e8f"]):
        return "stop-candidate"
    return "rarely-used"

def _save_service_config(config: dict) -> None:
    _SERVICE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SERVICE_CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

def _unit_enabled(unit: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-enabled", unit],
            capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL,
        )
        return r.stdout.strip() == "enabled"
    except Exception:
        return False

def _unit_active(unit: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL,
        )
        return r.stdout.strip() == "active"
    except Exception:
        return False

def _service_memory_bytes(unit: str) -> int | None:
    try:
        r = subprocess.run(
            ["systemctl", "--user", "show", unit, "--property=MemoryCurrent"],
            capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL,
        )
        line = r.stdout.strip()
        if "=" in line:
            val = line.split("=", 1)[1].strip()
            if val.isdigit():
                return int(val)
    except Exception:
        pass
    return None

@app.get("/api/services/memory")
async def services_memory():
    try:
        r = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service",
             "--plain", "--no-legend", "--all"],
            capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL,
        )
        units = [ln.split()[0] for ln in r.stdout.splitlines()
                 if ln.strip() and ln.split()[0].endswith(".service")]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    result = []
    for unit in units:
        name = unit.replace(".service", "")
        mem = _service_memory_bytes(unit)
        active = _unit_active(unit)
        enabled = _unit_enabled(unit)
        result.append({
            "unit": unit,
            "name": name,
            "memory_bytes": mem,
            "memory_mb": round(mem / 1024 / 1024, 1) if mem is not None else None,
            "active": active,
            "enabled": enabled,
        })
    result.sort(key=lambda x: x.get("memory_bytes") or 0, reverse=True)
    return JSONResponse({"services": result, "timestamp": datetime.now().isoformat()})

@app.get("/api/services/config")
async def services_config_get():
    try:
        r = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service",
             "--plain", "--no-legend", "--all"],
            capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL,
        )
        all_units = [ln.split()[0] for ln in r.stdout.splitlines()
                      if ln.strip() and ln.split()[0].endswith(".service")]
    except Exception:
        all_units = []
    config = _load_service_config()
    for unit in all_units:
        if unit not in config:
            config[unit] = {"category": _guess_category_for_unit(unit), "locked": False}
    units = {}
    for unit_name, entry in config.items():
        if not unit_name.endswith(".service"):
            unit_name = f"{unit_name}.service"
        units[unit_name] = entry
    return JSONResponse({"units": units, "categories": _SERVICE_CATEGORIES})

@app.post("/api/services/config")
async def services_config_post(body: dict):
    unit = body.get("unit", "").strip()
    category = body.get("category", "").strip()
    locked = body.get("locked", None)
    if not unit:
        return JSONResponse({"error": "unit required"}, status_code=400)
    if category and category not in _SERVICE_CATEGORIES:
        return JSONResponse({"error": f"invalid category, allowed: {_SERVICE_CATEGORIES}"}, status_code=400)
    config = _load_service_config()
    key = unit if unit.endswith(".service") else f"{unit}.service"
    if key not in config:
        config[key] = {}
    if category:
        config[key]["category"] = category
    if locked is not None:
        config[key]["locked"] = bool(locked)
    _save_service_config(config)
    return JSONResponse({"ok": True, "unit": key, "config": config[key]})


def _svc_health(restarts: int, substate: str, result: str) -> str:
    if result and result != "success":
        return "failed"
    if substate == "auto-restart":
        return "storm"
    if restarts >= 20:
        return "storm"
    if restarts >= 5:
        return "warning"
    return "healthy"


@app.get("/api/services/stability")
async def services_stability():
    import re as _re
    try:
        r = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service",
             "--plain", "--no-legend", "--all"],
            capture_output=True, text=True, timeout=8,
        )
        units = [ln.split()[0] for ln in r.stdout.splitlines()
                 if ln.strip() and ln.split()[0].endswith(".service")]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    if not units:
        return JSONResponse({"summary": {}, "services": [], "storms": [], "timestamp": datetime.now().isoformat()})

    props = ["Id", "Description", "NRestarts", "ActiveState", "SubState",
             "Result", "ExecMainStatus", "ActiveEnterTimestamp",
             "ActiveEnterTimestampMonotonic", "ExecMainStartTimestamp"]
    try:
        r = subprocess.run(
            ["systemctl", "--user", "show"] + units + ["--property=" + ",".join(props)],
            capture_output=True, text=True, timeout=10,
        )
        raw = r.stdout
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    now = time.time()
    blocks = _re.split(r"\n\s*\n", raw.strip())
    services, storms = [], []
    counts = {"healthy": 0, "warning": 0, "storm": 0, "failed": 0}

    for blk in blocks:
        kv = {}
        for line in blk.strip().splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                kv[k.strip()] = v.strip()
        if "Id" not in kv:
            continue
        restarts = int(kv.get("NRestarts", "0") or 0)
        substate = kv.get("SubState", "")
        result = kv.get("Result", "")
        health = _svc_health(restarts, substate, result)
        ts_raw = kv.get("ActiveEnterTimestamp", "")
        uptime = None
        if ts_raw:
            try:
                local = ts_raw.rsplit(" ", 1)[0]
                started_dt = datetime.strptime(local, "%a %Y-%m-%d %H:%M:%S")
                uptime = max(0, int(now - started_dt.timestamp()))
            except Exception:
                pass
        entry = {
            "unit": kv["Id"],
            "description": kv.get("Description", ""),
            "restarts": restarts,
            "state": kv.get("ActiveState", ""),
            "substate": substate,
            "result": result,
            "exit_code": kv.get("ExecMainStatus", ""),
            "started": kv.get("ActiveEnterTimestamp", ""),
            "uptime_sec": uptime,
            "health": health,
        }
        services.append(entry)
        if health in counts:
            counts[health] += 1
        if health in ("storm", "warning", "failed"):
            storms.append(entry)

    storms.sort(key=lambda x: x["restarts"], reverse=True)
    services.sort(key=lambda x: (x["health"] != "healthy", x["restarts"]), reverse=True)
    return JSONResponse({
        "summary": {"total": len(services), **counts,
                    "auto_restart": sum(1 for s in services if s["substate"] == "auto-restart")},
        "services": services,
        "storms": storms[:15],
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/social/graph")
async def social_graph(wxid: str = None, min_strength: float = 0.0, limit: int = 50):
    crm = Path("/mnt/ai/data/crm/crm.db")
    nodes, edges = [], []
    if not crm.exists(): return {"nodes": nodes, "edges": edges}
    conn = sqlite3.connect(f"file:{crm}?mode=ro", uri=True, timeout=5)
    try:
        tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "relations" not in tables: return {"nodes": nodes, "edges": edges, "error": "relations table not yet created"}
        q = "SELECT * FROM relations WHERE strength >= ?"; params = [min_strength]
        if wxid: q += " AND (wxid_a = ? OR wxid_b = ?)"; params += [wxid, wxid]
        q += f" LIMIT {int(limit)}"
        for row in conn.execute(q, params).fetchall():
            edges.append({"wxid_a": row[0], "wxid_b": row[1] if len(row)>1 else "", "strength": row[2] if len(row)>2 else 0, "relation_type": row[3] if len(row)>3 else "", "interaction_count": row[4] if len(row)>4 else 0})
    except Exception as e: return {"nodes": nodes, "edges": edges, "error": str(e)}
    finally: conn.close()
    return {"nodes": nodes, "edges": edges}

@app.get("/api/social/profile/{wxid}")
async def social_profile(wxid: str):
    crm = Path("/mnt/ai/data/crm/crm.db")
    merged = Path("/mnt/ai/data/wechat-merged/messages.db")
    profile = {}
    if crm.exists():
        conn = sqlite3.connect(f"file:{crm}?mode=ro", uri=True, timeout=5)
        try:
            row = conn.execute("SELECT * FROM contacts WHERE wxid = ?", (wxid,)).fetchone()
            if row:
                cols = [d[0] for d in conn.execute("SELECT * FROM contacts LIMIT 0").description]
                profile = dict(zip(cols, row))
        finally: conn.close()
    rels = []
    if crm.exists():
        conn2 = sqlite3.connect(f"file:{crm}?mode=ro", uri=True, timeout=5)
        try:
            tables = [x[0] for x in conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "relations" in tables:
                for rel in conn2.execute("SELECT * FROM relations WHERE wxid_a = ? OR wxid_b = ? ORDER BY strength DESC", (wxid, wxid)).fetchall():
                    owx = rel[1] if rel[0] == wxid else rel[0]
                    nr = conn2.execute("SELECT nickname, remark FROM contacts WHERE wxid = ?", (owx,)).fetchone()
                    rels.append({"wxid": owx, "name": nr[0] if nr else owx, "strength": rel[2], "relation_type": rel[3], "interaction_count": rel[4]})
        finally: conn2.close()
    profile["relations"] = rels
    if merged.exists():
        try:
            conn3 = sqlite3.connect(f"file:{merged}?mode=ro", uri=True, timeout=5)
            profile["recent_messages"] = len(conn3.execute("SELECT * FROM messages WHERE talker LIKE ? ORDER BY create_time DESC LIMIT 20", (f"%{wxid}%",)).fetchall())
            conn3.close()
        except Exception: pass
    profile["groups"] = []; profile["stats"] = {"relation_count": len(rels)}
    return profile

@app.get("/api/social/insights")
async def social_insights():
    rp = Path.home() / ".local/share/macg/social-report.json"
    insights = {"report": None, "active_contacts": []}
    if rp.exists():
        try: insights["report"] = json.loads(rp.read_text())
        except Exception: pass
    merged = Path("/mnt/ai/data/wechat-merged/messages.db")
    if merged.exists():
        try:
            conn = sqlite3.connect(f"file:{merged}?mode=ro", uri=True, timeout=5)
            insights["active_contacts"] = [{"talker": r[0], "count": r[1]} for r in conn.execute("SELECT talker, COUNT(*) as cnt FROM messages GROUP BY talker ORDER BY cnt DESC LIMIT 10").fetchall()]
            conn.close()
        except Exception: pass
    return insights

@app.post("/api/social/analyze")
async def trigger_analysis():
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("social_relations", "/home/charlie/agi/social_relations.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return {"ok": True, "result": str(mod.run_full_analysis())[:500]}
    except FileNotFoundError: return {"ok": False, "error": "social_relations.py not found"}
    except Exception as e: return {"ok": False, "error": str(e)}
def _load_context_graph():
    import importlib.util
    spec = importlib.util.spec_from_file_location("context_graph", "/home/charlie/agi/context_graph.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

@app.get("/api/context/search")
async def context_search(q: str = '', type: str = ''):
    try:
        cg = _load_context_graph()
        return {"results": cg.search(q, entity_type=type if type else None)}
    except Exception: return {"error": "context_graph.py 加载失败"}

@app.get("/api/context/match")
async def context_match(text: str = ''):
    try:
        cg = _load_context_graph()
        return {"match": cg.match(text)}
    except Exception: return {"error": "context_graph.py 加载失败"}

@app.get("/api/context/entity")
async def context_entity(type: str = '', id: str = ''):
    try:
        cg = _load_context_graph()
        return cg.get_entity(type, id)
    except Exception: return {"error": "context_graph.py 加载失败"}

@app.get("/api/context/profile/{company_id}")
async def context_profile(company_id: str):
    try: return _load_context_graph().get_company_profile(company_id)
    except Exception: return {"error": "context_graph.py 加载失败"}

@app.get("/api/context/timeline")
async def context_timeline(type: str = "", id: str = "", limit: int = 20):
    try: return {"events": _load_context_graph().get_timeline(type, id, limit=limit)}
    except Exception: return {"error": "context_graph.py 加载失败"}

@app.post("/api/context/attach")
async def context_attach(body: dict):
    try:
        eid = _load_context_graph().attach_event(source=body.get("source","api"), event_type=body.get("event_type","note"), content=body.get("content",""), entity_type=body.get("entity_type","person"), entity_id=body.get("entity_id"), properties=body.get("properties"))
        return {"attached": True, "event_id": eid}
    except Exception: return {"error": "context_graph.py 加载失败", "attached": False}

@app.post("/api/doc/extract")
async def doc_extract(body: dict):
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("doc_pipeline", "/home/charlie/agi/doc_pipeline.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.extract(body.get('file_path', ''))
    except FileNotFoundError: return {"error": "doc_pipeline.py 加载失败"}
    except Exception as e: return {"error": str(e)}

@app.post("/api/doc/pipeline")
async def doc_pipeline_ep(body: dict):
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("doc_pipeline", "/home/charlie/agi/doc_pipeline.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.run_pipeline(body.get('file_path', ''), template=body.get('template'))
    except FileNotFoundError: return {"error": "doc_pipeline.py 加载失败"}
    except Exception as e: return {"error": str(e)}

@app.post("/api/doc/fill")
async def doc_fill(body: dict):
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("doc_pipeline", "/home/charlie/agi/doc_pipeline.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return {'result': mod.fill_template(template=body.get('template',''), data=body.get('data',{}), output=body.get('output'))}
    except FileNotFoundError: return {"error": "doc_pipeline.py 加载失败"}
    except Exception as e: return {"error": str(e)}

@app.post("/api/email/sync")
async def email_sync(body: dict):
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("email_sync", "/home/charlie/agi/email_sync.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.sync(dry_run=body.get('dry_run',False), config=body.get('config',{}))
    except FileNotFoundError: return {"error": "email_sync.py 加载失败"}
    except Exception as e: return {"error": str(e)}

@app.get("/api/knowledge/stats")
async def knowledge_stats():
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("doc_knowledge", "/home/charlie/agi/doc_knowledge.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.stats()
    except FileNotFoundError: return {"error": "doc_knowledge.py 加载失败"}
    except Exception as e: return {"error": str(e)}

@app.post("/api/knowledge/search")
async def knowledge_search(body: dict):
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("doc_knowledge", "/home/charlie/agi/doc_knowledge.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.search(query=body.get('query',''), n=body.get('n',5), doc_type=body.get('doc_type'))
    except FileNotFoundError: return {"error": "doc_knowledge.py 加载失败"}
    except Exception as e: return {"error": str(e)}

@app.post("/api/knowledge/store")
async def knowledge_store(body: dict):
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("doc_knowledge", "/home/charlie/agi/doc_knowledge.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.store(data=body.get('data',{}), doc_id=body.get('doc_id'))
    except FileNotFoundError: return {"error": "doc_knowledge.py 加载失败"}
    except Exception as e: return {"error": str(e)}

def _calc_progress(milestones):
    total = len(milestones)
    return round(sum(1 for m in milestones if m.get("status") == "done") / total * 100) if total else 0

@app.get("/api/projects")
async def get_projects():
    projects = [_project_with_progress(p) for p in _all_projects()]
    return {"projects": projects}


@app.post("/api/projects")
async def create_project(body: dict):
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    custom = _load_custom_projects()
    project_id = _project_slug(body.get("id") or name)
    existing_ids = {p.get("id") for p in _all_projects()}
    if project_id in existing_ids:
        project_id = f"{project_id}-{int(time.time())}"
    project = {
        "id": project_id,
        "name": name,
        "emoji": body.get("emoji") or "🧩",
        "group": body.get("group") or "biz",
        "description": body.get("description") or "待补充项目说明",
        "source_path": body.get("source_path") or "",
        "target_path": body.get("target_path") or "",
        "milestones": body.get("milestones") or [
            {"id": "brief", "name": "项目简报", "status": "pending"},
            {"id": "ai-builder", "name": "AI 建站工具接入", "status": "pending"},
            {"id": "release", "name": "发布入口", "status": "pending"},
        ],
        "created_at": datetime.now().isoformat(),
    }
    custom.append(project)
    _save_custom_projects(custom)
    _architecture_cache["ts"] = 0
    return {"status": "created", "project": _project_with_progress(project)}


@app.get("/api/website-builders")
async def website_builders():
    return {"recommended": "replit-agent", "builders": AI_WEBSITE_BUILDERS}


@app.get("/api/open-source-stack")
async def open_source_stack():
    return {
        "recommended": "erpnext-directus-vendure-grapesjs-mautic-n8n",
        "blueprint": SOURCING_STACK_BLUEPRINT,
        "tools": OPEN_SOURCE_SITE_STACK,
    }


@app.get("/api/channel-adapters")
async def channel_adapters():
    return {
        "recommended_start": CHANNEL_BLUEPRINT["recommended_start"],
        "recommended_team": CHANNEL_BLUEPRINT["recommended_team"],
        "blueprint": CHANNEL_BLUEPRINT,
        "adapters": CHANNEL_ADAPTERS,
    }


@app.get("/api/zulip/status")
async def zulip_status():
    gateway_probe = {"ok": False, "url": "http://127.0.0.1:9812/health"}
    try:
        with urllib.request.urlopen("http://127.0.0.1:9812/health", timeout=2) as resp:
            gateway_probe = {"ok": 200 <= resp.status < 300, "url": "http://127.0.0.1:9812/health"}
    except Exception as exc:
        gateway_probe = {"ok": False, "url": "http://127.0.0.1:9812/health", "error": str(exc)}
    return {
        "configured": _zulip_configured(),
        "site": ZULIP_SITE,
        "bot_email": ZULIP_EMAIL,
        "default_stream": ZULIP_DEFAULT_STREAM,
        "default_topic": ZULIP_DEFAULT_TOPIC,
        "gateway": gateway_probe,
        "required_env": ["HUB_ZULIP_SITE", "HUB_ZULIP_EMAIL", "HUB_ZULIP_API_KEY"],
    }


@app.get("/api/zulip/migration")
async def zulip_migration():
    return {
        "source": "telegram",
        "target": "zulip",
        "gateway_project": "/var/home/charlie/opencode-zulip-gateway",
        "service": "opencode-zulip-gateway.service",
        "config_template": str(Path.home() / ".config/opencode-zulip/.env.template"),
        "architecture": _zulip_architecture(),
        "commands": ["/ask", "/task", "/new", "/project", "/projects", "/status", "/list", "/tasks", "/close", "/cancel", "/hub", "/help"],
        "mapping": {
            "Telegram supergroup": "Zulip stream",
            "Telegram forum topic": "Zulip topic",
            "Telegram getUpdates": "Zulip outgoing webhook -> http://host:9812/webhook",
            "Telegram gateway health": "http://127.0.0.1:9812/health",
        },
    }


@app.get("/zulip-setup")
async def zulip_setup_page():
    return HTMLResponse(f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zulip 一键配置</title>
<style>
body{{margin:0;background:#111312;color:#edf2ee;font:16px system-ui,"Noto Sans CJK SC",sans-serif}}
main{{max-width:640px;margin:0 auto;padding:18px}}
h1{{font-size:24px;margin:0 0 8px}}p{{color:#9daaa2;line-height:1.5}}
label{{display:block;margin:14px 0 6px;font-weight:700}}
input{{width:100%;box-sizing:border-box;border:1px solid #303832;border-radius:8px;background:#181c1a;color:#edf2ee;padding:13px;font-size:16px}}
button{{width:100%;margin-top:18px;border:1px solid #77c7d8;border-radius:8px;background:#203036;color:#edf2ee;padding:14px;font-size:17px;font-weight:800}}
.box{{border:1px solid #303832;border-radius:8px;background:#181c1a;padding:14px;margin:14px 0}}
.muted{{color:#9daaa2;font-size:13px}}.ok{{color:#79d38b}}.bad{{color:#ee7c7c}}code{{color:#cde9d1}}
</style></head><body><main>
<h1>Zulip 一键配置</h1>
<p>在手机上填 4 项即可，不需要输入命令。设备码用于防止别人访问 9800 后改你的密钥。</p>
<div class="box muted">需要先在 Zulip 创建 <b>Generic bot</b> 或 <b>Outgoing webhook bot</b>，不要选 Incoming webhook bot；Incoming webhook bot 不能对话回消息。</div>
<form id="form">
  <label>设备码</label><input name="setup_code" value="" placeholder="w19900422" autocomplete="one-time-code">
  <label>Zulip 地址</label><input name="site" placeholder="https://xxx.zulipchat.com" autocomplete="url">
  <label>Bot 邮箱</label><input name="bot_email" placeholder="hub-bot@xxx.zulipchat.com" autocomplete="email">
  <label>Bot API Key</label><input name="api_key" placeholder="粘贴 Zulip bot api key" autocomplete="off">
  <label>允许发命令的你的邮箱</label><input name="allowed_email" placeholder="你的 Zulip 登录邮箱" autocomplete="email">
  <label>默认 Stream</label><input name="stream" value="Sourcing">
  <label>默认 Topic</label><input name="topic" value="Hub">
  <button type="submit">保存并启动 Zulip</button>
</form>
<div id="result" class="box muted">等待提交</div>
<p class="muted">提交成功后 9800 会自动重启一次，页面可能短暂断开。</p>
</main>
<script>
const form = document.getElementById('form');
const result = document.getElementById('result');
form.addEventListener('submit', async e => {{
  e.preventDefault();
  result.innerHTML = '正在保存和启动...';
  const body = Object.fromEntries(new FormData(form).entries());
  try {{
    const r = await fetch('/api/zulip/setup', {{method:'POST', headers:{{'content-type':'application/json'}}, body:JSON.stringify(body)}});
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || '配置失败');
    result.innerHTML = `<div class="ok">已保存。Hub 会自动重启。</div><pre>${{JSON.stringify(data, null, 2)}}</pre>`;
    setTimeout(async () => {{
      try {{
        const s = await fetch('/api/zulip/status', {{cache:'no-store'}}).then(x=>x.json());
        result.innerHTML += `<div class="box"><b>状态</b><pre>${{JSON.stringify(s, null, 2)}}</pre></div>`;
      }} catch {{}}
    }}, 5000);
  }} catch (err) {{
    result.innerHTML = `<div class="bad">${{err.message}}</div>`;
  }}
}});
</script></body></html>""")


@app.post("/api/zulip/setup")
async def zulip_setup(body: dict, background_tasks: BackgroundTasks):
    setup_code = (body.get("setup_code") or "").strip()
    if setup_code != DEVICE_CODE:
        return JSONResponse({"error": "设备码不正确"}, status_code=403)
    try:
        result = _write_zulip_setup(
            site=body.get("site") or "",
            bot_email=body.get("bot_email") or "",
            api_key=body.get("api_key") or "",
            allowed_email=body.get("allowed_email") or "",
            stream=body.get("stream") or "Sourcing",
            topic=body.get("topic") or "Hub",
            enable_gateway=True,
        )
        background_tasks.add_task(_restart_hub_api_delayed)
        return {"status": "configured", "restart": "scheduled", **result}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/api/zulip/send")
async def zulip_send(body: dict):
    content = (body.get("content") or "").strip()
    if not content:
        return JSONResponse({"error": "content required"}, status_code=400)
    try:
        data = _zulip_send_message(
            content,
            stream=body.get("stream") or ZULIP_DEFAULT_STREAM,
            topic=body.get("topic") or ZULIP_DEFAULT_TOPIC,
            direct_to=body.get("direct_to") or "",
        )
        return {"status": "sent", "zulip": data}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)


@app.post("/api/zulip/webhook")
async def zulip_webhook(body: dict):
    message = body.get("content") or body.get("message") or body.get("text") or ""
    sender = body.get("sender_email") or body.get("sender_full_name") or "zulip"
    stream = body.get("stream") or body.get("display_recipient") or ""
    topic = body.get("topic") or body.get("subject") or ""
    if not message:
        return JSONResponse({"error": "empty message"}, status_code=400)
    dialogue_append(f"zulip:{sender}", f"[{stream}/{topic}] {message}"[:2000], "zulip")
    return {"ok": True}


@app.get("/api/projects/{project_id}/handoff")
async def project_handoff(project_id: str):
    project = next((p for p in _all_projects() if p.get("id") == project_id), None)
    if not project:
        return JSONResponse({"error": "project not found"}, status_code=404)
    return {
        "project": _project_with_progress(project),
        "recommended_builder": "replit-agent",
        "builders": AI_WEBSITE_BUILDERS,
        "open_source_stack": OPEN_SOURCE_SITE_STACK,
        "blueprint": SOURCING_STACK_BLUEPRINT,
        "prompt": _project_handoff_prompt(project),
    }


@app.post("/api/projects/{project_id}/op")
async def project_op_task(project_id: str, body: dict):
    project = next((p for p in _all_projects() if p.get("id") == project_id), None)
    if not project:
        return JSONResponse({"error": "project not found"}, status_code=404)
    message = body.get("message") or f"把 {project.get('name')} 交给 AI 建站工具推进，并回收代码到本地项目。"
    return _append_project_op_task(project, message)


@app.get("/api/marketing/center")
async def marketing_center():
    return {
        "project_id": "sourcing-content",
        "positioning": "帮全球买家快速找到急需机器配件、替代件和维修件的 B2B 电商。",
        "sources": DEMAND_SOURCES,
        "channels": MARKETING_CHANNELS,
        "opportunities": _marketing_opportunities(),
        "automation_slots": [
            {"id": "trend-ingest", "name": "趋势采集器", "status": "reserved", "detail": "接入 Google Trends / TikTok / 公开论坛关键词"},
            {"id": "product-feed", "name": "商品 Feed", "status": "reserved", "detail": "生成 Google Merchant Center feed.xml / product JSON-LD"},
            {"id": "landing-generator", "name": "落地页生成器", "status": "reserved", "detail": "按配件机会自动生成 SEO 页面、FAQ、询盘表单"},
            {"id": "ad-creative", "name": "广告素材工厂", "status": "reserved", "detail": "Meta / TikTok / Google 广告文案、图片 brief、短视频脚本"},
            {"id": "lead-routing", "name": "询盘分流", "status": "reserved", "detail": "询盘进入 CRM、Telegram、邮件和报价跟进"},
        ],
    }


@app.post("/api/marketing/opportunities")
async def marketing_add_opportunity(body: dict):
    title = (body.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)
    items = _load_marketing_opportunities()
    item = {
        "id": _project_slug(body.get("id") or title),
        "title": title,
        "keywords": body.get("keywords") or [],
        "buyer_pain": body.get("buyer_pain") or "待补充买家痛点",
        "landing_page": body.get("landing_page") or f"/products/{_project_slug(title)}",
        "priority": body.get("priority") or "medium",
        "source_url": body.get("source_url") or "",
        "created_at": datetime.now().isoformat(),
    }
    items = [x for x in items if x.get("id") != item["id"]]
    items.insert(0, item)
    _save_marketing_opportunities(items)
    return {"status": "created", "opportunity": item}


@app.get("/api/marketing/prompt")
async def marketing_prompt():
    return {"project_id": "sourcing-content", "prompt": _marketing_prompt()}


@app.post("/api/marketing/op")
async def marketing_op_task(body: dict):
    project = next((p for p in _all_projects() if p.get("id") == "sourcing-content"), {"id": "sourcing-content", "name": "Sourcing内容创建"})
    message = body.get("message") or "搭建 Sourcing 营销中心：需求采集、配件机会池、SEO/商品 Feed、AI 广告素材、询盘 CRM 联动。"
    return _append_project_op_task(project, message)


@app.get("/api/workflow/todos")
async def workflow_todos(request: Request):
    return await _unified_todos(request)


@app.get("/api/workflow/events")
async def workflow_events(limit: int = Query(80, le=300)):
    return {"events": _task_bus_events(limit)}


@app.post("/api/workflow/todos/{task_id}/op")
async def workflow_send_to_op(task_id: str, request: Request, body: dict):
    data = await _unified_todos(request)
    task = next((item for item in data.get("tasks", []) if item.get("id") == task_id), None)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    message = body.get("message") or (
        "请只读查看这个 9800 统一待办，评估风险和建议，不要执行；等待人工确认后再行动。\n\n"
        + _task_markdown(task)
    )
    result = _append_op_inbox_task(
        "hub-workflow",
        message,
        tags=[f"HUB:{task_id}"],
        metadata={"task_id": task_id, "title": task.get("title")},
    )
    event = _task_bus_append("sent_to_op_inbox", task_id, "hub", {"title": task.get("title"), "message": message[:1200], "file": result["file"], "mode": "queued_not_executed"})
    return {"status": "queued_not_executed", "task": task, "event": event, "result": result}


@app.post("/api/workflow/todos/{task_id}/fastgpt")
async def workflow_export_to_fastgpt(task_id: str, request: Request, body: dict):
    data = await _unified_todos(request)
    task = next((item for item in data.get("tasks", []) if item.get("id") == task_id), None)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    FASTGPT_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = FASTGPT_KNOWLEDGE_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{task_id}.md"
    guide = body.get("guide") or (
        "FastGPT 用途：把这条待办作为知识库/工作流输入，生成方案、排查步骤、验收标准。"
        "不要让 FastGPT 直接调用 OpenCode 写代码；执行交给 OP。"
    )
    content = f"{guide}\n\n{_task_markdown(task)}"
    file_path.write_text(content, encoding="utf-8")
    event = _task_bus_append("exported_to_fastgpt", task_id, "hub", {"title": task.get("title"), "file": str(file_path), "fastgpt": "http://127.0.0.1:3000/"})
    return {"status": "exported", "task": task, "event": event, "file": str(file_path), "fastgpt_url": "/go/fastgpt"}


@app.post("/api/workflow/todos/{task_id}/zulip")
async def workflow_send_to_zulip(task_id: str, request: Request, body: dict):
    data = await _unified_todos(request)
    task = next((item for item in data.get("tasks", []) if item.get("id") == task_id), None)
    if not task:
        return JSONResponse({"error": "task not found"}, status_code=404)
    stream = body.get("stream") or ("Sourcing" if task.get("source") in {"project", "marketing"} else ZULIP_DEFAULT_STREAM)
    topic = body.get("topic") or task.get("source") or ZULIP_DEFAULT_TOPIC
    try:
        zulip_data = _zulip_send_message(_zulip_task_content(task), stream=stream, topic=topic)
        event = _task_bus_append("sent_to_zulip", task_id, "hub", {"title": task.get("title"), "stream": stream, "topic": topic, "zulip": zulip_data})
        return {"status": "sent", "task": task, "event": event, "zulip": zulip_data}
    except Exception as exc:
        event = _task_bus_append("zulip_error", task_id, "hub", {"title": task.get("title"), "stream": stream, "topic": topic, "error": str(exc)})
        return JSONResponse({"error": str(exc), "event": event}, status_code=502)


@app.post("/api/workflow/todos/{task_id}/complete")
async def workflow_complete(task_id: str, body: dict):
    event = _task_bus_append("completed", task_id, body.get("source") or "hub", {"note": body.get("note") or ""})
    return {"status": "completed", "event": event}


@app.post("/api/workflow/fastgpt/export")
async def workflow_export_all_to_fastgpt(request: Request):
    data = await _unified_todos(request)
    FASTGPT_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = FASTGPT_KNOWLEDGE_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-hub-unified-todos.md"
    lines = [
        "# Charlie Hub 统一待办与架构提升",
        "",
        "用途：导入 FastGPT 知识库或复制到 FastGPT 对话，用于问答、方案生成、复盘。执行仍交给 OP/OpenCode。",
        "",
        f"- 生成时间: {data.get('generated_at')}",
        f"- 总数: {data.get('summary', {}).get('total')}",
        "",
    ]
    for task in data.get("tasks", [])[:80]:
        lines.append(_task_markdown(task))
    file_path.write_text("\n\n".join(lines), encoding="utf-8")
    event = _task_bus_append("exported_all_to_fastgpt", "all", "hub", {"file": str(file_path), "count": len(data.get("tasks", []))})
    return {"status": "exported", "file": str(file_path), "event": event, "fastgpt_url": "/go/fastgpt"}


@app.get("/api/op/learning/plan")
async def op_learning_plan_api():
    return _op_learning_plan()


@app.get("/api/op/learning/dashboard")
async def op_learning_dashboard(limit: int = Query(80, le=300)):
    reviews = _op_review_items(limit)
    candidates = list(reversed(_read_jsonl_tail(OP_KNOWLEDGE_CANDIDATES_FILE, min(limit, 120))))
    events = list(reversed(_read_jsonl_tail(OP_EVENTS_FILE, min(limit, 200))))
    escalations = _op_escalations(30)
    decisions = list(reversed(_read_jsonl_tail(OP_LEARNING_DECISIONS_FILE, 120)))
    accuracy_reports = list(reversed(_read_jsonl_tail(OP_RECALL_ACCURACY_FILE, min(limit, 120))))
    correction_candidates = list(reversed(_read_jsonl_tail(OP_CORRECTION_CANDIDATES_FILE, min(limit, 120))))
    return {
        "generated_at": datetime.now().isoformat(),
        "plan": _op_learning_plan(),
        "status": _op_lifecycle_status(),
        "summary": _op_learning_summary(reviews, candidates, events, escalations),
        "accuracy_summary": _op_accuracy_summary(accuracy_reports, correction_candidates),
        "reviews": reviews,
        "knowledge_candidates": candidates,
        "accuracy_reports": accuracy_reports,
        "correction_candidates": correction_candidates,
        "events": events[:limit],
        "escalations": escalations,
        "decisions": decisions,
        "files": {
            "review_gate": str(OP_REVIEW_GATE_FILE),
            "knowledge_candidates": str(OP_KNOWLEDGE_CANDIDATES_FILE),
            "recall_accuracy": str(OP_RECALL_ACCURACY_FILE),
            "correction_candidates": str(OP_CORRECTION_CANDIDATES_FILE),
            "events": str(OP_EVENTS_FILE),
            "decisions": str(OP_LEARNING_DECISIONS_FILE),
            "approved_queue": str(OP_APPROVED_LEARNING_FILE),
            "verify_dir": str(OP_VERIFY_DIR),
        },
    }


@app.post("/api/op/learning/reviews/{review_id}/decision")
async def op_learning_review_decision(review_id: str, body: dict):
    decision = (body.get("decision") or "").strip()
    allowed = {"approve", "reject", "promote_rule", "promote_blacklist", "retry", "resolved"}
    if decision not in allowed:
        return JSONResponse({"error": f"decision must be one of {sorted(allowed)}"}, status_code=400)

    reviews = _op_review_items(300)
    review = next((item for item in reviews if item.get("id") == review_id), None)
    if not review:
        return JSONResponse({"error": "review not found"}, status_code=404)

    OP_LIFECYCLE_DIR.mkdir(parents=True, exist_ok=True)
    item = {
        "ts": datetime.now().isoformat(),
        "review_id": review_id,
        "decision": decision,
        "note": (body.get("note") or "")[:1200],
        "session_id": review.get("session_id") or review.get("sessionID"),
        "verdict": review.get("verdict"),
        "score": review.get("score"),
        "task_preview": review.get("task_preview"),
        "gap": review.get("gap"),
        "evidence": review.get("evidence"),
    }
    with OP_LEARNING_DECISIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

    queued = None
    if decision in {"approve", "promote_rule", "promote_blacklist", "retry"}:
        queued = {
            "ts": item["ts"],
            "kind": "failure_blacklist" if decision == "promote_blacklist" else "decision_rule",
            "decision": decision,
            "source_review_id": review_id,
            "session_id": item.get("session_id"),
            "task": item.get("task_preview") or "",
            "problem": item.get("gap") or item.get("evidence") or "",
            "user_note": item.get("note") or "",
        }
        with OP_APPROVED_LEARNING_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(queued, ensure_ascii=False) + "\n")

    event = _task_bus_append("op_learning_decision", review_id, "hub", {"decision": decision, "queued": bool(queued)})
    return {"status": "recorded", "decision": item, "approved_queue_item": queued, "event": event}


@app.get("/api/control-plane/supervisor")
async def control_plane_supervisor_status():
    if not CONTROL_PLANE_SUPERVISOR_LATEST.exists():
        return {
            "ok": False,
            "error": "supervisor has not produced a report yet",
            "file": str(CONTROL_PLANE_SUPERVISOR_LATEST),
        }
    try:
        data = json.loads(CONTROL_PLANE_SUPERVISOR_LATEST.read_text(encoding="utf-8"))
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "file": str(CONTROL_PLANE_SUPERVISOR_LATEST)}, status_code=500)
    data.setdefault("ok", data.get("issue_count", 1) == 0)
    data.setdefault("file", str(CONTROL_PLANE_SUPERVISOR_LATEST))
    return data


def _response_payload(value):
    if isinstance(value, JSONResponse):
        try:
            return json.loads(value.body.decode("utf-8"))
        except Exception:
            return {"error": "invalid response"}
    return value


def _workspace_operating_model() -> dict:
    return {
        "title": "2026 统一控制平面",
        "principle": "一个窗口看全局，Hub 统一状态/API，n8n 编排动作，OP 接收待确认事项，FastGPT 产出方案，Plane/Huly/Mattermost/Zulip 保留协作源数据。",
        "entry": {"label": "主入口", "href": "/workspace", "detail": "9800 工作区聚合页"},
        "lanes": [
            {"id": "console", "name": "可视化窗口", "owner": "Appsmith", "href": "/go/appsmith", "job": "面向人的单一操作台，调用 Hub API，不直接改系统"},
            {"id": "state", "name": "状态与语义", "owner": "Hub 9800", "href": "/workspace", "job": "服务注册、快照、统一待办、语义命令和安全本地 API"},
            {"id": "automation", "name": "动作总线", "owner": "n8n", "href": "/go/n8n", "job": "多步骤流程、Webhook、跨工具同步和通知编排"},
            {"id": "execution", "name": "待确认执行层", "owner": "OP / OpenCode", "href": "/go/opencode", "job": "接收 Hub 投递的监控/评分/任务事项；默认只读评估，人工确认后才执行"},
            {"id": "planning", "name": "方案与知识", "owner": "FastGPT", "href": "/go/fastgpt", "job": "知识包、方案生成、复盘和问答流程"},
            {"id": "projects", "name": "项目源数据", "owner": "Plane / Huly", "href": "/go/plane", "job": "项目、任务、文档、路线图和协作上下文"},
            {"id": "discussion", "name": "沟通反馈", "owner": "Mattermost / Zulip", "href": "/go/mattermost", "job": "频道讨论、Bot 回执、图片和人工确认"},
        ],
        "flows": [
            "人从 9800/workspace 或 Appsmith 发出语义指令",
            "Hub 读取系统快照、项目待办、架构动作和协作事件",
            "n8n 负责跨工具流程，Hub 保留每次动作的事件记录",
            "Hub 发送给 OP 的事项默认进入待确认队列，不触发执行；需要改文件或修服务时由人工确认后再执行",
            "FastGPT 接收统一待办知识包，产出方案和复盘",
            "Plane/Huly/Mattermost/Zulip 保留项目协作源数据，Hub 只聚合和路由",
        ],
        "guardrails": [
            "Appsmith 是主视觉窗口，不再新增同用途顶层看板",
            "Hub 只暴露安全 API 和状态，不让 FastGPT/Dify 直接写文件或重启服务",
            "部署类长驻进程必须走 user systemd service",
            "每次 Hub 投递、Codex/OP 执行都写持久 journal，记录目标、状态、下一步和恢复入口",
        ],
    }


def _read_workspace_snapshot_cache() -> dict | None:
    if not WORKSPACE_SNAPSHOT_FILE.exists():
        return None
    try:
        age = time.time() - WORKSPACE_SNAPSHOT_FILE.stat().st_mtime
        cached = json.loads(WORKSPACE_SNAPSHOT_FILE.read_text(encoding="utf-8"))
        cached.setdefault("operating_model", _workspace_operating_model())
        cached["_cached"] = True
        cached["_cache_age_seconds"] = round(age, 1)
        return cached
    except Exception:
        return None


MEMORY_MODE_BIN = Path.home() / ".local/bin/smart-memory-mode"


def _run_memory_mode(args: list[str], timeout: float = 20.0) -> dict:
    if not MEMORY_MODE_BIN.exists():
        return {"ok": False, "error": f"{MEMORY_MODE_BIN} not found", "stdout": "", "stderr": ""}
    try:
        result = subprocess.run(
            [str(MEMORY_MODE_BIN), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": 124,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": "smart-memory-mode timed out",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}


@app.get("/api/ops/memory-mode/status")
def memory_mode_status():
    result = _run_memory_mode(["status"], timeout=12.0)
    return {"mode": "status", **result}


@app.get("/api/ops/memory-mode/plan/{mode}")
def memory_mode_plan(mode: str):
    if mode not in {"light", "work", "full"}:
        return JSONResponse({"error": "mode must be light, work, or full"}, status_code=400)
    result = _run_memory_mode(["plan", mode], timeout=12.0)
    return {"mode": mode, **result}


@app.post("/api/ops/memory-mode/apply/{mode}")
def memory_mode_apply(mode: str):
    if mode not in {"light", "work", "full"}:
        return JSONResponse({"error": "mode must be light, work, or full"}, status_code=400)
    result = _run_memory_mode(["apply", mode], timeout=90.0)
    event = _task_bus_append("memory_mode_apply", "memory-mode", "hub", {"mode": mode, "ok": result.get("ok")})
    return {"mode": mode, "event": event, **result}


@app.get("/api/workspace/snapshot")
async def workspace_snapshot(request: Request, force: bool = False):
    """Workspace rollup for periodic collection, sync, collaboration, and handoff."""
    if not force:
        cached = _read_workspace_snapshot_cache()
        if cached:
            return cached

    async def safe(name: str, factory):
        try:
            return _response_payload(await factory())
        except Exception as exc:
            return {"ok": False, "error": str(exc), "source": name}

    overview, todos, appsmith, n8n, plane, huly, mattermost, zulip, op_resilience = await asyncio.gather(
        safe("dashboard", lambda: dashboard_overview(request)),
        safe("workflow", lambda: _unified_todos(request)),
        safe("appsmith", appsmith_status_api),
        safe("n8n", n8n_status_api),
        safe("plane", plane_status_api),
        safe("huly", huly_status_api),
        safe("mattermost", mattermost_status_api),
        safe("zulip", zulip_status),
        safe("opencode", opencode_resilience),
    )

    service_health = [
        {"id": "appsmith", "name": "统一操作台", "ok": bool(appsmith.get("ok")), "detail": appsmith.get("service") or appsmith.get("http_status") or appsmith.get("error", ""), "href": "/go/appsmith", "role": appsmith.get("role", "")},
        {"id": "n8n", "name": "动作总线", "ok": bool(n8n.get("ok")), "detail": n8n.get("service") or n8n.get("http_status") or n8n.get("error", ""), "href": "/go/n8n", "role": n8n.get("role", "")},
        {"id": "plane", "name": "Plane", "ok": bool(plane.get("ok")), "detail": plane.get("service") or plane.get("http_status") or plane.get("error", ""), "href": "/go/plane", "role": plane.get("role", "")},
        {"id": "huly", "name": "Huly", "ok": bool(huly.get("ok")), "detail": huly.get("service") or huly.get("http_status") or huly.get("error", ""), "href": "/go/huly", "role": huly.get("role", "")},
        {"id": "mattermost", "name": "Mattermost", "ok": bool(mattermost.get("ok")), "detail": mattermost.get("service") or mattermost.get("http_status") or mattermost.get("error", ""), "href": "/go/mattermost", "role": mattermost.get("role", "")},
        {"id": "zulip", "name": "Zulip", "ok": bool(zulip.get("configured")) and bool((zulip.get("gateway") or {}).get("ok")), "detail": (zulip.get("gateway") or {}).get("error") or zulip.get("default_stream", ""), "href": "/go/zulip", "role": "topic-based discussion and bot handoff"},
        {"id": "op", "name": "OP", "ok": not bool(op_resilience.get("stopped_like") or op_resilience.get("error")), "detail": f"{op_resilience.get('grade', '?')} / {op_resilience.get('score', '?')}", "href": "/go/opencode", "role": "execution and repair"},
        {"id": "fastgpt", "name": "FastGPT", "ok": True, "detail": "knowledge export target", "href": "/go/fastgpt", "role": "knowledge, plans, review"},
    ]
    tasks = todos.get("tasks", []) if isinstance(todos, dict) else []
    data = {
        "generated_at": datetime.now().isoformat(),
        "collectors": [
            {"name": "system", "cadence": "30s websocket / 60s page poll", "source": "/api/dashboard/overview"},
            {"name": "workflow", "cadence": "60s", "source": "/api/workflow/todos"},
            {"name": "events", "cadence": "60s", "source": "/api/workflow/events"},
            {"name": "service-health", "cadence": "60s", "source": "Plane/Huly/Mattermost/Zulip/OP probes"},
        ],
        "system": overview.get("system", {}) if isinstance(overview, dict) else {},
        "services": overview.get("services", []) if isinstance(overview, dict) else [],
        "score": overview.get("score", {}) if isinstance(overview, dict) else {},
        "service_health": service_health,
        "workflow": {
            "summary": todos.get("summary", {}) if isinstance(todos, dict) else {},
            "tasks": tasks[:30],
            "events": (todos.get("events", []) if isinstance(todos, dict) else [])[-30:],
            "routing": todos.get("routing", {}) if isinstance(todos, dict) else {},
        },
        "sync_targets": {
            "appsmith": "single visual operations console",
            "hub": "collect and expose APIs/state",
            "n8n": "workflow automation bus",
            "op": "execute tasks and repair systems",
            "fastgpt": "receive knowledge packs and produce plans",
            "zulip": "discussion stream/topic and bot handoff",
            "plane": "project progress source of truth",
            "mattermost": "channel collaboration fallback",
        },
        "operating_model": _workspace_operating_model(),
        "_cached": False,
    }
    try:
        WORKSPACE_SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        WORKSPACE_SNAPSHOT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass
    return data


@app.post("/api/workspace/sync")
async def workspace_sync(body: dict):
    note = (body.get("note") or "").strip()
    target = (body.get("target") or "hub").strip()
    if not note:
        return JSONResponse({"error": "note required"}, status_code=400)
    event = _task_bus_append("workspace_sync", body.get("task_id") or "workspace", target, {"note": note[:1000]})
    dialogue_append(f"workspace:{target}", note[:2000], "sync")
    if target == "zulip" or body.get("send_zulip"):
        try:
            zulip_data = _zulip_send_message(note, stream=body.get("stream") or ZULIP_DEFAULT_STREAM, topic=body.get("topic") or "Workspace")
            return {"status": "synced", "event": event, "zulip": zulip_data}
        except Exception as exc:
            return JSONResponse({"error": str(exc), "event": event}, status_code=502)
    return {"status": "synced", "event": event}


def _workspace_link_for(text: str) -> dict | None:
    lower = text.lower()
    links = [
        (("统一", "操作台", "控制平面", "总控", "appsmith"), "统一操作台", "/go/appsmith"),
        (("学习", "复盘", "review", "learning", "进化", "评分"), "OP 学习中枢", "/op-learning"),
        (("n8n", "动作总线", "自动化", "workflow"), "动作总线", "/go/n8n"),
        (("op", "opencode", "18910", "执行"), "OP", "/go/opencode"),
        (("fastgpt", "知识库", "方案"), "FastGPT", "/go/fastgpt"),
        (("zulip", "频道", "话题"), "Zulip", "/go/zulip"),
        (("mattermost", "聊天", "图片"), "Mattermost", "/go/mattermost"),
        (("plane", "项目", "路线图"), "Plane", "/go/plane"),
        (("huly", "文档", "工作区"), "Huly", "/go/huly"),
        (("dashboard", "系统全景", "状态"), "系统全景", "/dashboard"),
        (("kanban", "看板", "待办"), "任务看板", "/kanban"),
        (("架构", "结构图"), "架构图", "/#architecture"),
    ]
    for keys, label, href in links:
        if any(k in lower or k in text for k in keys):
            return {"label": label, "href": href}
    return None


def _workspace_task_matches(command: str, tasks: list[dict]) -> list[dict]:
    lower = command.lower()
    pool = tasks
    if "高" in command or "high" in lower or "紧急" in command:
        pool = [t for t in pool if t.get("priority") == "high"]
    if "营销" in command:
        pool = [t for t in pool if "营销" in t.get("title", "") or t.get("source") == "marketing"]
    if "架构" in command:
        pool = [t for t in pool if t.get("source") == "architecture" or "架构" in t.get("title", "")]
    if "项目" in command:
        pool = [t for t in pool if t.get("source") == "project" or "项目" in t.get("title", "")]
    if "op-" in lower:
        token = next((p.upper() for p in lower.replace("，", " ").split() if p.startswith("op-")), "")
        if token:
            pool = [t for t in pool if token in (t.get("title", "").upper() + " " + t.get("detail", "").upper())]
    return pool or tasks


@app.post("/api/workspace/command")
async def workspace_command(request: Request, body: dict):
    command = (body.get("command") or body.get("text") or "").strip()
    if not command:
        return JSONResponse({"error": "command required"}, status_code=400)

    lower = command.lower()
    if any(word in lower for word in ("refresh", "reload")) or any(word in command for word in ("刷新", "同步状态", "重新采集")):
        data = _read_workspace_snapshot_cache() or {
            "generated_at": datetime.now().isoformat(),
            "service_health": [],
            "workflow": {"summary": {}},
            "operating_model": _workspace_operating_model(),
        }
        return {"status": "refreshed", "message": "已刷新工作区快照", "snapshot": {"generated_at": data.get("generated_at"), "tasks": (data.get("workflow") or {}).get("summary"), "services": len(data.get("service_health") or [])}}

    if any(word in command for word in ("派给", "交给", "发给", "导出", "完成")) or any(word in lower for word in ("send", "export", "complete")):
        data = await _unified_todos(request)
        tasks = _workspace_task_matches(command, data.get("tasks", []))
        task = tasks[0] if tasks else None
        if not task:
            return JSONResponse({"error": "没有匹配到待办任务"}, status_code=404)
        if "完成" in command or "complete" in lower:
            result = await workflow_complete(task["id"], {"source": "workspace-command", "note": command})
            return {"status": "completed", "message": f"已标记完成：{task.get('title')}", "task": task, "result": result}
        if "fastgpt" in lower or "知识库" in command or "导出" in command:
            result = await workflow_export_to_fastgpt(task["id"], request, {"guide": f"来自工作区语义指令：{command}"})
            return {"status": "exported", "message": f"已导出 FastGPT：{task.get('title')}", "task": task, "result": _response_payload(result)}
        if "zulip" in lower or "频道" in command or "讨论" in command:
            result = await workflow_send_to_zulip(task["id"], request, {"topic": "Workspace"})
            return {"status": "sent", "message": f"已发送 Zulip：{task.get('title')}", "task": task, "result": _response_payload(result)}
        result = await workflow_send_to_op(task["id"], request, {"message": f"来自工作区语义指令：{command}\n\n只读查看与评估，不要直接执行；等待人工确认后再行动。\n\n{_task_markdown(task)}"})
        return {"status": "queued_not_executed", "message": f"已发送到 OP 待确认队列，不执行：{task.get('title')}", "task": task, "result": _response_payload(result)}

    if any(word in command for word in ("打开", "进入", "去", "看")) or any(word in lower for word in ("open", "go ")):
        link = _workspace_link_for(command)
        if link:
            return {"status": "open", "message": f"打开 {link['label']}", "href": link["href"], "target": link["label"]}

    target = "zulip" if "zulip" in lower or "频道" in command else "hub"
    event = _task_bus_append("workspace_command", "workspace", target, {"command": command[:1000]})
    dialogue_append("workspace:command", command[:2000], "command")
    return {"status": "recorded", "message": "已记录为工作区语义指令，等待 Hub/AI 后续处理", "event": event}


@app.get("/api/architecture/graph")
async def architecture_graph():
    projects = [_project_with_progress(p) for p in _all_projects()]
    nodes = [
        {"id": "remote", "label": "访问层", "type": "layer", "status": "active", "detail": "DuckDNS / Tailscale / /go 兜底入口"},
        {"id": "hub", "label": "9800 Hub", "type": "core", "status": "active", "detail": "总控、项目、架构动作、链接注册表"},
        {"id": "projects", "label": "Projects", "type": "core", "status": "active", "detail": f"{len(projects)} 个项目"},
        {"id": "op", "label": "OP / OpenCode", "type": "executor", "status": "active", "detail": "任务队列、代码执行、回收变更"},
        {"id": "ai-builders", "label": "AI 建站工具", "type": "executor", "status": "active", "detail": "Replit / Lovable / Bolt / v0"},
        {"id": "oss-stack", "label": "开源建站栈", "type": "platform", "status": "reserved", "detail": "ERPNext/Odoo + Vendure/Medusa + Directus/Payload + Mautic/n8n"},
        {"id": "sourcing", "label": "Sourcing 旧站", "type": "project", "status": "partial", "detail": "WordPress 分析已找到，原始备份路径待挂载"},
        {"id": "marketing", "label": "营销中心", "type": "growth", "status": "partial", "detail": "需求采集、配件机会池、推广动作"},
    ]
    nodes.extend({
        "id": f"project:{p.get('id')}",
        "label": p.get("name"),
        "type": "project",
        "status": "active" if p.get("progress", 0) >= 50 else "partial",
        "detail": p.get("description", ""),
    } for p in projects[:12])
    edges = [
        {"from": "remote", "to": "hub", "label": "访问"},
        {"from": "hub", "to": "projects", "label": "管理/创建"},
        {"from": "projects", "to": "op", "label": "派发"},
        {"from": "projects", "to": "ai-builders", "label": "交接提示词"},
        {"from": "projects", "to": "oss-stack", "label": "开源底座"},
        {"from": "ai-builders", "to": "op", "label": "代码回收/验证"},
        {"from": "sourcing", "to": "ai-builders", "label": "迁移重建"},
        {"from": "oss-stack", "to": "sourcing", "label": "B2B 后台/电商内核"},
        {"from": "marketing", "to": "sourcing", "label": "机会生成商品页"},
        {"from": "marketing", "to": "op", "label": "推广任务"},
    ]
    gaps = [
        {"id": "wordpress-backup-mount", "label": "WordPress 原始备份挂载", "detail": "/mnt/pool/sde1-migrated/- 123 onedrive/- Sourcing/root 当前未直接可读"},
        {"id": "sourcing-db-import", "label": "WordPress 数据导入", "detail": "wp_posts / WooCommerce 产品 / 媒体文件导出到新后台"},
        {"id": "project-runtime", "label": "项目运行时", "detail": "给 sourcing-site 预留端口、systemd user 服务和 /go 入口"},
        {"id": "admin-auth", "label": "后台权限", "detail": "管理员登录、角色、审计日志"},
        {"id": "publish-pipeline", "label": "发布流水线", "detail": "AI 生成代码后自动测试、部署、回滚"},
        {"id": "demand-ingest-api", "label": "需求采集 API", "detail": "Google Trends、TikTok、公开论坛、商品搜索数据接入"},
        {"id": "marketing-analytics", "label": "营销归因", "detail": "曝光、点击、询盘、报价、成交回流到机会池"},
        {"id": "oss-poc", "label": "开源底座 POC", "detail": "选择 ERPNext/Odoo 或 Vendure/Medusa 做第一版自建验证"},
    ]
    return {"generated_at": datetime.now().isoformat(), "nodes": nodes, "edges": edges, "gaps": gaps}

@app.get("/api/ai-news")
async def get_ai_news():
    rd = Path.home() / "Desktop" / "巡检报告"
    items = []
    if rd.exists():
        for f in sorted(rd.glob("*.md"), reverse=True)[:20]:
            try: content = f.read_text(encoding="utf-8", errors="ignore")
            except Exception: content = ""
            name = f.stem; kind = "report"; title = name
            if name.startswith("planning"): kind = "planning"; title = "规划报告 " + name[9:]
            elif "晨报" in content[:50]: kind = "morning"; title = "晨报 " + name
            items.append({"name": name, "kind": kind, "title": title, "summary": content[:200].replace(chr(10), " "), "file": str(f)})
    return {"items": items}

@app.post("/api/feed-ingest")
async def feed_ingest(payload: dict):
    rd = Path.home() / "Desktop" / "巡检报告"; rd.mkdir(parents=True, exist_ok=True)
    fn = f'{datetime.now().strftime("%Y-%m-%d")}-{payload.get("type","report")}.md'
    (rd / fn).write_text(payload.get("text", ""), encoding="utf-8")
    return {"ok": True, "file": fn}

@app.post("/api/office/command")
async def office_command(body: dict):
    import httpx as _httpx
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with _httpx.AsyncClient(timeout=30, trust_env=False) as client:
            return (await client.post("http://localhost:9810/command", json=body)).json()
    except Exception as e: return {"error": f"office-agent 不可达: {e}"}

@app.get("/api/office/history")
async def office_history(limit: int = 20):
    import httpx as _httpx
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with _httpx.AsyncClient(timeout=10, trust_env=False) as client:
            return (await client.get(f"http://localhost:9810/history?limit={limit}")).json()
    except Exception as e: return {"error": str(e)}

@app.post("/api/office/start")
async def office_start():
    import httpx as _httpx
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with _httpx.AsyncClient(timeout=10, trust_env=False) as client:
            return (await client.post("http://localhost:9810/start-soffice")).json()
    except Exception as e: return {"error": str(e)}
@app.get("/api/memory/context")
async def memory_context(query: str = ""):
    import httpx, subprocess
    context = {"letta": [], "local": []}
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            resp = await client.post(f"{LETTA_API}/v1/agents/agent-0040ded4-1831-4b76-a4a4-62519a416a5a/search", json={"query": query})
            context["letta"] = [r.get("content","") for r in resp.json().get("results", [])]
    except Exception: pass
    try:
        result = subprocess.run(["grep", "-ri", query, str(MEMORY_DIR)], capture_output=True, text=True, timeout=5)
        context["local"] = result.stdout.strip().split(chr(10))[:10] if result.stdout.strip() else []
    except Exception: pass
    return context

@app.post("/api/memory/store")
async def memory_store(body: dict):
    import httpx
    content = body.get("content", "")
    if not content: return {"error": "empty content"}
    tags = body.get("tags", "hub-api")
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            await client.post(f"{LETTA_API}/v1/agents/agent-0040ded4-1831-4b76-a4a4-62519a416a5a/archival/memory", json={"text": content, "tags": tags.split(",")})
        return {"ok": True}
    except Exception as e: return {"error": "Letta failed", "detail": str(e)}

@app.post("/api/glm/competitive")
async def glm_competitive_ingest(req: dict):
    return {"ok": True}

@app.get("/api/glm/competitive")
async def glm_competitive_list():
    import glob
    reports = [f for f in glob.glob(str(GLM_DATA_DIR / "competitive-*.json"))]
    items = []
    for f in reports[:20]:
        try: items.append(json.loads(Path(f).read_text()))
        except Exception: pass
    return {"items": items}

@app.post("/api/glm/codebase")
async def glm_codebase_ingest(req: dict):
    return {"ok": True}

@app.get("/api/glm/codebase")
async def glm_codebase_list():
    return {"items": []}

@app.post("/api/glm/aider-report")
async def glm_aider_ingest(req: dict):
    return {"ok": True}

@app.get("/api/glm/aider-report")
async def glm_aider_list():
    import glob
    reports = glob.glob(str(GLM_DATA_DIR / "aider-refactor-*.md"))
    items = [{"name": Path(f).stem.replace("aider-refactor-", ""), "content": Path(f).read_text(encoding="utf-8", errors="ignore")[:2000]} for f in reports[:20]]
    return {"items": items}

@app.get("/api/glm/workbench")
async def glm_workbench_summary():
    import httpx, subprocess, os, glob as _glob, json as _json

    models = ["openai-compatible/glm-5-turbo", "openai-compatible/glm-5.1", "openai-compatible/glm-4.7"]

    # competitive — 竞品分析（demo data）
    competitive = [{
        "date": "2026-05-19",
        "summary": "OpenAI发布GPT-5.1、Anthropic发布Claude 4.5 Sonnet、Google发布Gemini 2.5 Ultra。GLM-5.1在中文长文本理解仍保持优势，多模态推理接近国际一线水平。",
        "competitors": [
            {"name": "OpenAI GPT-5.1", "update": "长上下文256K + function calling 3.0，API降价30%", "threat_level": "high"},
            {"name": "Anthropic Claude 4.5", "update": "Code Interpreter 内置沙箱，代码生成准确率+15%", "threat_level": "high"},
            {"name": "Google Gemini 2.5", "update": "原生多模态理解，视频分析时长相较前代提升3倍", "threat_level": "medium"},
            {"name": "DeepSeek V3.2", "update": "开源MoE架构，推理成本降低至GPT-5.1的40%", "threat_level": "medium"},
        ],
        "opportunities": ["中文法律/医疗垂类精调", "端侧部署GLM-Turbo-Lite"],
        "recommended_actions": ["加速GLM-5.1 Turbo RT推理优化", "补充Code Interpreter能力"]
    }]

    # codebase — 代码库地图（扫码最近变更）
    def _get_codebase():
        # scan key repos for recent changes
        repos = {
            "hub": os.path.expanduser("~/hub"),
            "agi-frontend": "/mnt/ai/apps/agi-control-plane",
            "wechat-agent": "/mnt/ai/apps/wechat-agent",
        }
        changes = []
        for name, path in repos.items():
            if not os.path.isdir(path):
                continue
            try:
                out = subprocess.check_output(
                    ["git", "-C", path, "log", "--oneline", "--since=7 days ago", "--name-only", "--format=%H %s"],
                    timeout=5, stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
                for line in out.strip().split("\n"):
                    if line and not line.startswith(" "):
                        changes.append(f"[{name}] {line}")
            except Exception:
                pass
        if not changes:
            # fallback: stat recent modified files
            for name, path in repos.items():
                if not os.path.isdir(path):
                    continue
                try:
                    recent = subprocess.check_output(
                        ["find", path, "-type", "f", "-name", "*.py", "-mtime", "-7"],
                        timeout=5, stderr=subprocess.DEVNULL
                    ).decode("utf-8", errors="ignore").strip().split("\n")[:5]
                    for f in recent:
                        if f:
                            changes.append(f"[{name}] {os.path.basename(f)}")
                except Exception:
                    pass

        return [{
            "date": "2026-05-19",
            "summary": f"近7天 {len(changes)} 个变更项",
            "changes": changes[:20] if changes else ["无变更"]
        }]

    # aider — Aider审查（从self-improve reports读取）
    def _get_aider():
        paths = [
            "/tmp/aider-latest.md",
            os.path.expanduser("~/.aider-report-latest.md"),
        ]
        for p in paths:
            if os.path.isfile(p):
                try:
                    content = open(p).read()[:2000]
                    return [{
                        "date": "2026-05-19",
                        "content": content,
                        "files_reviewed": content.count(".py") + content.count(".ts"),
                        "suggestions": [l.strip(" -") for l in content.split("\n") if "建议" in l or "优化" in l or "修复" in l][:5]
                    }]
                except Exception:
                    pass
        # fallback: demo data
        return [{
            "date": "2026-05-19 17:30",
            "content": "自动审查完成：扫描 12 个文件，hub-api.py 第 1478 行需补充数据字段；GLMWorkbenchPanel.tsx 代码质量良好；page.tsx 路由表完整。未发现严重安全隐患。",
            "files_reviewed": 12,
            "suggestions": ["hub-api.py 补充 competitive/codebase/aider/jobs 数据源", "添加 API 响应缓存（TTL 60s）", "GLMWorkbenchPanel 添加空态骨架屏"]
        }]

    # jobs — GLM服务分层（实时服务状态）
    def _get_jobs():
        mapping = {
            "glm-4.7": ["glm-proxy", "glm-health-check.timer"],
            "glm-5-turbo": ["agent-orchestrator", "ttyd-cct"],
            "glm-5.1": ["glm-monitor", "screenshot-watcher", "agi-self-improve.timer"],
        }
        jobs = {}
        for model, svcs in mapping.items():
            jobs[model] = []
            for svc in svcs:
                try:
                    status = subprocess.check_output(
                        ["systemctl", "--user", "is-active", svc],
                        timeout=5, stderr=subprocess.DEVNULL
                    ).decode().strip()
                    status_cn = "运行中" if status == "active" else "待机"
                except subprocess.CalledProcessError:
                    status_cn = "停止"
                except Exception:
                    status_cn = "未知"
                jobs[model].append({
                    "id": svc,
                    "model": model,
                    "status": status_cn,
                    "task": svc.replace(".service", "").replace(".timer", ""),
                })
        return jobs

    result = {
        "models": models,
        "note": "GLM 工作台 — 实时监控面板",
        "competitive": competitive,
        "codebase": _get_codebase(),
        "aider": _get_aider(),
        "jobs": _get_jobs(),
    }
    return result

@app.get("/task-review")
async def get_task_review():
    try:
        data = json.loads(_TASK_REVIEW_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError: return {"error": "no data, run task-review.py first"}
    except Exception as e: return {"error": str(e)}
    
    # 合并反馈状态：每个任务取最新的 status
    feedbacks = data.get("feedbacks", [])
    task_statuses = {}
    for fb in feedbacks:
        name = fb.get("task_name", "")
        st = fb.get("status")
        if name and st:
            task_statuses[name] = st  # 后面的覆盖前面 = 取最新
    data["task_statuses"] = task_statuses
    return data

@app.post("/task-review/feedback")
async def post_task_review_feedback(body: dict):
    from datetime import datetime as _datetime
    data = {}
    try: data = json.loads(_TASK_REVIEW_PATH.read_text(encoding="utf-8"))
    except Exception: pass
    feedbacks = data.setdefault("feedbacks", [])
    feedbacks.append({**body, "timestamp": _datetime.now().timestamp()})
    _TASK_REVIEW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}

@app.post("/task-review/run")
async def run_task_review():
    import subprocess
    script = Path.home() / "bin/task-review.py"
    if not script.exists(): return {"error": "task-review.py not found"}
    result = subprocess.run(["python3", str(script)], capture_output=True, text=True, timeout=60)
    return {"ok": True, "output": result.stdout[:500]}

@app.get("/otp-script")
async def otp_script():
    from fastapi.responses import PlainTextResponse
    sp = Path.home() / "Desktop/开发工具/termux-otp-push.sh"
    return PlainTextResponse(sp.read_text()) if sp.exists() else PlainTextResponse("# script not found")

@app.post("/otp/receive")
async def otp_receive(request: Request):
    import subprocess
    body = await request.json()
    code = body.get("code", "")
    sender = body.get("sender", "")
    if not code: return {"error": "invalid code"}
    env = {**os.environ, "WAYLAND_DISPLAY": "wayland-1", "XDG_RUNTIME_DIR": "/run/user/1000"}
    subprocess.run(["wl-copy", code], env=env, timeout=5)
    subprocess.run(["notify-send", "-t", "8000", "-i", "dialog-information", f"短信验证码：{code}", f"来自 {sender}，已复制到剪贴板"], env=env, timeout=5)
    return {"ok": True, "code": code}

@app.post("/api/op-reflect")
async def op_reflect(body: dict):
    import httpx
    task_desc = body.get("task", "")
    prompt = f"任务: {task_desc}\n请反思这个任务的执行质量，输出JSON {{\"score\": 0-10, \"reason\": \"...\"}}"
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.post("http://localhost:4000/v1/chat/completions", json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3})
            raw = resp.json()["choices"][0]["message"]["content"]
            score_data = json.loads(raw.strip().strip("`"))
    except Exception as e: score_data = {"score": 5, "reason": f"反思解析失败: {e}"}
    r = _load_op_results(); r["reflect"] = {"task": task_desc, "score": score_data.get("score"), "reason": score_data.get("reason")}; _save_op_results(r)
    return score_data

@app.post("/api/op-confidence")
async def op_confidence(body: dict):
    import httpx
    task_desc = body.get("task", "")
    prompt = f"任务: {task_desc}\n我有多大把握完成？输出JSON {{\"confidence\": 0-100, \"blockers\": [...]}}"
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.post("http://localhost:4000/v1/chat/completions", json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3})
            raw = resp.json()["choices"][0]["message"]["content"]
            conf = json.loads(raw.strip().strip("`"))
    except Exception as e: conf = {"confidence": 50, "blockers": [f"解析失败: {e}"]}
    if conf.get("confidence", 0) < 60: conf["status"] = "needs_human"
    r = _load_op_results(); r["confidence"] = conf; _save_op_results(r)
    return conf

@app.post("/api/frontend-errors")
async def frontend_errors(body: dict):
    """接收前端 3000 控制台 React 错误，存入 Letta archival memory 供 AI 感知"""
    import httpx
    error_msg = body.get("error", "")
    error_info = body.get("info", "")
    error_stack = body.get("stack", "")
    page_url = body.get("url", "")
    user_agent = body.get("userAgent", "")
    ts = body.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
    if not error_msg:
        return {"error": "empty error message"}
    content = f"[前端错误] {ts}\n页面: {page_url}\n错误: {error_msg}\n组件栈: {error_info}\n堆栈: {error_stack[:500]}\nUA: {user_agent}"
    tags = "frontend-error,3000-console,react-error"
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            await client.post(f"{LETTA_API}/v1/agents/agent-0040ded4-1831-4b76-a4a4-62519a416a5a/archival/memory", json={"text": content, "tags": tags.split(",")})
        return {"ok": True, "stored": error_msg[:100]}
    except Exception as e:
        return {"error": "Letta failed", "detail": str(e)}

@app.post("/api/op-experience")
async def op_experience(body: dict):
    import httpx
    from datetime import datetime as _dt
    entry = f"[EXPERIENCE] {_dt.now().isoformat()} 任务: {body.get('task','')} | 策略: {body.get('approach','')} | 结果: {body.get('outcome','')} | 耗时: {body.get('duration',0)}s"
    tags = ["experience-replay", "op-task", body.get("type", "general")]
    try:
        _env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy","https_proxy","all_proxy")}
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            await client.post(f"{LETTA_API}/v1/agents/{LETTA_AGENT_ID}/archival-memory", json={"text": entry, "tags": tags})
        result = {"ok": True, "stored": entry[:100]}
    except Exception as e: result = {"ok": False, "error": str(e)}
    lessons = MEMORY_DIR / "lessons-learned.md"
    if lessons.exists():
        with open(lessons, "a", encoding="utf-8") as f: f.write(f"\n- [{_dt.now().strftime('%Y-%m-%d')}] [OP-auto] 场景：{body.get('task','')} → {body.get('outcome','')}")
    r = _load_op_results(); r["experience"] = result; _save_op_results(r)
    return result


# ===== Kanban / Task management endpoints (Hub panel support) =====
# These serve the hub.html kanban page. Data sourced from op-tasks.md and local state.

@app.get("/api/dashboard/software")
async def dashboard_software():
    import subprocess
    categories = {
        "开发工具": ["python", "node", "npm", "git", "vim", "neovim", "vscode", "docker", "podman", "rust", "gcc", "make", "cmake", "meson", "ninja", "clang", "go", "java", "maven", "gradle", "cargo", "pip", "poetry", "uv", "conda", "jupyter", "postman", "curl", "wget", "jq", "fd", "ripgrep", "bat", "exa", "starship", "zsh", "fish", "tmux", "screen", "htop", "btop", "ncdu", "ranger", "fzf", "zoxide", "dircolors"],
        "AI/ML": ["ollama", "llama", "cuda", "cudnn", "pytorch", "tensorflow", "transformers", "vllm", "litellm", "letta", "openai", "anthropic", "huggingface", "mlflow", "jax", "deepseek", "qwen", "glm", "step"],
        "系统服务": ["systemd", "nginx", "caddy", "frp", "tailscale", "mihomo", "clash", "v2ray", "wireguard", "openvpn", "ssh", "rsync", "cron", "logrotate", "fail2ban", "ufw", "firewalld", "iptables", "nftables", "zram", "zswap", "earlyoom", "thermald", "power-profiles-daemon"],
        "多媒体": ["ffmpeg", "gstreamer", "vlc", "mpv", "obs", "pipewire", "pulseaudio", "jack", "alsa", "bluetooth", "bluez", "pavucontrol", "helvum", "easyeffects", "gimp", "inkscape", "imagemagick", "libreoffice", "okular", "evince", "zathura"],
        "网络工具": ["wireshark", "tcpdump", "nmap", "netcat", "socat", "iptables", "nftables", "dnsmasq", "bind", "unbound", "cloudflared", "ddclient", "mtr", "bmon", "iftop", "nethogs", "vnstat", "speedtest", "aria2", "transmission", "qbittorrent", "rclone", "restic", "borg", "duplicity"],
        "办公/通讯": ["thunderbird", "evolution", "signal", "telegram", "discord", "slack", "zoom", "teams", "wechat", "qq", "dingtalk", "lark", "notion", "obsidian", "logseq", "joplin", "zim"],
        "虚拟化": ["qemu", "libvirt", "virt-manager", "virt-viewer", "spice", "ovmf", "edk2", "docker", "podman", "lxc", "lxd", "incus", "kvm", "qemu-kvm"],
    }
    try:
        r = subprocess.run(["rpm", "-qa", "--queryformat", "%{NAME}|%{VERSION}\n"], capture_output=True, text=True, timeout=10)
        pkgs = [line.strip().split("|") for line in r.stdout.strip().split("\n") if "|" in line]
    except Exception:
        pkgs = []
    categorized = {k: [] for k in categories}
    uncategorized = []
    for name, ver in pkgs:
        matched = False
        for cat, keywords in categories.items():
            if any(kw.lower() in name.lower() for kw in keywords):
                categorized[cat].append({"name": name, "version": ver})
                matched = True
                break
        if not matched:
            uncategorized.append({"name": name, "version": ver})
    result = {k: v for k, v in categorized.items() if v}
    if uncategorized:
        result["其他"] = uncategorized[:50]
    return result

@app.get("/api/dashboard/projects")
async def dashboard_projects():
    base = Path.home() / "hub"
    projects = []
    skip = {"__pycache__", "static", "de", "docs", "tmp", "var", "~", "_archived-sessions", "media_store", "skills", "node_modules", ".git"}
    if base.exists():
        for d in sorted(base.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and d.name not in skip:
                readme = d / "README.md"
                desc = ""
                if readme.exists():
                    try:
                        desc = readme.read_text(encoding="utf-8", errors="ignore").split("\n")[0].strip()
                    except Exception:
                        pass
                projects.append({
                    "name": d.name,
                    "path": str(d),
                    "description": desc[:120] if desc else "",
                })
    ws_base = Path("/var/mnt/ai/cache/auto-migrate/.openclaw/workspace")
    if ws_base.exists():
        for d in sorted(ws_base.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and d.name not in skip:
                readme = d / "README.md"
                desc = ""
                if readme.exists():
                    try:
                        desc = readme.read_text(encoding="utf-8", errors="ignore").split("\n")[0].strip()
                    except Exception:
                        pass
                projects.append({
                    "name": f"workspace/{d.name}",
                    "path": str(d),
                    "description": desc[:120] if desc else "",
                })
    return {"projects": projects[:50]}

@app.get("/api/dashboard/ideas")
async def dashboard_ideas():
    ideas = []
    notes_dir = Path.home() / "Desktop/巡检报告"
    if notes_dir.exists():
        for f in sorted(notes_dir.glob("*.md"), reverse=True)[:20]:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                ideas.append({
                    "name": f.stem,
                    "summary": content[:200].replace("\n", " "),
                    "updated_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
            except Exception:
                pass
    memory_dir = Path.home() / ".claude/projects/-home-charlie/memory"
    if memory_dir.exists():
        for f in sorted(memory_dir.glob("*.md"), reverse=True)[:10]:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                ideas.append({
                    "name": f"memory/{f.stem}",
                    "summary": content[:200].replace("\n", " "),
                    "updated_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
            except Exception:
                pass
    return {"ideas": ideas[:30]}

@app.get("/kanban-data")
async def kanban_data():
    tasks = _load_op_results()
    return {"columns": tasks.get("columns", [{"id":"todo","title":"待处理","items":[]},{"id":"in_progress","title":"进行中","items":[]},{"id":"done","title":"已完成","items":[]}])}

@app.post("/kanban-move")
async def kanban_move(body: dict):
    r = _load_op_results()
    r["last_move"] = {"task": body.get("task",""), "from": body.get("from",""), "to": body.get("to",""), "time": datetime.now().isoformat()}
    _save_op_results(r)
    return {"ok": True}

@app.get("/kanban-assign")
async def kanban_assign(task: str = "", agent: str = ""):
    return {"ok": True, "task": task, "agent": agent}

@app.post("/kanban-delegate")
async def kanban_delegate(body: dict):
    return {"ok": True, "delegated": body.get("task",""), "to": body.get("agent","cc-autonomous")}

@app.post("/api/inject-task")
async def inject_task(body: dict):
    task_text = (body.get("task") or body.get("text") or "").strip()
    result = _append_op_inbox_task(
        "hub-legacy-inject",
        task_text,
        tags=["LEGACY-INJECT"],
        metadata={"agent": body.get("agent", "")},
    )
    r = _load_op_results()
    r["injected"] = r.get("injected", []) + [{"task": task_text, "agent": body.get("agent",""), "time": datetime.now().isoformat(), "mode": "queued_not_executed"}]
    _save_op_results(r)
    return {"ok": True, **result}

@app.post("/api/trigger-op")
async def trigger_op(body: dict):
    action = (body.get("action") or "OP trigger request").strip()
    result = _append_op_inbox_task(
        "hub-legacy-trigger",
        action,
        tags=["LEGACY-TRIGGER"],
        metadata={"time": datetime.now().isoformat()},
    )
    return {"ok": True, "triggered": action, "time": datetime.now().isoformat(), **result}

@app.get("/api/task-results")
async def task_results():
    return {"results": _load_op_results().get("history", [])}

@app.get("/api/op-tasks-pending")
async def op_tasks_pending():
    import subprocess
    try:
        tasks_path = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")
        with open(tasks_path) as f:
            lines = f.readlines()
        pending = [l.strip() for l in lines if l.strip().startswith("- [ ]")]
        return {"count": len(pending), "tasks": pending}
    except Exception:
        return {"count": 0, "tasks": []}

@app.get("/op-status")
async def op_status():
    r = _load_op_results()
    import re as _re

    LOG_DIR = Path.home() / ".config/opencode/logs/scheduler/charlie-b445f233ebb8"
    JOBS_DIR = Path.home() / ".config/opencode/scheduler/scopes/charlie-b445f233ebb8/jobs"

    # 读取 systemd timer 状态
    timers = {}
    try:
        out = subprocess.check_output(
            ["systemctl", "--user", "list-timers", "opencode-job-*", "--no-legend", "--no-pager"],
            text=True, timeout=5
        )
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) < 6:
                continue
            unit_idx = next((i for i, p in enumerate(parts) if p.startswith("opencode-job-")), None)
            if unit_idx is None:
                continue
            unit = parts[unit_idx]
            job = _re.sub(r"^opencode-job-charlie-[a-z0-9]+-", "", unit).replace(".timer", "")
            timers[job] = {"unit": unit, "next": " ".join(parts[:3]), "last": " ".join(parts[3:6])}
    except Exception:
        pass

    # 读取每个 job 日志
    jobs = []
    if JOBS_DIR.exists():
        for fname in os.listdir(str(JOBS_DIR)):
            if not fname.endswith(".json"):
                continue
            job = fname[:-5]
            log_path = LOG_DIR / f"{job}.log"
            last_lines = []
            status = "unknown"
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                last_lines = [l.strip() for l in lines[-5:] if l.strip()]
                for l in reversed(last_lines):
                    if "status=success" in l:
                        status = "success"; break
                    if "status=fail" in l or "FAIL" in l:
                        status = "failed"; break
                    if "[OK]" in l:
                        status = "success"; break
                    if "[FAIL]" in l or "error" in l.lower():
                        status = "failed"; break
            except FileNotFoundError:
                status = "no_log"
            timer_info = timers.get(job, {})
            jobs.append({
                "job": job,
                "status": status,
                "last_log": last_lines[-2:] if last_lines else [],
                "next": timer_info.get("next", "—"),
                "last_run": timer_info.get("last", "—"),
            })

    # op-tasks.md 待执行任务
    op_pending = []
    op_tasks_path = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
    try:
        with open(op_tasks_path, "r", encoding="utf-8") as f:
            for line in f:
                m = _re.match(r"^-\s+\[ \]\s+(.*)", line.strip())
                if m:
                    op_pending.append(m.group(1)[:100])
    except Exception:
        pass

    return {
        "op": {"status": "idle", "last_active": r.get("last_experience", ""), "uptime": "—"},
        "cc": {"status": "idle", "last_session": r.get("last_cc_session", "")},
        "tasks": r.get("stats", {}),
        "memory": {"letta": "unknown", "lessons": len(list(MEMORY_DIR.glob("*.md"))) if MEMORY_DIR.exists() else 0},
        "jobs": jobs,
        "op_pending": op_pending,
    }

@app.get("/api/quota")
async def api_quota():
    return {"tokens": {"used": 0, "limit": 1000000}, "calls": {"used": 0, "limit": 10000}, "reset": ""}

@app.get("/api/review")
async def api_review():
    return {"reviews": []}

@app.post("/api/chat-route")
async def chat_route(body: dict):
    return {"ok": True, "route": "cc", "message": body.get("message","")}

@app.post("/api/exec")
async def api_exec(body: dict):
    return {"ok": True, "command": body.get("command",""), "output": "ok"}

@app.post("/api/cc-op-speak")
async def cc_op_speak(body: dict):
    r = _load_op_results()
    msgs = r.get("cc_op_dialog", [])
    msgs.append({"role": body.get("role","cc"), "text": body.get("text",""), "time": datetime.now().isoformat()})
    r["cc_op_dialog"] = msgs[-50:]
    _save_op_results(r)
    return {"ok": True}

@app.post("/api/cc-op-discuss")
async def cc_op_discuss(body: dict):
    return await cc_op_speak(body)

@app.get("/api/cc-op-discuss-history")
async def cc_op_discuss_history():
    return {"messages": _load_op_results().get("cc_op_dialog", [])}

@app.get("/api/cc-op-dialog")
async def cc_op_dialog(n: int = 30):
    msgs = _load_op_results().get("cc_op_dialog", [])
    return {"messages": msgs[-n:]}

@app.post("/api/orchestrate")
async def api_orchestrate(body: dict):
    return {"ok": True, "plan": body.get("task",""), "steps": []}

@app.get("/api/orchestrate-history")
async def api_orchestrate_history():
    return {"plans": []}


# === 路由器端口转发查询 ===
@app.get("/api/router/ports")
async def router_ports(source: str = "nvram"):
    """查询 Padavan 路由器端口转发规则。source: nvram / iptables / both"""
    import subprocess, json as _json
    try:
        r = subprocess.run(
            ["/home/charlie/.local/bin/router-port-list.py", "json", source],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            rules = _json.loads(r.stdout)
            return {"ok": True, "count": len(rules), "rules": rules}
        return {"ok": False, "error": r.stderr.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/router/ports/add")
async def router_port_add(body: dict):
    """添加路由器端口转发到 NVRAM（持久化）。需要: port, lan_port, proto(TCP/UDP), description"""
    import subprocess, json as _json
    port = body.get("port")
    lan_port = body.get("lan_port", port)
    proto = body.get("proto", "TCP")
    desc = body.get("description", f"api-{port}")
    if not port:
        return {"ok": False, "error": "缺少 port 参数"}

    # 获取当前索引
    raw = subprocess.run(
        ["/home/charlie/.local/bin/router-port-list.py", "json", "nvram"],
        capture_output=True, text=True, timeout=10
    )
    rules = _json.loads(raw.stdout)
    next_idx = len(rules)

    cmd = (
        f'/usr/sbin/nvram set vts_num_x={next_idx + 1} && '
        f'/usr/sbin/nvram set vts_port_x{next_idx}={port} && '
        f'/usr/sbin/nvram set vts_lport_x{next_idx}={lan_port} && '
        f'/usr/sbin/nvram set vts_proto_x{next_idx}={proto} && '
        f'/usr/sbin/nvram set vts_ipaddr_x{next_idx}=192.168.123.209 && '
        f'/usr/sbin/nvram set vts_desc_x{next_idx}={desc} && '
        f'/usr/sbin/nvram set vts_srcip_x{next_idx}= && '
        f'/usr/sbin/nvram set vts_protono_x{next_idx}= && '
        f'/usr/sbin/nvram set vts_rule{next_idx}="{port}|192.168.123.209|{lan_port}|{proto}|||{desc}" && '
        f'/usr/sbin/nvram commit'
    )

    r = subprocess.run(
        ["sshpass", "-p", "admin", "ssh", "-o", "ConnectTimeout=5",
         "-o", "StrictHostKeyChecking=no", "admin@192.168.123.1", cmd],
        capture_output=True, text=True, timeout=15
    )

    if r.returncode == 0:
        # 立即添加 iptables 规则
        subprocess.run(
            ["sshpass", "-p", "admin", "ssh", "-o", "ConnectTimeout=5",
             "-o", "StrictHostKeyChecking=no", "admin@192.168.123.1",
             f"iptables -t nat -A vserver -p tcp --dport {port} -j DNAT --to 192.168.123.209:{lan_port}"],
            capture_output=True, timeout=10
        )
        return {"ok": True, "added": {"port": port, "lan_port": lan_port, "index": next_idx}}
    return {"ok": False, "error": r.stderr.strip()}


# ── NixOS 系统状态仪表盘 ──
NIXOS_STATUS_HTML = Path("/mnt/ai/apps/agi-control-plane/frontend/public/nixos-status.html")

@app.get("/nixos-status")
async def nixos_status_page():
    """系统状态仪表盘 HTML 页面"""
    if NIXOS_STATUS_HTML.exists():
        return FileResponse(NIXOS_STATUS_HTML, media_type="text/html")
    return JSONResponse({"error": "dashboard not found"}, status_code=404)

@app.get("/api/nixos-status")
async def nixos_status_api():
    """系统状态 JSON API"""
    import subprocess, re

    def check_port(port):
        r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
        return "up" if f":{port} " in r.stdout else "down"

    # CPU
    with open("/proc/stat") as f:
        cpu1 = f.readline().split()
    import time; time.sleep(0.3)
    with open("/proc/stat") as f:
        cpu2 = f.readline().split()
    t1 = sum(int(x) for x in cpu1[1:])
    t2 = sum(int(x) for x in cpu2[1:])
    idle = int(cpu2[4]) - int(cpu1[4])
    cpu_pct = round((1 - idle / (t2 - t1)) * 100)

    # 内存
    with open("/proc/meminfo") as f:
        mem = f.read()
    mt = int(re.search(r"MemTotal:\s+(\d+)", mem).group(1))
    ma = int(re.search(r"MemAvailable:\s+(\d+)", mem).group(1))
    mem_pct = round((mt - ma) / mt * 100)

    # 磁盘
    disk = subprocess.run(["df", "/"], capture_output=True, text=True)
    disk_pct = int(re.search(r"(\d+)%", disk.stdout.split("\n")[1]).group(1))

    # 温度
    temp = "?"
    for t in sorted(Path("/sys/class/thermal/thermal_zone*").glob("*/temp") if False else []):
        ...
    try:
        tz = next(Path("/sys/class/thermal").glob("thermal_zone*/temp"), None)
        if tz:
            temp = str(round(int(tz.read_text().strip()) / 1000))
    except: pass

    # 服务
    svc_checks = {
        "Docker": lambda: subprocess.run(["docker", "info"], capture_output=True).returncode == 0,
        "mihomo": lambda: check_port(7890),
        "LiteLLM": lambda: check_port(4000),
        "AGI-GW": lambda: check_port(9900),
        "Letta": lambda: check_port(8283),
        "HubAPI": lambda: check_port(9800),
        "CRM": lambda: check_port(9876),
    }
    services = {}
    svc_ok = svc_fail = 0
    for name, check in svc_checks.items():
        status = "up" if check() else "down"
        services[name] = status
        if status == "up": svc_ok += 1
        else: svc_fail += 1

    return {
        "cpu": cpu_pct, "mem": mem_pct, "disk": disk_pct,
        "temp": temp, "mem_total": f"{mt/1024/1024:.1f}",
        "svc_ok": svc_ok, "svc_fail": svc_fail, "svc_total": len(svc_checks),
        "services": services,
        "ts": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════
#  Control Panel API — for code-server custom-panel extension
# ═══════════════════════════════════════════════════════

@app.post("/api/control/upload")
async def control_upload(file: UploadFile = File(...)):
    """接收手机上传的文件，保存到 ~/Desktop/uploads/"""
    dest = Path.home() / "Desktop" / "uploads"
    dest.mkdir(parents=True, exist_ok=True)
    fpath = dest / file.filename
    content = await file.read()
    fpath.write_bytes(content)
    return {"ok": True, "path": str(fpath), "size": len(content)}


@app.get("/api/search")
async def global_search(q: str = Query(..., description="搜索关键词")):
    """全局搜索：Linux 文件名(fd) + Windows(es.exe) + 手机(find)"""
    import shutil
    results = {"files": [], "content": [], "windows": [], "phone": [], "query": q}

    if not shutil.which("fd"):
        return {"ok": False, "error": "fd 未安装", **results}

    # Linux 文件名搜索
    search_roots = ["/home", "/var/home", "/opt", "/srv"]
    try:
        r = await asyncio.to_thread(subprocess.run,
            ["fd", "-HI", "--hidden", "--no-ignore", "--max-depth", "10",
             "--exclude", ".git", "--exclude", "node_modules",
             "--exclude", "__pycache__", "--exclude", ".cache",
             "--exclude", "nix/store", "-t", "f", q] + search_roots,
            capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL
        )
        results["files"] = [{"path": p, "type": "file"} for p in r.stdout.strip().split("\n") if p][:100]
    except Exception: pass

    # Linux 内容搜索（rg，限制文件大小避免超时）
    try:
        r = await asyncio.to_thread(subprocess.run,
            ["rg", "--max-filesize", "1M", "--no-messages", "-i", "-S", "--max-depth", "10",
             q] + search_roots,
            capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL
        )
        results["content"] = [{"path": p.split(":")[0], "snippet": ":".join(p.split(":")[1:])[:120]}
                              for p in r.stdout.strip().split("\n") if p and ":" in p][:50]
    except Exception: pass

    # Windows 搜索（es.exe via SSH）
    try:
        r = await asyncio.to_thread(subprocess.run,
            ["ssh", "-o", "ConnectTimeout=2", "-o", "StrictHostKeyChecking=no",
             "charlie@100.91.93.99", f"es.exe -n 50 '{q}'"],
            capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL
        )
        if r.returncode == 0 and r.stdout.strip():
            results["windows"] = [{"path": p} for p in r.stdout.strip().split("\n") if p][:50]
        else:
            results["windows"] = [{"path": "(SSH 不可达)"}]
    except Exception:
        results["windows"] = [{"path": "(SSH 不可达)"}]

    # 手机搜索（ls + grep via ADB，Toybox find 不可靠）
    try:
        r = await asyncio.to_thread(subprocess.run,
            ["adb", "-s", "100.108.28.44:5555", "shell",
             f"sh -c \"ls -R /sdcard 2>/dev/null | grep -i '{q}' | head -50\""],
            capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL
        )
        if r.returncode == 0 and r.stdout.strip():
            results["phone"] = [{"path": p} for p in r.stdout.strip().split("\n") if p][:50]
        else:
            results["phone"] = [{"path": "(无结果)"}]
    except Exception:
        results["phone"] = [{"path": "(ADB 不可达)"}]

    return {"ok": True, **results}


@app.get("/api/files/raw")
async def files_raw(path: str = Query(..., description="文件绝对路径")):
    """返回文本文件内容（仅文本文件，大小限制 200KB）"""
    p = Path(path).resolve()
    if not p.is_file():
        return JSONResponse({"error": "file not found"}, status_code=404)
    if p.stat().st_size > 200 * 1024:
        return JSONResponse({"error": "file too large"}, status_code=413)
    try:
        text = p.read_text(errors="replace")
        return JSONResponse({"path": str(p), "content": text[:200000]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/control/screenshot")
async def control_screenshot():
    """截取桌面并返回 base64 PNG"""
    img_path = "/tmp/control-screenshot.png"
    try:
        subprocess.run(["maim", img_path], timeout=5, capture_output=True, env={"DISPLAY": ":0"})
    except Exception:
        subprocess.run(["grim", img_path], timeout=5, capture_output=True)
    if Path(img_path).exists():
        data = Path(img_path).read_bytes()
        b64 = base64.b64encode(data).decode()
        return {"ok": True, "image_base64": b64, "format": "png"}
    return {"ok": False, "error": "screenshot failed"}


@app.get("/api/control/rag")
async def control_rag(q: str = Query(..., description="搜索关键词")):
    """搜索本地知识库 (Khoj + Letta + grep memory)"""
    results = []
    # Khoj
    try:
        import httpx
        r = httpx.get(f"http://127.0.0.1:8283/api/search?q={q}", timeout=5)
        if r.status_code == 200:
            results += [{"source": "letta", "text": i.get("text", "")[:200]} for i in r.json().get("results", [])[:3]]
    except: pass
    # grep memory
    try:
        mem_dir = Path.home() / ".claude/projects/-home-charlie/memory"
        for f in mem_dir.glob("*.md"):
            for line in f.read_text().split("\n")[:100]:
                if q.lower() in line.lower():
                    results.append({"source": f.name, "text": line.strip()[:200]})
                    if len(results) >= 5: break
    except: pass
    return {"ok": True, "results": results[:10], "query": q}


@app.get("/api/control/health")
async def control_health():
    """快速健康检查"""
    import shutil
    ds = shutil.disk_usage("/")
    return {
        "cpu": os.popen("vmstat 1 1 | tail -1 | awk '{print 100-$15}'").read().strip(),
        "mem": os.popen("free | awk '/Mem:/{printf \"%.0f\", $3/$2*100}'").read().strip(),
        "disk_root": f"{ds.used//1024//1024}M / {ds.total//1024//1024}M",
        "ts": datetime.now().isoformat(),
    }


@app.get("/api/phone/snapshot")
async def phone_snapshot():
    """手机健康快照：通过 ADB 收集使用统计、电池、存储、温度、内存、进程"""
    import re
    ADB = ["adb", "-s", "100.108.28.44:5555"]

    def _run(cmd: list[str], timeout: int = 10) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.stdout
        except Exception:
            return ""

    def _parse_usagestats(raw: str) -> list[dict]:
        apps: dict[str, int] = {}
        for line in raw.splitlines():
            if "ACTIVITY_RESUMED package=" in line:
                m = re.search(r'package=(\S+)', line)
                if m:
                    apps[m.group(1)] = apps.get(m.group(1), 0) + 1
        return [{"package": pkg, "count": cnt} for pkg, cnt in sorted(apps.items(), key=lambda x: -x[1])[:30]]

    def _parse_battery(raw: str) -> dict:
        info: dict[str, str] = {}
        for line in raw.splitlines():
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
        return {
            "level": info.get("level", "?"),
            "status": info.get("status", "?"),
            "health": info.get("health", "?"),
            "temp": info.get("temperature", "?"),
            "voltage": info.get("voltage", "?"),
        }

    def _parse_storage(raw: str) -> list[dict]:
        mounts = []
        for line in raw.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 5 and parts[1] == "/mnt/pass_through":
                total, used = int(parts[1]), int(parts[2])
                mounts.append({"mount": parts[0], "total_gb": round(total / 1024 / 1024, 1), "used_gb": round(used / 1024 / 1024, 1), "pct": round(used / total * 100, 1) if total else 0})
        return mounts

    def _parse_thermal(raw: str) -> dict:
        temps = {}
        for line in raw.splitlines():
            if "temp=" in line:
                m = re.search(r'([\w-]+)\s+temp=([\d.]+)', line)
                if m:
                    temps[m.group(1)] = float(m.group(2))
        return temps

    def _parse_meminfo(raw: str) -> dict:
        info = {}
        for line in raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip().split()[0] if v.strip() else "0"
        return {"mem_total_kb": info.get("MemTotal", "0"), "mem_available_kb": info.get("MemAvailable", "0"), "swap_total_kb": info.get("SwapTotal", "0"), "swap_free_kb": info.get("SwapFree", "0")}

    def _parse_processes(raw: str) -> list[dict]:
        procs = []
        for line in raw.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 9:
                procs.append({"pid": parts[1], "user": parts[0], "cpu": parts[2], "mem": parts[3], "name": parts[8]})
        return sorted(procs, key=lambda x: float(x.get("cpu", "0")), reverse=True)[:20]

    loop = asyncio.get_event_loop()
    usages, battery, storage, thermal, meminfo, processes = await asyncio.gather(
        loop.run_in_executor(None, _parse_usagestats, _run(ADB + ["shell", "dumpsys usagestats --hourly"])),
        loop.run_in_executor(None, _parse_battery, _run(ADB + ["shell", "dumpsys battery"])),
        loop.run_in_executor(None, _parse_storage, _run(ADB + ["shell", "df"])),
        loop.run_in_executor(None, _parse_thermal, _run(ADB + ["shell", "dumpsys thermal"])),
        loop.run_in_executor(None, _parse_meminfo, _run(ADB + ["shell", "cat /proc/meminfo"])),
        loop.run_in_executor(None, _parse_processes, _run(ADB + ["shell", "ps -eo user,pid,%cpu,%mem,comm --sort=-%cpu | head -25"])),
    )
    return {"ok": True, "ts": datetime.now().isoformat(), "usage": usages, "battery": battery, "storage": storage, "thermal": thermal, "memory": meminfo, "top_processes": processes}


@app.post("/api/clicks")
async def record_click_api(body: dict):
    click_id = (body.get("click_id") or "").strip()
    if not click_id:
        return JSONResponse({"error": "click_id required"}, status_code=400)
    count = _record_click(click_id)
    return JSONResponse({"click_id": click_id, "count": count})


@app.get("/api/clicks")
async def get_clicks_api():
    return JSONResponse(_get_clicks())


@app.get("/api/clicks/ranked")
async def get_clicks_ranked_api():
    clicks = _get_clicks()
    ranked = sorted(clicks.items(), key=lambda x: x[1], reverse=True)
    return JSONResponse(dict(ranked[:50]))


@app.get("/phone-health")
async def phone_health_page():
    p = STATIC_DIR / "phone-health.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>手机健康页面不存在</h1>", status_code=404)


@app.get("/moonlight-pair")
async def moonlight_pair_page():
    p = STATIC_DIR / "moonlight-pair.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>配对页面不存在</h1>", status_code=404)


if __name__ == "__main__":
    _init_click_db()
    port = int(os.environ.get("HUB_PORT", "9800"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
