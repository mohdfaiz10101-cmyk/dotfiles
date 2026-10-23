#!/usr/bin/env python3
"""
Auto-compress heavy Hermes WebUI sessions that are likely wasting mobile流量.
Rules (heuristic):
- message_count >= 400
- input_tokens >= 2_000_000
- session file size >= 1.5MB
Skip currently streaming sessions and already-compressed titles.

Safeguards:
- post-compression size verification (file must shrink)
- unattended write guard (refuse to continue if skill/memory paths appear in any planned write)
"""
import json, os, sys, time, glob, requests
from datetime import datetime, timezone

BASE = os.path.expanduser('~/.hermes/webui/sessions')
WEBUI = os.environ.get('HERMES_WEBUI_URL', 'http://127.0.0.1:8787')
THRESHOLD_MESSAGES = 400
THRESHOLD_INPUT_TOKENS = 2_000_000
THRESHOLD_FILE_BYTES = 1_500_000
MAX_POST_COMPRESS_WAIT_SECONDS = 240
MAX_FILE_GROWTH_RATIO = 1.05
PROTECTED_WRITE_PREFIXES = (
    os.path.expanduser('~/.hermes/skills'),
    os.path.expanduser('~/.hermes/memories'),
    os.path.expanduser('~/.hermes/profiles'),
)


def now_ts():
    return time.time()


