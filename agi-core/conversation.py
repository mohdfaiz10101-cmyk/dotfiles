"""
conversation.py — AGI Brain 自然语言对话接口
Why: 让用户通过自然语言与 AGI Brain 交互，隐藏底层复杂性
What: 意图识别 + SQLite 对话历史持久化 + 结构化响应生成
Test: 发送"系统状态如何"，验证返回包含状态摘要；发送"派任务给OP"，验证 op-tasks.md 被写入
"""

import json
import os
import sqlite3
import httpx
from pathlib import Path
from datetime import datetime
from typing import Literal

# 意图类型
Intent = Literal["query_status", "execute_action", "manage_goals", "chat"]

DB_PATH = os.environ.get("AGI_DB_PATH", "/home/charlie/agi/agi.db")
LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-charlie-2026")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "glm-4.7")
OP_TASKS_FILE = os.environ.get(
    "OP_TASKS_FILE",
    "/home/charlie/.claude/projects/-home-charlie/memory/op-tasks.md"
)
STATUS_FILE = os.environ.get("STATUS_FILE", Path.home() / ".local/state/agi-brain-status.json")


def _init_db() -> None:
    """初始化 SQLite 数据库，创建对话历史表。

    Why: 持久化对话历史，让 LLM 保持上下文连贯性
    What: 创建 conversations 表（如不存在）
    Test: 调用后检查 agi.db 中存在 conversations 表
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _get_recent_history(session_id: str, limit: int = 5) -> list[dict]:
    """读取最近 N 条对话历史。

    Why: 为 LLM 提供上下文，避免每次从头开始
    What: 从 SQLite 读取指定 session 的最近记录
    Test: 插入 10 条记录后调用，验证只返回 5 条
    """
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT role, content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    # 反转为正序
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]


def _save_message(session_id: str, role: str, content: str) -> None:
    """保存一条对话记录到数据库。

    Why: 持久化对话，支持跨重启的上下文连续性
    What: INSERT 一条记录到 conversations 表
    Test: 调用后 SELECT COUNT(*) 应增加 1
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?,?,?,?)",
        (session_id, role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def _detect_intent(text: str) -> Intent:
    """简单关键词意图识别。

    Why: 快速分流用户请求，无需 LLM 调用
    What: 关键词匹配，返回四种意图之一
    Test: "状态如何" → query_status；"执行任务" → execute_action
    """
    text_lower = text.lower()
    if any(kw in text for kw in ["状态", "状况", "运行", "服务", "健康", "系统"]):
        return "query_status"
    if any(kw in text for kw in ["执行", "运行", "派任务", "OP", "op", "操作"]):
        return "execute_action"
    if any(kw in text for kw in ["目标", "计划", "任务列表", "待办"]):
        return "manage_goals"
    return "chat"


def _read_status() -> dict:
    """读取 AGI Brain 最新状态文件。

    Why: 为用户查询提供实时系统状态数据
    What: 读取 /tmp/agi-brain-status.json，不存在返回空字典
    Test: 文件不存在时返回 {}，文件存在时返回解析后的 dict
    """
    status_path = Path(STATUS_FILE)
    if not status_path.exists():
        return {"note": "状态文件不存在，Brain 可能未运行"}
    try:
        return json.loads(status_path.read_text())
    except Exception:
        return {"note": "状态文件损坏"}


def _write_op_task(task_desc: str) -> str:
    """写入任务到 op-tasks.md 供 OP 执行。

    Why: AGI Brain 通过文件接口向 OP 派发任务
    What: 追加格式化任务行到 op-tasks.md
    Test: 调用后检查文件末尾包含对应任务行
    """
    op_tasks_path = Path(OP_TASKS_FILE)
    op_tasks_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    task_line = f"- [ ] [AGI→OP] [{now}] {task_desc}\n"
    with open(op_tasks_path, "a", encoding="utf-8") as f:
        f.write(task_line)
    return task_line.strip()


async def chat(user_message: str, session_id: str = "default") -> str:
    """主对话接口：接收用户消息，返回 AGI Brain 回复。

    Why: 统一的自然语言交互入口，支持 Telegram/Discord/CLI 调用
    What: 意图识别 → 读取历史 → 构建 prompt → LLM 调用 → 保存历史 → 返回回复
    Test: 发送"你好"验证返回非空字符串；发送"查看系统状态"验证包含状态摘要
    """
    _init_db()
    intent = _detect_intent(user_message)

    # 核心系统提示（统一风格）
    _BASE = """你是 Charlie 的 AGI Brain，运行在 NixOS 主机上的个人智能助理。

Charlie 的系统架构：
- CC（Claude Code/Sonnet）= 规划决策层 | OP（OpenCode/GLM-4.7）= 执行层
- 服务：LiteLLM:4000 / Letta:8283 / AGI Brain / Paperclip:3100 / charlie-hub:9875
- 任务流：CC → op-tasks.md → OP 执行 → op-task-results.json

输出规范：中文，直接给结论和行动建议，不废话，不说"作为AI我..."。"""

    if intent == "query_status":
        status = _read_status()
        system_msg = _BASE + f"\n\n当前系统状态：\n{json.dumps(status, ensure_ascii=False)}"
    elif intent == "execute_action":
        system_msg = _BASE + "\n\n用户要派任务给OP执行。提取任务描述，确认后回复：任务内容 + '已写入 op-tasks.md'。"
    elif intent == "manage_goals":
        system_msg = _BASE + "\n\n帮助用户管理目标和待办任务，给出具体可执行的建议。"
    else:
        system_msg = _BASE

    # 读取对话历史
    history = _get_recent_history(session_id)
    messages = [{"role": "system", "content": system_msg}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # 保存用户消息
    _save_message(session_id, "user", user_message)

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post(
                f"{LITELLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
                json={
                    "model": DEFAULT_MODEL,
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 1000,
                }
            )
            resp.raise_for_status()
            reply = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"抱歉，LLM 调用失败：{e}"

    # 如果是派发任务意图，实际写入 op-tasks.md
    if intent == "execute_action" and "已写入" in reply:
        _write_op_task(user_message)

    # 保存 AI 回复
    _save_message(session_id, "assistant", reply)
    return reply
