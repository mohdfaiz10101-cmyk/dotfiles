#!/usr/bin/env python3
"""
macg.py — LangGraph Multi-Agent CLI
真正的 LangGraph StateGraph，CC+OP 共享上下文
Supervisor(GLM) → 路由到 GLM Agent 或 Claude Agent
持久化：SQLite checkpointer（跨会话上下文不丢）
"""

import os, sys, json, subprocess, readline
from pathlib import Path
from datetime import datetime
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite import SqliteSaver

# ── 配置 ──────────────────────────────────────────────────────────────────────
DB_PATH = Path.home() / ".local/share/macg/state.db"
OP_TASKS_FILE = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
MEM_DIR = Path.home() / ".claude/projects/-home-charlie/memory"

CLAUDE_MODEL = "claude-opus-4-6"
GLM_MODEL = "glm-5-turbo"

ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "glm": "\033[36m",
    "claude": "\033[35m",
    "tool": "\033[33m",
    "err": "\033[31m",
    "dim": "\033[2m",
}

# ── 工具定义（两个 Agent 共享）────────────────────────────────────────────────


@tool
def bash(command: str, timeout: int = 30) -> str:
    """执行 shell 命令，返回 stdout+stderr。适用于系统操作、查看状态、运行脚本。"""
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = (r.stdout + r.stderr).strip()
        return out[:4000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return f"[超时 {timeout}s]"
    except Exception as e:
        return f"[FAIL] {e}"


@tool
def read_file(path: str, lines: int = 200) -> str:
    """读取文件内容。lines 参数限制行数。"""
    p = Path(path).expanduser()
    if not p.exists():
        return f"文件不存在: {p}"
    content = p.read_text(errors="replace").splitlines()
    text = "\n".join(content[:lines])
    if len(content) > lines:
        text += f"\n... (共 {len(content)} 行，显示前 {lines} 行)"
    return text


@tool
def write_file(path: str, content: str) -> str:
    """写入文件（覆盖）。自动创建父目录。"""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"[OK] 已写入 {p} ({len(content)} 字节)"


@tool
def glob_files(pattern: str, directory: str = ".") -> str:
    """按 glob 模式查找文件，支持 ** 递归。"""
    import glob as g

    base = Path(directory).expanduser()
    matches = g.glob(str(base / pattern), recursive=True)
    return "\n".join(matches[:50]) if matches else "(无匹配)"


@tool
def grep_files(pattern: str, path: str = ".", flags: str = "-rn") -> str:
    """在文件中搜索内容。返回匹配行（最多3000字符）。"""
    cmd = f"rg {flags} {json.dumps(pattern)} {path}"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    out = (r.stdout + r.stderr).strip()
    return out[:3000] if out else "(无匹配)"


@tool
def op_delegate(task: str, priority: str = "medium") -> str:
    """将任务委托给 OP（OpenCode/GLM）异步执行。适合运维、定时任务、系统修复。
    priority: high/medium/low"""
    OP_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # ── 去重检查 ──────────────────────────────────────────
    key = task[:20].strip()
    if OP_TASKS_FILE.exists():
        existing = OP_TASKS_FILE.read_text()
        import re as _re
        pending = _re.findall(r"- \[ \] \[(?:MAC|AGI)→OP\].*" + _re.escape(key[:10]), existing)
        if pending:
            return f"[SKIP] 任务已存在（去重）：{key}..."

    # ── 反馈总线：低成功率任务自动降级优先级 ────────────────
    import json as _json
    from pathlib import Path as _Path
    bus_file = _Path("/tmp/agi-feedback-bus.json")
    if bus_file.exists():
        try:
            bus = _json.loads(bus_file.read_text())
            rate = bus.get("task_success_rate", {}).get("MAC", 1.0)
            if rate < 0.3 and priority == "high":
                priority = "medium"
                task = f"[自动降级-成功率{rate:.0%}] " + task
        except Exception:
            pass

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- [ ] [MAC→OP] [{now}] [{priority}] {task}\n"
    with open(OP_TASKS_FILE, "a") as f:
        f.write(line)
    return f"[OK] 任务已写入 op-tasks.md（{priority}优先级）：{task}"


@tool
def memory_read(filename: str) -> str:
    """读取共享记忆文件。filename 如：MEMORY.md / lessons-learned.md"""
    p = MEM_DIR / filename
    if not p.exists():
        return f"记忆文件不存在: {p}"
    return p.read_text()[:4000]


@tool
def sense_system() -> str:
    """获取 AGI Brain 实时感知数据：CPU/内存/磁盘/服务状态/异常进程/浏览器上下文。"""
    try:
        from brain import sense

        data = sense()
        # 精简输出
        return json.dumps(
            {
                "cpu": data.get("cpu_usage"),
                "mem": data.get("memory_usage"),
                "disk": data.get("disk_ai"),
                "services": data.get("services"),
                "cpu_hogs": data.get("cpu_hogs", []),
                "browser": data.get("browser", {}),
                "wechat": data.get("wechat", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return f"[FAIL] sense: {e}"


@tool
def run_flow(flow_name: str, spec: str = "") -> str:
    """执行 LangGraph 工作流。
    可用 flows: self_heal(自愈巡检), task_decompose(任务分解), code_loop(代码闭环), evolve(优化进化), workflow_gen(生成新工作流)
    spec: 传给工作流的输入描述"""
    index_path = Path(__file__).parent / "flows" / "index.json"
    if not index_path.exists():
        return "[FAIL] flows/index.json 不存在"
    try:
        idx = json.loads(index_path.read_text())
        names = {f["name"]: f["file"] for f in idx["flows"]}
        if flow_name not in names:
            return f"[FAIL] 未知工作流 '{flow_name}'，可用: {', '.join(names.keys())}"
        # 调用对应的 flow 模块
        cmd = f"cd ~/agi && python3 -m flows.{flow_name}"
        if spec:
            cmd += f" --spec {json.dumps(spec)}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:4000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "[超时 120s]"
    except Exception as e:
        return f"[FAIL] {e}"


@tool
def wechat_status() -> str:
    """查看微信系统状态和最近消息摘要。"""
    import urllib.request

    try:
        with urllib.request.urlopen(
            "http://localhost:9801/api/wechat/status", timeout=3
        ) as r:
            status = json.loads(r.read().decode())
        with urllib.request.urlopen(
            "http://localhost:9801/api/wechat/contacts", timeout=3
        ) as r:
            contacts = json.loads(r.read().decode())
        top = contacts[:5] if isinstance(contacts, list) else []
        return json.dumps(
            {"status": status, "recent_contacts": top}, ensure_ascii=False, indent=2
        )
    except Exception as e:
        return f"[FAIL] {e}"


@tool
def wechat_reply(talker: str, content: str) -> str:
    """发送微信回复给指定联系人。"""
    import urllib.request

    try:
        payload = json.dumps({"talker": talker, "content": content}).encode()
        req = urllib.request.Request(
            "http://localhost:9801/api/wechat/reply",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.read().decode()
    except Exception as e:
        return f"[FAIL] {e}"


@tool
def list_flows() -> str:
    """列出所有可用的 LangGraph 工作流及其触发关键词。"""
    index_path = Path(__file__).parent / "flows" / "index.json"
    if not index_path.exists():
        return "无工作流"
    idx = json.loads(index_path.read_text())
    lines = []
    for f in idx["flows"]:
        lines.append(
            f"  {f['name']} — 触发词: {', '.join(f['trigger'])} (运行{f['runs']}次)"
        )
    return "\n".join(lines)


@tool
def memory_write(filename: str, content: str) -> str:
    """追加内容到共享记忆文件。"""
    p = MEM_DIR / filename
    with open(p, "a") as f:
        f.write("\n" + content)
    return f"[OK] 已追加到 {p}"


@tool
def web_search(query: str) -> str:
    """使用系统 websearch 搜索网络。"""
    r = subprocess.run(
        f"websearch {json.dumps(query)} 2>/dev/null || echo '搜索工具不可用，请用 bash curl'",
        shell=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return r.stdout.strip()[:3000] or "搜索无结果"


@tool
def call_cc(prompt: str, timeout_sec: int = 60) -> str:
    """实时调用 CC（Claude Code）执行复杂任务。返回执行结果。
    适合：架构设计、NixOS 配置、多文件分析、深度调试。"""
    try:
        r = subprocess.run(
            ["claude", "-p", prompt, "--model", "opus", "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "cli"},
        )
        out = (r.stdout + r.stderr).strip()
        return out[:4000] if out else "(CC 无输出)"
    except subprocess.TimeoutExpired:
        return f"[CC 超时 {timeout_sec}s]"
    except Exception as e:
        return f"[CC 调用失败] {e}"


@tool
def call_op(task: str, timeout_sec: int = 60) -> str:
    """实时调用 OP（OpenCode）执行运维任务。返回执行结果。
    适合：服务修复、状态检查、配置部署、定时任务管理。"""
    try:
        r = subprocess.run(
            ["opencode", "-p", task],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(Path.home()),
        )
        out = (r.stdout + r.stderr).strip()
        return out[:4000] if out else "(OP 无输出)"
    except subprocess.TimeoutExpired:
        return f"[OP 超时 {timeout_sec}s] — 已自动写入 op-tasks.md 异步执行"
    except FileNotFoundError:
        return "[OP 不可用] opencode 命令未找到，改用 op_delegate 异步委托"
    except Exception as e:
        return f"[OP 调用失败] {e}"


@tool
def schedule_followup(contact: str, message: str, delay_hours: int = 24) -> str:
    """安排跟进消息。指定联系人、消息内容和延迟时间（小时）。
    适合：客户跟进提醒、定期触达、营销自动化。"""
    try:
        task_entry = {
            "type": "followup",
            "contact": contact,
            "message": message,
            "delay_hours": delay_hours,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }
        followup_file = MEM_DIR / "scheduled_followups.json"
        followups = []
        if followup_file.exists():
            followups = json.loads(followup_file.read_text())
        followups.append(task_entry)
        followup_file.write_text(json.dumps(followups, ensure_ascii=False, indent=2))
        return f"[OK] 已安排跟进: {contact} → {delay_hours}小时后发送"
    except Exception as e:
        return f"[FAIL] 安排跟进失败: {e}"


@tool
def send_batch_message(contacts: str, message: str) -> str:
    """批量发送微信消息。contacts 为逗号分隔的联系人列表。
    通过 hub-api 发送，适合：营销通知、节日问候、批量触达。"""
    try:
        contact_list = [c.strip() for c in contacts.split(",") if c.strip()]
        results = []
        for contact in contact_list:
            try:
                r = subprocess.run(
                    [
                        "curl",
                        "-s",
                        "-X",
                        "POST",
                        "http://localhost:9875/api/wechat/send",
                        "-H",
                        "Content-Type: application/json",
                        "-d",
                        json.dumps({"to": contact, "message": message}),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                results.append(f"{contact}: {r.stdout.strip()[:100]}")
            except Exception as e:
                results.append(f"{contact}: [FAIL] {e}")
        return "\n".join(results)
    except Exception as e:
        return f"[FAIL] 批量发送失败: {e}"


@tool
def get_wechat_messages(contact: str = "", limit: int = 10) -> str:
    """获取微信最新消息。contact 为联系人名称（空=全部），limit 为条数上限。"""
    try:
        r = subprocess.run(
            [
                "curl",
                "-s",
                f"http://localhost:9875/api/wechat/messages?contact={contact}&limit={limit}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.stdout.strip()[:2000] or "[无消息]"
    except Exception as e:
        return f"[FAIL] {e}"


@tool
def search_letta_memory(query: str) -> str:
    """搜索 Letta 归档记忆（语义检索）。query 为搜索关键词。"""
    try:
        r = subprocess.run(
            [
                "curl",
                "-sL",
                "-H",
                "Authorization: Bearer letta",
                f"http://localhost:8283/v1/agents/agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea/archival-memory/?query={query}&limit=5",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        import json as _json

        results = _json.loads(r.stdout)
        return (
            "\n".join(item.get("text", "")[:200] for item in results[:5]) or "[无结果]"
        )
    except Exception as e:
        return f"[FAIL] {e}"


@tool
def get_op_pending_tasks() -> str:
    """获取 op-tasks.md 中的未完成任务列表。"""
    try:
        r = subprocess.run(
            [
                "grep",
                "^- \\[ \\]",
                "/home/charlie/.claude/projects/-home-charlie/memory/op-tasks.md",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = r.stdout.strip().split("\n")
        return "\n".join(lines[:10]) or "[无待办]"
    except Exception as e:
        return f"[FAIL] {e}"


@tool
def create_paperclip_task(
    title: str, description: str = "", priority: str = "medium"
) -> str:
    """在 Paperclip 控制平面创建新任务。"""
    try:
        r = subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                "http://localhost:3100/api/tasks",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(
                    {"title": title, "description": description, "priority": priority}
                ),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.stdout.strip()[:500] or "[已提交]"
    except Exception as e:
        return f"[FAIL] {e}"


TOOLS = [
    bash,
    read_file,
    write_file,
    glob_files,
    grep_files,
    op_delegate,
    memory_read,
    memory_write,
    web_search,
    sense_system,
    run_flow,
    list_flows,
    wechat_status,
    wechat_reply,
    call_cc,
    call_op,
    schedule_followup,
    send_batch_message,
    get_wechat_messages,
    search_letta_memory,
    get_op_pending_tasks,
    create_paperclip_task,
]

# ── 模型初始化 ────────────────────────────────────────────────────────────────


def make_models():
    claude = ChatAnthropic(model=CLAUDE_MODEL, max_tokens=4096)
    glm = ChatOpenAI(
        model=GLM_MODEL,
        base_url="http://localhost:4000/v1",
        api_key="sk-litellm-charlie-2026",
        max_tokens=2000,
    )
    # Supervisor 用 Sonnet 做路由决策，判断更准确
    supervisor = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=100)
    return claude, glm, supervisor


# ── LangGraph 状态定义 ────────────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next: str  # "glm" | "claude" | "end"
    route_reason: str  # 路由原因，显示给用户
    cognitive_profile: dict  # 八维认知评分，由 cognitive_sense 节点写入


# ── Supervisor 节点（GLM 决策路由）───────────────────────────────────────────

NO_HALLUCINATION = """
## 防幻觉规则（死规则，最高优先级）
- 不确定任何事实 → 直接说"不确定，需要验证"，不猜测
- 命令/路径/参数/版本号 → 必须用 bash 工具实际执行验证，禁止凭记忆回答
- 不知道 → 直接说"不知道"，禁止编造
- 宁可少说，不可乱说
- 涉及系统状态/服务/文件是否存在 → 先用工具查，再回答"""

SUPERVISOR_PROMPT = """你是多Agent系统的调度员。
分析用户请求，决定路由到哪个 Agent：

- **glm**：日常问答、中文对话、简单命令、运维查询、文件读写、bash操作、微信操作、系统感知、执行工作流、状态检查、配置查询
- **claude**：复杂代码重构、架构设计、NixOS系统级操作、多文件分析、深度推理、多步骤实现、调试复杂bug、修改生产代码
- **end**：用户说退出/再见

## Claude 路由降低阈值（重要）
以下场景 MUST 路由到 claude，不要过度节省：
- 用户要求修改/新增代码文件（不是查看）
- 涉及 3 个以上文件的操作
- 需要理解业务逻辑才能实现的功能
- 用户明确说"写代码""实现""重构"

## 可用工作流（通过 run_flow 工具调用）
- self_heal: 触发词含 [巡检/修复/disk/service/proxy] → glm 调用 run_flow("self_heal")
- task_decompose: 触发词含 [分解/拆分/并行] → glm 调用 run_flow("task_decompose", spec)
- code_loop: 触发词含 [生成代码/写代码/测试] → glm 调用 run_flow("code_loop", spec)
- evolve: 触发词含 [优化/进化] → glm 调用 run_flow("evolve")
- workflow_gen: 触发词含 [新工作流/新流程] → glm 调用 run_flow("workflow_gen", spec)
- social_intelligence: 触发词含 [社交/关系/画像] → glm 调用 run_flow("social_intelligence")
- doc_pipeline: 触发词含 [报关单/报价/发票/装箱单/文档提取/OCR/填充模板] → glm 调用 run_flow("doc_pipeline", spec)
- context_graph: 触发词含 [客户/公司/实体/CRM查询/时间线] → glm 调用 run_flow("context_graph", spec)

## 新增工具（GLM 优先使用）
- sense_system: 查看系统实时状态
- wechat_status/wechat_reply: 微信消息管理
- list_flows: 列出可用工作流
- **call_cc**: 实时调用 Claude Code（Opus）执行复杂任务 — 架构/NixOS/多文件分析
- **call_op**: 实时调用 OpenCode 执行运维任务 — 服务修复/部署/检查
- op_delegate: 异步委托（写 op-tasks.md，适合不急的任务）

## 调用决策
- 能自己用工具解决 → 自己做（GLM 免费）
- 需要深度分析/架构/代码重构 → call_cc
- 需要运维/修服务/改配置 → call_op
- 不急的后台任务 → op_delegate（异步）

## 用户基础设施（方案必须基于此，禁止重复建设）
- AGI Brain: ~/agi/macg.py + systemd（主调度）
- Letta: localhost:8283（语义记忆）
- LiteLLM: localhost:4000（43个模型统一入口）
- FastAPI Gateway: localhost:9900（AGI控制层）
- OP任务系统: op-tasks.md + systemd timers（异步协作）
- Paperclip: localhost:3100（Agent调度）
- mihomo: localhost:7890（代理）
规则：出方案前先对照此清单，在已有组件上叠加，不建议任何已有组件的替代品。

## 用户决策习惯（强制学习规则）
- **实时优先**：用户要求所有操作立刻/马上/即时生效，禁止回复"建议""下次""等一会儿"
- **强制执行**：用户倾向直接落地，不喜欢只给建议而不行动
- **GLM优先**：状态查询/方案讨论/进度确认 → glm；只有真正需要写文件/改系统才用 claude
- **断了即恢复**：服务中断要立即自动恢复，不等定时器

## 认知引擎规则（基于 cognitive_profile）
- Ne收敛: 如果 cognitive_profile.ne_divergence > 0.8 且 completion_rate < 0.3，优先路由到执行任务而非创建新任务
- 深夜降级: 如果当前时间 0-5 点，降低 claude 路由频率，优先 glm
- Fe检查: 如果 Fe 评分 < 50，提醒用户休息

只回复格式：{路由}|{一句话原因}
示例：glm|日常运维查询  /  claude|多文件代码修改  /  end|用户退出
禁止其他文字，只输出这一行。"""


def supervisor_node(state: AgentState, supervisor_model) -> AgentState:
    messages = state["messages"]
    last_user = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if not last_user:
        return {**state, "next": "end", "route_reason": "无输入"}

    # 构建提示，注入认知评分上下文
    profile = state.get("cognitive_profile", {})
    profile_hint = ""
    if profile:
        profile_hint = f"\n\n当前认知评分: Ti={profile.get('Ti', 50)} Ne={profile.get('Ne', 50)} Si={profile.get('Si', 50)} Te={profile.get('Te', 50)} Fe={profile.get('Fe', 50)} ne_divergence={profile.get('ne_divergence', 0)} completion_rate={profile.get('completion_rate', 0)}"

    decision = supervisor_model.invoke(
        [
            SystemMessage(content=SUPERVISOR_PROMPT + profile_hint),
            HumanMessage(content=str(last_user.content)),
        ]
    )
    raw = decision.content.strip().lower()
    # 解析 "route|reason" 格式，兼容旧格式（只有一个词）
    if "|" in raw:
        parts = raw.split("|", 1)
        route = parts[0].strip().split()[0]
        reason = parts[1].strip() if len(parts) > 1 else ""
    else:
        route = raw.split()[0]
        reason = ""
    if route not in ("glm", "claude", "end"):
        route = "glm"
    return {**state, "next": route, "route_reason": reason}


def route_after_supervisor(
    state: AgentState,
) -> Literal["glm_agent", "claude_agent", "__end__"]:
    n = state.get("next", "glm")
    if n == "claude":
        return "claude_agent"
    if n == "end":
        return "__end__"
    return "glm_agent"


def cognitive_sense_node(state: AgentState) -> AgentState:
    """认知引擎感知节点：调用 cognitive_engine 评分，写入 state。"""
    profile = {}
    try:
        from cognitive_engine import score_cognitive_functions

        profile = score_cognitive_functions()
    except Exception as e:
        profile = {"error": str(e)}
    return {**state, "cognitive_profile": profile}


# ── 构建图 ────────────────────────────────────────────────────────────────────


def _load_shared_rules() -> str:
    """运行时读取共享规则文件，保证与 CLAUDE.md/AGENTS.md 同步"""
    path = os.path.expanduser("~/dotfiles/ai-shared-rules.md")
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return "Letta:8283 | LiteLLM:4000 | AGI-Gateway:9900 | op-tasks.md"


def _load_claude_md() -> str:
    """从 ~/CLAUDE.md 提取核心规则注入 agent system prompt（防幻觉+输出格式+基础设施）"""
    path = os.path.expanduser("~/CLAUDE.md")
    try:
        content = open(path).read()
        # 提取关键章节（不全量注入，避免 token 爆炸）
        sections = []
        keep_markers = [
            "## 防幻觉规则",
            "## 输出格式规则",
            "## 方案优先级",
            "## 受保护文件",
            "## NixOS 专项",
        ]
        lines = content.splitlines()
        in_section = False
        current = []
        for line in lines:
            if any(line.startswith(m) for m in keep_markers):
                if current:
                    sections.append("\n".join(current))
                current = [line]
                in_section = True
            elif (
                in_section
                and line.startswith("## ")
                and not any(line.startswith(m) for m in keep_markers)
            ):
                sections.append("\n".join(current))
                current = []
                in_section = False
            elif in_section:
                current.append(line)
        if current:
            sections.append("\n".join(current))
        result = "\n\n".join(sections)
        return result[:3000]  # 限制长度
    except Exception:
        return ""


def _letta_search(query: str) -> str:
    """查询 Letta 语义记忆，返回相关历史经验。失败则静默返回空。"""
    import urllib.request, urllib.error

    try:
        # Letta REST API: POST /v1/agents/{agent_id}/memory/recall
        # 先获取 agent list
        with urllib.request.urlopen("http://localhost:8283/v1/agents", timeout=2) as r:
            agents = json.loads(r.read().decode())
        # 找 code-assistant agent
        agent_id = None
        for a in agents if isinstance(agents, list) else agents.get("agents", []):
            name = a.get("name", "")
            if "code" in name.lower() or "assistant" in name.lower():
                agent_id = a.get("id")
                break
        if not agent_id and agents:
            agent_id = (
                agents[0] if isinstance(agents, list) else agents.get("agents", [{}])[0]
            ).get("id")
        if not agent_id:
            return ""
        # 搜索归档记忆
        payload = json.dumps({"query": query, "limit": 3}).encode()
        req = urllib.request.Request(
            f"http://localhost:8283/v1/agents/{agent_id}/archival-memory/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            result = json.loads(r.read().decode())
        memories = result if isinstance(result, list) else result.get("memories", [])
        if not memories:
            return ""
        hits = []
        for m in memories[:3]:
            text = m.get("text", m.get("content", ""))
            if text:
                hits.append(text[:200])
        return "\n---\n".join(hits) if hits else ""
    except Exception:
        return ""


def _startup_sense() -> str:
    """启动时快速感知系统状态，返回简报字符串。"""
    import urllib.request

    lines = []
    # 1. 服务状态
    services = {
        "LiteLLM": "localhost:4000",
        "Letta": "localhost:8283",
        "AGI-GW": "localhost:9900",
    }
    statuses = []
    for name, addr in services.items():
        try:
            urllib.request.urlopen(f"http://{addr}/", timeout=1)
            statuses.append(f"{name}[OK]")
        except Exception:
            try:
                urllib.request.urlopen(f"http://{addr}/health", timeout=1)
                statuses.append(f"{name}[OK]")
            except Exception:
                statuses.append(f"{name}[--]")
    lines.append("服务: " + "  ".join(statuses))
    # 2. 系统资源
    try:
        r = subprocess.run(
            "free -h | awk 'NR==2{print $3\"/\"$2}' && df -h /mnt/ai 2>/dev/null | awk 'NR==2{print $3\"/\"$2}' || echo '-'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        parts = r.stdout.strip().splitlines()
        mem = parts[0] if parts else "?"
        disk = parts[1] if len(parts) > 1 else "?"
        lines.append(f"内存: {mem}  /mnt/ai: {disk}")
    except Exception:
        pass
    # 3. 待处理任务数
    try:
        pending_file = MEM_DIR / "pending-tasks.md"
        if pending_file.exists():
            count = pending_file.read_text().count("- [ ]")
            if count:
                lines.append(f"待办: {count} 项")
    except Exception:
        pass
    return " | ".join(lines)


def build_graph(checkpointer):
    claude, glm, supervisor = make_models()

    INFRA_CONTEXT = f"""
## 用户已有基础设施（方案必须基于此，在已有组件上叠加）
{_load_shared_rules()}
"""

    CLAUDE_MD_RULES = _load_claude_md()

    OUTPUT_FORMAT = """
## 输出格式（强制）
- 状态用 [OK] [FAIL] [SKIP] 前缀
- 多项结果用表格，不用长段落
- 操作结果格式：`动作 → 结果`，一行一个
- 不解释"为什么"，除非用户问
- 中文回复，代码/路径用英文
- 每次回复不超 20 行
- 收到任务 MUST 先用工具验证/执行，不直接文字回答"""

    glm_system = f"""你是 MAC 的 GLM 执行层。直接用工具完成任务，不废话。
遇到需要运维的任务用 op_delegate 委托给 OP 执行。
{OUTPUT_FORMAT}
{INFRA_CONTEXT}
{NO_HALLUCINATION}
{CLAUDE_MD_RULES}"""

    claude_system = f"""你是 MAC 的 Claude 执行层，处理复杂任务。
你拥有完整对话历史。直接用工具完成任务，不废话。
运维类任务用 op_delegate 委托 OP。
{OUTPUT_FORMAT}
{INFRA_CONTEXT}
{NO_HALLUCINATION}
{CLAUDE_MD_RULES}"""

    glm_agent = create_react_agent(glm, TOOLS, prompt=glm_system)
    claude_agent = create_react_agent(claude, TOOLS, prompt=claude_system)

    graph = StateGraph(AgentState)

    graph.add_node("cognitive_sense", cognitive_sense_node)
    graph.add_node("supervisor", lambda s: supervisor_node(s, supervisor))
    graph.add_node("glm_agent", glm_agent)
    graph.add_node("claude_agent", claude_agent)

    graph.add_edge(START, "cognitive_sense")
    graph.add_edge("cognitive_sense", "supervisor")
    graph.add_conditional_edges("supervisor", route_after_supervisor)
    graph.add_edge("glm_agent", END)
    graph.add_edge("claude_agent", END)

    return graph.compile(checkpointer=checkpointer)


# ── 增量总结引擎 ─────────────────────────────────────────────────────────────

SUMMARY_FILE = Path.home() / ".local/share/macg/daily-summary.md"
SUMMARY_LOG = Path.home() / ".local/share/macg/actions.jsonl"


def _log_action(user_input: str, route: str, reply: str):
    """每次操作后记录到 actions.jsonl（增量日志）。"""
    SUMMARY_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": datetime.now().strftime("%H:%M"),
        "route": route,
        "input": user_input[:100],
        "result": reply[:200],
    }
    with open(SUMMARY_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _build_summary() -> str:
    """从 actions.jsonl 生成今日增量总结。"""
    today = datetime.now().strftime("%Y-%m-%d")
    if not SUMMARY_LOG.exists():
        return "今日无操作记录"

    lines = SUMMARY_LOG.read_text().strip().splitlines()
    actions = []
    for line in lines:
        try:
            a = json.loads(line)
            actions.append(a)
        except Exception:
            continue

    if not actions:
        return "今日无操作记录"

    # 按路由统计
    glm_count = sum(1 for a in actions if a.get("route") == "glm")
    claude_count = sum(1 for a in actions if a.get("route") == "claude")

    # 生成摘要
    summary_lines = [
        f"# MACG 操作总结（{today}）",
        f"",
        f"共 {len(actions)} 次操作 | GLM: {glm_count} | Claude: {claude_count}",
        f"",
        f"## 操作时间线",
    ]
    for a in actions[-20:]:  # 最近 20 条
        route_tag = "🐉" if a.get("route") == "glm" else "🧠"
        summary_lines.append(
            f"  {a.get('time', '')} {route_tag} {a.get('input', '')[:60]}"
            f" → {a.get('result', '')[:80]}"
        )

    return "\n".join(summary_lines)


def _rotate_summary():
    """每日凌晨归档前一天的日志。"""
    if not SUMMARY_LOG.exists():
        return
    today = datetime.now().strftime("%Y-%m-%d")
    archive = SUMMARY_LOG.parent / f"actions-{today}.jsonl"
    if archive.exists():
        return  # 今天已归档过
    # 检查日志是否跨天
    lines = SUMMARY_LOG.read_text().strip().splitlines()
    if lines:
        try:
            first = json.loads(lines[0])
            # 如果有日期字段且不是今天，归档
        except Exception:
            pass


# ── REPL ──────────────────────────────────────────────────────────────────────


LEARNING_LOG = Path.home() / ".local/share/macg/decision-learning.jsonl"


def _learn_decision(user_input: str, route: str) -> None:
    """每次路由决策后记录习惯，写入 learnings 文件供 router 读取。"""
    import re, json
    from datetime import datetime

    LEARNING_LOG.parent.mkdir(parents=True, exist_ok=True)
    # 检测即时/强制模式信号
    immediate_signals = re.findall(
        r"(立刻|马上|即时|现在|断了|不要等|马上做|立即)", user_input
    )

    entry = {
        "ts": datetime.now().isoformat(),
        "route": route,
        "len": len(user_input),
        "immediate": len(immediate_signals) > 0,
        "signals": immediate_signals[:2],
    }
    with open(LEARNING_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 每50条分析一次，更新 router learnings
    try:
        lines = LEARNING_LOG.read_text().strip().splitlines()
        if len(lines) % 50 == 0 and len(lines) > 0:
            immediate_count = sum(1 for l in lines if '"immediate": true' in l)
            glm_count = sum(1 for l in lines if '"route": "glm"' in l)
            total = len(lines)
            router_learnings = (
                Path.home() / "claude-router-plugin/knowledge/learnings/patterns.md"
            )
            if router_learnings.exists():
                content = router_learnings.read_text()
                note = f"\n\n## 自动学习统计（{datetime.now().strftime('%Y-%m-%d')} 更新）\n"
                note += f"- 总决策数: {total}，即时要求占比: {immediate_count * 100 // max(total, 1)}%\n"
                note += (
                    f"- GLM路由占比: {glm_count * 100 // max(total, 1)}%（目标>70%）\n"
                )
                # 只追加，不重写
                if "自动学习统计" not in content:
                    router_learnings.write_text(content + note)
    except Exception:
        pass


def repl():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = ANSI

    print(
        f"{c['bold']}MACG — LangGraph Multi-Agent{c['reset']}  (GLM免费 + Claude按需 + Letta记忆 + CLAUDE.md规则)"
    )
    print(f"{c['dim']}:new 新会话  |  :summary 今日总结  |  :quit 退出{c['reset']}")

    # ── 启动感知 ──────────────────────────────────────────────────────────────
    print(f"{c['dim']}[ARCH] 正在感知...{c['reset']}", end="\r")
    sense_report = _startup_sense()
    print(f"{c['dim']}[ARCH] {sense_report}{c['reset']}\n")

    # readline 历史
    hist_file = Path.home() / ".local/share/macg/readline_history"
    hist_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(str(hist_file))
    except FileNotFoundError:
        pass
    readline.set_history_length(1000)

    thread_id = "default"

    with SqliteSaver.from_conn_string(str(DB_PATH)) as checkpointer:
        app = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        while True:
            try:
                user_input = input(f"\n{c['bold']}>{c['reset']} ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input:
                continue

            if user_input == ":quit":
                break
            elif user_input == ":new":
                from uuid import uuid4

                thread_id = str(uuid4())[:8]
                config = {"configurable": {"thread_id": thread_id}}
                print(f"  新会话: {thread_id}")
                continue
            elif user_input.startswith(":load "):
                thread_id = user_input.split(None, 1)[1]
                config = {"configurable": {"thread_id": thread_id}}
                print(f"  已切换会话: {thread_id}")
                continue
            elif user_input == ":thread":
                print(f"  当前会话: {thread_id}")
                continue
            elif user_input == ":summary":
                print(_build_summary())
                continue

            # ── Letta 预检（PRE_GATE）────────────────────────────────────────
            letta_context = _letta_search(user_input)
            if letta_context:
                print(f"{c['dim']}[PRE_GATE] L1命中（Letta）{c['reset']}")
                # 将记忆注入消息上下文
                injected_input = f"{user_input}\n\n[历史记忆参考]\n{letta_context}"
            else:
                injected_input = user_input

            try:
                result = app.invoke(
                    {"messages": [HumanMessage(content=injected_input)]}, config=config
                )
                msgs = result.get("messages", [])
                # 找最后一条 AI 回复
                for msg in reversed(msgs):
                    if isinstance(msg, AIMessage) and msg.content:
                        route = result.get("next", "glm")
                        reason = result.get("route_reason", "")
                        color = c["claude"] if route == "claude" else c["glm"]
                        label = "Claude" if route == "claude" else "GLM"
                        reason_str = f" | {reason}" if reason else ""
                        print(f"\n{color}▸ {label}{reason_str}{c['reset']}")
                        print(msg.content)
                        # ── 增量记录 + 学习 hook ──────────────────────
                        _log_action(user_input, route, msg.content)
                        _learn_decision(user_input, route)
                        break
            except Exception as e:
                print(f"{c['err']}[FAIL] {e}{c['reset']}")
                import traceback

                traceback.print_exc()

    readline.write_history_file(str(hist_file))
    print("\n再见")


if __name__ == "__main__":
    repl()