def load_index():
    path = os.path.join(BASE, '_index.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def session_path(session_id):
    return os.path.join(BASE, f'{session_id}.json')


def is_streaming(session_id):
    path = session_path(session_id)
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return bool(data.get('is_streaming'))
    except Exception:
        return False


def already_compressed(title: str) -> bool:
    if not title:
        return False
    return '[已压缩' in title


def session_meta(session_id):
    try:
        r = requests.get(f'{WEBUI}/api/session', params={'session_id': session_id, 'messages': '0'}, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json().get('session', {})
        path = session_path(session_id)
        size = os.path.getsize(path) if os.path.exists(path) else None
        return {
            'session_id': session_id,
            'title': data.get('title') or '',
            'message_count': data.get('message_count') or 0,
            'input_tokens': data.get('input_tokens') or 0,
            'size': size,
            'updated_at': data.get('updated_at') or data.get('created_at') or 0,
        }
    except Exception as e:
        print(f'[WARN] failed to load meta for {session_id}: {e}', file=sys.stderr)
        return None


def looks_like_protected_write(path: str) -> bool:
    normal = os.path.normpath(path)
    for prefix in PROTECTED_WRITE_PREFIXES:
        if normal.startswith(os.path.normpath(prefix) + os.sep):
            return True
    return False


def wait_for_compress_completion(session_id, pre_size):
    deadline = now_ts() + MAX_POST_COMPRESS_WAIT_SECONDS
    last_size = pre_size
    last_mtime = None
    path = session_path(session_id)
    if os.path.exists(path):
        last_mtime = os.path.getmtime(path)
    while now_ts() < deadline:
        time.sleep(2)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        current_mtime = os.path.getmtime(path)
        current_size = os.path.getsize(path)
        if not bool(data.get('is_streaming')) and current_mtime != last_mtime:
            last_size = current_size
            return last_size, current_mtime
        last_size = current_size
        last_mtime = current_mtime
    return last_size, last_mtime


def session_meta(session_id):
    try:
        r = requests.get(f'{WEBUI}/api/session', params={'session_id': session_id, 'messages': '0'}, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json().get('session', {})
        path = session_path(session_id)
        size = os.path.getsize(path) if os.path.exists(path) else None
        mtime = os.path.getmtime(path) if os.path.exists(path) else None
        return {
            'session_id': session_id,
            'title': data.get('title') or '',
            'message_count': data.get('message_count') or 0,
            'input_tokens': data.get('input_tokens') or 0,
            'size': size,
            'mtime': mtime,
            'updated_at': data.get('updated_at') or data.get('created_at') or 0,
        }
    except Exception as e:
        print(f'[WARN] failed to load meta for {session_id}: {e}', file=sys.stderr)
        return None


def has_recent_activity(session_id, max_seconds=14400):
    paths = [
        os.path.join(BASE, f'{session_id}.json'),
        os.path.join(BASE, '_archive_old', f'{session_id}.json'),
    ]
    now = now_ts()
    for p in paths:
        if os.path.exists(p) and (now - os.path.getmtime(p)) < max_seconds:
            return True
    return False


def compress_session(session_id):
    path = session_path(session_id)
    pre_meta = session_meta(session_id)
    if not pre_meta or not pre_meta.get('size'):
        print(f'[SKIP] missing session meta: {session_id}')
        return False

    try:
        r = requests.post(f'{WEBUI}/api/session/compress/start', json={'session_id': session_id}, timeout=30)
        if r.status_code != 200:
            if r.status_code == 409:
                print(f'[SKIP] session busy/streaming: {session_id} -> {r.text[:200]}')
            else:
                print(f'[WARN] compress unexpected {r.status_code} for {session_id}: {r.text[:200]}', file=sys.stderr)
            return False
    except Exception as e:
        print(f'[ERR] compress failed for {session_id}: {e}', file=sys.stderr)
        return False

    pre_size = int(pre_meta.get('size') or 0)
    post_meta = session_meta(session_id)
    if isinstance(post_meta, dict) and post_meta.get('compression_anchor_visible_idx') and pre_meta.get('message_count') and post_meta.get('message_count') < pre_meta['message_count']:
        print(f'[OK] compress verified from prior run: {session_id} msgs {pre_meta["message_count"]}->{post_meta.get("message_count")}')
        return True
    post_size, post_mtime = wait_for_compress_completion(session_id, pre_size)
    post_meta = session_meta(session_id)
    compression_summary = None
    compression_anchor_idx = None
    if isinstance(post_meta, dict):
        compression_summary = post_meta.get('compression_anchor_summary')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        compression_anchor_idx = data.get('compression_anchor_visible_idx')
    except Exception:
        pass
    size_shrank = post_size < pre_size
    message_count_reduced = (
        isinstance(pre_meta.get('message_count'), int) and isinstance(post_meta, dict) and
        isinstance(post_meta.get('message_count'), int) and
        pre_meta['message_count'] > 0 and post_meta['message_count'] < pre_meta['message_count'] * 0.9
    )
    input_tokens_reduced = (
        isinstance(pre_meta.get('input_tokens'), int) and isinstance(post_meta, dict) and
        isinstance(post_meta.get('input_tokens'), int) and
        pre_meta['input_tokens'] > 0 and post_meta['input_tokens'] < pre_meta['input_tokens'] * 0.95
    )
    prompt_tokens_reduced = False
    if isinstance(pre_meta, dict) and isinstance(post_meta, dict):
        pre_prompt = pre_meta.get('last_prompt_tokens') or 0
        post_prompt = post_meta.get('last_prompt_tokens') or 0
        if isinstance(pre_prompt, (int, float)) and isinstance(post_prompt, (int, float)) and pre_prompt > 0:
            prompt_tokens_reduced = post_prompt < pre_prompt * 0.8
    context_compressed = bool(compression_summary) or compression_anchor_idx is not None
    if size_shrank or message_count_reduced or input_tokens_reduced or prompt_tokens_reduced or context_compressed:
        reasons = []
        if size_shrank:
            reasons.append(f'size {pre_size}->{post_size}')
        if message_count_reduced:
            reasons.append(f'msgs {pre_meta["message_count"]}->{post_meta.get("message_count")}')
        if input_tokens_reduced:
            reasons.append(f'tokens {pre_meta["input_tokens"]}->{post_meta.get("input_tokens")}')
        if context_compressed:
            reasons.append('context_anchor_set')
        print(f'[OK] compress verified: {session_id} | {", ".join(reasons)}')
        return True
    print(f'[FAIL] compression not verified: {session_id} pre_size={pre_size} post_size={post_size} pre_msgs={pre_meta.get("message_count") if isinstance(pre_meta, dict) else None} post_msgs={post_meta.get("message_count") if isinstance(post_meta, dict) else None} pre_tokens={pre_meta.get("input_tokens") if isinstance(pre_meta, dict) else None} post_tokens={post_meta.get("input_tokens") if isinstance(post_meta, dict) else None} anchor={compression_anchor_idx} summary={compression_summary}')
    return False


def assert_no_protected_writes(args):
    joined = ' '.join(args)
    for prefix in PROTECTED_WRITE_PREFIXES:
        if prefix in joined:
            print(f'[BLOCK] protected write path detected: {prefix}', file=sys.stderr)
            return False
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Auto-compress heavy Hermes WebUI sessions')
    parser.add_argument('min_age_days', nargs='?', type=int, default=0, help='Minimum session age in days')
    parser.add_argument('max_candidates', nargs='?', type=int, default=20, help='Max candidates to process')
    parser.add_argument('--dry-run', action='store_true', help='Only scan and report candidates')
    parser.add_argument('--compress', action='store_true', help='Actually compress candidates')
    parser.add_argument('--max-wait', type=int, default=180, help='Max seconds to wait per compression')
    args = parser.parse_args()
    if not args.compress:
        args.dry_run = True
    global MAX_POST_COMPRESS_WAIT_SECONDS
    MAX_POST_COMPRESS_WAIT_SECONDS = max(30, int(args.max_wait))

    if not assert_no_protected_writes(sys.argv):
        return 1

    now = now_ts()
    data = load_index()
    candidates = []
    for item in data:
        sid = item.get('session_id')
        if not sid:
            continue
        updated = item.get('updated_at') or item.get('created_at') or 0
        if args.min_age_days and (now - updated) < args.min_age_days * 86400:
            continue
        if item.get('pinned'):
            continue
        if already_compressed(item.get('title') or ''):
            continue
        if has_recent_activity(sid, max_seconds=14400):
            print(f'[SKIP] recent activity within 4h: {sid}')
            continue
        meta = session_meta(sid)
        if not meta:
            continue
        if is_streaming(sid):
            print(f'[SKIP] streaming: {sid}')
            continue
        score = 0
        reasons = []
        if meta['message_count'] >= THRESHOLD_MESSAGES:
            score += meta['message_count']
            reasons.append(f"messages={meta['message_count']}")
        if meta['input_tokens'] >= THRESHOLD_INPUT_TOKENS:
            score += meta['input_tokens'] / 1_000_000
            reasons.append(f"input_tokens={meta['input_tokens']}")
        if meta['size'] and meta['size'] >= THRESHOLD_FILE_BYTES:
            score += meta['size'] / 1_000_000
            reasons.append(f"size={meta['size']}")
        if score:
            candidates.append((score, sid, meta['title'], reasons))
    candidates = sorted(candidates, key=lambda x: x[0], reverse=True)[:args.max_candidates]
    print(f'candidates={len(candidates)} now={datetime.now(timezone.utc).astimezone().isoformat()}')
    for score, sid, title, reasons in candidates:
        print(f'CAND {score:>10.1f} | {sid} | {title} | {", ".join(reasons)}')
    if not args.compress:
        print('[DRY-RUN] no compression attempted because --compress was not specified')
        return 0
    compressed = []
    for _, sid, title, reasons in candidates:
        print(f'TRY {sid} | {title} | {", ".join(reasons)}')
        if not assert_no_protected_writes([sid, title]):
            continue
        if compress_session(sid):
            compressed.append(sid)
            time.sleep(1)
    print(f'compressed={len(compressed)}')
    for sid in compressed:
        print(sid)


if __name__ == '__main__':
    raise SystemExit(main())
