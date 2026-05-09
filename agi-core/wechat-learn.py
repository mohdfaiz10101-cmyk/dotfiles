#!/usr/bin/env python3
"""微信聊天记录 → Letta 记忆学习管道。

从 UOS 加密 DB / Wine 明文 DB / TXT/CSV/HTML 备份文件读取微信文字消息，
去重后格式化写入 Letta archival memory。

用法:
    python3 wechat-learn.py --source db       # 从微信 DB 读取并导入
    python3 wechat-learn.py --source file     # 从备份文件导入
    python3 wechat-learn.py --source all      # 两者都做
    python3 wechat-learn.py --dry-run         # 只显示统计，不写入 Letta
    python3 wechat-learn.py --status          # 显示已导入统计
"""

import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── 常量 ────────────────────────────────────────────────────────────────────────

PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80

LETTA_API = "http://localhost:8283"
LETTA_AGENT_ID = "agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea"

BACKUP_DIR = Path("/mnt/ai/apps/wechat-backup")
IMPORTED_DIR = BACKUP_DIR / "imported"
HASHES_FILE = IMPORTED_DIR / "hashes.json"
STATS_FILE = IMPORTED_DIR / "stats.json"

UOS_KEYS_CACHE = Path.home() / ".cache/wechat-finance/keys.json"
UOS_DB_BASE = Path.home() / "文档/xwechat_files"
WINE_DB_BASE = Path("/mnt/data/WeChat Files")

BATCH_SIZE = 50

INTENT_KEYWORDS = {
    "询价": ["多少钱", "价格", "报价", "费用", "怎么收费", "优惠", "多少钱一个"],
    "技术支持": ["怎么用", "报错", "打不开", "不能用", "bug", "问题", "安装", "配置"],
    "售后": ["退款", "退货", "换货", "售后", "不满意", "维修"],
    "物流": ["发货", "快递", "到了吗", "物流", "运费", "到货"],
    "闲聊": [],
}

TZ_OFFSET = time.timezone  # seconds west of UTC, China: negative
LOCAL_TZ = timezone(-timedelta(seconds=TZ_OFFSET))


# ─── 解密（从 wechat_agent.py 复制） ────────────────────────────────────────────


