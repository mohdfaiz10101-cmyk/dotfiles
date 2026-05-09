#!/usr/bin/env python3
"""
mac.py — Multi-Agent CLI (CC+OP 融合)
GLM 默认处理（免费）→ 自动升级 Claude（复杂任务）
工具: bash / 文件 / glob / grep / memory / op-delegate
持久对话历史 (SQLite)
"""

import os, sys, json, subprocess, sqlite3, readline, re
from pathlib import Path
from datetime import datetime
from typing import Optional
import anthropic
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────────────────────────────
CLAUDE_MODEL   = "claude-sonnet-4-6"
GLM_MODEL      = "glm-5-turbo"
LITELLM_BASE   = "http://localhost:4000/v1"
LITELLM_KEY    = "sk-litellm-charlie-2026"
DB_PATH        = Path.home() / ".local/share/mac/history.db"
OP_TASKS_FILE  = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"

ANSI = {
    "reset": "\033[0m", "bold": "\033[1m",
    "glm": "\033[36m",    # cyan
    "claude": "\033[35m", # magenta
    "tool": "\033[33m",   # yellow
    "err": "\033[31m",    # red
    "dim": "\033[2m",
}

# ── 工具定义 ──────────────────────────────────────────────────────────────────
TOOLS_CLAUDE = [
    {"name": "bash", "description": "执行 shell 命令，返回 stdout+stderr",
     "input_schema": {"type": "object", "properties": {
         "command": {"type": "string"},
         "timeout": {"type": "integer", "default": 30}
     }, "required": ["command"]}},
    {"name": "read_file", "description": "读取文件内容",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"},
         "lines": {"type": "integer", "description": "最多读取行数", "default": 200}
     }, "required": ["path"]}},
    {"name": "write_file", "description": "写入文件（覆盖）",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"}, "content": {"type": "string"}
     }, "required": ["path", "content"]}},
    {"name": "glob", "description": "按 glob 模式查找文件",
     "input_schema": {"type": "object", "properties": {
         "pattern": {"type": "string"}, "dir": {"type": "string", "default": "."}
     }, "required": ["pattern"]}},
    {"name": "grep", "description": "在文件中搜索内容",
     "input_schema": {"type": "object", "properties": {
         "pattern": {"type": "string"}, "path": {"type": "string", "default": "."},
         "flags": {"type": "string", "default": "-rn --include='*'"}
     }, "required": ["pattern"]}},
    {"name": "op_delegate", "description": "将任务委托给 OP（OpenCode/GLM）异步执行，适合运维/定时任务",
     "input_schema": {"type": "object", "properties": {
         "task": {"type": "string"}, "priority": {"type": "string", "enum": ["high","medium","low"], "default": "medium"}
     }, "required": ["task"]}},
    {"name": "memory_read", "description": "读取记忆文件",
     "input_schema": {"type": "object", "properties": {
         "filename": {"type": "string", "description": "如 lessons-learned.md / MEMORY.md"}
     }, "required": ["filename"]}},
    {"name": "memory_write", "description": "追加内容到记忆文件",
     "input_schema": {"type": "object", "properties": {
         "filename": {"type": "string"}, "content": {"type": "string"}
     }, "required": ["filename", "content"]}},
]

def _to_openai_tools(claude_tools):
    result = []
    for t in claude_tools:
        schema = dict(t["input_schema"])
        result.append({"type": "function", "function": {
            "name": t["name"], "description": t["description"], "parameters": schema
        }})
    return result

TOOLS_OPENAI = _to_openai_tools(TOOLS_CLAUDE)

# ── 工具执行 ──────────────────────────────────────────────────────────────────
def run_tool(name: str, args: dict) -> str:
    try:
        if name == "bash":
            timeout = args.get("timeout", 30)
            r = subprocess.run(args["command"], shell=True, capture_output=True,
                               text=True, timeout=timeout)
            out = (r.stdout + r.stderr).strip()
            return out[:4000] if out else "(no output)"

        elif name == "read_file":
            p = Path(args["path"]).expanduser()
            if not p.exists(): return f"文件不存在: {p}"
            lines = p.read_text(errors="replace").splitlines()
            limit = args.get("lines", 200)
            text = "\n".join(lines[:limit])
            if len(lines) > limit:
                text += f"\n... (共 {len(lines)} 行，显示前 {limit} 行)"
            return text

        elif name == "write_file":
            p = Path(args["path"]).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"])
            return f"[OK] 已写入 {p} ({len(args['content'])} 字节)"

        elif name == "glob":
            import glob as g
            base = Path(args.get("dir", ".")).expanduser()
            matches = g.glob(str(base / args["pattern"]), recursive=True)
            return "\n".join(matches[:50]) if matches else "(无匹配)"

        elif name == "grep":
            cmd = f"rg {args.get('flags','-rn')} {json.dumps(args['pattern'])} {args.get('path','.')}"
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            out = (r.stdout + r.stderr).strip()
            return out[:3000] if out else "(无匹配)"

        elif name == "op_delegate":
            task = args["task"]
            priority = args.get("priority", "medium")
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            line = f"- [ ] [MAC→OP] [{now}] [{priority}] {task}\n"
            OP_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OP_TASKS_FILE, "a") as f:
                f.write(line)
            return f"[OK] 任务已写入 op-tasks.md：{task}"

        elif name == "memory_read":
            mem_dir = Path.home() / ".claude/projects/-home-charlie/memory"
            p = mem_dir / args["filename"]
            if not p.exists(): return f"记忆文件不存在: {p}"
            return p.read_text()[:3000]

        elif name == "memory_write":
            mem_dir = Path.home() / ".claude/projects/-home-charlie/memory"
            p = mem_dir / args["filename"]
            with open(p, "a") as f:
                f.write("\n" + args["content"])
            return f"[OK] 已追加到 {p}"

        return f"未知工具: {name}"
    except Exception as e:
        return f"[FAIL] {name}: {e}"

