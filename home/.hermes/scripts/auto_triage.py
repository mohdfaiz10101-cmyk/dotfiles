#!/usr/bin/env python3
import sqlite3
import subprocess
import os
from datetime import datetime, timedelta, timezone

# Hermes Web UI DB (has session titles and message content)
WEB_UI_DB = os.path.expanduser("~/.hermes-web-ui/hermes-web-ui.db")
# Hermes CLI state DB (fallback, no titles)
STATE_DB = os.path.expanduser("~/.hermes/state.db")
HERMES_BIN = "/var/home/charlie/.local/bin/hermes"

LIMIT = 20
RECENT_DAYS = 3

RULES = [
    (
        ["会议", "项目", "deadline", "报告", "需求", "上线", "部署", "工作", "会议纪要", "周报", "月报", "评审", "milestone", "sprint"],
        "work",
        2,
    ),
    (
        ["报错", "bug", "故障", "崩溃", "异常", "修复", "error", "traceback", "exception", "core dump", "segfault", "500", "404", "timeout"],
        "bugs",
        1,
    ),
    (
        ["新功能", "需求", "产品", "迭代", "优化", "功能", "feature", "enhancement", "roadmap", "重构", "架构"],
        "features",
        3,
    ),
    (
        ["购物", "缴费", "日常", "家庭", "旅行", "吃饭", "生活", "买菜", "物业", "水电", "机票", "酒店", "快递"],
        "life",
        4,
    ),
    (
        ["调研", "学习", "资料", "技术选型", "论文", "research", "benchmark", "对比", "技术预研", "教程", "文档"],
        "research",
        3,
    ),
]

URGENT_KEYWORDS = ["紧急", "ASAP", "马上", "urgent", "immediately", "紧急修复", "hotfix", "马上处理", "urgent"]


def get_db_sessions(conn, limit=20, recent_days=3):
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=recent_days)).timestamp())
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, started_at, message_count
        FROM sessions
        WHERE started_at >= ?
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (cutoff, limit),
    )
    return cur.fetchall()


def get_db_messages(conn, session_id, limit=8):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content
        FROM messages
        WHERE session_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    rows = cur.fetchall()
    rows.reverse()
    return rows


def extract_text(messages):
    parts = []
    for role, content in messages:
        if not content:
            continue
        if role in ("user", "assistant"):
            # Skip empty assistant messages and tool-call-only messages
            if role == "assistant" and not content.strip():
                continue
            parts.append(content)
        elif role == "tool":
            # Tool outputs often contain useful context
            try:
                import json
                obj = json.loads(content)
                if isinstance(obj, dict) and "output" in obj:
                    parts.append(obj["output"])
                elif isinstance(obj, dict) and "error" in obj:
                    parts.append(obj["error"])
            except Exception:
                pass
    return " ".join(parts)


def classify(title, messages):
    text = " ".join(
        [title or ""] + [m[1] or "" for m in messages if m[0] in ("user", "assistant")]
    ).lower()

    # Urgent check first
    is_urgent = any(kw.lower() in text for kw in URGENT_KEYWORDS)
    priority = 1 if is_urgent else 3

    for keywords, board, prio_hint in RULES:
        if any(kw.lower() in text for kw in keywords):
            return board, min(priority, prio_hint)

    return "inbox", priority


def create_kanban_task(title, body, board, priority, idempotency_key):
    env = os.environ.copy()
    env["HERMES_KANBAN_BOARD"] = board
    cmd = [
        HERMES_BIN,
        "kanban",
        "create",
        "--priority",
        str(priority),
        "--idempotency-key",
        idempotency_key,
        "--json",
    ]
    if body:
        cmd.extend(["--body", body])
    cmd.append(title)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
            env=env,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr or e.stdout}"
    except Exception as e:
        return f"ERROR: {e}"


def load_existing_idempotency_keys():
    """Load all existing idempotency keys from all kanban boards to prevent duplicates."""
    keys = set()
    kanban_root = os.path.expanduser("~/.hermes/kanban/boards")
    if not os.path.isdir(kanban_root):
        return keys
    for board_name in os.listdir(kanban_root):
        db_path = os.path.join(kanban_root, board_name, "kanban.db")
        if not os.path.isfile(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT idempotency_key FROM tasks WHERE status != 'archived' AND idempotency_key IS NOT NULL AND idempotency_key != ''"
            )
            for (key,) in cur.fetchall():
                keys.add(key)
            conn.close()
        except Exception:
            pass
    return keys


def main():
    # Prefer Web UI DB (has titles), fallback to CLI state DB
    db_path = None
    if os.path.exists(WEB_UI_DB):
        db_path = WEB_UI_DB
    elif os.path.exists(STATE_DB):
        db_path = STATE_DB
    else:
        print("ERROR: No session DB found")
        return

    existing_keys = load_existing_idempotency_keys()
    conn = sqlite3.connect(db_path)
    sessions = get_db_sessions(conn, LIMIT, RECENT_DAYS)
    if not sessions:
        print("No recent sessions found.")
        return

    created = 0
    skipped = 0
    errors = 0
    details = []

    for session_id, title, started_at, message_count in sessions:
        if session_id in existing_keys:
            skipped += 1
            details.append(f"SKIP (exists) [{title or session_id}]")
            continue

        messages = get_db_messages(conn, session_id, 8)
        board, priority = classify(title, messages)

        safe_title = (title or f"session-{session_id}").strip()[:120]

        # Build a concise body with classification reason
        text_sample = extract_text(messages)[:200]
        body = (
            f"来源会话: {session_id}\n"
            f"最近活跃: {datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat() if started_at else 'N/A'}\n"
            f"消息数: {message_count or 0}\n"
            f"分类: {board} (priority={priority})\n"
            f"关键词依据: {text_sample}"
        )

        result = create_kanban_task(safe_title, body, board, priority, session_id)
        if result.startswith("ERROR"):
            errors += 1
            details.append(f"FAIL [{board}] {safe_title}: {result[:100]}")
        else:
            created += 1
            details.append(f"CREATE [{board}] {safe_title}")

    for line in details:
        print(line)
    print(f"Done. created={created} skipped={skipped} errors={errors} total={len(sessions)}")


if __name__ == "__main__":
    main()
