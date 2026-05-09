"""
social_relations.py — 微信社交关系分析引擎
分析消息DB中的群友共现、@互动、私聊频率，计算关系强度

数据源:
- /mnt/ai/data/wechat-merged/messages.db (合并消息库, talker为MD5 hash)
- ~/.local/share/macg/wechat-table-map.json (table映射元数据)

输出:
- /mnt/ai/apps/wechat-agent/data/crm.db (relations/groups/group_members表)
"""

import sqlite3
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations

# --- paths ---
CRM_DB = Path("/mnt/ai/apps/wechat-agent/data/crm.db")
MERGED_DB = Path("/mnt/ai/data/wechat-merged/messages.db")
TABLE_MAP = Path.home() / ".local/share/macg/wechat-table-map.json"

# --- regex: extract sender wxid from group message content ---
# pattern: "wxid_xxxxxx:\n" or "w123456789:\n" at line start
SENDER_RE = re.compile(r"^(wxid_[a-z0-9]+|[a-z]\d{7,12}):\n", re.MULTILINE)
# @mention pattern in message body
AT_MENTION_RE = re.compile(r"@(\S+)")

# WeChat private chat identifier: no wxid_ prefix in content
# Group messages always start with "wxid_xxx:\n" or "w123456:\n"


def _load_table_map() -> dict:
    """加载 wechat-table-map.json"""
    if not TABLE_MAP.exists():
        return {}
    with open(TABLE_MAP, "r", encoding="utf-8") as f:
        return json.load(f)


def _ts_to_iso(ts: int) -> str:
    """Unix timestamp → ISO datetime string"""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return None


# ===========================================================================
# Schema
# ===========================================================================