# ── 数据库 ────────────────────────────────────────────────────────────────────
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY, name TEXT, created_at TEXT, last_active TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY, session_id INTEGER, role TEXT,
            content TEXT, model TEXT, timestamp TEXT
        );
    """)
    con.commit()
    return con

def get_or_create_session(con, name: Optional[str] = None) -> int:
    now = datetime.now().isoformat()
    if name:
        row = con.execute("SELECT id FROM sessions WHERE name=?", (name,)).fetchone()
        if row: return row[0]
    # 取最近会话
    row = con.execute("SELECT id FROM sessions ORDER BY last_active DESC LIMIT 1").fetchone()
    if row and not name: return row[0]
    # 新建
    name = name or f"session-{datetime.now().strftime('%m%d-%H%M')}"
    cur = con.execute("INSERT INTO sessions(name,created_at,last_active) VALUES(?,?,?)", (name,now,now))
    con.commit()
    return cur.lastrowid

def load_messages(con, session_id: int) -> list:
    rows = con.execute(
        "SELECT role, content FROM messages WHERE session_id=? ORDER BY id",
        (session_id,)
    ).fetchall()
    return [{"role": r, "content": c} for r, c in rows]

def save_message(con, session_id: int, role: str, content: str, model: str = ""):
    con.execute(
        "INSERT INTO messages(session_id,role,content,model,timestamp) VALUES(?,?,?,?,?)",
        (session_id, role, content, model, datetime.now().isoformat())
    )
    con.execute("UPDATE sessions SET last_active=? WHERE id=?",
                (datetime.now().isoformat(), session_id))
    con.commit()

# ── GLM 调用（带工具）────────────────────────────────────────────────────────
def call_glm(messages: list, escalate_check: bool = True) -> tuple[str, bool]:
    """返回 (回复文本, 是否需要升级到Claude)"""
    client = OpenAI(base_url=LITELLM_BASE, api_key=LITELLM_KEY)

    system = """你是 MAC 的 GLM 层，处理日常任务。
工具调用规则：需要执行命令/读写文件时直接调用工具，不要解释。
升级规则：如果任务需要复杂架构设计、深度代码分析、NixOS系统级操作、多文件重构，
在回复开头加上 [ESCALATE] 原因，然后停止。"""

    msgs = [{"role": "system", "content": system}] + messages

    response = client.chat.completions.create(
        model=GLM_MODEL, messages=msgs, tools=TOOLS_OPENAI,
        tool_choice="auto", max_tokens=2000
    )

    msg = response.choices[0].message

    # 处理工具调用
    while msg.tool_calls:
        tool_results = []
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = run_tool(tc.function.name, args)
            _print_tool(tc.function.name, args, result)
            tool_results.append({
                "role": "tool", "tool_call_id": tc.id, "content": result
            })
        # 追加 assistant 消息和工具结果
        msgs.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})
        msgs.extend(tool_results)
        # 继续
        response = client.chat.completions.create(
            model=GLM_MODEL, messages=msgs, tools=TOOLS_OPENAI,
            tool_choice="auto", max_tokens=2000
        )
        msg = response.choices[0].message

    text = msg.content or ""
    should_escalate = escalate_check and text.startswith("[ESCALATE]")
    return text, should_escalate

# ── Claude 调用（带工具）─────────────────────────────────────────────────────
def call_claude(messages: list) -> str:
    client = anthropic.Anthropic()

    system = """你是 MAC 的 Claude 层，处理复杂任务。
