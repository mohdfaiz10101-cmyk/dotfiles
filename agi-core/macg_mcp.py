#!/usr/bin/env python3
"""
macg_mcp.py — macg 工具的 MCP Server
让 CC 原生调用 macg 的能力：sense_system / wechat / letta / op_delegate / run_flow
CC 用 Claude 思考，macg 用 GLM 执行 — 各司其职，只开一个终端
"""

import os, sys, json, subprocess, urllib.request, urllib.error, urllib.parse
from pathlib import Path
import requests
from datetime import datetime

# 确保 agi 目录在 path 中
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("macg")

MEM_DIR = Path.home() / ".claude/projects/-home-charlie/memory"
OP_TASKS_FILE = MEM_DIR / "op-tasks.md"

# ── 系统感知 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def macg_sense() -> str:
    """获取系统实时状态：CPU/内存/磁盘/服务/浏览器上下文。来自 macg AGI Brain。"""
    try:
        from brain import sense
        data = sense()
        return json.dumps({
            "cpu": data.get("cpu_usage"),
            "mem": data.get("memory_usage"),
            "disk": data.get("disk_ai"),
            "services": data.get("services"),
            "cpu_hogs": data.get("cpu_hogs", []),
            "browser": data.get("browser", {}),
            "wechat": data.get("wechat", {}),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        # 降级：直接读系统状态
        r = subprocess.run(
            "echo cpu:$(grep 'cpu ' /proc/stat | awk '{u=$2+$4; t=$2+$3+$4+$5; printf \"%.1f%%\", u*100/t}') "
            "mem:$(free -h | awk 'NR==2{print $3\"/\"$2}') "
            "disk_ai:$(df -h /mnt/ai 2>/dev/null | awk 'NR==2{print $3\"/\"$2}')",
            shell=True, capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() or f"[FAIL] {e}"


@mcp.tool()
def macg_services() -> str:
    """检查 macg 生态服务状态：LiteLLM/Letta/AGI-GW/mihomo/Paperclip。"""
    import urllib.request
    checks = {
        "LiteLLM": ("http://localhost:4000/health", LITELLM_HEADERS),
        "Letta": ("http://localhost:8283/v1/agents/", LETTA_HEADERS),
        "AGI-GW": ("http://localhost:9900/health", {}),
        "Paperclip": ("http://localhost:3100/health", {}),
        "mihomo": ("http://localhost:9090/", {}),
    }
    results = {}
    for name, (url, hdrs) in checks.items():
        try:
            req = urllib.request.Request(url, headers=hdrs)
            urllib.request.urlopen(req, timeout=5)
            results[name] = "OK"
        except Exception as e:
            results[name] = f"DOWN({e})"
    return json.dumps(results, ensure_ascii=False)


# ── 微信 ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def macg_wechat_status() -> str:
    """查看微信系统状态和最近联系人。"""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:9801/api/wechat/status", timeout=3) as r:
            status = json.loads(r.read().decode())
        with urllib.request.urlopen("http://localhost:9801/api/wechat/contacts", timeout=3) as r:
            contacts = json.loads(r.read().decode())
        return json.dumps({"status": status, "recent": contacts[:5]}, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[FAIL] 微信服务不可达: {e}"


@mcp.tool()
def macg_wechat_reply(talker: str, content: str) -> str:
    """发送微信回复给指定联系人。talker: 联系人名称，content: 消息内容。"""
    import urllib.request
    try:
        payload = json.dumps({"talker": talker, "content": content}).encode()
        req = urllib.request.Request(
            "http://localhost:9801/api/wechat/reply",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.read().decode()
    except Exception as e:
        return f"[FAIL] {e}"


# ── Letta 记忆 ────────────────────────────────────────────────────────────────

@mcp.tool()
def macg_letta_search(query: str) -> str:
    """搜索 Letta 语义记忆。查询历史经验、踩坑记录、架构决策。"""
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(f"{LETTA_BASE}/v1/agents/", headers=LETTA_HEADERS)
        with urllib.request.urlopen(req, timeout=2) as r:
            agents = json.loads(r.read().decode())
        agent_list = agents if isinstance(agents, list) else agents.get("agents", [])
        agent_id = None
        for a in agent_list:
            if "code" in a.get("name", "").lower() or "assistant" in a.get("name", "").lower():
                agent_id = a.get("id")
                break
        if not agent_id and agent_list:
            agent_id = agent_list[0].get("id")
        if not agent_id:
            return "[FAIL] 无可用 Letta agent"

        from urllib.parse import quote
        req = urllib.request.Request(
            f"{LETTA_BASE}/v1/agents/{agent_id}/archival-memory/search",
            headers=LETTA_HEADERS, method="GET"
        )
        # append query params to URL
        sep = "?" if "?" not in req.full_url else "&"
        req.full_url = f"{req.full_url}{sep}query={quote(query)}&limit=5"
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read().decode())
        memories = result if isinstance(result, list) else result.get("results", result.get("memories", []))
        if not memories:
            return "Letta 无相关记忆"
        hits = [m.get("text", m.get("content", ""))[:300] for m in memories[:5] if m.get("text") or m.get("content")]
        return "\n---\n".join(hits)
    except Exception as e:
        return f"[FAIL] Letta 不可达: {e}"


@mcp.tool()
def macg_letta_store(text: str, tags: str = "") -> str:
    """向 Letta 写入新记忆。text: 内容，tags: 逗号分隔标签。"""
    import urllib.request
    try:
        req = urllib.request.Request(f"{LETTA_BASE}/v1/agents/", headers=LETTA_HEADERS)
        with urllib.request.urlopen(req, timeout=2) as r:
            agents = json.loads(r.read().decode())
        agent_list = agents if isinstance(agents, list) else agents.get("agents", [])
        agent_id = agent_list[0].get("id") if agent_list else None
        if not agent_id:
            return "[FAIL] 无可用 Letta agent"

        payload = json.dumps({"text": text}).encode()
        req = urllib.request.Request(
            f"{LETTA_BASE}/v1/agents/{agent_id}/archival-memory/",
            data=payload, headers=LETTA_HEADERS, method="POST"
        )
        with _LETTA_OPENER.open(req, timeout=3) as r:
            return "[OK] 已写入 Letta"
    except Exception as e:
        return f"[FAIL] {e}"


# ── OP 任务委托 ───────────────────────────────────────────────────────────────

@mcp.tool()
def macg_op_delegate(task: str, priority: str = "medium") -> str:
    """委托任务给 OP（OpenCode/GLM）异步执行。priority: high/medium/low。
    适合：服务修复、定时任务、系统配置、运维操作。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- [ ] [CC→OP] [{now}] [{priority}] {task}\n"
    OP_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OP_TASKS_FILE, "a") as f:
        f.write(line)
    return f"[OK] 已委托给 OP（{priority}优先级）：{task}"


@mcp.tool()
def macg_op_status() -> str:
    """查看 op-tasks.md 中待处理和最近完成的任务。"""
    if not OP_TASKS_FILE.exists():
        return "op-tasks.md 不存在"
    content = OP_TASKS_FILE.read_text()
    lines = content.splitlines()
    pending = [l for l in lines if "- [ ]" in l][-10:]
    done = [l for l in lines if "- [x]" in l or "- [X]" in l][-5:]
    return f"待处理({len(pending)}):\n" + "\n".join(pending) + f"\n\n最近完成({len(done)}):\n" + "\n".join(done)


# ── 工作流 ────────────────────────────────────────────────────────────────────

@mcp.tool()
def macg_run_flow(flow_name: str, spec: str = "") -> str:
    """运行 macg LangGraph 工作流。
    可用: self_heal(自愈巡检), task_decompose(任务分解), code_loop(代码闭环), evolve(优化进化)"""
    cmd = f"cd ~/agi && .venv/bin/python3 -m flows.{flow_name}"
    if spec:
        cmd += f" --spec {json.dumps(spec)}"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    out = (r.stdout + r.stderr).strip()
    return out[:4000] if out else "(无输出)"


@mcp.tool()
def macg_memory_read(filename: str) -> str:
    """读取 macg 共享记忆文件。filename 如：MEMORY.md / lessons-learned.md / pending-tasks.md"""
    p = MEM_DIR / filename
    if not p.exists():
        return f"文件不存在: {p}"
    return p.read_text()[:5000]


@mcp.tool()
def macg_memory_write(filename: str, content: str) -> str:
    """追加内容到 macg 共享记忆文件。"""
    p = MEM_DIR / filename
    with open(p, "a") as f:
        f.write("\n" + content)
    return f"[OK] 已追加到 {p}"


@mcp.tool()
def macg_cc_delegate(task: str, timeout_sec: int = 120) -> str:
    """将规划/架构/分析任务委托给 CC（Claude Code Opus）执行。
    适合：架构设计、NixOS 配置分析、多文件代码分析、复杂调试、方案对比。
    返回 CC 的执行结果（最多 4000 字符）。"""
    import subprocess, os
    try:
        r = subprocess.run(
            ["claude", "-p", task, "--model", "opus", "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(os.path.expanduser("~")),
            env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "cli"},
        )
        out = (r.stdout + r.stderr).strip()
        return out[:4000] if out else "(CC 无输出)"
    except subprocess.TimeoutExpired:
        return f"[CC 超时 {timeout_sec}s] — 建议用 macg_op_delegate 异步委托"
    except FileNotFoundError:
        return "[CC 不可用] claude 命令未找到，检查 PATH"
    except Exception as e:
        return f"[CC 调用失败] {e}"


# ── Prompt 优化器 ─────────────────────────────────────────────────────────────

LETTA_BASE = "http://localhost:8283"
LETTA_API_KEY = os.environ.get("LETTA_API_KEY", "letta")
LETTA_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LETTA_API_KEY}",
}
LETTA_AGENTS = ["nixos-sysadmin", "code-assistant", "opus-analyst"]
LITELLM_URL = "http://localhost:4000"
LITELLM_KEY = "sk-litellm-charlie-2026"
LITELLM_HEADERS = {
    "Authorization": f"Bearer {LITELLM_KEY}",
}


class _LettaRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Letta 返回 307 但 urllib 不跟随 POST 重定向，需要手动处理。"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # 307 Temporary Redirect: 保持 POST method 和 body
        new_req = urllib.request.Request(newurl, data=req.data, headers=req.headers, method=req.method)
        return new_req


_LETTA_OPENER = urllib.request.build_opener(_LettaRedirectHandler)

# 排除的 memory 文件（过旧/无关）
_SKIP_FILES = {"MEMORY.md", "rules-secondary.md", "lessons-learned-archive.md",
               "op-tasks-archive-20260423.md", "SYSTEM-INDEX.md"}


def _letta_search_multi(query: str, limit: int = 3) -> list[dict]:
    """并行搜索多个 Letta agent 的归档记忆。"""
    import urllib.request, urllib.error
    results = []
    try:
        req = urllib.request.Request(f"{LETTA_BASE}/v1/agents/", headers=LETTA_HEADERS)
        with urllib.request.urlopen(req, timeout=2) as r:
            agents = json.loads(r.read().decode())
        agent_list = agents if isinstance(agents, list) else agents.get("agents", [])
        agent_map = {a["name"].lower(): a["id"] for a in agent_list if a.get("name")}
    except Exception:
        return results

    for target_name in LETTA_AGENTS:
        aid = agent_map.get(target_name.lower())
        if not aid:
            continue
        try:
            from urllib.parse import quote
            search_url = f"{LETTA_BASE}/v1/agents/{aid}/archival-memory/search?query={quote(query)}&limit={limit}"
            req = urllib.request.Request(search_url, headers=LETTA_HEADERS, method="GET")
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
            items = data if isinstance(data, list) else data.get("results", data.get("memories", []))
            for m in items[:limit]:
                text = m.get("text", m.get("content", ""))
                if text:
                    results.append({"source": f"letta:{target_name}", "text": text[:500]})
        except Exception:
            continue
    return results


def _local_search(query: str) -> list[dict]:
    """搜索本地 memory/*.md 文件。"""
    results = []
    keywords = query.lower().split()
    index_file = MEM_DIR / "MEMORY.md"

    # 读索引确定哪些文件可能相关
    relevant_files = []
    if index_file.exists():
        for line in index_file.read_text().splitlines():
            if "(" in line and ")" in line:
                fname = line.split("(")[1].split(")")[0]
                if fname not in _SKIP_FILES and any(k in line.lower() for k in keywords):
                    relevant_files.append(fname)
    # 兜底：如果没有匹配到，尝试全部文件
    if not relevant_files:
        relevant_files = [f.name for f in MEM_DIR.glob("*.md") if f.name not in _SKIP_FILES]

    for fname in relevant_files[:8]:
        fpath = MEM_DIR / fname
        if not fpath.exists():
            continue
        try:
            lines = fpath.read_text().splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in keywords):
                start = max(0, i - 2)
                end = min(len(lines), i + 4)
                snippet = "\n".join(lines[start:end])
                if snippet.strip():
                    results.append({"source": f"local:{fname}", "text": snippet[:400]})
                break  # 每个文件只取第一个匹配
    return results


def _litellm_generate(system_prompt: str, user_prompt: str, model: str = "glm-4-flash") -> str:
    """通过 LiteLLM 生成文本。"""
    import urllib.request, urllib.error
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{LITELLM_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LITELLM_KEY}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LLM 生成失败] {e}"


@mcp.tool()
def macg_context_probe(query: str) -> str:
    """探查某话题在记忆系统中有多少上下文可用。双路并行搜索 Letta + 本地文件，返回原始匹配片段。"""
    letta_hits = _letta_search_multi(query, limit=2)
    local_hits = _local_search(query)
    all_hits = letta_hits + local_hits
    if not all_hits:
        return json.dumps({"found": 0, "message": "无相关记忆"}, ensure_ascii=False)
    # 合并输出
    output = {"found": len(all_hits), "sources": []}
    for h in all_hits:
        output["sources"].append({"from": h["source"], "preview": h["text"][:200]})
    return json.dumps(output, ensure_ascii=False, indent=2)


@mcp.tool()
def macg_prompt_optimize(question: str, target: str = "auto") -> str:
    """优化 prompt 省 token：双路搜索记忆上下文 → 压缩成精准关键词 prompt。
    target: cc(Claude Code) / glm / deepseek / auto(自动判断)
    返回: 优化后的 prompt + 命中来源 + token 节省估算。"""
    # 1. 双路并行搜索
    letta_hits = _letta_search_multi(question, limit=3)
    local_hits = _local_search(question)
    all_hits = letta_hits + local_hits

    # 2. 构建上下文
    context_parts = []
    source_tags = set()
    for h in all_hits[:6]:
        src = h["source"]
        source_tags.add(src)
        context_parts.append(f"[{src}] {h['text'][:300]}")
    context = "\n".join(context_parts) if context_parts else "（无相关记忆）"

    # 3. 判断目标模型格式
    target_map = {
        "cc": "Claude Code — 中文回复，指令式，零废话，用 R1-R8 格式",
        "glm": "GLM — 中文回复，简洁直接",
        "deepseek": "DeepSeek — 中文回复，技术深度分析",
        "auto": "自动判断：NixOS/系统运维用 CC，简单问答用 GLM，复杂分析用 DeepSeek",
    }
    target_hint = target_map.get(target, target_map["auto"])

    # 4. 用 GLM-4-flash 生成优化 prompt
    system_prompt = """你是 prompt 优化器。任务：将用户的模糊问题 + 检索到的上下文，压缩成一个精准、省 token 的 prompt。
要求：
1. 保留所有关键技术细节和约束条件
2. 删除冗余描述和口语化表达
3. 如果上下文有相关信息，直接注入到 prompt 中（避免 AI 重复搜索）
4. 输出格式严格为 JSON：{"optimized_prompt": "...", "keywords": ["..."], "context_injected": true/false, "estimated_token_save": "XX%"}
5. optimized_prompt 必须是可以直接粘贴使用的完整 prompt"""

    user_prompt = f"用户问题：{question}\n\n检索到的上下文：\n{context}\n\n目标平台：{target_hint}"

    result_text = _litellm_generate(system_prompt, user_prompt)

    # 5. 组装最终输出
    try:
        optimized = json.loads(result_text)
    except Exception:
        optimized = {"optimized_prompt": result_text, "keywords": [], "context_injected": False, "estimated_token_save": "0%"}

    output = {
        "optimized_prompt": optimized.get("optimized_prompt", question),
        "keywords": optimized.get("keywords", []),
        "context_injected": optimized.get("context_injected", False),
        "estimated_token_save": optimized.get("estimated_token_save", "0%"),
        "sources_hit": list(source_tags),
        "total_memories_found": len(all_hits),
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# ── A2A Agent 间通信 ───────────────────────────────────────────────────────────

A2A_CHANNEL = Path.home() / ".local/share/macg/a2a-channel.jsonl"
A2A_CHANNEL.parent.mkdir(parents=True, exist_ok=True)


@mcp.tool()
def macg_a2a_send(to_agent: str, message: str, task_type: str = "info") -> str:
    """A2A 通信：发送消息给其他 Agent（CC/OP/Letta）。
    to_agent: cc / op / letta / all
    task_type: info(通知) / task(任务) / question(提问) / result(结果)
    消息持久化到 a2a-channel.jsonl，目标 Agent 可通过 macg_a2a_inbox 读取。"""
    now = datetime.now().isoformat()
    entry = {
        "id": f"{now[:19].replace(':','')}-{os.urandom(4).hex()}",
        "from": "cc", "to": to_agent,
        "type": task_type,
        "message": message[:500],
        "ts": now,
        "status": "pending"
    }
    with open(A2A_CHANNEL, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return json.dumps({"status": "sent", "id": entry["id"], "to": to_agent}, ensure_ascii=False)


@mcp.tool()
def macg_a2a_inbox(agent: str = "cc") -> str:
    """A2A 通信：读取发送给指定 Agent 的收件箱。
    agent: cc / op / letta / all
    返回未读消息列表（最近20条）。"""
    if not A2A_CHANNEL.exists():
        return json.dumps({"messages": [], "unread": 0}, ensure_ascii=False)
    lines = A2A_CHANNEL.read_text().strip().splitlines()
    messages = []
    for line in lines[-50:]:
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if agent == "all" or entry.get("to") in (agent, "all"):
            messages.append(entry)
    # 按时间倒序
    messages.sort(key=lambda x: x.get("ts", ""), reverse=True)
    unread = [m for m in messages if m.get("status") == "pending"]
    return json.dumps({"messages": unread[:20], "unread": len(unread), "total": len(messages)}, ensure_ascii=False, indent=2)


@mcp.tool()
def macg_a2a_mark_read(msg_id: str) -> str:
    """A2A 通信：标记消息为已读。"""
    if not A2A_CHANNEL.exists():
        return "[FAIL] 通道不存在"
    lines = A2A_CHANNEL.read_text().strip().splitlines()
    updated = 0
    new_lines = []
    for line in lines:
        try:
            entry = json.loads(line)
        except Exception:
            new_lines.append(line)
            continue
        if entry.get("id") == msg_id and entry.get("status") == "pending":
            entry["status"] = "read"
            updated += 1
        new_lines.append(json.dumps(entry, ensure_ascii=False))
    if updated:
        A2A_CHANNEL.write_text("\n".join(new_lines) + "\n")
    return json.dumps({"status": "ok", "updated": updated}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 18092
    mcp.run(transport="streamable-http")


# ── mem0-lite 工具 (port 8285) ──
MEM0_URL = "http://localhost:8285"

def _mem0_get(path: str, params: dict = None) -> dict:
    try:
        r = requests.get(f"{MEM0_URL}{path}", params=params, timeout=5)
        return r.json()
    except Exception:
        return {"error": "mem0 不可用"}

def _mem0_post(path: str, data: dict) -> dict:
    try:
        r = requests.post(f"{MEM0_URL}{path}", json=data, timeout=5)
        return r.json()
    except Exception:
        return {"error": "mem0 不可用"}


@mcp.tool()
def macg_mem0_search(query: str, limit: int = 5) -> str:
    """mem0 短期记忆搜索。输入关键词，返回匹配的记忆片段。"""
    result = _mem0_get("/search", {"q": query, "limit": limit})
    if "error" in result:
        return f"[FAIL] {result['error']}"
    if not result.get("results"):
        return "[OK] 无匹配记忆"
    hits = []
    for r in result["results"]:
        hits.append(f"- {r['memory']} (dist={r['distance']:.2f})")
    return f"[OK] {len(hits)} 条匹配:\n" + "\n".join(hits)

@mcp.tool()
def macg_mem0_add(text: str, source: str = "mcp") -> str:
    """mem0 写入短期记忆。输入文本和来源标签。"""
    result = _mem0_post("/add", {"text": text, "metadata": {"source": source}})
    if "error" in result:
        return f"[FAIL] {result['error']}"
    return f"[OK] 已写入 (id={result.get('result',{}).get('id','?')}, summary={result.get('result',{}).get('summary','')[:80]})"

@mcp.tool()
def macg_mem0_get_all(limit: int = 20) -> str:
    """mem0 获取所有短期记忆。"""
    result = _mem0_get("/get_all", {"limit": limit})
    if "error" in result:
        return f"[FAIL] {result['error']}"
    mems = result.get("memories", [])
    if not mems:
        return "[OK] 暂无记忆"
    lines = [f"- [{m['metadata'].get('id','?')}] {m['memory']}" for m in mems]
    return f"[OK] 共 {len(mems)} 条:\n" + "\n".join(lines)

@mcp.tool()
def macg_mem0_delete(memory_id: str) -> str:
    """mem0 删除指定记忆。输入 memory_id。"""
    result = _mem0_post("/delete", {"memory_id": memory_id})
    return f"[OK] 删除 {memory_id}" if result.get("status") == "deleted" else f"[FAIL] {result}"