def ensure_schema():
    """确保 CRM DB 有 relations/groups/group_members 表"""
    with sqlite3.connect(str(CRM_DB)) as conn:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wxid_a TEXT NOT NULL,
            wxid_b TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            strength REAL DEFAULT 0.0,
            co_group_count INTEGER DEFAULT 0,
            interaction_count INTEGER DEFAULT 0,
            last_interaction DATETIME,
            metadata TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (wxid_a) REFERENCES contacts(wxid),
            FOREIGN KEY (wxid_b) REFERENCES contacts(wxid),
            UNIQUE(wxid_a, wxid_b, relation_type)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS groups (
            room_id TEXT PRIMARY KEY,
            name TEXT,
            member_count INTEGER DEFAULT 0,
            members_json TEXT,
            message_count INTEGER DEFAULT 0,
            last_active DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS group_members (
            room_id TEXT NOT NULL,
            wxid TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            join_time DATETIME,
            message_count INTEGER DEFAULT 0,
            last_message DATETIME,
            PRIMARY KEY (room_id, wxid),
            FOREIGN KEY (room_id) REFERENCES groups(room_id),
            FOREIGN KEY (wxid) REFERENCES contacts(wxid)
        )""")
        conn.commit()


# ===========================================================================
# Helper: classify talkers & extract senders
# ===========================================================================


def _classify_talkers(msg_conn: sqlite3.Connection) -> dict:
    """
    从 messages 表分类 talker: 群聊 vs 私聊
    判断标准: talker 的消息内容中是否包含 wxid_/w数字 发送者前缀

    Returns:
        {
            "group_talkers": {talker_hash: {"members": set(wxid...), "msg_count": N, "last_time": ts}},
            "private_talkers": {talker_hash: {"msg_count": N, "last_time": ts}},
            "talker_wxid_map": {talker_hash: wxid_or_None}
        }
    """
    cur = msg_conn.cursor()
    cur.execute(
        "SELECT talker, message_content, create_time FROM messages ORDER BY talker, create_time"
    )

    group_talkers = {}  # hash → {members, msg_count, last_time}
    private_talkers = {}  # hash → {msg_count, last_time}
    talker_wxid_map = {}  # hash → possible wxid (for private chats with sender info)

    for talker, content, ts in cur.fetchall():
        if not content:
            continue
        # Check if content starts with wxid_/w数字 pattern → group message
        has_sender_prefix = bool(SENDER_RE.match(content))

        if has_sender_prefix:
            if talker not in group_talkers:
                group_talkers[talker] = {
                    "members": set(),
                    "msg_count": 0,
                    "last_time": 0,
                }
            group_talkers[talker]["msg_count"] += 1
            group_talkers[talker]["last_time"] = max(
                group_talkers[talker]["last_time"], ts or 0
            )
            # Extract sender wxid
            for m in SENDER_RE.finditer(content):
                wxid = m.group(1)
                group_talkers[talker]["members"].add(wxid)
        else:
            if talker not in private_talkers:
                private_talkers[talker] = {"msg_count": 0, "last_time": 0}
            private_talkers[talker]["msg_count"] += 1
            private_talkers[talker]["last_time"] = max(
                private_talkers[talker]["last_time"], ts or 0
            )
            # Try to extract wxid from content for private chat identification
            # Some private chats embed wxid in forwarded messages etc.
            wxids_found = SENDER_RE.findall(content)
            if wxids_found and talker not in talker_wxid_map:
                talker_wxid_map[talker] = wxids_found[0]

    return {
        "group_talkers": group_talkers,
        "private_talkers": private_talkers,
        "talker_wxid_map": talker_wxid_map,
    }


# ===========================================================================
# Analysis 1: Group co-occurrence
# ===========================================================================


def analyze_group_cooccurrence():
    """
    分析群内共现：同群出现的两个人有关系。
    从消息内容中提取群成员列表。
    计算共同群数 → 写入 relations(type='group_cooccurrence')
    同时填充 groups 和 group_members 表。
    """
    if not MERGED_DB.exists():
        print(f"[SKIP] messages.db not found: {MERGED_DB}", file=sys.stderr)
        return 0

    with sqlite3.connect(str(MERGED_DB)) as msg_conn:
        info = _classify_talkers(msg_conn)
    group_talkers = info["group_talkers"]

    if not group_talkers:
        print("[SKIP] No group talkers found")
        return 0

    # Build co-occurrence: (wxid_a, wxid_b) → {shared_groups, count}
    pair_groups = defaultdict(lambda: {"groups": set(), "count": 0})

    # Also build group member data for DB insertion
    group_data = {}  # room_id → {members, msg_count, last_time}
    member_msg_counts = defaultdict(lambda: defaultdict(int))  # room_id → wxid → count
    member_last_msg = defaultdict(dict)  # room_id → wxid → ts

    for talker_hash, ginfo in group_talkers.items():
        members = ginfo["members"]
        room_id = f"group_{talker_hash}"  # Use hash as room_id since no real room_id available
        group_data[room_id] = {
            "member_count": len(members),
            "members": members,
            "msg_count": ginfo["msg_count"],
            "last_time": ginfo["last_time"],
        }

        # Track per-member stats from messages
        with sqlite3.connect(str(MERGED_DB)) as msg_conn:
            cur = msg_conn.cursor()
            cur.execute(
                "SELECT message_content, create_time FROM messages WHERE talker = ? ORDER BY create_time",
                (talker_hash,),
            )
            for content, ts in cur.fetchall():
                if not content:
                    continue
                m = SENDER_RE.match(content)
                if m:
                    wxid = m.group(1)
                    member_msg_counts[room_id][wxid] += 1
                    if (
                        wxid not in member_last_msg[room_id]
                        or ts > member_last_msg[room_id][wxid]
                    ):
                        member_last_msg[room_id][wxid] = ts

        # Co-occurrence pairs
        if len(members) >= 2:
            for a, b in combinations(sorted(members), 2):
                pair_groups[(a, b)]["groups"].add(room_id)
                pair_groups[(a, b)]["count"] += 1

    # Write to CRM DB
    with sqlite3.connect(str(CRM_DB)) as conn:
        cur = conn.cursor()

        # Write groups table
        for room_id, gd in group_data.items():
            members_list = sorted(gd["members"])
            cur.execute(
                """
                INSERT OR REPLACE INTO groups (room_id, member_count, members_json, message_count, last_active)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    room_id,
                    gd["member_count"],
                    json.dumps(members_list, ensure_ascii=False),
                    gd["msg_count"],
                    _ts_to_iso(gd["last_time"]),
                ),
            )

        # Write group_members table
        for room_id, gd in group_data.items():
            for wxid in gd["members"]:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO group_members (room_id, wxid, message_count, last_message)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        room_id,
                        wxid,
                        member_msg_counts[room_id].get(wxid, 0),
                        _ts_to_iso(member_last_msg[room_id].get(wxid)),
                    ),
                )

        # Write relations (group_cooccurrence)
        upserted = 0
        for (a, b), pg in pair_groups.items():
            groups_list = sorted(pg["groups"])
            cur.execute(
                """
                INSERT INTO relations (wxid_a, wxid_b, relation_type, co_group_count, interaction_count, metadata)
                VALUES (?, ?, 'group_cooccurrence', ?, ?, ?)
                ON CONFLICT(wxid_a, wxid_b, relation_type) DO UPDATE SET
                    co_group_count = excluded.co_group_count,
                    interaction_count = excluded.interaction_count,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (
                    a,
                    b,
                    len(pg["groups"]),
                    pg["count"],
                    json.dumps({"groups": groups_list}, ensure_ascii=False),
                ),
            )
            upserted += 1

        conn.commit()

    print(f"[OK] 群共现分析: {len(group_data)} 个群, {upserted} 对关系")
    return upserted


# ===========================================================================
# Analysis 2: @ interactions
# ===========================================================================


def analyze_at_interactions():
    """
    分析@互动：从消息内容中提取 @xxx 模式。
    对于群消息: 发送者@了某人 → 发送者与被@人有互动关系。
    写入 relations(type='at_interaction')
    """
    if not MERGED_DB.exists():
        print(f"[SKIP] messages.db not found: {MERGED_DB}", file=sys.stderr)
        return 0

    # Build (sender, target) → {count, last_ts}
    at_pairs = defaultdict(lambda: {"count": 0, "last_ts": 0})

    with sqlite3.connect(str(MERGED_DB)) as msg_conn:
        cur = msg_conn.cursor()
        cur.execute(
            "SELECT talker, message_content, create_time FROM messages WHERE message_content IS NOT NULL"
        )

        for talker, content, ts in cur.fetchall():
            if not content:
                continue
            m = SENDER_RE.match(content)
            if not m:
                continue  # Skip private chats (no sender prefix)
            sender = m.group(1)
            body = content[m.end() :]  # Content after sender prefix

            # Find @mentions in body
            mentions = AT_MENTION_RE.findall(body)
            for target in mentions:
                # Skip self-mentions and non-wxid mentions
                if target == sender:
                    continue
                if target.startswith("wxid_") or re.match(r"^[a-z]\d{7,12}$", target):
                    key = tuple(sorted([sender, target]))
                    at_pairs[key]["count"] += 1
                    at_pairs[key]["last_ts"] = max(at_pairs[key]["last_ts"], ts or 0)

    if not at_pairs:
        print("[SKIP] No @interactions found")
        return 0

    # Write to CRM DB
    with sqlite3.connect(str(CRM_DB)) as conn:
        cur = conn.cursor()
        upserted = 0
        for (a, b), info in at_pairs.items():
            cur.execute(
                """
                INSERT INTO relations (wxid_a, wxid_b, relation_type, interaction_count, last_interaction, metadata)
                VALUES (?, ?, 'at_interaction', ?, ?, ?)
                ON CONFLICT(wxid_a, wxid_b, relation_type) DO UPDATE SET
                    interaction_count = excluded.interaction_count,
                    last_interaction = excluded.last_interaction,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (
                    a,
                    b,
                    info["count"],
                    _ts_to_iso(info["last_ts"]),
                    json.dumps({"at_count": info["count"]}, ensure_ascii=False),
                ),
            )
            upserted += 1
        conn.commit()

    print(f"[OK] @互动分析: {upserted} 对关系")
    return upserted


