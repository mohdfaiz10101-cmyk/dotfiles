#!/run/current-system/sw/bin/python3
"""
letta-sync.py — memory/*.md + changelog.jsonl → Letta archival 增量同步
v2: 新增 changelog 事件流增量写入，hash 去重
"""
import hashlib, json, os, re, requests, time
from pathlib import Path
from urllib.parse import urljoin

BASE = "http://localhost:8283/v1"
HEADERS = {"Authorization": "Bearer letta", "Content-Type": "application/json"}
SYSADMIN = "agent-8651643c-e753-47ed-9759-bd955c6ac240"
CODE = "agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea"
MEM = Path.home() / ".claude/projects/-home-charlie/memory"
HASH_CACHE = Path(Path.home() / ".local/state/letta-sync-hashes.json")
CHANGELOG = MEM / "changelog.jsonl"
CL_SYNC_POS = Path(Path.home() / ".local/state/letta-sync-cl-pos")  # changelog 读取位置

def load_hashes():
    return json.loads(HASH_CACHE.read_text()) if HASH_CACHE.exists() else {}

def save_hashes(h):
    HASH_CACHE.write_text(json.dumps(h))

def entry_hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def write_letta(agent_id, text):
    url = urljoin(f"{BASE.rstrip('/')}/", f"agents/{agent_id}/archival-memory/")
    for attempt in range(3):
        try:
            r = requests.post(
                url,
                headers=HEADERS,
                json={"text": text},
                timeout=10,
                allow_redirects=True,
            )
            if r.ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(2 ** attempt)
    return False

def count_letta(agent_id):
    r = requests.get(f"{BASE}/agents/{agent_id}/archival-memory?limit=2000", headers=HEADERS, timeout=15)
    return len(r.json()) if r.ok else -1

def get_agent(scope):
    """根据 scope 路由到 Letta agent"""
    s = scope.lower()
    if any(k in s for k in ('nixos','systemd','service','proxy','security','docker')):
        return SYSADMIN
    if any(k in s for k in ('agi','frontend','openclaw','opencode','code','api')):
        return CODE
    return SYSADMIN  # 默认

def sync_changelog(hashes):
    """增量同步 changelog.jsonl 新事件到 Letta"""
    if not CHANGELOG.exists():
        return 0
    lines = CHANGELOG.read_text().strip().split('\n')
    pos = int(CL_SYNC_POS.read_text()) if CL_SYNC_POS.exists() else 0
    if pos >= len(lines):
        return 0

    added = 0
    for line in lines[pos:]:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            pos += 1
            continue
        text = f"[event:{ev['type']}] {ev['desc']}"
        if ev.get('scope'):
            text += f" (scope: {ev['scope']})"
        text = text[:800]
        h = entry_hash(text)
        if h not in hashes:
            agent = get_agent(ev.get('scope', ''))
            if write_letta(agent, text):
                hashes[h] = True
                added += 1
        pos += 1

    CL_SYNC_POS.write_text(str(pos))
    return added

# 主流程
hashes = load_hashes()
new_total = 0

# 1. changelog 增量（优先，最新数据）
cl_added = sync_changelog(hashes)
if cl_added > 0:
    print(f"[SYNC] changelog.jsonl: +{cl_added} 条事件")
    new_total += cl_added

# 2. memory/*.md 全量扫描（兜底）
ROUTES = [
    (MEM / "lessons-learned.md",    SYSADMIN, "[lessons]",      r"^- \[20\d\d"),
    (MEM / "nixos-config.md",       SYSADMIN, "[nixos-config]", r"^##"),
    (MEM / "troubleshooting.md",    SYSADMIN, "[troubleshoot]", r"^\|[^─]"),
    (MEM / "codebase-map.md",       CODE,     "[codebase-map]", r"^- \[20\d\d"),
    (MEM / "app-dev-journal.md",    CODE,     "[app-dev]",      r"^## "),
    (MEM / "ai-tools.md",           CODE,     "[ai-tools]",     r"^## "),
    (MEM / "router-infra.md",       SYSADMIN, "[router-infra]", r"^##"),
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
print(f"[SYNC] 完成: +{new_total} 条 | changelog={cl_added} | nixos-sysadmin={count_letta(SYSADMIN)} | code-assistant={count_letta(CODE)}")
