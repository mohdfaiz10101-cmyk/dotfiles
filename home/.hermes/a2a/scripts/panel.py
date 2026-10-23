#!/usr/bin/env python3
"""A2A Web Panel: manage rooms, agents, queues, knowledge, Hermes sessions, and mesh tasks."""
import os, sys, json, sqlite3, shutil, subprocess
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

try:
    import yaml
except ImportError:
    yaml = None

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
QUEUE = BASE / 'queue'
KNOWLEDGE = BASE / 'knowledge'
DB_PATH = Path.home() / '.hermes/state.db'
A2A_CLI = Path.home() / '.local/bin/a2a'
TASKS_ROOT = BASE / 'tasks'
TASK_INDEX = Path.home() / '.local/bin/hermes-task-index'
MESH_CLEANUP = Path.home() / '.local/bin/hermes-mesh-cleanup'

app = FastAPI(title='A2A Panel')
templates = Jinja2Templates(directory=str(BASE / 'scripts' / 'templates'))


def load_rooms():
    if yaml is None:
        return {}
    return yaml.safe_load((BASE / 'rooms.yaml').read_text())['rooms']


def load_agents():
    if yaml is None:
        return {}
    return yaml.safe_load((BASE / 'agents.yaml').read_text())['agents']


def get_queue_stats():
    stats = {}
    for status in ['pending', 'approved', 'rejected', 'synced']:
        target = QUEUE / status
        if not target.exists():
            stats[status] = 0
            continue
        stats[status] = sum(1 for f in target.rglob('*.json') if f.is_file())
    return stats


