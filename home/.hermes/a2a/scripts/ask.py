#!/usr/bin/env python3
"""A2A Ask: query agent knowledge bases."""
import os, sys, argparse, re
from pathlib import Path

BASE = Path(os.environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
KNOWLEDGE = BASE / 'knowledge'


def _pattern(query):
    words = re.findall(r'\w+', query)
    return re.compile('|'.join(r'\b' + re.escape(w) + r'\b' for w in words), re.IGNORECASE)


def ask(query, room=None):
    pattern = _pattern(query)
    rooms = [room] if room else sorted([d.name for d in KNOWLEDGE.iterdir() if d.is_dir()])
    results = []
    for r in rooms:
        kdir = KNOWLEDGE / r
        if not kdir.exists():
            continue
        for f in sorted(kdir.glob('*.md')):
            try:
                text = f.read_text()
            except OSError:
                continue
            if pattern.search(text):
                lines = text.splitlines()
                matches = [l for l in lines if pattern.search(l)][:8]
                results.append({'room': r, 'file': f.name, 'matches': matches})

    if not results:
        print('No matches found.')
        return

    print(f'Found {len(results)} matches:')
    for res in results:
        print(f"\n=== {res['room']} / {res['file']} ===")
        for m in res['matches']:
            print(f'  {m.strip()}')


def main():
    parser = argparse.ArgumentParser(description='A2A ask')
    parser.add_argument('query')
    parser.add_argument('--room')
    args = parser.parse_args()
    ask(args.query, args.room)


if __name__ == '__main__':
    main()
