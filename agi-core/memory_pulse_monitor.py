#!/usr/bin/env python3
"""
memory_pulse_monitor.py — 记忆呼吸灯监控
从 Letta / mem0 / memory/*.md 同步记忆到 pulse.db，追踪访问和衰减
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# === 配置 ===
DB_PATH = Path(os.environ.get("PULSE_DB", "/mnt/ai/data/memory-pulse/pulse.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
MEMORY_DIR = Path(os.environ.get("MEMORY_DIR",
    os.path.expanduser("~/.claude/projects/-home-charlie/memory")))

LETTA_BASE = "http://localhost:8283/v1/agents"
LETTA_TOKEN = os.environ.get("LETTA_TOKEN", "letta")
LETTA_AGENTS = {
    "code-assistant": "agent-9b3bcec2-0a26-458c-a2e0-639c0f9686ca",
    "nixos-sysadmin": "agent-0040ded4-1831-4b76-a4a4-62519a416a5a",
}
MEM0_URL = "http://localhost:8285/get_all?limit=200"
DECAY_FACTOR = 0.95
LOG_FILE = Path("/home/charlie/agi/memory-pulse.log")


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS pulse (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_accessed_at TEXT NOT NULL,
        access_count INTEGER DEFAULT 0,
        pulse_score REAL DEFAULT 1.0,
        status TEXT DEFAULT 'green',
        tags TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS pulse_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pulse_id TEXT NOT NULL,
        event TEXT NOT NULL,
        ts TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_pulse_status ON pulse(status);
    CREATE INDEX IF NOT EXISTS idx_pulse_source ON pulse(source);
    CREATE INDEX IF NOT EXISTS idx_pulse_score ON pulse(pulse_score);
    """)
    conn.commit()


def content_hash(text: str, source: str) -> str:
    raw = f"{source}:{text[:200]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def upsert_pulse(conn: sqlite3.Connection, source: str, text: str,
                 tags: str = "", created_at: str = None):
    cid = content_hash(text, source)
    now = datetime.now().isoformat()
    if created_at is None:
        created_at = now

    existing = conn.execute(
        "SELECT id, access_count FROM pulse WHERE id=?", (cid,)
    ).fetchone()

    if existing:
        log(f"[skip] 已存在: {cid[:8]} ({source})")
        return 0

    conn.execute(
        """INSERT OR IGNORE INTO pulse
           (id, source, content, created_at, last_accessed_at,
            access_count, pulse_score, status, tags)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (cid, source, text[:500], created_at, now, 0, 1.0, "green", tags),
    )
    conn.execute(
        "INSERT INTO pulse_log (pulse_id, event, ts) VALUES (?,?,?)",
        (cid, "add", now),
    )
    conn.commit()
    log(f"[add] {cid[:8]} ({source}): {text[:60]}...")
    return 1


def compute_status(score: float) -> str:
    if score > 0.7:
        return "green"
    elif score > 0.4:
        return "yellow"
    elif score > 0.1:
        return "red"
    else:
        return "archived"


def decay_scores(conn: sqlite3.Connection):
    conn.execute("UPDATE pulse SET pulse_score = pulse_score * ? WHERE status != 'archived'",
                 (DECAY_FACTOR,))
    rows = conn.execute(
        "SELECT id, pulse_score FROM pulse WHERE status != 'archived'"
    ).fetchall()
    updated = 0
    now = datetime.now().isoformat()
    for r in rows:
        new_status = compute_status(r["pulse_score"])
        if new_status == "archived":
            conn.execute("UPDATE pulse SET status='archived' WHERE id=?", (r["id"],))
            conn.execute("INSERT INTO pulse_log (pulse_id, event, ts) VALUES (?,?,?)",
                         (r["id"], "archived", now))
            updated += 1
        else:
            conn.execute("UPDATE pulse SET status=? WHERE id=?", (new_status, r["id"]))
    conn.commit()
    log(f"[decay] 衰减完成, {len(rows)}条记录, {updated}条归档")
    return len(rows)


def access_pulse(conn: sqlite3.Connection, pulse_id: str) -> bool:
    row = conn.execute("SELECT id FROM pulse WHERE id=?", (pulse_id,)).fetchone()
    if not row:
        return False
    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE pulse SET pulse_score=1.0, last_accessed_at=?,
           access_count=access_count+1, status='green' WHERE id=?""",
        (now, pulse_id),
    )
    conn.execute(
        "INSERT INTO pulse_log (pulse_id, event, ts) VALUES (?,?,?)",
        (pulse_id, "access", now),
    )
    conn.commit()
    return True


