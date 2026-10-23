#!/usr/bin/env python3
"""A2A Bridge for 8787: simple web page listing Hermes Studio rooms/agents."""
import os, sys, json, requests
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

try:
    import yaml
except ImportError:
    yaml = None

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
TOKEN_PATH = Path.home() / '.hermes-web-ui/.token'
STUDIO_URL = 'http://127.0.0.1:8648'
BRIDGE_PORT = int(os.environ.get('A2A_BRIDGE_PORT', '8789'))

app = FastAPI(title='A2A Bridge')


def get_token():
    return TOKEN_PATH.read_text().strip() if TOKEN_PATH.exists() else None


def studio_headers():
    tok = get_token()
    if not tok:
        return {}
    return {'Authorization': f'Bearer {tok}'}


def load_rooms():
    if yaml is None:
        return {}
    return yaml.safe_load((BASE / 'rooms.yaml').read_text())['rooms']


def load_agents():
    if yaml is None:
        return {}
    return yaml.safe_load((BASE / 'agents.yaml').read_text())['agents']


def get_studio_rooms():
    try:
        r = requests.get(f'{STUDIO_URL}/api/hermes/group-chat/rooms', headers=studio_headers(), timeout=5)
        if r.status_code == 200:
            return r.json().get('rooms', [])
    except Exception:
        pass
    return []


def get_room_agents(room_id):
    try:
        r = requests.get(f'{STUDIO_URL}/api/hermes/group-chat/rooms/{room_id}/agents', headers=studio_headers(), timeout=5)
        if r.status_code == 200:
            return r.json().get('agents', [])
    except Exception:
        pass
    return []


def _render_html(merged):
    cards = []
    for m in merged:
        agents_html = ''.join(
            f'<div class="agent"><div class="agent-name">{a["name"]}</div>'
            f'<div class="agent-desc">{a["description"]}</div></div>'
            for a in m['agents']
        )
        cards.append(
            f'<div class="card">'
            f'<h3>{m["name"]} <span class="tag">{m["profile"]}</span></h3>'
            f'<div class="meta">inviteCode: {m["inviteCode"]} · agents: {len(m["agents"])}</div>'
            f'{agents_html}'
            f'<a class="btn" href="{STUDIO_URL}/hermes/group-chat/room/{m["roomId"]}" target="_blank">Open Room</a>'
            f'</div>'
        )
    cards_html = ''.join(cards)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>A2A Rooms</title>
<style>
body{{font-family:system-ui;margin:0;background:#0b0d12;color:#e6e6e6;padding:24px}}
header{{margin-bottom:24px}}
h1{{font-size:20px;margin:0 0 8px}}
p{{color:#93b4c4;margin:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
.card{{background:#11151c;border:1px solid #232a35;border-radius:10px;padding:16px}}
.card h3{{margin:0 0 8px;font-size:16px;color:#e6e6e6}}
.meta{{color:#7b8a99;font-size:12px;margin-bottom:12px}}
.agent{{background:#1f2630;border-radius:8px;padding:10px;margin-bottom:8px}}
.agent-name{{font-weight:600;color:#b6d4f5}}
.agent-desc{{font-size:12px;color:#93b4c4;margin-top:4px}}
.tag{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;background:#1f2630;color:#93b4c4;margin-right:6px}}
a{{color:#93b4c4;text-decoration:none}}
.btn{{display:inline-block;margin-top:10px;padding:6px 12px;border-radius:6px;background:#154734;color:#b6f5c7;font-size:12px;text-decoration:none}}
</style>
</head>
<body>
<header>
<h1>A2A Rooms</h1>
<p>Hermes Studio rooms and agents · <a href="{STUDIO_URL}/hermes/group-chat" target="_blank">Open Hermes Studio Group Chat</a></p>
</header>
<div class="grid">
{cards_html}
</div>
</body>
</html>'''


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    rooms = load_rooms()
    agents = load_agents()
    studio_rooms = get_studio_rooms()
    studio_map = {r['name']: r for r in studio_rooms}

    merged = []
    for name, cfg in rooms.items():
        sr = studio_map.get(name, {})
        room_agents = []
        for agent_name in cfg.get('agents', []):
            acfg = agents.get(agent_name, {})
            room_agents.append({
                'name': agent_name,
                'profile': acfg.get('profile', 'secondary'),
                'description': acfg.get('description', ''),
            })
        merged.append({
            'name': name,
            'inviteCode': sr.get('inviteCode', f'{name}-room'),
            'roomId': sr.get('id', ''),
            'profile': cfg.get('profile', 'secondary'),
            'description': cfg.get('description', ''),
            'agents': room_agents,
        })

    return HTMLResponse(content=_render_html(merged))


@app.get('/api/rooms')
async def api_rooms():
    rooms = load_rooms()
    agents = load_agents()
    studio_rooms = get_studio_rooms()
    studio_map = {r['name']: r for r in studio_rooms}
    result = []
    for name, cfg in rooms.items():
        sr = studio_map.get(name, {})
        room_agents = []
        for agent_name in cfg.get('agents', []):
            acfg = agents.get(agent_name, {})
            room_agents.append({
                'name': agent_name,
                'profile': acfg.get('profile', 'secondary'),
                'description': acfg.get('description', ''),
            })
        result.append({
            'name': name,
            'roomId': sr.get('id', ''),
            'inviteCode': sr.get('inviteCode', f'{name}-room'),
            'profile': cfg.get('profile', 'secondary'),
            'description': cfg.get('description', ''),
            'agents': room_agents,
        })
    return JSONResponse(content={'rooms': result})


def main():
    import uvicorn
    print(f'A2A Bridge starting on http://127.0.0.1:{BRIDGE_PORT}')
    uvicorn.run(app, host='127.0.0.1', port=BRIDGE_PORT)


if __name__ == '__main__':
    main()
