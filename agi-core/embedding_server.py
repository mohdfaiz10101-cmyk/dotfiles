#!/usr/bin/env python3
import os
os.environ["LD_LIBRARY_PATH"] = "/mnt/ai/apps/mem0-venv/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
"""轻量 embedding 服务 — 复用 ChromaDB ONNX 模型"""
import os
os.environ["LD_LIBRARY_PATH"] = "/mnt/ai/apps/mem0-venv/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
import json
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# 加载 ONNX 模型
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
embed_fn = ONNXMiniLM_L6_V2()

class Handler(BaseHTTPRequestHandler):
    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        if self.path in ("/v1/embeddings", "/embeddings"):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            texts = body.get("input", [])
            if isinstance(texts, str): texts = [texts]
            embeddings = embed_fn(texts)
            result = {"data": [{"object": "embedding", "embedding": e.tolist(), "index": i} for i, e in enumerate(embeddings)],
                      "model": "all-MiniLM-L6-v2", "usage": {"total_tokens": sum(len(t.split()) for t in texts)}}
            self._json(200, result)
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, *args): pass

if __name__ == "__main__":
    port = int(os.environ.get("EMBEDDING_PORT", 8286))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[embedding] 启动: http://0.0.0.0:{port} (all-MiniLM-L6-v2)")
    server.serve_forever()
