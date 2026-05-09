#!/usr/bin/env python3
"""
letta-sync.py — memory/*.md → Letta archival 增量同步
每日运行，只注入新增条目（基于 hash 去重）
"""
import hashlib, json, os, re, requests, time
from pathlib import Path

BASE = "http://localhost:8283/v1"
HEADERS = {"Authorization": "Bearer letta", "Content-Type": "application/json"}
SYSADMIN = "agent-8651643c-e753-47ed-9759-bd955c6ac240"
CODE = "agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea"
MEM = Path.home() / ".claude/projects/-home-charlie/memory"
HASH_CACHE = Path("/tmp/letta-sync-hashes.json")

def load_hashes():
    return json.loads(HASH_CACHE.read_text()) if HASH_CACHE.exists() else {}

def save_hashes(h):
    HASH_CACHE.write_text(json.dumps(h))

def entry_hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def write_letta(agent_id, text):
    r = requests.post(f"{BASE}/agents/{agent_id}/archival-memory",
                      headers=HEADERS, json={"text": text}, timeout=10)
    return r.ok

def count_letta(agent_id):
    r = requests.get(f"{BASE}/agents/{agent_id}/archival-memory?limit=2000", headers=HEADERS, timeout=15)
    return len(r.json()) if r.ok else -1

hashes = load_hashes()
new_total = 0

ROUTES = [
    (MEM / "lessons-learned.md",    SYSADMIN, "[lessons]",      r"^- \[20\d\d"),
    (MEM / "nixos-config.md",       SYSADMIN, "[nixos-config]", r"^##"),
    (MEM / "troubleshooting.md",    SYSADMIN, "[troubleshoot]", r"^\|[^─]"),
    (MEM / "codebase-map.md",       CODE,     "[codebase-map]", r"^- \[20\d\d"),
    (MEM / "app-dev-journal.md",    CODE,     "[app-dev]",      r"^## "),
    (MEM / "ai-tools.md",           CODE,     "[ai-tools]",     r"^## "),
]

for fpath, agent_id, prefix, pattern in ROUTES:
    if not fpath.exists():
        continue
    content = fpath.read_text()
    entries = [l.strip() for l in content.split('\n') if re.match(pattern, l.strip()) and len(l.strip()) > 20]
    added = 0
    for e in entries:
        h = entry_hash(e)
        if h not in hashes:
            text = f"{prefix} {e}"[:800]
            if write_letta(agent_id, text):
                hashes[h] = True
                added += 1
                new_total += 1
    if added > 0:
        print(f"[SYNC] {fpath.name}: +{added} 条新增")

save_hashes(hashes)
print(f"[SYNC] 完成: +{new_total} 条 | nixos-sysadmin={count_letta(SYSADMIN)} | code-assistant={count_letta(CODE)}")
