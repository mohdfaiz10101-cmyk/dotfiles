#!/usr/bin/env python3
"""A2A Skill Change Detector: watch skills dir for changes and generate proposals."""
import os, sys, json, time, re, requests, argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
QUEUE = BASE / 'queue'
SKILLS = Path.home() / '.hermes/skills'
LAST_SCAN = QUEUE / '.last-skill-scan'
INDEX = QUEUE / 'index.jsonl'

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


def skill_to_rooms(skill_name, rooms):
    matched = set()
    for room, cfg in rooms.items():
        if skill_name in cfg.get('primary_skills', []):
            matched.add(room)
            continue
        for prefix in cfg.get('skill_prefixes', []):
            if skill_name == prefix or skill_name.startswith(prefix) or prefix in skill_name:
                matched.add(room)
                break
    return list(matched) if matched else ['ops']


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
                return {'summary': 'Skill updated', 'impact': 'medium'}
            m = re.search(r'\{.*\}', content, re.DOTALL)
            if m:
                return json.loads(m.group())
            return {'summary': 'Skill updated', 'impact': 'medium'}
        print(f"LLM {provider['name']} HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
    except Exception as e:
        print(f"LLM {provider['name']} error: {type(e).__name__}: {e}", file=sys.stderr)
    return None


def summarize_change(skill_name, new_text):
    if os.environ.get('A2A_SKILL_SUMMARY_MODE', 'deterministic') == 'deterministic':
        return {'summary': f'Skill {skill_name} updated; review the SKILL.md diff before promoting behavior changes.', 'impact': 'medium'}
    prompt = (
        'Summarize what changed in this skill file in one sentence. '
        'Return JSON: {"summary": "...", "impact": "low|medium|high"}\n'
        f'Skill: {skill_name}\n'
        f'Content (first 1000 chars):\n{new_text[:1000]}'
    )
    for provider in PROVIDERS:
        if os.environ.get(MODEL_ENV):
            provider['model'] = os.environ[MODEL_ENV]
        result = call_llm(provider, prompt)
        if result is not None:
            return result
    return {'summary': f'Skill {skill_name} updated', 'impact': 'medium'}


def main():
    last = 0.0
    if LAST_SCAN.exists():
        last = float(LAST_SCAN.read_text().strip() or '0')
    rooms = load_rooms()
    agent_map = load_agent_map()
    changed = []

    if not SKILLS.exists():
        print('Skills dir not found.')
        return

    for skill_dir in sorted(SKILLS.iterdir()):
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.exists():
            continue
        try:
            mtime = skill_md.stat().st_mtime
        except OSError:
            continue
        if mtime > last:
            changed.append((skill_dir.name, skill_md))

    if not changed:
        print('No skill changes.')
        return

    proposals = 0
    for skill_name, skill_md in changed:
        new_text = skill_md.read_text()
        summary = summarize_change(skill_name, new_text)
        target_rooms = skill_to_rooms(skill_name, rooms)
        for room in target_rooms:
            proposal_id = (
                f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                f"-skill-{__import__('uuid').uuid4().hex[:6]}"
            )
            proposal = {
                'id': proposal_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'room': room,
                'target_agent': agent_map.get(room, f'{room}-agent'),
                'type': 'skill-update',
                'source': {'skill': skill_name, 'file': str(skill_md)},
                'content': (
                    f"Skill `{skill_name}` updated. "
                    f"{summary.get('summary', '')} "
                    f"Impact: {summary.get('impact', 'medium')}"
                ),
                'confidence': 0.9 if summary.get('impact') == 'high' else 0.7,
                'status': 'pending',
                'review_note': '',
            }
            outdir = QUEUE / 'pending' / room
            outdir.mkdir(parents=True, exist_ok=True)
            path = outdir / f'skill-{skill_name}-{proposal_id}.json'
            path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2))
            with INDEX.open('a') as f:
                f.write(json.dumps({
                    'id': proposal_id,
                    'room': room,
                    'type': 'skill-update',
                    'skill': skill_name,
                }) + '\n')
            proposals += 1

    LAST_SCAN.write_text(str(time.time()))
    print(f'Detected {len(changed)} skill changes, generated {proposals} proposals.')


if __name__ == '__main__':
    main()
