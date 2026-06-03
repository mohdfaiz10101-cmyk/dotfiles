"""
memory_fusion.py — 三库并行融合检索（Reciprocal Rank Fusion）

Why: 串行 fallback 浪费时间，且只用一个源的结果
What: ChromaDB + Letta + Memgraph 三路并行 → RRF 融合 → 统一排名
Test: python3 memory_fusion.py search "关键词" → 融合结果

RRF 公式: score(d) = Σ 1/(k + rank_i(d))  where k=60 (standard)
"""

import asyncio
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

MEMORY_DIR = Path(os.path.expanduser("~/.claude/projects/-home-charlie/memory"))
CHROMADB_URL = os.environ.get("CHROMADB_URL", "http://127.0.0.1:8285")
LETTA_URL = os.environ.get("LETTA_URL", "http://127.0.0.1:8283")
MEMGRAPH_URL = os.environ.get("MEMGRAPH_URL", "http://127.0.0.1:7687")

RRF_K = 60  # RRF constant (standard value from Cormack et al.)


@dataclass
class FusionResult:
    """单条融合结果。"""
    text: str
    sources: list[str] = field(default_factory=list)
    rrf_score: float = 0.0
    individual_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text[:200],
            "sources": self.sources,
            "rrf_score": round(self.rrf_score, 4),
            "individual_scores": self.individual_scores,
            "metadata": self.metadata,
        }


def _http_get(url: str, timeout: int = 5) -> Optional[dict]:
    """安全 HTTP GET。"""
    try:
        resp = urlopen(url, timeout=timeout)
        return json.loads(resp.read())
    except Exception:
        return None


def _http_post(url: str, data: bytes, timeout: int = 10) -> Optional[dict]:
    """安全 HTTP POST。"""
    try:
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception:
        return None


# ── 源1: ChromaDB 语义搜索 ──────────────────────────────────────────────────

def search_chromadb(query: str, limit: int = 10) -> list[tuple[str, float, dict]]:
    """ChromaDB 语义搜索 → [(text, score, metadata), ...]"""
    try:
        from urllib.parse import quote
        q = quote(query, safe="")
        url = f"{CHROMADB_URL}/search?q={q}&limit={limit}"
        data = _http_get(url, timeout=8)
        if not data:
            return []
        results = []
        for r in data.get("results", []):
            text = r.get("memory", "")
            score = 1 - r.get("distance", 1)  # distance → similarity
            meta = r.get("metadata", {})
            results.append((text, round(score, 4), meta))
        return results
    except Exception:
        return []


# ── 源2: Letta 归档记忆搜索 ──────────────────────────────────────────────────

def search_letta(query: str, limit: int = 10) -> list[tuple[str, float, dict]]:
    """Letta archival 搜索 → [(text, score, metadata), ...]"""
    try:
        # Letta REST API: /v1/agents/{id}/archival-memory/search
        from urllib.parse import quote
        agent_id = os.environ.get("LETTA_AGENT_ID", "")
        if not agent_id:
            # fallback: try to list agents and pick first
            agents_data = _http_get(f"{LETTA_URL}/v1/agents/", timeout=5)
            if agents_data and isinstance(agents_data, list) and agents_data:
                agent_id = agents_data[0].get("id", "")
        if not agent_id:
            return []

        q = quote(query, safe="")
        url = f"{LETTA_URL}/v1/agents/{agent_id}/archival-memory/search?query={q}&limit={limit}"
        data = _http_get(url, timeout=8)
        if not data:
            return []
        results = []
        for r in data:
            text = r.get("content", "")
            score = r.get("score", 0.5)
            meta = {"source": "letta-archival", "id": r.get("id", "")}
            results.append((text, round(score, 4), meta))
        return results
    except Exception:
        return []


# ── 源3: Memgraph 图搜索 ──────────────────────────────────────────────────

def search_memgraph(query: str, limit: int = 10) -> list[tuple[str, float, dict]]:
    """Memgraph 图数据库搜索 → [(text, score, metadata), ...]"""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            MEMGRAPH_URL.replace("http://", "bolt://"),
            auth=("", "")
        )
        with driver.session() as session:
            # Fulltext search on entity names and values
            cypher = """
            CALL db.index.fulltext.queryNodes('entity_search', $query)
            YIELD node, score
            RETURN node.name AS name, node.value AS value,
                   labels(node)[0] AS label, score
            LIMIT $limit
            """
            result = session.run(cypher, query=query, limit=limit)
            results = []
            for record in result:
                name = record["name"] or ""
                value = record["value"] or ""
                label = record["label"] or ""
                score = record["score"] or 0.5
                text = f"[{label}] {name}: {value}"
                meta = {"source": "memgraph", "label": label, "name": name}
                results.append((text, round(score, 4), meta))
            return results
        driver.close()
    except Exception:
        # neo4j driver not available or memgraph down — skip
        return []


