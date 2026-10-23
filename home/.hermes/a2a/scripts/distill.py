#!/usr/bin/env python3
"""A2A Distiller: scan Hermes sessions and extract durable knowledge proposals."""
import os, sys, json, uuid, time, re, sqlite3, requests, argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
QUEUE = BASE / 'queue'
INDEX = QUEUE / 'index.jsonl'
LAST_SCAN = QUEUE / '.last-scan'
DB_PATH = Path.home() / '.hermes/state.db'

PROVIDERS = [
    {'name': 'sub2api', 'base_url': 'http://127.0.0.1:19090/v1/chat/completions', 'model': 'gpt-5.4-mini', 'key_env': 'SUB2API_API_KEY', 'key_path': ['providers', 'sub2api', 'api_key']},
    {'name': 'stepfun', 'base_url': 'https://api.stepfun.com/step_plan/v1/chat/completions', 'model': 'step-3.7-flash', 'key_env': 'STEPFUN_API_KEY', 'key_path': ['providers', 'stepfun', 'api_key']},
]
MODEL_ENV = 'A2A_MODEL'


def load_rooms():
    if yaml is None:
        print('PyYAML missing: pip install pyyaml', file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load((BASE / 'rooms.yaml').read_text())['rooms']


def load_agent_map():
    agents_path = BASE / 'agents.yaml'
    if not agents_path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(agents_path.read_text())
    return {room: cfg.get('agent_name', f'{room}-agent') for room, cfg in data.get('rooms', {}).items()}


def get_cfg():
    if not yaml or not (Path.home() / '.hermes/config.yaml').exists():
        return {}
    return yaml.safe_load((Path.home() / '.hermes/config.yaml').read_text())


def get_api_key(provider):
    cfg = get_cfg()
    try:
        val = cfg
        for k in provider['key_path']:
            val = val[k]
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(provider['key_env'])


def classify_room(title, texts, rooms):
    text = f"{title} {' '.join(texts)}".lower()
    best_room = 'ops'
    best_score = 0
    for room, cfg in rooms.items():
        score = 0
        for skill in cfg.get('primary_skills', []):
            if skill.lower() in text:
                score += 2
        for prefix in cfg.get('skill_prefixes', []):
            if prefix.lower() in text:
                score += 1
        if score > best_score:
            best_score = score
            best_room = room
    return best_room


def call_llm(provider, prompt):
    api_key = get_api_key(provider)
    if not api_key:
        return None
    try:
        r = requests.post(provider['base_url'], json={
            'model': provider['model'],
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.1,
            'max_tokens': 4096
        }, headers={'Authorization': f'Bearer {api_key}'}, timeout=120)
        if r.status_code == 200:
            data = r.json()
            msg = data['choices'][0]['message']
            content = msg.get('content', '') or msg.get('reasoning_content', '') or ''
            if not content:
                return [] if provider.get('return_empty', True) else None
            m = re.search(r'\[.*\]', content, re.DOTALL)
            if m:
                return json.loads(m.group())
            return []
        print(f"LLM {provider['name']} HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
    except Exception as e:
        print(f"LLM {provider['name']} error: {type(e).__name__}: {e}", file=sys.stderr)
    return None


def extract_with_llm(title, snippets):
    prompt = (
        "You are a knowledge extraction assistant. "
        "Extract up to 3 durable, actionable facts from this Hermes session "
        "that an AI agent should remember long-term.\n"
        "Focus on: config patterns, reusable workflows, domain pitfalls, "
        "user preferences, environment facts, architecture decisions.\n"
        "Avoid transient one-off debugging.\n"
        "Return JSON array of objects with keys: insight (string), confidence (0.0-1.0).\n"
        f"Session title: {title}\n"
        f"Snippets:\n{chr(10).join(snippets[:8])}\n"
    )
    for provider in PROVIDERS:
        if os.environ.get(MODEL_ENV):
            provider['model'] = os.environ[MODEL_ENV]
        result = call_llm(provider, prompt)
        if result is not None:
            return result
    return []


def get_sessions(since_hours=24, since_ts=None, limit=2000):
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}", file=sys.stderr)
        return []
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    if since_ts is None:
        since_ts = datetime.now(timezone.utc).timestamp() - since_hours * 3600
    cur.execute(
        "SELECT id, title, started_at, message_count "
        "FROM sessions WHERE started_at > ? ORDER BY started_at DESC LIMIT ?",
        (since_ts, limit)
    )
    rows = cur.fetchall()
    con.close()
    return [{'session_id': str(r[0]), 'title': r[1] or '', 'started_at': r[2], 'message_count': r[3]} for r in rows]


def load_processed_sessions():
    if not INDEX.exists():
        return set()
    processed = set()
    with INDEX.open('r') as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj.get('type') == 'session-insight':
                    processed.add(obj.get('source', {}).get('session_id') or obj.get('session_id'))
            except Exception:
                pass
    return processed


def get_snippets(session_id, limit=20):
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    cur.execute(
        "SELECT content FROM messages "
        "WHERE session_id = ? AND role IN ('user','assistant') "
        "ORDER BY timestamp ASC LIMIT ?",
        (session_id, limit)
    )
    rows = cur.fetchall()
    con.close()
    snippets = []
    for r in rows:
        raw = r[0] or ''
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                c = obj.get('content', '')
                if isinstance(c, list):
                    c = ' '.join(str(x) for x in c)
                snippets.append(str(c)[:800])
                continue
        except Exception:
            pass
        snippets.append(raw[:800])
    return snippets


def main():
    parser = argparse.ArgumentParser(description='A2A session distiller')
    parser.add_argument('--room', help='restrict to room')
    parser.add_argument('--since-hours', type=int, default=24)
    parser.add_argument('--all', action='store_true', help='ignore dedup and process all sessions in range')
    args = parser.parse_args()

    rooms = load_rooms()
    agent_map = load_agent_map()
    if args.room:
        if args.room not in rooms:
            print(f"Unknown room: {args.room}. Available: {list(rooms.keys())}")
            sys.exit(1)
        rooms = {args.room: rooms[args.room]}

    since_ts = None
    if not args.all and LAST_SCAN.exists():
        try:
            since_ts = float(LAST_SCAN.read_text().strip() or '0')
        except ValueError:
            since_ts = None

    sessions = get_sessions(args.since_hours, since_ts, limit=5000)
    if args.all:
        processed_sessions = set()
    else:
        processed_sessions = load_processed_sessions()
    sessions = [s for s in sessions if s['session_id'] not in processed_sessions]

    if not sessions:
        print('No new sessions.')
        return

    processed = 0
    errors = 0
    for idx, s in enumerate(sessions, 1):
        sid = s['session_id']
        snippets = get_snippets(sid)
        if not snippets:
            continue

        room = classify_room(s.get('title', ''), snippets, rooms)
        facts = extract_with_llm(s.get('title', ''), snippets)

        for fact in facts:
            confidence = float(fact.get('confidence', 0.5) or 0.5)
            if confidence < 0.6:
                continue
            proposal_id = (
                f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                f"-{room[:3]}-{uuid.uuid4().hex[:6]}"
            )
            proposal = {
                'id': proposal_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'room': room,
                'target_agent': agent_map.get(room, f'{room}-agent'),
                'type': 'session-insight',
                'source': {
                    'session_id': sid,
                    'title': s.get('title', ''),
                    'created_at': s.get('started_at', ''),
                },
                'content': fact.get('insight', ''),
                'confidence': confidence,
                'status': 'pending',
                'review_note': '',
            }
            outdir = QUEUE / 'pending' / room
            outdir.mkdir(parents=True, exist_ok=True)
            path = outdir / f"{proposal_id}.json"
            path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2))
            with INDEX.open('a') as f:
                f.write(json.dumps({
                    'id': proposal_id,
                    'room': room,
                    'created_at': proposal['created_at'],
                    'type': 'session-insight',
                }) + '\n')
            processed += 1

        if idx % 20 == 0:
            print(f"  processed {idx}/{len(sessions)} sessions, {processed} proposals so far...", flush=True)
        time.sleep(0.1)

    LAST_SCAN.write_text(str(datetime.now(timezone.utc).timestamp()))
    print(f"Processed {len(sessions)} sessions, created {processed} proposals, {errors} errors.")


if __name__ == '__main__':
    main()
