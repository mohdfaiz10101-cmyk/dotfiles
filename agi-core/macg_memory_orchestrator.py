#!/usr/bin/env python3
"""
macg_memory_orchestrator.py — 双层记忆编排器
Layer 1 (AI优先): ChromaDB 语义搜索 (mem0-bridge :8285)
Layer 2 (Fallback): Letta MCP 文件搜索 (letta-mcp :8284)
Layer 3 (兜底):    直接 grep memory/*.md

用法:
  python3 macg_memory_orchestrator.py search "关键词" [--limit 5]
  python3 macg_memory_orchestrator.py write "内容" --source "cc" --tags "tag1,tag2"
  python3 macg_memory_orchestrator.py sync    # 触发文件增量同步
  python3 macg_memory_orchestrator.py status  # 显示各层状态
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

MEMORY_DIR = Path(os.path.expanduser("~/.claude/projects/-home-charlie/memory"))
CHROMADB_URL = "http://127.0.0.1:8285"
LETTA_URL = "http://127.0.0.1:8284"
SYNC_SCRIPT = Path(os.path.expanduser("~/agi/mem0_file_sync.py"))


def chromadb_healthy():
    try:
        resp = urlopen(f"{CHROMADB_URL}/health", timeout=3)
        return json.loads(resp.read()).get("status") == "ok"
    except Exception:
        return False


def letta_healthy():
    try:
        resp = urlopen(f"{LETTA_URL}/health", timeout=3)
        return json.loads(resp.read()).get("status") == "healthy"
    except Exception:
        return False


def search_chromadb(query: str, limit: int = 5) -> list:
    """Layer 1: ChromaDB 语义搜索"""
    try:
        from urllib.parse import quote
        q = quote(query, safe="")
        url = f"{CHROMADB_URL}/search?q={q}&limit={limit}"
        resp = urlopen(url, timeout=10)
        data = json.loads(resp.read())
        results = []
        for r in data.get("results", []):
            results.append({
                "layer": "chromadb",
                "text": r.get("memory", ""),
                "metadata": r.get("metadata", {}),
                "score": round(1 - r.get("distance", 1), 3),  # distance→similarity
                "source": r.get("metadata", {}).get("file", "unknown"),
            })
        return results
    except Exception as e:
        return [{"layer": "chromadb", "error": str(e)[:80]}]


def search_letta(query: str, limit: int = 5) -> list:
    """Layer 2: Letta MCP 文件搜索"""
    try:
        resp = urlopen(f"{LETTA_URL}/recall?query={query}&limit={limit}", timeout=10)
        data = json.loads(resp.read())
        results = []
        for r in data.get("results", []):
            results.append({
                "layer": "letta",
                "text": r.get("content", r.get("text", "")),
                "metadata": r.get("metadata", {}),
                "source": r.get("source", "letta-memory.json"),
            })
        return results
    except Exception as e:
        return [{"layer": "letta", "error": str(e)[:80]}]


def search_files(query: str, limit: int = 5) -> list:
    """Layer 3: 直接 grep memory/*.md"""
    try:
        # rg is faster than grep for many files
        cmd = ["rg", "-l", "-i", query, str(MEMORY_DIR)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        files = result.stdout.strip().split("\n")[:limit]
        if not files or files == [""]:
            return [{"layer": "files", "results": 0, "message": "未找到匹配"}]

        matches = []
        for f in files[:limit]:
            fpath = Path(f)
            rel = fpath.relative_to(MEMORY_DIR) if fpath.is_relative_to(MEMORY_DIR) else fpath.name
            # Get matching lines with context
            cmd2 = ["rg", "-i", "-C", "1", "--max-count", "2", query, f]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=5)
            matches.append({
                "layer": "files",
                "source": str(rel),
                "text": r2.stdout.strip()[:500],
            })
        return matches
    except Exception as e:
        return [{"layer": "files", "error": str(e)[:80]}]


def search(query: str, limit: int = 5) -> dict:
    """三层串联搜索：ChromaDB → Letta → grep"""
    results = {"query": query, "layers_checked": [], "results": []}

    # Layer 1: ChromaDB
    if chromadb_healthy():
        results["layers_checked"].append("chromadb")
        r = search_chromadb(query, limit)
        if r and "error" not in r[0]:
            results["results"] = r
            results["used_layer"] = "chromadb"
            return results
        results["results"] = r

    # Layer 2: Letta
    if letta_healthy():
        results["layers_checked"].append("letta")
        r = search_letta(query, limit)
        if r and "error" not in r[0] and r[0].get("text"):
            results["results"] = r
            results["used_layer"] = "letta"
            return results

    # Layer 3: File grep
    results["layers_checked"].append("files")
    r = search_files(query, limit)
    results["results"] = r
    results["used_layer"] = "files"
    return results


def write_memory(text: str, source: str = "op", tags: str = "") -> dict:
    """写入记忆：文件 + ChromaDB 双写"""
    result = {"text": text[:100], "operations": []}

    # 1. 写入文件 (源真)
    ts = time.strftime("%Y-%m-%d %H:%M")
    entry = f"\n- [{ts}] [{source}] {text}\n"
    lessons = MEMORY_DIR / "lessons-learned.md"
    try:
        with open(lessons, "a") as f:
            f.write(entry)
        result["operations"].append("file:lessons-learned.md")
    except OSError as e:
        result["operations"].append(f"file:error:{e}")

    # 2. 索引到 ChromaDB
    if chromadb_healthy():
        meta = {"source": source, "tags": tags}
        payload = json.dumps({"text": text, "metadata": meta}).encode()
        req = Request(f"{CHROMADB_URL}/add_raw", data=payload,
                       headers={"Content-Type": "application/json"})
        try:
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read())
            result["operations"].append(f"chromadb:{data.get('result', {}).get('id', 'ok')}")
        except URLError as e:
            result["operations"].append(f"chromadb:error:{e}")

    return result


def trigger_sync() -> dict:
    """触发文件→ChromaDB增量同步"""
    try:
        r = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT)],
            capture_output=True, text=True, timeout=120
        )
        return {"status": "ok", "output": r.stdout.strip()[-200:]}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:80]}


def status() -> dict:
    """各层健康状态"""
    return {
        "chromadb": {"healthy": chromadb_healthy(), "url": CHROMADB_URL},
        "letta": {"healthy": letta_healthy(), "url": LETTA_URL},
        "files": {"path": str(MEMORY_DIR), "exists": MEMORY_DIR.is_dir()},
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: search <query> | write <text> | sync | status", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        if not query:
            print(json.dumps({"error": "missing query"}, ensure_ascii=False))
            sys.exit(1)
        result = search(query, limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "write":
        text = sys.argv[2] if len(sys.argv) > 2 else ""
        source = ""
        tags = ""
        for i, arg in enumerate(sys.argv):
            if arg == "--source" and i + 1 < len(sys.argv):
                source = sys.argv[i + 1]
            if arg == "--tags" and i + 1 < len(sys.argv):
                tags = sys.argv[i + 1]
        if not text:
            print(json.dumps({"error": "missing text"}, ensure_ascii=False))
            sys.exit(1)
        result = write_memory(text, source or "op", tags)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "sync":
        print(json.dumps(trigger_sync(), ensure_ascii=False, indent=2))

    elif cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))

    else:
        print(json.dumps({"error": f"unknown command: {cmd}"}, ensure_ascii=False))
        sys.exit(1)