def _derive_key(enc_key: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha512", enc_key, salt, 64000, dklen=KEY_SZ)


def decrypt_uos_db(enc_path: Path, enc_key_hex: str) -> Path | None:
    try:
        enc_key = bytes.fromhex(enc_key_hex)
    except ValueError:
        return None

    try:
        data = enc_path.read_bytes()
    except OSError:
        return None

    if len(data) < PAGE_SZ:
        return None

    try:
        from Crypto.Cipher import AES
    except ImportError:
        print("[FAIL] 缺少 pycryptodome，无法解密 UOS DB", file=sys.stderr)
        return None

    salt = data[:SALT_SZ]
    key = _derive_key(enc_key, salt)

    pages: list[bytes] = []
    for page_no in range(len(data) // PAGE_SZ):
        offset = page_no * PAGE_SZ
        page = data[offset : offset + PAGE_SZ]
        if page_no == 0:
            iv = page[SALT_SZ : SALT_SZ + IV_SZ]
            payload = page[SALT_SZ + IV_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
        else:
            iv = page[:IV_SZ]
            payload = page[IV_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plain = cipher.decrypt(payload)
        if page_no == 0:
            pages.append(b"SQLite format 3\x00" + plain[16:])
        else:
            pages.append(plain)

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.write(b"".join(pages))
    tmp.close()
    return Path(tmp.name)


# ─── 消息读取 ────────────────────────────────────────────────────────────────────


def find_uos_message_dbs() -> list[tuple[Path, str]]:
    if not UOS_KEYS_CACHE.exists():
        return []
    try:
        keys: dict = json.loads(UOS_KEYS_CACHE.read_text())
    except Exception:
        return []

    result: list[tuple[Path, str]] = []
    if not UOS_DB_BASE.exists():
        return result
    for wxid_dir in UOS_DB_BASE.iterdir():
        if not wxid_dir.is_dir():
            continue
        msg_dir = wxid_dir / "db_storage" / "message"
        if not msg_dir.exists():
            continue
        for db_file in sorted(msg_dir.glob("message_*.db")):
            rel = f"message/{db_file.name}"
            if rel in keys:
                val = keys[rel]
                key_str = val["enc_key"] if isinstance(val, dict) else val
                result.append((db_file, key_str))
    return result


def _query_messages(db_path: Path, include_sent: bool = True) -> list[dict]:
    """查询 SQLite 消息，自适应列名，返回标准字典。"""
    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        conn.row_factory = sqlite3.Row

        cols = {row[1] for row in conn.execute("PRAGMA table_info(ChatMsg)").fetchall()}
        if not cols:
            conn.close()
            return []

        id_col = "localId" if "localId" in cols else "MsgLocalID"
        talker_col = "talker" if "talker" in cols else "StrTalker"
        content_col = "content" if "content" in cols else "StrContent"
        type_col = "type" if "type" in cols else "Type"
        time_col = "CreateTime"
        is_send_col = "isSend" if "isSend" in cols else "IsSender"

        send_filter = ""
        params: tuple = ()
        if not include_sent:
            send_filter = f" AND {is_send_col}=0"
        else:
            send_filter = f" AND {is_send_col} IN (0, 1)"

        rows = conn.execute(
            f"SELECT {id_col}, {type_col}, {time_col}, {talker_col}, {content_col}, {is_send_col}"
            f" FROM ChatMsg"
            f" WHERE {type_col}=1{send_filter}"
            f" ORDER BY {time_col} ASC",
            params,
        ).fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "type": row[1],
                "create_time": row[2],
                "talker": row[3] or "",
                "content": (row[4] or ""),
                "is_send": row[5],
            }
            for row in rows
            if row[4]  # skip empty content
        ]
    except sqlite3.Error:
        return []


def read_uos_messages() -> list[dict]:
    """从 UOS 加密 DB 读取消息。"""
    msgs: list[dict] = []
    pairs = find_uos_message_dbs()
    for enc_path, key_hex in pairs:
        tmp_path = decrypt_uos_db(enc_path, key_hex)
        if tmp_path is None:
            continue
        try:
            batch = _query_messages(tmp_path)
            for m in batch:
                m["source"] = "uos"
            msgs.extend(batch)
        finally:
            tmp_path.unlink(missing_ok=True)
    return msgs


def read_wine_messages() -> list[dict]:
    """从 Wine 明文 DB 读取消息。"""
    msgs: list[dict] = []
    if not WINE_DB_BASE.exists():
        return msgs
    for wxid_dir in WINE_DB_BASE.iterdir():
        if not wxid_dir.is_dir():
            continue
        db_path = wxid_dir / "Msg" / "ChatMsg.db"
        if not db_path.exists():
            continue
        batch = _query_messages(db_path)
        for m in batch:
            m["source"] = "wine"
        msgs.extend(batch)
    return msgs


# ─── 文件导入 ────────────────────────────────────────────────────────────────────


def _classify_intent(text: str) -> str:
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return intent
    return "其他"


def _import_txt(path: Path) -> list[dict]:
    """TXT 导入：支持两种格式。

    格式1（微信导出多行）：
        2024-01-15 10:30:00 张三
        你好，明天下午有空吗？

        2024-01-15 10:31:00 我
        有空的，什么事？

    格式2（单行带时间戳）：
        [2024-01-15 10:30:00] 你好
    """
    msgs: list[dict] = []
    text = path.read_text(encoding="utf-8", errors="ignore")

    # Pattern 1: 微信导出格式 — "YYYY-MM-DD HH:MM:SS 发送者" 后跟内容行
    wechat_header = re.compile(
        r"^(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$"
    )
    # Pattern 2: 单行 [时间] 内容
    bracket_pattern = re.compile(
        r"\[(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)"
    )

    now = int(time.time())
    lines = text.splitlines()

    # First pass: detect if wechat multi-line format by checking header ratio
    header_count = sum(1 for l in lines if wechat_header.match(l.strip()))
    use_wechat_format = header_count >= 2 and header_count / max(len(lines), 1) < 0.5

    if use_wechat_format:
        # Parse wechat multi-line format: header line → content line(s) → blank separator
        current_ts = 0
        current_talker = ""
        content_lines: list[str] = []
        msg_idx = 0

        for line in lines:
            stripped = line.strip()
            m = wechat_header.match(stripped)
            if m:
                # Flush previous message
                if content_lines and current_talker:
                    content = "\n".join(content_lines).strip()
                    if content:
                        is_send = 1 if current_talker in ("我", "自己", "self") else 0
                        msgs.append(
                            {
                                "id": msg_idx,
                                "type": 1,
                                "create_time": current_ts,
                                "talker": current_talker,
                                "content": content,
                                "is_send": is_send,
                                "source": f"txt:{path.name}",
                            }
                        )
                        msg_idx += 1
                # Start new message
                try:
                    ts_str = m.group(1).replace("/", "-")
                    dt = datetime.strptime(
                        ts_str,
                        "%Y-%m-%d %H:%M" if len(ts_str) < 17 else "%Y-%m-%d %H:%M:%S",
                    )
                    current_ts = int(dt.replace(tzinfo=LOCAL_TZ).timestamp())
                except ValueError:
                    current_ts = now - msg_idx
                current_talker = m.group(2).strip()
                content_lines = []
            elif stripped:
                # Content line (may span multiple lines before blank separator)
                content_lines.append(stripped)

        # Flush last message
        if content_lines and current_talker:
            content = "\n".join(content_lines).strip()
            if content:
                is_send = 1 if current_talker in ("我", "自己", "self") else 0
                msgs.append(
                    {
                        "id": msg_idx,
                        "type": 1,
                        "create_time": current_ts,
                        "talker": current_talker,
                        "content": content,
                        "is_send": is_send,
                        "source": f"txt:{path.name}",
                    }
                )
    else:
        # Fallback: single-line [time] content format
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            m = bracket_pattern.match(line)
            if m:
                try:
                    ts_str = m.group(1).replace("/", "-")
                    dt = datetime.strptime(
                        ts_str,
                        "%Y-%m-%d %H:%M" if len(ts_str) < 17 else "%Y-%m-%d %H:%M:%S",
                    )
                    ts = int(dt.replace(tzinfo=LOCAL_TZ).timestamp())
                except ValueError:
                    ts = now - i
                content = m.group(2)
            else:
                ts = now - i
                content = line

            msgs.append(
                {
                    "id": i,
                    "type": 1,
                    "create_time": ts,
                    "is_send": 1,
                    "talker": f"file:{path.stem}",
                    "content": content,
                    "source": f"txt:{path.name}",
                }
            )
    return msgs


def _import_csv(path: Path) -> list[dict]:
    """CSV 导入：自动检测分隔符，要求有 content 列。"""
    msgs: list[dict] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(text[:4096])
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return msgs

    content_col = None
    for c in reader.fieldnames:
        if c.strip().lower() in ("content", "内容", "消息", "message", "text"):
            content_col = c
            break
    if content_col is None:
        print(
            f"[WARN] CSV {path.name} 未找到 content 列 (可用列: {reader.fieldnames})",
            file=sys.stderr,
        )
        return msgs

    now = int(time.time())
    for i, row in enumerate(reader):
        content = (row.get(content_col) or "").strip()
        if not content:
            continue
        talker = (
            row.get("talker")
            or row.get("from")
            or row.get("sender")
            or f"file:{path.stem}"
        )
        msgs.append(
            {
                "id": i,
                "type": 1,
                "create_time": now,
                "talker": talker,
                "content": content,
                "is_send": 1,
                "source": f"csv:{path.name}",
            }
        )
    return msgs


def _import_html(path: Path) -> list[dict]:
    """HTML 导入：解析微信导出的聊天记录 HTML。"""
    msgs: list[dict] = []
    text = path.read_text(encoding="utf-8", errors="ignore")

    # 微信导出格式: <div class="content">... 时间 ... 消息内容 ...</div>
    # 或更简单的: 尝试提取所有文本块
    # 通用策略: 提取 <p> 或 <div> 中的文本内容
    clean = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    now = int(time.time())
    lines = [l.strip() for l in clean.splitlines() if l.strip()]

    # 尝试按时间行分割
    time_pattern = re.compile(
        r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}\s*(?:日\s*)?(?:\d{1,2}:\d{2}(?::\d{2})?)?"
    )
    current_ts = now
    for i, line in enumerate(lines):
        if time_pattern.match(line):
            try:
                ts_str = (
                    line.replace("年", "-")
                    .replace("月", "-")
                    .replace("日", "")
                    .replace("/", "-")
                    .strip()
                )
                dt = datetime.strptime(
                    ts_str,
                    "%Y-%m-%d %H:%M" if len(ts_str) < 17 else "%Y-%m-%d %H:%M:%S",
                )
                current_ts = int(dt.replace(tzinfo=LOCAL_TZ).timestamp())
                continue  # 时间行本身不是消息
            except ValueError:
                pass
        msgs.append(
            {
                "id": i,
                "type": 1,
                "create_time": current_ts,
                "talker": f"file:{path.stem}",
                "content": line,
                "is_send": 1,
                "source": f"html:{path.name}",
            }
        )
    return msgs


def read_file_messages() -> list[dict]:
    """从备份目录读取所有导入文件。"""
    file_dir = BACKUP_DIR  # 根目录下的备份文件
    msgs: list[dict] = []
    if not file_dir.exists():
        return msgs

    for f in sorted(file_dir.iterdir()):
        if f.is_dir() or f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        if ext == ".txt":
            msgs.extend(_import_txt(f))
        elif ext == ".csv":
            msgs.extend(_import_csv(f))
        elif ext == ".html" or ext == ".htm":
            msgs.extend(_import_html(f))
    return msgs


# ─── 去重 + 格式化 ───────────────────────────────────────────────────────────────


def _load_hashes() -> set[str]:
    if HASHES_FILE.exists():
        try:
            return set(json.loads(HASHES_FILE.read_text()))
        except Exception:
            return set()
    return set()


def _save_hashes(hashes: set[str]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    HASHES_FILE.write_text(json.dumps(sorted(hashes), ensure_ascii=False, indent=2))


def _msg_hash(msg: dict) -> str:
    """消息去重 hash：基于 talker + content（不用时间戳，避免每次运行不同）。"""
    raw = f"{msg['talker']}|{msg['content']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _format_timestamp(ts: int) -> str:
    try:
        dt = datetime.fromtimestamp(ts, tz=LOCAL_TZ)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return "1970-01-01 00:00"


def _format_message(msg: dict) -> str:
    direction = "发出" if msg.get("is_send") else "收到"
    ts = _format_timestamp(msg["create_time"])
    content = msg["content"]
    # 截断过长消息
    if len(content) > 2000:
        content = content[:2000] + "...(已截断)"
    intent = _classify_intent(content)
    return (
        f"[微信消息] {ts} {msg['talker']} ({direction})\n"
        f"内容：{content}\n"
        f"标签：{intent}"
    )


# ─── Letta 写入 ─────────────────────────────────────────────────────────────────


def _letta_write(archival_texts: list[str]) -> bool:
    """逐条写入 Letta archival memory（API 只支持单条写入）。"""
    if not archival_texts:
        return True
    url = f"{LETTA_API}/v1/agents/{LETTA_AGENT_ID}/archival-memory"
    success = 0
    for text in archival_texts:
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                if isinstance(result, list) and result:
                    success += 1
        except urllib.error.URLError as e:
            print(f"[FAIL] Letta API 错误: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[FAIL] Letta 写入失败: {e}", file=sys.stderr)
    return success == len(archival_texts)


# ─── 状态追踪 ────────────────────────────────────────────────────────────────────


def _load_stats() -> dict:
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except Exception:
            pass
    return {"total_imported": 0, "by_wxid": {}, "last_import": None, "by_source": {}}


def _save_stats(stats: dict) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2))


