#!/usr/bin/env python3
"""A2A Approval CLI: list / approve / reject proposals."""
import os, sys, json, shutil, argparse
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
QUEUE = BASE / 'queue'


def _find_file(proposal_id, statuses):
    for status in statuses:
        target = QUEUE / status
        if not target.exists():
            continue
        for room_dir in target.iterdir():
            if not room_dir.is_dir():
                continue
            for candidate in room_dir.iterdir():
                if candidate.suffix == '.json' and proposal_id in candidate.stem:
                    return candidate, status, room_dir.name
    return None, None, None


def list_items(status='pending', room=None):
    target = QUEUE / status
    if not target.exists():
        print(f'No {status} directory.')
        return
    items = []
    for room_dir in sorted(target.iterdir()):
        if not room_dir.is_dir():
            continue
        if room and room_dir.name != room:
            continue
        for f in sorted(room_dir.iterdir()):
            if f.suffix == '.json':
                items.append(json.loads(f.read_text()))
    if not items:
        print(f'No {status} items.')
        return
    print(f"=== {status.upper()} ({len(items)}) ===")
    for it in items:
        src = it.get('source', {})
        print(f"[{it['id']}] room={it['room']} agent={it['target_agent']} conf={it['confidence']}")
        print(f"  type={it['type']} | {it['content'][:120]}")
        if src:
            print(f"  source: {src.get('title', '')[:80]} ({src.get('session_id', '')})")
        if it.get('review_note'):
            print(f"  note: {it['review_note']}")
        print()


def approve(proposal_id):
    path, status, room = _find_file(proposal_id, ['pending', 'rejected'])
    if not path:
        print(f'Not found: {proposal_id}')
        return False
    data = json.loads(path.read_text())
    data['status'] = 'approved'
    data['approved_at'] = datetime.now(timezone.utc).isoformat()
    dest = QUEUE / 'approved' / room / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    path.unlink()
    print(f"Approved {proposal_id} (from {status})")
    return True


def reject(proposal_id, reason=''):
    path, status, room = _find_file(proposal_id, ['pending', 'approved'])
    if not path:
        print(f'Not found: {proposal_id}')
        return False
    data = json.loads(path.read_text())
    data['status'] = 'rejected'
    data['rejected_at'] = datetime.now(timezone.utc).isoformat()
    data['reject_reason'] = reason
    dest = QUEUE / 'rejected' / room / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    path.unlink()
    print(f"Rejected {proposal_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description='A2A approve/reject')
    parser.add_argument('action', choices=['list', 'approve', 'reject'])
    parser.add_argument('id', nargs='?')
    parser.add_argument('--room', help='filter by room')
    parser.add_argument('--reason', default='')
    args = parser.parse_args()

    if args.action == 'list':
        list_items('pending', args.room)
    elif args.action == 'approve':
        if not args.id:
            print('Usage: a2a approve <id>')
            sys.exit(1)
        approve(args.id)
    elif args.action == 'reject':
        if not args.id:
            print('Usage: a2a reject <id> [--reason ...]')
            sys.exit(1)
        reject(args.id, args.reason)


if __name__ == '__main__':
    main()