# === 数据源拉取 ===

def fetch_json(url: str, headers: dict = None) -> list:
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"[warn] 拉取失败 {url}: {e}")
        return []


def sync_letta(conn: sqlite3.Connection):
    count = 0
    for agent_name, agent_id in LETTA_AGENTS.items():
        url = f"{LETTA_BASE}/{agent_id}/archival-memory"
        items = fetch_json(url, {"Authorization": f"Bearer {LETTA_TOKEN}"})
        for item in items:
            text = item.get("text", "").strip()
            if not text or item.get("is_deleted"):
                continue
            created = item.get("created_at", "")
            tags = ",".join(item.get("tags") or [])
            count += upsert_pulse(conn, f"letta:{agent_name}", text, tags, created)
    log(f"[sync] Letta: {count} 条新增")


def sync_mem0(conn: sqlite3.Connection):
    data = fetch_json(MEM0_URL)
    items = data.get("memories", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        log(f"[warn] mem0 返回格式异常: {type(items)}")
        return
    count = 0
    for item in items:
        text = item.get("memory", "").strip()
        if not text:
            continue
        meta = item.get("metadata") or {}
        ts = meta.get("ts", "")
        tags = f"mem0,{meta.get('source', '')}"
        count += upsert_pulse(conn, "mem0", text, tags, ts)
    log(f"[sync] mem0: {count} 条新增")


def sync_files(conn: sqlite3.Connection):
    if not MEMORY_DIR.exists():
        log(f"[warn] memory目录不存在: {MEMORY_DIR}")
        return
    count = 0
    for md_file in MEMORY_DIR.glob("*.md"):
        try:
            lines = md_file.read_text(errors="ignore").splitlines()
        except Exception:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---") or len(line) < 10:
                continue
            if re.match(r"^- \[( |x|!)\]", line):
                text = re.sub(r"^- \[(?: |x|!)\] \[[^\]]*\] ", "", line).strip()
            elif line.startswith("- "):
                text = line[2:].strip()
            else:
                continue
            if len(text) < 10:
                continue
            tags = md_file.stem
            count += upsert_pulse(conn, f"file:{md_file.stem}", text, tags)
    log(f"[sync] memory文件: {count} 条新增")


def run_sync():
    conn = get_db()
    init_db(conn)
    try:
        sync_letta(conn)
        sync_mem0(conn)
        sync_files(conn)
    finally:
        conn.close()


def run_decay():
    conn = get_db()
    try:
        decay_scores(conn)
    finally:
        conn.close()


def run_status():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM pulse GROUP BY status"
        ).fetchall()
        summary = {r["status"]: r["cnt"] for r in rows}
        total = sum(summary.values())
        avg = conn.execute("SELECT AVG(pulse_score) as a FROM pulse WHERE status!='archived'").fetchone()
        oldest = conn.execute(
            """SELECT id, source, last_accessed_at, pulse_score
               FROM pulse WHERE status!='archived'
               ORDER BY last_accessed_at ASC LIMIT 5"""
        ).fetchall()
        red_count = conn.execute(
            "SELECT COUNT(*) as c FROM pulse WHERE status='red'"
        ).fetchone()["c"]
        print(json.dumps({
            "summary": summary,
            "total": total,
            "avg_score": round(avg["a"], 3) if avg["a"] else 0,
            "red_count": red_count,
            "oldest_unaccessed": [
                {"id": r["id"], "source": r["source"],
                 "last_accessed": r["last_accessed_at"], "score": round(r["pulse_score"], 3)}
                for r in oldest
            ],
        }, ensure_ascii=False, indent=2))
    finally:
        conn.close()


# === CLI ===
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if cmd == "sync":
        run_sync()
    elif cmd == "decay":
        run_decay()
    elif cmd == "status":
        run_status()
    elif cmd == "init":
        conn = get_db()
        init_db(conn)
        conn.close()
        log("[init] 数据库初始化完成")
    else:
        print(f"用法: {sys.argv[0]} [sync|decay|status|init]")
        sys.exit(1)