# ─── 核心流程 ────────────────────────────────────────────────────────────────────


def process_messages(msgs: list[dict], dry_run: bool = False) -> tuple[int, int]:
    """处理消息列表，返回 (新增数, 跳过数)。"""
    if not msgs:
        print("[INFO] 无消息可处理")
        return 0, 0

    hashes = _load_hashes()
    new_msgs = []
    skipped = 0
    for msg in msgs:
        h = _msg_hash(msg)
        if h in hashes:
            skipped += 1
            continue
        new_msgs.append(msg)
        hashes.add(h)

    if not new_msgs:
        print(f"[INFO] 全部 {len(msgs)} 条已导入过，无新增")
        return 0, skipped

    print(f"[INFO] 去重结果: {len(new_msgs)} 新增 / {skipped} 跳过 / {len(msgs)} 总计")

    if dry_run:
        print(f"\n[DRY-RUN] 将导入 {len(new_msgs)} 条消息（不实际写入）:")
        # 按来源分组统计
        by_source: dict[str, int] = {}
        for m in new_msgs:
            src = m.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
        for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
            print(f"  {src}: {count} 条")
        # 显示前 5 条样例
        print("\n[DRY-RUN] 前 5 条样例:")
        for m in new_msgs[:5]:
            print(f"  {_format_message(m)}")
            print()
        return len(new_msgs), skipped

    # 按 talker 分组，每批 BATCH_SIZE 条写入 Letta
    grouped: dict[str, list[dict]] = {}
    for m in new_msgs:
        talker = m["talker"]
        grouped.setdefault(talker, []).append(m)

    total_written = 0
    total_batches = sum(
        (len(v) + BATCH_SIZE - 1) // BATCH_SIZE for v in grouped.values()
    )
    batch_idx = 0
    for talker, batch_msgs in sorted(grouped.items()):
        for i in range(0, len(batch_msgs), BATCH_SIZE):
            chunk = batch_msgs[i : i + BATCH_SIZE]
            texts = [_format_message(m) for m in chunk]
            batch_idx += 1
            print(
                f"  写入批次 {batch_idx}/{total_batches} — {talker} ({len(chunk)} 条) ...",
                end=" ",
            )
            if _letta_write(texts):
                total_written += len(chunk)
                print(f"[OK]")
            else:
                print(f"[FAIL]")

    # 保存去重 hash
    _save_hashes(hashes)

    # 更新统计
    stats = _load_stats()
    stats["total_imported"] += total_written
    stats["last_import"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for m in new_msgs:
        wxid = m["talker"]
        stats["by_wxid"][wxid] = stats["by_wxid"].get(wxid, 0) + 1
        src = m.get("source", "unknown")
        stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
    _save_stats(stats)

    print(f"\n[OK] 本次导入 {total_written} 条，累计 {stats['total_imported']} 条")
    return total_written, skipped


def show_status() -> None:
    stats = _load_stats()
    hashes = _load_hashes()
    print(f"━━━ 微信学习管道 状态 ━━━")
    print(f"  已导入消息总数: {stats['total_imported']}")
    print(f"  已处理 hash 数: {len(hashes)}")
    print(f"  最后导入时间:   {stats.get('last_import') or '从未'}")

    if stats.get("by_wxid"):
        print(f"\n  按联系人 (Top 10):")
        for wxid, count in sorted(stats["by_wxid"].items(), key=lambda x: -x[1])[:10]:
            print(f"    {wxid}: {count} 条")

    if stats.get("by_source"):
        print(f"\n  按来源:")
        for src, count in sorted(stats["by_source"].items(), key=lambda x: -x[1]):
            print(f"    {src}: {count} 条")

    # 数据源可用性检查
    print(f"\n━━━ 数据源检查 ━━━")
    uos_pairs = find_uos_message_dbs()
    print(f"  UOS 加密 DB: {len(uos_pairs)} 个")
    for p, _ in uos_pairs:
        print(f"    {p}")

    wine_count = 0
    if WINE_DB_BASE.exists():
        for d in WINE_DB_BASE.iterdir():
            db = d / "Msg" / "ChatMsg.db"
            if db.exists():
                wine_count += 1
                print(f"  Wine 明文 DB: {db}")
    if wine_count == 0:
        print(f"  Wine 明文 DB: 无")


# ─── CLI ─────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="微信聊天记录 → Letta 记忆学习管道",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --source db       从微信 DB 读取并导入
  %(prog)s --source file     从备份文件导入
  %(prog)s --source all      两者都做
  %(prog)s --dry-run --source db  试运行，只显示统计
  %(prog)s --status          查看已导入统计
        """,
    )
    parser.add_argument(
        "--source",
        choices=["db", "file", "all"],
        default="all",
        help="数据来源: db=微信数据库, file=备份文件, all=两者 (默认: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式：只显示统计，不实际写入 Letta",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示已导入统计",
    )
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    print(
        f"微信学习管道 v1.0 | 来源: {args.source} | 模式: {'试运行' if args.dry_run else '正式'}"
    )
    print()

    all_msgs: list[dict] = []

    if args.source in ("db", "all"):
        print("━━━ 读取 UOS 加密 DB ━━━")
        uos_msgs = read_uos_messages()
        print(f"  读取 {len(uos_msgs)} 条消息")
        all_msgs.extend(uos_msgs)

        print("\n━━━ 读取 Wine 明文 DB ━━━")
        wine_msgs = read_wine_messages()
        print(f"  读取 {len(wine_msgs)} 条消息")
        all_msgs.extend(wine_msgs)

    if args.source in ("file", "all"):
        print("\n━━━ 读取备份文件 ━━━")
        file_msgs = read_file_messages()
        print(f"  读取 {len(file_msgs)} 条消息")
        all_msgs.extend(file_msgs)

    print(f"\n━━━ 总计 {len(all_msgs)} 条消息待处理 ━━━")
    process_messages(all_msgs, dry_run=args.dry_run)

    if not args.dry_run and all_msgs:
        _trigger_social_flow()


def _trigger_social_flow() -> None:
    try:
        import subprocess, json
        from pathlib import Path

        flow_file = Path(__file__).parent / "flows" / "social_intelligence.py"
        if not flow_file.exists():
            return
        proc = subprocess.run(
            [sys.executable, str(flow_file)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        idx = Path(__file__).parent / "flows" / "index.json"
        if idx.exists():
            data = json.loads(idx.read_text())
            for f in data.get("flows", []):
                if f["name"] == "social_intelligence":
                    f["runs"] = f.get("runs", 0) + 1
                    break
            idx.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"[FLOW] social_intelligence 已触发 (exit={proc.returncode})")
    except Exception as e:
        print(f"[FLOW] social_intelligence 触发失败: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