def get_recent_sessions(limit=20):
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        "SELECT id, title, started_at, message_count, source FROM sessions ORDER BY started_at DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    con.close()
    result = []
    for r in rows:
        result.append({
            'id': str(r['id']),
            'title': r['title'] or '',
            'started_at': r['started_at'],
            'message_count': r['message_count'],
            'source': r['source'] or '',
        })
    return result


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def iter_mesh_tasks():
    if not TASKS_ROOT.exists():
        return
    for path in sorted(TASKS_ROOT.glob('mesh-*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        payload = read_json(path, {})
        if payload:
            payload['_path'] = str(path)
            yield payload


def get_mesh_tasks(limit=50, status=''):
    items = []
    for payload in iter_mesh_tasks():
        if status and payload.get('status') != status:
            continue
        items.append(payload)
        if len(items) >= limit:
            break
    return items


def summarize_mesh_task(payload: dict):
    history = payload.get('history') or []
    last_event = history[-1] if history else {}
    return {
        'id': payload.get('id'),
        'title': payload.get('title', ''),
        'status': payload.get('status', ''),
        'profile': payload.get('profile', ''),
        'source_port': payload.get('source_port'),
        'active_port': payload.get('active_port'),
        'source_session': payload.get('source_session', ''),
        'active_session': payload.get('active_session', ''),
        'parent_task': payload.get('parent_task', ''),
        'parent_session': payload.get('parent_session', ''),
        'summary': payload.get('summary', ''),
        'updated_at': payload.get('updated_at'),
        'created_at': payload.get('created_at'),
        'children': payload.get('children', []),
        'rollups': payload.get('rollups', []),
        'handoffs': payload.get('handoffs', []),
        'message_count': payload.get('message_count', 0),
        'estimated_tokens': payload.get('estimated_tokens', 0),
        'last_event': last_event,
    }


def get_mesh_tree(limit=100):
    tasks = [summarize_mesh_task(item) for item in get_mesh_tasks(limit=limit)]
    by_id = {item['id']: dict(item, children_nodes=[]) for item in tasks if item.get('id')}
    roots = []
    for item in by_id.values():
        parent_id = item.get('parent_task')
        if parent_id and parent_id in by_id:
            by_id[parent_id]['children_nodes'].append(item)
        else:
            roots.append(item)
    roots.sort(key=lambda item: item.get('updated_at') or '', reverse=True)
    return {'roots': roots, 'tasks': list(by_id.values())}


def get_mesh_handoffs(limit=20):
    events = []
    for payload in get_mesh_tasks(limit=100):
        task_id = payload.get('id')
        for handoff in payload.get('handoffs', []):
            events.append({
                'task_id': task_id,
                'type': 'handoff',
                'ts': handoff.get('ts'),
                'to': handoff.get('to'),
                'reason': handoff.get('reason', ''),
                'status': payload.get('status', ''),
                'title': payload.get('title', ''),
            })
        for item in payload.get('history', []):
            if item.get('event') == 'updated' and payload.get('status') == 'rolled_over':
                events.append({
                    'task_id': task_id,
                    'type': 'rollover',
                    'ts': item.get('ts'),
                    'to': '',
                    'reason': item.get('summary', ''),
                    'status': payload.get('status', ''),
                    'title': payload.get('title', ''),
                })
    events.sort(key=lambda item: item.get('ts') or '', reverse=True)
    return events[:limit]


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    rooms = load_rooms()
    agents = load_agents()
    stats = get_queue_stats()
    sessions = get_recent_sessions()
    return templates.TemplateResponse('panel.html', {
        'request': request,
        'rooms': rooms,
        'agents': agents,
        'stats': stats,
        'sessions': sessions,
        'now': datetime.now(timezone.utc).isoformat(),
    })


@app.get('/api/queue')
async def api_queue(status: str = 'pending', room: str = ''):
    target = QUEUE / status
    if not target.exists():
        return JSONResponse(content={'items': []})
    items = []
    for room_dir in sorted(target.iterdir()):
        if not room_dir.is_dir():
            continue
        if room and room_dir.name != room:
            continue
        for f in sorted(room_dir.iterdir()):
            if f.suffix == '.json':
                try:
                    data = json.loads(f.read_text())
                    items.append(data)
                except Exception:
                    pass
    return JSONResponse(content={'items': items})


@app.post('/api/approve')
async def api_approve(request: Request):
    body = await request.json()
    proposal_id = body.get('id')
    if not proposal_id:
        raise HTTPException(400, 'id required')
    result = subprocess.run([str(A2A_CLI), 'approve', proposal_id], capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(500, result.stderr or result.stdout)
    return JSONResponse(content={'ok': True, 'output': result.stdout})


@app.post('/api/reject')
async def api_reject(request: Request):
    body = await request.json()
    proposal_id = body.get('id')
    reason = body.get('reason', '')
    if not proposal_id:
        raise HTTPException(400, 'id required')
    result = subprocess.run([str(A2A_CLI), 'reject', proposal_id, '--reason', reason], capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(500, result.stderr or result.stdout)
    return JSONResponse(content={'ok': True, 'output': result.stdout})


@app.post('/api/sync')
async def api_sync(request: Request):
    body = await request.json()
    room = body.get('room')
    cmd = [str(A2A_CLI), 'sync']
    if room:
        cmd.extend(['--room', room])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(500, result.stderr or result.stdout)
    return JSONResponse(content={'ok': True, 'output': result.stdout})


@app.get('/api/knowledge')
async def api_knowledge(room: str = '', date: str = ''):
    rooms = [room] if room else sorted([d.name for d in KNOWLEDGE.iterdir() if d.is_dir()])
    data = {}
    for r in rooms:
        kdir = KNOWLEDGE / r
        if not kdir.exists():
            continue
        files = sorted([f.name for f in kdir.glob('*.md')])
        if date:
            files = [f for f in files if date in f]
        data[r] = files
    return JSONResponse(content=data)


@app.get('/api/sessions')
async def api_sessions(limit: int = 20):
    return JSONResponse(content={'sessions': get_recent_sessions(limit)})


@app.get('/api/rooms')
async def api_rooms():
    return JSONResponse(content=load_rooms())


@app.get('/api/stats')
async def api_stats():
    return JSONResponse(content=get_queue_stats())


@app.get('/api/mesh/tasks')
async def api_mesh_tasks(limit: int = 50, status: str = ''):
    return JSONResponse(content={'items': [summarize_mesh_task(item) for item in get_mesh_tasks(limit, status)]})


@app.get('/api/mesh/tree')
async def api_mesh_tree(limit: int = 100):
    return JSONResponse(content=get_mesh_tree(limit))


@app.get('/api/mesh/handoffs')
async def api_mesh_handoffs(limit: int = 20):
    return JSONResponse(content={'items': get_mesh_handoffs(limit)})


@app.get('/api/mesh/task')
async def api_mesh_task(task_id: str = ''):
    if not task_id:
        raise HTTPException(400, 'task_id required')
    path = TASKS_ROOT / f'{task_id}.json'
    payload = read_json(path)
    if not payload:
        raise HTTPException(404, 'not found')
    return JSONResponse(content=payload)


@app.post('/api/mesh/cleanup')
async def api_mesh_cleanup(request: Request):
    body = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
    cmd = [str(MESH_CLEANUP), '--json']
    if body.get('execute'):
        cmd.append('--execute')
    if body.get('include_submitted'):
        cmd.append('--include-submitted')
    if body.get('keep_hours'):
        cmd.extend(['--keep-hours', str(body.get('keep_hours'))])
    for item in body.get('task_ids', []):
        cmd.extend(['--task-id', item])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(500, result.stderr or result.stdout)
    return JSONResponse(content=json.loads(result.stdout))


@app.get('/api/knowledge/file')
async def api_knowledge_file(room: str = '', file: str = ''):
    if not room or not file:
        raise HTTPException(400, 'room and file required')
    path = KNOWLEDGE / room / file
    if not path.exists() or not path.is_file():
        raise HTTPException(404, 'not found')
    text = path.read_text()
    return JSONResponse(content={'room': room, 'file': file, 'content': text})


def main():
    port = int(os.environ.get('A2A_PANEL_PORT', '8788'))
    uvicorn.run(app, host='127.0.0.1', port=port)


if __name__ == '__main__':
    main()
