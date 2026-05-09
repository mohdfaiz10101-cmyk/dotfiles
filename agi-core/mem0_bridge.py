#!/usr/bin/env python3
"""
mem0_bridge.py — 轻量短期记忆服务
ChromaDB 向量存储 + LiteLLM GLM-4-flash 摘要
"""

import json
import os
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import chromadb
from openai import OpenAI

PORT = int(os.environ.get("MEM0_PORT", 8285))
DATA_DIR = Path(os.environ.get("MEM0_DATA", "/mnt/ai/apps/mem0-data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

LLM_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-litellm-charlie-2026")
LLM_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:4000/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "glm-4-flash")

# 初始化 ChromaDB（自带 ONNX embedding，无需外部模型）
db = chromadb.PersistentClient(path=str(DATA_DIR))
col = db.get_or_create_collection("mem0")

# 初始化 LLM（用于摘要/去重）
llm = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


def llm_extract(title: str, content: str) -> str:
    """用 LLM 提取核心记忆（摘要去重）"""
    try:
        resp = llm.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": "从文本提取核心事实，一句话概括，去掉冗余。只输出结果。"},
                {"role": "user", "content": f"标题: {title}\n内容: {content}"}
            ],
            timeout=10,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return content[:200]


def add_memory(text: str, metadata: dict = None) -> dict:
    """添加记忆"""
    mem_id = str(uuid.uuid4())[:8]
    meta = metadata or {}
    meta["ts"] = datetime.now().isoformat()
    meta["id"] = mem_id
    summary = llm_extract(meta.get("title", ""), text)
    col.add(documents=[summary], metadatas=[meta], ids=[mem_id])
    return {"id": mem_id, "summary": summary}


def search_memory(query: str, limit: int = 5) -> list:
    """搜索记忆"""
    results = col.query(query_texts=[query], n_results=limit)
    memories = []
    for i, doc in enumerate(results["documents"][0]):
        memories.append({
            "memory": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return memories


def get_all(limit: int = 50) -> list:
    """获取所有记忆"""
    results = col.get(limit=limit)
    memories = []
    for i, doc in enumerate(results["documents"]):
        memories.append({
            "memory": doc,
            "metadata": results["metadatas"][i],
        })
    return memories


def delete_memory(mem_id: str) -> bool:
    """删除记忆"""
    try:
        col.delete(ids=[mem_id])
        return True
    except Exception:
        return False


def reset_all():
    """清空所有记忆"""
    db.delete_collection("mem0")
    db.create_collection("mem0")


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/health":
            count = col.count()
            self._json(200, {"status": "ok", "service": "mem0-lite", "backend": "chromadb-onnx", "count": count})
        elif p.path == "/search":
            q = parse_qs(p.query).get("q", [""])[0]
            n = int(parse_qs(p.query).get("limit", [5])[0])
            if not q:
                return self._json(400, {"error": "missing q"})
            self._json(200, {"results": search_memory(q, n)})
        elif p.path == "/get_all":
            n = int(parse_qs(p.query).get("limit", [50])[0])
            self._json(200, {"memories": get_all(n)})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        p = urlparse(self.path)
        body = self._body()
        if p.path == "/add":
            text = body.get("text", "")
            if not text:
                return self._json(400, {"error": "missing text"})
            self._json(200, {"status": "ok", "result": add_memory(text, body.get("metadata"))})
        elif p.path == "/add_batch":
            items = body.get("items", [])
            if not items:
                return self._json(400, {"error": "missing items"})
            results = [add_memory(it.get("text", ""), it.get("metadata")) for it in items]
            self._json(200, {"status": "ok", "count": len(results)})
        elif p.path == "/delete":
            mid = body.get("memory_id", "")
            if not mid:
                return self._json(400, {"error": "missing memory_id"})
            self._json(200, {"status": "deleted" if delete_memory(mid) else "not found"})
        elif p.path == "/reset":
            reset_all()
            self._json(200, {"status": "reset"})
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[mem0-lite] 启动: http://127.0.0.1:{PORT} (chromadb-onnx + {LLM_MODEL})")
    server.serve_forever()