# ── 源4 (backup): File grep ──────────────────────────────────────────────────

def search_files(query: str, limit: int = 5) -> list[tuple[str, float, dict]]:
    """文件 grep 搜索 → [(text, score, metadata), ...]"""
    try:
        cmd = ["rg", "-l", "-i", query, str(MEMORY_DIR)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        files = [f for f in result.stdout.strip().split("\n") if f][:limit]
        if not files:
            return []

        results = []
        for i, f in enumerate(files):
            fpath = Path(f)
            rel = fpath.relative_to(MEMORY_DIR) if fpath.is_relative_to(MEMORY_DIR) else fpath.name
            cmd2 = ["rg", "-i", "-C", "1", "--max-count", "3", query, f]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=5)
            # File rank by position in results (rg sorts by relevance)
            score = 1.0 / (i + 1)
            results.append((r2.stdout.strip()[:500], round(score, 4), {"source": str(rel)}))
        return results
    except Exception:
        return []


# ── RRF 融合引擎 ──────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[tuple[str, float, dict]]],
    k: int = RRF_K,
) -> list[FusionResult]:
    """Reciprocal Rank Fusion: 多源排序融合。

    Args:
        ranked_lists: {"chromadb": [(text, score, meta), ...], "letta": [...], ...}
        k: RRF 常数（默认60）

    Returns:
        融合后的排序结果列表

    RRF score(d) = Σ_sources 1/(k + rank_source(d))
    """
    # 文本归一化 key（前100字符，去空白）
    def norm_key(text: str) -> str:
        return " ".join(text[:100].split()).lower().strip()

    # 收集所有唯一文档
    doc_map: dict[str, FusionResult] = {}

    for source_name, results in ranked_lists.items():
        for rank, (text, score, meta) in enumerate(results):
            key = norm_key(text)
            if not key:
                continue

            rrf_contribution = 1.0 / (k + rank + 1)

            if key not in doc_map:
                doc_map[key] = FusionResult(
                    text=text,
                    sources=[source_name],
                    rrf_score=rrf_contribution,
                    individual_scores={source_name: score},
                    metadata=meta,
                )
            else:
                existing = doc_map[key]
                existing.rrf_score += rrf_contribution
                existing.sources.append(source_name)
                existing.individual_scores[source_name] = score
                # Merge metadata (prefer longer text)
                if len(text) > len(existing.text):
                    existing.text = text
                    existing.metadata.update(meta)

    # Sort by RRF score descending
    sorted_results = sorted(doc_map.values(), key=lambda x: x.rrf_score, reverse=True)
    return sorted_results


# ── 并行检索 + 融合 ──────────────────────────────────────────────────────────

def search_fusion(query: str, limit: int = 10, timeout: int = 15) -> dict:
    """三库并行检索 + RRF 融合。

    Why: 串行 fallback 浪费 ~30s，并行只需 ~3s
    What: ThreadPoolExecutor 并行3路 → RRF → 统一排名
    Test: python3 memory_fusion.py search "磁盘清理"
    """
    start = time.time()
    ranked_lists: dict[str, list] = {}
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            "chromadb": pool.submit(search_chromadb, query, limit),
            "letta": pool.submit(search_letta, query, limit),
            "memgraph": pool.submit(search_memgraph, query, limit),
            "files": pool.submit(search_files, query, limit),
        }

        for name, future in futures.items():
            try:
                result = future.result(timeout=timeout)
                if result:
                    ranked_lists[name] = result
            except Exception as e:
                errors[name] = str(e)[:80]

    # RRF 融合
    fused = reciprocal_rank_fusion(ranked_lists, k=RRF_K)

    elapsed = round(time.time() - start, 2)

    return {
        "query": query,
        "elapsed_sec": elapsed,
        "sources_queried": list(ranked_lists.keys()),
        "sources_failed": errors,
        "total_results": len(fused),
        "results": [r.to_dict() for r in fused[:limit]],
    }


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3 or sys.argv[1] != "search":
        print("用法: python3 memory_fusion.py search <query> [--limit 10]", file=sys.stderr)
        sys.exit(1)

    q = sys.argv[2]
    lim = 10
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        lim = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 10

    result = search_fusion(q, limit=lim)
    print(json.dumps(result, ensure_ascii=False, indent=2))
