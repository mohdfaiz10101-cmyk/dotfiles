#!/usr/bin/env python3
"""Document Knowledge Base — ChromaDB-backed document storage with entity linkage.

Stores extracted document data in ChromaDB vectors, linked to Context Graph entities.
Enables semantic search across all processed documents.
"""

import argparse, json, os, sys
from datetime import datetime
from pathlib import Path

try:
    import chromadb
    import httpx
except ImportError as e:
    print(f"[FAIL] 缺少依赖: {e}", file=sys.stderr)
    sys.exit(1)

CHROMA_URL = os.environ.get("CHROMA_URL", "http://localhost:8000")
LITELLM_URL = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-charlie-2026")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
COLLECTION_NAME = "agi_documents"
META_FILE = Path.home() / "agi" / "doc_kb_meta.json"

sys.path.insert(0, str(Path(__file__).parent))
from context_graph import entity_match, entity_search


def _get_client():
    return chromadb.HttpClient(host="localhost", port=8000)


def _get_or_create_collection(client=None):
    client = client or _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "description": "AGI document knowledge base"},
    )


def store_document(doc_data: dict, doc_id: str | None = None) -> dict:
    """Store a document (from doc_pipeline extract output) in ChromaDB with entity linkage."""
    collection = _get_or_create_collection()

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    doc_id = doc_id or f"doc_{ts}"

    # Build text for embedding
    fields = doc_data.get("fields", {})
    raw_text = doc_data.get("raw_text", "")
    doc_type = doc_data.get("doc_type", "unknown")
    line_items = doc_data.get("line_items", [])

    text_parts = [
        f"文档类型: {doc_type}",
        f"日期: {doc_data.get('doc_date', '未知')}",
        "字段: " + " | ".join(f"{k}={v}" for k, v in fields.items() if v),
    ]
    for i, item in enumerate(line_items[:10]):
        text_parts.append(
            f"商品{i + 1}: " + " | ".join(f"{k}={v}" for k, v in item.items() if v)
        )
    if raw_text:
        text_parts.append(f"原文: {raw_text[:2000]}")
    full_text = "\n".join(text_parts)

    # Entity linkage
    entities = doc_data.get("entities", {})
    linked_entity_ids = []
    for name in entities.get("company_names", []):
        m = entity_match(name)
        if m:
            linked_entity_ids.append(f"{m['type']}:{m['id']}")
    for name in entities.get("person_names", []):
        m = entity_match(name)
        if m:
            linked_entity_ids.append(f"{m['type']}:{m['id']}")

    metadata = {
        "doc_type": doc_type,
        "doc_date": doc_data.get("doc_date", ""),
        "source": "doc_pipeline",
        "created_at": ts,
        "entity_count": len(linked_entity_ids),
        "field_count": len([v for v in fields.values() if v]),
        "line_item_count": len(line_items),
        "confidence": str(doc_data.get("confidence", 0)),
    }

    # Store entity IDs in a separate JSON field since ChromaDB metadata values must be simple types
    meta_file = META_FILE
    meta_store = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    meta_store[doc_id] = {
        "entity_ids": linked_entity_ids,
        "file_path": doc_data.get("file_path", ""),
    }
    meta_file.write_text(json.dumps(meta_store, ensure_ascii=False, indent=2))

    collection.upsert(
        ids=[doc_id],
        documents=[full_text],
        metadatas=[metadata],
    )

    return {
        "id": doc_id,
        "stored": True,
        "entity_links": len(linked_entity_ids),
        "text_length": len(full_text),
    }


def search_documents(
    query: str, n_results: int = 10, doc_type: str | None = None
) -> list[dict]:
    """Semantic search across stored documents."""
    collection = _get_or_create_collection()

    where_filter = None
    if doc_type:
        where_filter = {"doc_type": doc_type}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,
    )

    docs = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    meta_store = json.loads(META_FILE.read_text()) if META_FILE.exists() else {}

    for i, doc_id in enumerate(ids):
        entry = {
            "id": doc_id,
            "score": round(1 - distances[i], 3) if distances else None,
            "type": metadatas[i].get("doc_type", ""),
            "date": metadatas[i].get("doc_date", ""),
            "entity_count": metadatas[i].get("entity_count", 0),
            "snippet": documents[i][:300] if i < len(documents) else "",
        }
        extra = meta_store.get(doc_id, {})
        if extra.get("entity_ids"):
            entry["linked_entities"] = extra["entity_ids"]
        docs.append(entry)

    return docs


def get_entity_documents(
    entity_type: str, entity_id: str, limit: int = 20
) -> list[dict]:
    """Find all documents linked to a specific entity."""
    meta_store = json.loads(META_FILE.read_text()) if META_FILE.exists() else {}
    target = f"{entity_type}:{entity_id}"

    linked = []
    for doc_id, meta in meta_store.items():
        if target in meta.get("entity_ids", []):
            linked.append({"id": doc_id, "file_path": meta.get("file_path", "")})

    return linked[:limit]


def collection_stats() -> dict:
    collection = _get_or_create_collection()
    count = collection.count()
    meta_store = json.loads(META_FILE.read_text()) if META_FILE.exists() else {}
    type_counts = {}
    entity_linked = sum(1 for m in meta_store.values() if m.get("entity_ids"))

    if count > 0:
        peek = collection.peek(min(count, 100))
        for m in peek.get("metadatas", []):
            dt = m.get("doc_type", "unknown")
            type_counts[dt] = type_counts.get(dt, 0) + 1

    return {
        "total_documents": count,
        "entity_linked": entity_linked,
        "by_type": type_counts,
        "collection": COLLECTION_NAME,
    }


def main():
    p = argparse.ArgumentParser(description="Document Knowledge Base (ChromaDB)")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("search", help="Semantic search documents")
    s.add_argument("query")
    s.add_argument("--type", default=None)
    s.add_argument("-n", type=int, default=10)

    st = sub.add_parser("store", help="Store doc_pipeline JSON output")
    st.add_argument("json_file")

    ent = sub.add_parser("entity", help="Find docs linked to entity")
    ent.add_argument("--type", required=True)
    ent.add_argument("--id", required=True)

    stats_cmd = sub.add_parser("stats", help="Collection statistics")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)

    if args.cmd == "search":
        results = search_documents(args.query, args.n, args.type)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.cmd == "store":
        data = json.loads(Path(args.json_file).read_text())
        result = store_document(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "entity":
        results = get_entity_documents(args.type, args.id)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.cmd == "stats":
        s = collection_stats()
        print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