你有完整的对话历史上下文。直接用工具完成任务，不要废话。
完成后如果有适合委托给 OP 的运维任务，使用 op_delegate 工具。"""

    # 过滤掉 tool role（Anthropic 格式不同）
    claude_msgs = []
    for m in messages:
        if m["role"] == "tool":
            continue
        claude_msgs.append({"role": m["role"], "content": m["content"]})

    resp = client.messages.create(
        model=CLAUDE_MODEL, max_tokens=4096, system=system,
        tools=TOOLS_CLAUDE, messages=claude_msgs
    )

    result_parts = []
    while resp.stop_reason == "tool_use":
        tool_results = []
        for block in resp.content:
            if block.type == "text":
                result_parts.append(block.text)
            elif block.type == "tool_use":
                result = run_tool(block.name, block.input)
                _print_tool(block.name, block.input, result)
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block.id, "content": result
                })
        # 继续对话
        claude_msgs.append({"role": "assistant", "content": resp.content})
        claude_msgs.append({"role": "user", "content": tool_results})
        resp = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=4096, system=system,
            tools=TOOLS_CLAUDE, messages=claude_msgs
        )

    for block in resp.content:
        if hasattr(block, "text"):
            result_parts.append(block.text)

    return "\n".join(result_parts)

# ── 打印工具 ──────────────────────────────────────────────────────────────────
def _print_tool(name, args, result):
    c = ANSI
    arg_str = ", ".join(f"{k}={json.dumps(v)[:40]}" for k,v in args.items())
    print(f"{c['tool']}  ⚙ {name}({arg_str}){c['reset']}")
    lines = result.splitlines()[:5]
    for l in lines:
        print(f"{c['dim']}    {l}{c['reset']}")
    if len(result.splitlines()) > 5:
        print(f"{c['dim']}    ... ({len(result.splitlines())} 行){c['reset']}")

# ── 主 REPL ───────────────────────────────────────────────────────────────────
def repl():
    con = init_db()
    session_id = get_or_create_session(con)
    messages = load_messages(con, session_id)

    c = ANSI
    print(f"{c['bold']}MAC — Multi-Agent CLI{c['reset']}  (GLM免费 + Claude按需)")
    print(f"{c['dim']}历史消息: {len(messages)} 条  |  :new 新会话  |  :sessions 列表  |  :quit 退出{c['reset']}\n")

    # 设置 readline 历史
    hist_file = Path.home() / ".local/share/mac/readline_history"
    hist_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(str(hist_file))
    except FileNotFoundError:
        pass
    readline.set_history_length(1000)

    current_model = "glm"

    while True:
        try:
            prefix = f"{c['claude']}claude{c['reset']}" if current_model == "claude" else f"{c['glm']}glm{c['reset']}"
            user_input = input(f"\n[{prefix}] > ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        # 内置命令
        if user_input == ":quit":
            break
        elif user_input == ":new":
            session_id = get_or_create_session(con, None)
            messages = []
            print(f"  新会话已创建 (id={session_id})")
            continue
        elif user_input == ":sessions":
            rows = con.execute("SELECT id, name, last_active FROM sessions ORDER BY last_active DESC LIMIT 10").fetchall()
            for sid, name, la in rows:
                marker = "◆" if sid == session_id else " "
                print(f"  {marker} [{sid}] {name}  {la[:16]}")
            continue
        elif user_input.startswith(":load "):
            sid = int(user_input.split()[1])
            session_id = sid
            messages = load_messages(con, session_id)
            print(f"  已加载会话 {sid}，{len(messages)} 条消息")
            continue
        elif user_input == ":claude":
            current_model = "claude"
            print("  已切换到 Claude 模式")
            continue
        elif user_input == ":glm":
            current_model = "glm"
            print("  已切换到 GLM 模式")
            continue
        elif user_input == ":status":
            print(f"  会话: {session_id}  消息: {len(messages)}  模型: {current_model}")
            continue

        # 保存用户消息
        messages.append({"role": "user", "content": user_input})
        save_message(con, session_id, "user", user_input)

        try:
            if current_model == "claude":
                print(f"\n{c['claude']}● Claude{c['reset']}")
                reply = call_claude(messages)
                print(reply)
                messages.append({"role": "assistant", "content": reply})
                save_message(con, session_id, "assistant", reply, CLAUDE_MODEL)
            else:
                # GLM 先处理
                print(f"\n{c['glm']}● GLM{c['reset']}")
                reply, should_escalate = call_glm(messages)

                if should_escalate:
                    reason = reply.replace("[ESCALATE]", "").strip().split("\n")[0]
                    print(f"{c['dim']}  → 升级到 Claude ({reason}){c['reset']}")
                    print(f"\n{c['claude']}● Claude{c['reset']}")
                    reply = call_claude(messages)
                    print(reply)
                    messages.append({"role": "assistant", "content": reply})
                    save_message(con, session_id, "assistant", reply, CLAUDE_MODEL)
                else:
                    print(reply)
                    messages.append({"role": "assistant", "content": reply})
                    save_message(con, session_id, "assistant", reply, GLM_MODEL)

        except Exception as e:
            print(f"{c['err']}[FAIL] {e}{c['reset']}")

    readline.write_history_file(str(hist_file))
    print("\n再见")

if __name__ == "__main__":
    repl()
