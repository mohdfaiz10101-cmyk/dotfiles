"""
think.py v2 — AGI Brain Tool-Aware Think Module
P0升级: Letta双向记忆闭环 + 本地知识库语义注入 + 工具感知推理
"""

import asyncio
import json
import logging
import os
import re
import sys
import httpx
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# ── Letta 配置 ──────────────────────────────────────────────────────────────────
LETTA_URL = os.environ.get("LETTA_BASE_URL", "http://localhost:8283")
LETTA_TOKEN = os.environ.get("LETTA_TOKEN", "letta")

# Agent ID 缓存（首次通过 name lookup 获取，后续复用）
_agent_id_cache: dict[str, str] = {}


async def _resolve_agent_id(agent_name: str, fallback_uuid: str = "") -> str:
    """通过 agent name 动态查找 ID，避免硬编码 UUID。
    
    Why: Letta 重建/迁移后 UUID 会变，name 是稳定标识
    What: 优先从 .env 读取 → 再通过 API name lookup → 最后用 fallback
    Test: Letta 不可达时返回 fallback，不阻塞主流程
    """
    # 1. 缓存命中
    if agent_name in _agent_id_cache:
        return _agent_id_cache[agent_name]
    
    # 2. 环境变量覆盖（最高优先级）
    env_key = f"LETTA_AGENT_{agent_name.upper().replace('-', '_')}"
    env_val = os.environ.get(env_key, "")
    if env_val and env_val.startswith("agent-"):
        _agent_id_cache[agent_name] = env_val
        return env_val
    
    # 3. API name lookup
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{LETTA_URL}/v1/agents/",
                headers={"Authorization": f"Bearer {LETTA_TOKEN}"},
            )
            if resp.status_code == 200:
                agents = resp.json()
                if isinstance(agents, list):
                    for a in agents:
                        a_name = a.get("name", "")
                        a_id = a.get("id", "")
                        # 匹配：完全匹配 或 包含关系
                        if a_name and (a_name == agent_name or agent_name in a_name or a_name in agent_name):
                            _agent_id_cache[agent_name] = a_id
                            return a_id
    except Exception:
        pass
    
    # 4. fallback（硬编码 UUID，最后手段）
    if fallback_uuid:
        _agent_id_cache[agent_name] = fallback_uuid
        return fallback_uuid
    
    return ""


# 旧变量保留兼容（但值为空，运行时动态解析）
LETTA_CODE_AGENT = ""  # 运行时通过 _resolve_agent_id("nixos-sysadmin") 获取
LETTA_ARCHIVAL_AGENT = ""  # 运行时通过 _resolve_agent_id("code-assistant") 获取

# ── 本地知识库路径 ─────────────────────────────────────────────────────────────
MEMORY_DIR = Path(os.environ.get(
    "MEMORY_DIR", "/home/charlie/.claude/projects/-home-charlie/memory"
))
MEMORY_FILES = ["lessons-learned.md", "troubleshooting.md", "MEMORY.md"]

# ── 用户偏好（永久规则，来自 lessons-learned + op-tasks 历史） ──────────────
USER_PREFERENCES = """## 用户偏好（永久规则）
- 只为真正的异常生成告警，正常状态无需告警
- 进程PID已过期的不追查（python3.13/corepack/nix-daemon 为正常系统服务）
- 服务level=inactive且Result=success是oneshot timer正常完成，非故障
- 磁盘使用<90%为正常波动，禁止生成告警或任务
- 凌晨00:00-07:59降级为非紧急
- 同类告警1小时内不重复推送（冷却机制已实现）"""

# ── 系统提示词（核心角色定义） ─────────────────────────────────────────────────
SYSTEM_PROMPT = """你是 Charlie 的 AGI Brain v2，运行在 NixOS 主机上的工具感知智能助理。

职责层次：
1. **感知分析**：分析系统数据（CPU/内存/服务/代理），结合历史经验判断异常真伪
2. **工具调用**：你可以使用以下工具自主执行操作
   - `letta_recall`: 查询历史记忆判断是否为已知问题
   - `delegate_op`: 委托OP执行具体任务（如重启服务、检查日志）
   - `notify_user`: 向用户推送重要消息（Telegram + Discord）
3. **决策输出**：生成结构化行动方案

输出格式（MUST 有效JSON）：
{
  "summary": "一句话系统状态（中文）",
  "severity": "normal/warning/critical",
  "alerts": ["需关注的异常（经过历史去重）"],
  "actions": [
    {"priority": "high/medium/low", "task": "具体可执行任务", "assign_to": "op/user"}
  ],
  "proactive_message": "主动推送（为空则跳过）",
  "reasoning": "决策依据（1句）"
}

规则：
- 所有输出用中文
- 对比历史经验（注入上下文），已知假阳性不重复告警
- 只派发OP能执行的具体任务（重启/检查/清理）"""


