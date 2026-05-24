#!/usr/bin/env python3
"""
mem0_file_sync.py — memory/*.md 文件 → ChromaDB 增量同步
通过 mem0-bridge :8285 的 /add_raw 端点索引，跳过 LLM 提取。
ChromaDB ONNX embedding 自动向量化。

用法: python3 mem0_file_sync.py [--full] [--dry-run]
  --full    强制全量重新索引
  --dry-run 只显示将要索引的文件，不实际执行
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

MEMORY_DIR = Path(os.path.expanduser("~/.claude/projects/-home-charlie/memory"))
STATE_FILE = Path(os.path.expanduser("~/.local/state/mem0-file-sync.json"))
BRIDGE_URL = "http://127.0.0.1:8285"
CHUNK_SIZE = 800  # 每块字符数
CHUNK_OVERLAP = 100  # 重叠字符数
EXCLUDE_PATTERNS = [".backup", ".bak", ".gz", ".jsonl", ".json", ".toml", ".yaml"]

STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def file_hash(filepath: Path) -> str:
    """基于路径+mtime+size的快速哈希"""
    stat = filepath.stat()
    raw = f"{filepath}:{stat.st_mtime}:{stat.st_size}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def should_skip(filepath: Path) -> bool:
    name = filepath.name.lower()
    return any(p in name for p in EXCLUDE_PATTERNS)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """将文本分成重叠块"""
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def index_file(filepath: Path, dry_run: bool = False) -> dict:
    """索引单个文件的所有块"""
    rel_path = str(filepath.relative_to(MEMORY_DIR))
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"file": rel_path, "status": "error", "error": str(e)}

    chunks = chunk_text(content)
    if dry_run:
        return {"file": rel_path, "status": "dry_run", "chunks": len(chunks)}

    indexed = 0
    errors = 0
    for i, chunk in enumerate(chunks):
        meta = {
            "source": "file-sync",
            "file": rel_path,
            "chunk": i,
            "total_chunks": len(chunks),
        }
        payload = json.dumps({"text": chunk, "metadata": meta}).encode()
        req = Request(f"{BRIDGE_URL}/add_raw", data=payload,
                       headers={"Content-Type": "application/json"})
        try:
            urlopen(req, timeout=10)
            indexed += 1
        except URLError as e:
            errors += 1
            if errors <= 3:
                print(f"  [!] chunk {i} 失败: {e}", file=sys.stderr)

    return {"file": rel_path, "status": "indexed", "chunks": indexed, "errors": errors}


def main():
    full = "--full" in sys.argv
    dry_run = "--dry-run" in sys.argv

    state = {} if full else load_state()
    files = sorted(
        [f for f in MEMORY_DIR.rglob("*.md") if f.is_file() and not should_skip(f)]
    )

    to_index = []
    for fp in files:
        fhash = file_hash(fp)
        rel = str(fp.relative_to(MEMORY_DIR))
        if not full and state.get(rel) == fhash:
            continue
        to_index.append((fp, fhash))

    if not to_index:
        print(f"[mem0-file-sync] 全部 {len(files)} 个文件已同步，无需更新")
        return

    print(f"[mem0-file-sync] 待索引: {len(to_index)}/{len(files)} 个文件")
    if dry_run:
        for fp, _ in to_index:
            print(f"  - {fp.relative_to(MEMORY_DIR)}")
        return

    total_chunks = 0
    total_errors = 0
    for fp, fhash in to_index:
        rel = str(fp.relative_to(MEMORY_DIR))
        result = index_file(fp)
        total_chunks += result.get("chunks", 0)
        total_errors += result.get("errors", 0)
        state[rel] = fhash
        status = "ok" if result["status"] == "indexed" else result["status"]
        print(f"  [{status}] {rel} — {result.get('chunks', 0)} 块")

    save_state(state)
    print(f"[mem0-file-sync] 完成: {len(to_index)} 文件, {total_chunks} 块, {total_errors} 错误")


if __name__ == "__main__":
    main()