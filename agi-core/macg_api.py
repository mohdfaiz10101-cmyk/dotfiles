#!/usr/bin/env python3
"""macg_api.py — macg LangGraph 的 OpenAI 兼容 API 包装

让 OpenCode/Aider/任何 OpenAI 客户端都能调用 macg 的完整能力（14 个工具 + 5 个 flow + supervisor 路由）。

启动: cd ~/agi && source .venv/bin/activate && python3 macg_api.py
端口: 9910
注册到 LiteLLM: model_name=macg, api_base=http://localhost:9910/v1
"""

import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from macg import build_graph

app = FastAPI(title="MACG API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = Path.home() / ".local/share/macg/api-state.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 全局 graph 实例
_graph = None
_checkpointer = None


def get_graph():
    global _graph, _checkpointer
    if _graph is None:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        _graph = build_graph(_checkpointer)
    return _graph


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "macg"
    messages: list[Message]
    max_tokens: int = 2048
    temperature: float = 0.7
    stream: bool = False


@app.get("/v1/models")
async def list_models():
    return {
        "data": [
            {"id": "macg", "object": "model", "owned_by": "local",
             "permission": [{"allow_create_engine": True}]}
        ]
    }


@app.on_event("startup")
async def warmup():
    """预热：启动时加载 graph，避免首次请求超时。"""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_graph)


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    import asyncio
    import hashlib

    graph = get_graph()

    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        return _error("无用户消息")

    last_input = user_msgs[-1].content
    ctx_key = hashlib.md5(
        json.dumps([m.content for m in req.messages[:3]]).encode()
    ).hexdigest()[:8]
    config = {"configurable": {"thread_id": f"api-{ctx_key}"}}

    try:
        # 在线程池中执行同步的 LangGraph invoke，不阻塞 uvicorn
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: graph.invoke(
                {"messages": [HumanMessage(content=last_input)]},
                config=config,
            )
        )

        reply = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                reply = msg.content
                break

        route = result.get("next", "glm")
        reply = f"[{route.upper()}] {reply}" if reply else "无回复"

    except Exception as e:
        reply = f"[ERROR] {e}"

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "macg",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": len(last_input), "completion_tokens": len(reply), "total_tokens": len(last_input) + len(reply)},
    }


def _error(msg: str):
    return {"error": {"message": msg, "type": "invalid_request_error"}}


@app.get("/health")
async def health():
    return {"status": "ok", "tools": 14, "flows": 5}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9910, log_level="warning")