# ── 记忆检索层（P0核心：双向闭环） ────────────────────────────────────────────

async def _letta_recall(query: str, limit: int = 3) -> str:
    """查询 Letta 语义记忆，获取相关历史上下文。
    
    Why: 让 LLM 了解同类异常的历史处理方式，避免重复决策
    What: 调用 Letta archival memory search API（动态解析 agent ID）
    Test: Letta不可达时静默返回空，不阻塞主流程
    """
    try:
        agent_id = await _resolve_agent_id("nixos-sysadmin", "agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea")
        if not agent_id:
            return ""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{LETTA_URL}/v1/agents/{agent_id}/archival-memory/",
                params={"query": query, "limit": limit},
                headers={"Authorization": f"Bearer {LETTA_TOKEN}"},
            )
            if resp.status_code != 200:
                return ""
            data = resp.json()
            items = data if isinstance(data, list) else data.get("results", data.get("memories", []))
            texts = []
            for item in items[:limit]:
                t = item.get("text", item.get("content", ""))
                if t:
                    texts.append(t[:250])
            return "\n".join(f"  • {t}" for t in texts) if texts else ""
    except Exception:
        return ""


async def _knowledge_grep(keywords: list[str]) -> str:
    """在本地 memory 文件中搜索关键词，获取踩坑经验。
    
    Why: Letta可能不可达，本地grep作为降级检索方案
    What: 对 lessons-learned/troubleshooting/MEMORY 做关键词搜索
    Test: 无匹配时静默返回空
    """
    if not MEMORY_DIR.exists():
        return ""
    try:
        results = []
        seen_files = set()
        for kw in keywords[:3]:
            kw_clean = kw[:30].replace('"', '').replace("'", "")
            if len(kw_clean) < 3:
                continue
            for mf in MEMORY_FILES:
                fp = MEMORY_DIR / mf
                if not fp.exists() or fp in seen_files:
                    continue
                proc = await asyncio.create_subprocess_exec(
                    "grep", "-i", "-m", "2", kw_clean, str(fp),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
                if stdout and proc.returncode == 0:
                    seen_files.add(fp)
                    lines = stdout.decode(errors="replace").strip().split("\n")
                    results.append(f"  [{mf}] {lines[0][:150]}")
        return "\n".join(results[:5]) if results else ""
    except Exception:
        return ""


async def _build_injected_context(sense_data: dict) -> str:
    """构建注入 LLM 的增强上下文（并行检索 Letta + 本地）。"""
    alerts = sense_data.get("alerts", [])
    hogs = sense_data.get("cpu_hogs", [])
    
    # 提取搜索关键词
    search_terms = []
    for a in alerts[:3]:
        # 去标签，取实质内容
        clean = re.sub(r"[\[\(\{].*?[\]\)\}]", "", a).strip()[:40]
        if clean:
            search_terms.append(clean)
    for h in hogs[:2]:
        if isinstance(h, dict):
            name = h.get("name", h.get("cmd", str(h)))
            search_terms.append(name[:40])
        elif isinstance(h, str):
            search_terms.append(h[:40])
    if not search_terms:
        search_terms = ["系统状态", "服务健康"]
    
    query = " ".join(search_terms[:3])
    
    # 并行检索（Letta 和本地 grep 同时进行，先返回先用）
    letta_task = _letta_recall(query)
    knowledge_task = _knowledge_grep(search_terms)
    
    # 设置总超时
    try:
        letta_ctx, knowledge_ctx = await asyncio.wait_for(
            asyncio.gather(letta_task, knowledge_task),
            timeout=8.0,
        )
    except asyncio.TimeoutError:
        letta_ctx, knowledge_ctx = "", ""
    
    parts = []
    if letta_ctx:
        parts.append(f"## 历史相关经验（Letta语义检索）\n{letta_ctx}")
    if knowledge_ctx:
        parts.append(f"## 本地踩坑记录\n{knowledge_ctx}")
    parts.append(USER_PREFERENCES)
    
    return "\n\n".join(parts)


# ── 核心分析函数（P0升级版） ──────────────────────────────────────────────────

async def analyze(sense_data: dict) -> dict:
    """调用 LLM 分析感知数据，返回结构化决策（v2增强版）。
    
    P0升级变更:
    - 分析前自动检索 Letta 记忆 + 本地知识库
    - 检索结果注入系统上下文，减少假阳性
    - 支持工具调用标记（tool_calls）
    
    Why: 将原始系统数据 + 历史经验转化为精准的行动建议
    What: 检索记忆 → 构建增强prompt → 调用LLM → 解析JSON
    Test: mock httpx 返回 {"summary":"OK","alerts":[],"actions":[]}
    """
    base_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
    api_key = os.environ.get("LITELLM_API_KEY", "sk-litellm-charlie-2026")
    model = os.environ.get("DEFAULT_MODEL", "glm-5.1")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ── Step 1: 注入历史上下文（P0核心） ──────────────────────────────────
    injected_ctx = await _build_injected_context(sense_data)
    if injected_ctx:
        logger.info("[THINK] 历史上下文已注入 (%d chars)", len(injected_ctx))
    
    # ── Step 2: 构建增强 System Prompt ────────────────────────────────────
    enhanced_system = SYSTEM_PROMPT
    if injected_ctx:
        enhanced_system += f"\n\n{injected_ctx}"
    
    # ── Step 3: 精简感知数据 ──────────────────────────────────────────────
    compact = {
        "time": now,
        "cpu_pct": sense_data.get("cpu_percent", sense_data.get("cpu_usage", "?")),
        "mem_used_mb": sense_data.get("memory_used_mb", sense_data.get("memory_usage", "?")),
        "disk_ai": sense_data.get("disk_ai", "?"),
        "services": _compact_services(sense_data.get("service_status", {})),
        "alerts": sense_data.get("alerts", []),
        "cpu_hogs": sense_data.get("cpu_hogs", [])[:3],
        "op_pending": sense_data.get("op_task_count", 0),
    }
    
    user_content = f"时间：{now}\n系统数据：{json.dumps(compact, ensure_ascii=False)}\n\n请基于以上数据和历史经验分析并输出JSON决策。"
    
    # ── Step 4: 调用 LLM ─────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": enhanced_system},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 2048,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            
            # ── Step 5: 写回 Letta（形成记忆闭环） ─────────────────────────
            if result.get("alerts") or result.get("actions"):
                _write_letta_archival(result, now)
            
            return result
            
    except json.JSONDecodeError as e:
        logger.error("LLM返回无效JSON: %s", e)
        return {
            "summary": f"LLM 返回无效 JSON：{e}",
            "severity": "warning",
            "alerts": ["think.py: JSON解析失败"],
            "actions": [],
            "proactive_message": "",
        }
    except Exception as e:
        logger.error("LLM调用失败: %s", e)
        return {
            "summary": f"LLM 调用失败：{e}",
            "severity": "warning",
            "alerts": [f"think.py: {type(e).__name__}: {e}"],
            "actions": [],
            "proactive_message": "",
        }


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def _compact_services(services: dict | list) -> dict:
    """精简服务状态，只保留异常项。"""
    if isinstance(services, list):
        return {"count": len(services), "details": "列表格式"}
    if not isinstance(services, dict):
        return {}
    # 只保留非running的服务
    abnormal = {}
    for name, status in services.items():
        if isinstance(status, str) and status.lower() not in ("running", "active", "online", "ok"):
            abnormal[name] = status
        elif isinstance(status, dict):
            state = status.get("state", status.get("status", "unknown"))
            if state.lower() not in ("running", "active", "online", "ok"):
                abnormal[name] = state
    return {"total": len(services), "abnormal": abnormal} if abnormal else {"total": len(services), "all_healthy": True}


def _write_letta_archival(result: dict, ts: str) -> None:
    """写入 Letta 归档记忆（形成闭环：分析→记录→下次检索可用）。"""
    import requests
    import time as _time
    import asyncio
    
    summary = result.get("summary", "")
    severity = result.get("severity", "normal")
    alerts = result.get("alerts", [])
    actions = [a.get("task", "") for a in result.get("actions", [])]
    reasoning = result.get("reasoning", "")
    
    text = f"[{ts}] [{severity}] {summary} | alerts={alerts} | actions={actions}"
    if reasoning:
        text += f" | 依据: {reasoning}"
    
    # 动态解析 archival agent ID
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 在 async 上下文中，使用缓存的 ID 或 fallback
            agent_id = _agent_id_cache.get("code-assistant", "agent-8651643c-e753-47ed-9759-bd955c6ac240")
        else:
            agent_id = loop.run_until_complete(
                _resolve_agent_id("code-assistant", "agent-8651643c-e753-47ed-9759-bd955c6ac240")
            )
    except Exception:
        agent_id = "agent-8651643c-e753-47ed-9759-bd955c6ac240"
    
    if not agent_id:
        return
    
    for attempt in range(3):
        try:
            resp = requests.post(
                urljoin(f"{LETTA_URL.rstrip('/')}/", f"v1/agents/{agent_id}/archival-memory/"),
                headers={
                    "Authorization": f"Bearer {LETTA_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
                timeout=5,
                allow_redirects=True,
            )
            resp.raise_for_status()
            return
        except Exception as e:
            if attempt < 2:
                logger.debug("Letta archival 写入重试 %d/3: %s", attempt + 1, e)
                _time.sleep(2 ** attempt)
            else:
                logger.warning("Letta archival 写入失败(重试3次): %s", e)


# ── 自主执行层（P2核心：低风险操作自主执行） ──────────────────────────────

# 允许自主执行的关键词映射（低风险操作）
AUTONOMOUS_ACTIONS = {
    "systemctl": {"cmd": ["systemctl", "--user"], "timeout": 15},
    "docker logs": {"cmd": ["docker", "logs", "--tail"], "timeout": 10},
    "docker restart": {"cmd": ["docker", "restart"], "timeout": 30},
    "curl": {"cmd": ["curl", "-s", "--max-time"], "timeout": 10},
    "journalctl": {"cmd": ["journalctl", "--user", "--no-pager", "-n"], "timeout": 10},
    "df -h": {"cmd": ["df", "-h"], "timeout": 5},
    "du -sh": {"cmd": ["du", "-sh"], "timeout": 10},
    "grep": {"cmd": ["grep", "-i"], "timeout": 5},
}

async def execute_autonomous(action: dict) -> dict:
    """自主执行低风险操作（P2升级）。
    
    Why: 简单操作无需经过op-tasks.md流转，AGI Brain直接执行并验证
    What: 解析 action.task 中的命令，匹配白名单后执行
    Returns: {"success": bool, "output": str, "error": str}
    
    安全规则:
    - 仅白名单命令可执行
    - 禁止 rm/kill/shutdown/nixos-rebuild
    - 超时后强制终止
    """
    task = action.get("task", "")
    task_lower = task.lower()
    
    # 安全拦截：禁止高危操作
    blocked = ["rm ", "kill", "shutdown", "reboot", "nixos-rebuild", "sudo "]
    for b in blocked:
        if b in task_lower:
            return {"success": False, "output": "", "error": f"安全拦截: 禁止 {b}"}
    
    # 匹配白名单
    matched_cmd = None
    for key, config in AUTONOMOUS_ACTIONS.items():
        if key in task_lower:
            matched_cmd = key
            # 从任务描述中提取参数
            # 例如: "docker restart musetalk" → ["docker", "restart", "musetalk"]
            parts = task.split()
            args = []
            capture = False
            for p in parts:
                if p in key.split():
                    capture = True
                    continue
                if capture and p:
                    # 排除中文和非命令字符
                    if not any('\u4e00' <= c <= '\u9fff' for c in p):
                        args.append(p.strip('"\'') )
            break
    
    if not matched_cmd:
        return {"success": False, "output": "", "error": f"未匹配白名单命令: {task[:50]}"}
    
    try:
        cfg = AUTONOMOUS_ACTIONS[matched_cmd]
        full_cmd = cfg["cmd"] + args
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=cfg["timeout"]
        )
        output = stdout.decode(errors="replace")[:500]
        err = stderr.decode(errors="replace")[:200]
        success = proc.returncode == 0
        
        logger.info("[AUTONOMOUS] %s → %s (exit=%d)", " ".join(full_cmd), "OK" if success else "FAIL", proc.returncode)
        return {"success": success, "output": output, "error": err}
    except asyncio.TimeoutError:
        return {"success": False, "output": "", "error": f"超时({cfg['timeout']}s)"}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


# ── 工具函数（供外部调用） ────────────────────────────────────────────────────

def load_memory_context() -> str:
    """加载 MEMORY.md 静态上下文（向后兼容）。"""
    memory_path = Path(
        os.environ.get("MEMORY_FILE", str(MEMORY_DIR / "MEMORY.md"))
    )
    if not memory_path.exists():
        return "（MEMORY.md 不存在）"
    content = memory_path.read_text(encoding="utf-8")
    return content[:1500] + "\n...(已截断)" if len(content) > 1500 else content