# ===========================================================================
# Analysis 3: Private chat frequency
# ===========================================================================


def analyze_private_chat_frequency():
    """
    分析私聊频率：talker 不是群聊的消息记录。
    私聊talker没有 wxid_ 前缀的发送者信息，用 talker hash 作为标识符。
    如果能从 table-map 推断wxid则使用，否则用 hash_talker_xxx 作为虚拟ID。
    写入 relations(type='mutual_chat')
    """
    if not MERGED_DB.exists():
        print(f"[SKIP] messages.db not found: {MERGED_DB}", file=sys.stderr)
        return 0

    # Get "me" identity from CRM contacts
    my_wxid = None
    with sqlite3.connect(str(CRM_DB)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT wxid FROM contacts LIMIT 1")
        row = cur.fetchone()
        if row:
            my_wxid = row[0]

    with sqlite3.connect(str(MERGED_DB)) as msg_conn:
        info = _classify_talkers(msg_conn)
    private_talkers = info["private_talkers"]
    wxid_map = info["talker_wxid_map"]

    if not private_talkers:
        print("[SKIP] No private talkers found")
        return 0

    # Build contact ID for each private talker
    contact_pairs = {}  # (my_wxid, contact_id) → {count, last_ts}
    for talker_hash, pinfo in private_talkers.items():
        contact_id = wxid_map.get(talker_hash)
        if not contact_id:
            contact_id = f"hash_{talker_hash}"

        if my_wxid and contact_id != my_wxid:
            key = tuple(sorted([my_wxid, contact_id]))
            contact_pairs[key] = {
                "count": pinfo["msg_count"],
                "last_ts": pinfo["last_time"],
            }

    if not contact_pairs:
        print("[SKIP] No private chat pairs to record")
        return 0

    # Write to CRM DB
    with sqlite3.connect(str(CRM_DB)) as conn:
        cur = conn.cursor()
        upserted = 0
        for (a, b), pinfo in contact_pairs.items():
            cur.execute(
                """
                INSERT INTO relations (wxid_a, wxid_b, relation_type, interaction_count, last_interaction, metadata)
                VALUES (?, ?, 'mutual_chat', ?, ?, ?)
                ON CONFLICT(wxid_a, wxid_b, relation_type) DO UPDATE SET
                    interaction_count = excluded.interaction_count,
                    last_interaction = excluded.last_interaction,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (
                    a,
                    b,
                    pinfo["count"],
                    _ts_to_iso(pinfo["last_ts"]),
                    json.dumps({"chat_count": pinfo["count"]}, ensure_ascii=False),
                ),
            )
            upserted += 1
        conn.commit()

    print(f"[OK] 私聊频率分析: {upserted} 对关系")
    return upserted


# ===========================================================================
# Strength computation
# ===========================================================================


def compute_strength():
    """
    综合计算关系强度 (0.0-1.0):
    strength = 0.3 * co_group_normalized + 0.3 * at_count_normalized + 0.4 * chat_freq_normalized

    每个维度用 min-max 归一化到 0-1（处理 max=0 的情况）。
    更新 relations.strength 字段。
    """
    with sqlite3.connect(str(CRM_DB)) as conn:
        cur = conn.cursor()

        # Fetch all relation pairs with their metrics
        # For each (wxid_a, wxid_b) pair, aggregate across relation_types
        cur.execute("""
            SELECT wxid_a, wxid_b,
                   MAX(CASE WHEN relation_type = 'group_cooccurrence' THEN co_group_count ELSE 0 END) as co_groups,
                   MAX(CASE WHEN relation_type = 'at_interaction' THEN interaction_count ELSE 0 END) as at_count,
                   MAX(CASE WHEN relation_type = 'mutual_chat' THEN interaction_count ELSE 0 END) as chat_count
            FROM relations
            GROUP BY wxid_a, wxid_b
        """)
        pairs = cur.fetchall()

        if not pairs:
            print("[SKIP] No relations to compute strength")
            return 0

        # Extract dimensions for normalization
        co_groups = [r[2] for r in pairs]
        at_counts = [r[3] for r in pairs]
        chat_counts = [r[4] for r in pairs]

        max_cg = max(co_groups) if co_groups else 1
        max_at = max(at_counts) if at_counts else 1
        max_ch = max(chat_counts) if chat_counts else 1
        # Prevent division by zero
        max_cg = max_cg or 1
        max_at = max_at or 1
        max_ch = max_ch or 1

        updated = 0
        for wxid_a, wxid_b, cg, at_cnt, ch_cnt in pairs:
            cg_norm = cg / max_cg if max_cg > 0 else 0.0
            at_norm = at_cnt / max_at if max_at > 0 else 0.0
            ch_norm = ch_cnt / max_ch if max_ch > 0 else 0.0
            strength = 0.3 * cg_norm + 0.3 * at_norm + 0.4 * ch_norm

            cur.execute(
                """
                UPDATE relations SET strength = ?, updated_at = CURRENT_TIMESTAMP
                WHERE wxid_a = ? AND wxid_b = ?
            """,
                (round(strength, 4), wxid_a, wxid_b),
            )
            updated += cur.rowcount

        conn.commit()

    print(
        f"[OK] 关系强度计算: {updated} 对更新 (max_cg={max_cg}, max_at={max_at}, max_ch={max_ch})"
    )
    return updated


# ===========================================================================
# Query: Social graph export
# ===========================================================================


def get_social_graph(wxid: str = None, min_strength: float = 0.1) -> dict:
    """
    导出社交图谱数据（给前端用）:
    {
        "nodes": [{"id": "wxid", "name": "昵称", "group_count": 3, "chat_count": 50}],
        "edges": [{"source": "a", "target": "b", "strength": 0.8, "types": [...]}]
    }
    如果指定 wxid，只返回该用户的 2 跳邻居。
    """
    with sqlite3.connect(str(CRM_DB)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Build nodes from contacts + relations
        cur.execute("""
            SELECT wxid, nickname, remark FROM contacts
        """)
        contacts_map = {}
        for row in cur.fetchall():
            contacts_map[row["wxid"]] = row["remark"] or row["nickname"] or row["wxid"]

        # Build edges from relations (aggregated per pair)
        cur.execute("""
            SELECT wxid_a, wxid_b,
                   ROUND(AVG(strength), 4) as avg_strength,
                   GROUP_CONCAT(relation_type) as types,
                   MAX(co_group_count) as co_groups,
                   MAX(interaction_count) as interactions
            FROM relations
            GROUP BY wxid_a, wxid_b
        """)

        all_wxids = set()
        edges = []
        for row in cur.fetchall():
            strength = row["avg_strength"]
            if strength < min_strength:
                continue
            edges.append(
                {
                    "source": row["wxid_a"],
                    "target": row["wxid_b"],
                    "strength": strength,
                    "types": row["types"].split(",") if row["types"] else [],
                    "co_groups": row["co_groups"],
                    "interactions": row["interactions"],
                }
            )
            all_wxids.add(row["wxid_a"])
            all_wxids.add(row["wxid_b"])

        # If wxid specified, filter to 2-hop neighbors
        if wxid:
            hop1 = set()
            hop2 = set()
            for e in edges:
                if e["source"] == wxid:
                    hop1.add(e["target"])
                elif e["target"] == wxid:
                    hop1.add(e["source"])
            for e in edges:
                if e["source"] in hop1:
                    hop2.add(e["target"])
                elif e["target"] in hop1:
                    hop2.add(e["source"])
            valid = {wxid} | hop1 | hop2
            edges = [e for e in edges if e["source"] in valid and e["target"] in valid]
            all_wxids = valid

        # Build nodes with stats
        nodes = []
        for w in all_wxids:
            name = contacts_map.get(w, w)
            # Count groups for this wxid
            cur.execute("SELECT COUNT(*) FROM group_members WHERE wxid = ?", (w,))
            group_count = cur.fetchone()[0]
            cur.execute(
                """
                SELECT SUM(interaction_count) FROM relations
                WHERE (wxid_a = ? OR wxid_b = ?)
            """,
                (w, w),
            )
            chat_count = cur.fetchone()[0] or 0
            nodes.append(
                {
                    "id": w,
                    "name": name,
                    "group_count": group_count,
                    "chat_count": chat_count,
                }
            )

    return {"nodes": nodes, "edges": edges}


# ===========================================================================
# Query: Contact profile
# ===========================================================================


def get_contact_profile(wxid: str) -> dict:
    """
    联系人社交画像:
    {
        "wxid": "...", "name": "...", "tags": [...],
        "groups": [{"id": "...", "name": "...", "role": "member"}],
        "relations": [{"wxid": "...", "name": "...", "strength": 0.8, "type": "..."}],
        "stats": {"total_chats": 50, "groups_count": 3, "strong_relations": 5, "weak_relations": 20}
    }
    """
    with sqlite3.connect(str(CRM_DB)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Basic contact info
        cur.execute("SELECT * FROM contacts WHERE wxid = ?", (wxid,))
        contact = cur.fetchone()
        if not contact:
            return {"error": f"Contact {wxid} not found"}

        tags = json.loads(contact["tags"]) if contact["tags"] else []
        name = contact["remark"] or contact["nickname"] or wxid

        # Groups
        cur.execute(
            """
            SELECT gm.room_id, gm.role, gm.message_count, gm.last_message, g.member_count
            FROM group_members gm
            LEFT JOIN groups g ON gm.room_id = g.room_id
            WHERE gm.wxid = ?
        """,
            (wxid,),
        )
        groups = []
        for row in cur.fetchall():
            groups.append(
                {
                    "id": row["room_id"],
                    "name": row["room_id"],  # No real name available from merged DB
                    "role": row["role"],
                    "message_count": row["message_count"],
                    "last_message": row["last_message"],
                    "total_members": row["member_count"],
                }
            )

        # Relations
        cur.execute(
            """
            SELECT
                CASE WHEN wxid_a = ? THEN wxid_b ELSE wxid_a END as other_wxid,
                relation_type, strength, interaction_count, last_interaction
            FROM relations
            WHERE wxid_a = ? OR wxid_b = ?
            ORDER BY strength DESC
        """,
            (wxid, wxid, wxid),
        )

        relations = []
        strong_count = 0
        weak_count = 0
        total_chats = 0
        for row in cur.fetchall():
            other = row["other_wxid"]
            # Get other's name
            cur2 = conn.cursor()
            cur2.execute(
                "SELECT nickname, remark FROM contacts WHERE wxid = ?", (other,)
            )
            oc = cur2.fetchone()
            other_name = (oc["remark"] or oc["nickname"] or other) if oc else other
            relations.append(
                {
                    "wxid": other,
                    "name": other_name,
                    "strength": row["strength"],
                    "type": row["relation_type"],
                    "interactions": row["interaction_count"],
                    "last_interaction": row["last_interaction"],
                }
            )
            total_chats += row["interaction_count"] or 0
            if row["strength"] >= 0.5:
                strong_count += 1
            else:
                weak_count += 1

        stats = {
            "total_chats": total_chats,
            "groups_count": len(groups),
            "strong_relations": strong_count,
            "weak_relations": weak_count,
        }

    return {
        "wxid": wxid,
        "name": name,
        "tags": tags,
        "groups": groups,
        "relations": relations,
        "stats": stats,
    }


# ===========================================================================
# Main
# ===========================================================================


def run_full_analysis():
    """运行全量分析流程"""
    ensure_schema()
    analyze_group_cooccurrence()
    analyze_at_interactions()
    analyze_private_chat_frequency()
    compute_strength()
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "graph":
            wxid = sys.argv[2] if len(sys.argv) > 2 else None
            min_s = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
            result = get_social_graph(wxid=wxid, min_strength=min_s)
        elif cmd == "profile":
            if len(sys.argv) < 3:
                print("Usage: social_relations.py profile <wxid>", file=sys.stderr)
                sys.exit(1)
            result = get_contact_profile(sys.argv[2])
        elif cmd == "schema":
            ensure_schema()
            result = {"status": "ok", "message": "Schema ensured"}
        else:
            result = run_full_analysis()
    else:
        result = run_full_analysis()

    print(json.dumps(result, ensure_ascii=False, indent=2))
