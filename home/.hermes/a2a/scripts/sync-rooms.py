#!/usr/bin/env python3
"""Sync A2A rooms/agents from ~/.hermes/a2a/rooms.yaml into Hermes native Group Chat API."""
import os, sys, json, yaml, requests
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

if yaml is None:
    print('PyYAML missing: pip install pyyaml', file=sys.stderr)
    sys.exit(1)

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
ROOMS_PATH = BASE / 'rooms.yaml'
AGENTS_PATH = BASE / 'agents.yaml'
TOKEN_PATH = Path.home() / '.hermes-web-ui/.token'
API_BASE = 'http://127.0.0.1:8648'


def get_token():
    return TOKEN_PATH.read_text().strip() if TOKEN_PATH.exists() else None


def headers():
    tok = get_token()
    if not tok:
        raise RuntimeError('Hermes Web UI token not found at ~/.hermes-web-ui/.token')
    return {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}


def create_room(name, invite_code):
    r = requests.post(f'{API_BASE}/api/hermes/group-chat/rooms', headers=headers(), json={
        'name': name,
        'inviteCode': invite_code,
    })
    r.raise_for_status()
    return r.json()['room']['id']


def create_agent(room_id, name, profile, description):
    r = requests.post(f'{API_BASE}/api/hermes/group-chat/rooms/{room_id}/agents', headers=headers(), json={
        'name': name,
        'profile': profile,
        'description': description,
    })
    r.raise_for_status()
    return r.json()['agent']


def main():
    rooms = yaml.safe_load(ROOMS_PATH.read_text())['rooms']
    agents = yaml.safe_load(AGENTS_PATH.read_text())['agents']

    existing = requests.get(f'{API_BASE}/api/hermes/group-chat/rooms', headers=headers()).json()['rooms']
    existing_map = {r['name']: r for r in existing}

    created_rooms = 0
    created_agents = 0

    for room_name, cfg in rooms.items():
        if room_name in existing_map:
            room_id = existing_map[room_name]['id']
            print(f'ROOM EXISTS {room_name}: {room_id}')
        else:
            room_id = create_room(room_name, f'{room_name}-room')
            print(f'ROOM CREATED {room_name}: {room_id}')
            created_rooms += 1

        # find agents for this room
        agent_names = cfg.get('agents', [])
        for agent_name in agent_names:
            agent_cfg = agents.get(agent_name, {})
            profile = agent_cfg.get('profile', 'secondary')
            description = agent_cfg.get('description', '')

            # check if agent already exists in room
            r = requests.get(f'{API_BASE}/api/hermes/group-chat/rooms/{room_id}/agents', headers=headers())
            r.raise_for_status()
            current_agents = r.json()['agents']
            if any(a['name'] == agent_name for a in current_agents):
                print(f'  AGENT EXISTS {agent_name} in {room_name}')
                continue

            agent = create_agent(room_id, agent_name, profile, description)
            print(f'  AGENT CREATED {agent_name} in {room_name}: profile={profile}')
            created_agents += 1

    print(f'\nSummary: created {created_rooms} rooms, {created_agents} agents.')


if __name__ == '__main__':
    main()
