#!/usr/bin/env python3
"""A2A Sync: push approved proposals to agent knowledge bases."""
import os, sys, json, shutil, argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
QUEUE = BASE / 'queue'
KNOWLEDGE = BASE / 'knowledge'
AGENTS_PATH = BASE / 'agents.yaml'


def load_agent_map():
    if not AGENTS_PATH.exists() or yaml is None:
        return {}
    data = yaml.safe_load(AGENTS_PATH.read_text())
    return {room: cfg.get('agent_name', f'{room}-agent') for room, cfg in data.get('rooms', {}).items()}


def sync_room(room=None):
    approved_dir = QUEUE / 'approved'
    if room:
        room_dirs = [approved_dir / room]
    else:
        room_dirs = [d for d in approved_dir.iterdir() if d.is_dir()]

    synced = 0
    for room_dir in room_dirs:
        if not room_dir.exists():
            continue
        r = room_dir.name
        kdir = KNOWLEDGE / r
        kdir.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        kfile = kdir / f'{today}.md'
        header = f'# {r} Knowledge - {today}\n\n'
        content = header if not kfile.exists() else kfile.read_text()

        new_entries = []
        for f in sorted(room_dir.iterdir()):
            if f.suffix != '.json':
                continue
            data = json.loads(f.read_text())
            entry = (
                f"\n## [{data['created_at']}] {data['content'][:100]}\n"
                f"Source: {data['source'].get('title', '')} "
                f"({data['source'].get('session_id', '')})\n"
                f"Confidence: {data['confidence']}\n\n"
                f"{data['content']}\n\n---\n"
            )
            new_entries.append((entry, data['content']))

        appended = 0
        for entry, content_text in new_entries:
            if content_text not in content:
                content += entry
                appended += 1

        if appended > 0:
            kfile.write_text(content)

        for f in list(room_dir.iterdir()):
            if f.suffix == '.json':
                dest = QUEUE / 'synced' / r / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dest))
                synced += 1

    print(f'Synced {synced} items.')


def main():
    parser = argparse.ArgumentParser(description='A2A sync')
    parser.add_argument('--room', help='restrict to room')
    args = parser.parse_args()
    sync_room(args.room)


if __name__ == '__main__':
    main()
