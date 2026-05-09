"""
task_decompose.py — 任务分解器工作流
LangGraph StateGraph: ParseIntent(GLM) → Decompose(GLM) → FanOut(Send并行) → Aggregate → Verify
动态并行执行子任务，每个子任务是 ReAct agent

Usage:
    cd ~/agi && python3 -m flows.task_decompose "安装并配置 nginx"
"""

import json
import sys
from typing import Annotated, Any, Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Send
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from safe_tools import bash_safe

FLOW_NAME = "task_decompose"

GLM = ChatOpenAI(
    model="glm-5-turbo",
    base_url="http://localhost:4000/v1",
    api_key="sk-litellm-charlie-2026",
    max_tokens=2000,
)


class TaskState(TypedDict):
    """任务分解工作流全局状态。"""

    user_input: str
    intent: str
    subtasks: list[dict]
    results: list[dict]
    summary: str
    verified: bool


class SubtaskState(TypedDict):
    """单个子任务执行状态。"""

    subtask: dict
    result: str


# ── ParseIntent ─────────────────────────────────────────────────────────────


def node_parse_intent(state: TaskState) -> dict:
    """用 GLM 分析用户意图，提取核心目标。"""
    user_input = state.get("user_input", "")
    resp = GLM.invoke(
        [
            SystemMessage(
                content="分析用户意图，用一句话概括核心目标。只输出概括，不要解释。"
            ),
            HumanMessage(content=user_input),
        ]
    )
    return {"intent": resp.content.strip()}


# ── Decompose ───────────────────────────────────────────────────────────────


def node_decompose(state: TaskState) -> dict:
    """用 GLM 将任务拆分为子任务列表。"""
    intent = state.get("intent", "")
    resp = GLM.invoke(
        [
            SystemMessage(
                content="""将任务拆分为子任务列表。输出严格 JSON 格式：
```json
[{"id": 1, "type": "bash|info", "priority": "high|medium|low", "description": "具体描述"}]
```
只输出 JSON，不要其他文字。"""
            ),
            HumanMessage(content=intent),
        ]
    )

    # 解析 JSON（处理 markdown 包裹）
    text = resp.content.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        subtasks = json.loads(text)
    except json.JSONDecodeError:
        subtasks = [
            {"id": 1, "type": "bash", "priority": "medium", "description": intent}
        ]

    return {"subtasks": subtasks, "results": []}


# ── FanOut 子任务执行 ───────────────────────────────────────────────────────


def node_execute_subtask(state: SubtaskState) -> dict:
    """执行单个子任务（ReAct: GLM + bash_safe）。"""
    subtask = state.get("subtask", {})
    desc = subtask.get("description", "")
    task_type = subtask.get("type", "bash")

    if task_type == "info":
        # 纯信息任务，不需要执行
        return {"result": f"[INFO] {desc}"}

    # 用 GLM 决定执行什么命令
    resp = GLM.invoke(
        [
            SystemMessage(
                content="根据任务描述，输出需要执行的 shell 命令。只输出命令，不要解释。"
            ),
            HumanMessage(content=desc),
        ]
    )

    cmd = resp.content.strip().split("\n")[0].strip().strip("`")
    if not cmd:
        return {"result": f"[SKIP] 无法解析命令: {desc}"}

    output = bash_safe(
        cmd, timeout=60, flow=FLOW_NAME, node=f"subtask_{subtask.get('id', '?')}"
    )

    # 如果失败，尝试让 GLM 修复一次
    if "[FAIL]" in output or "[超时" in output:
        fix_resp = GLM.invoke(
            [
                SystemMessage(content="命令执行失败，请给出修复命令。只输出命令。"),
                HumanMessage(content=f"原命令: {cmd}\n错误: {output}"),
            ]
        )
        fix_cmd = fix_resp.content.strip().split("\n")[0].strip().strip("`")
        if fix_cmd:
            output = bash_safe(
                fix_cmd,
                timeout=60,
                flow=FLOW_NAME,
                node=f"subtask_{subtask.get('id', '?')}_fix",
            )

    return {"result": f"[子任务{subtask.get('id', '?')}] {desc}\n{output}"}


# ── Aggregate ────────────────────────────────────────────────────────────────


def node_aggregate(state: TaskState) -> dict:
    """收集子任务结果。"""
    results = state.get("results", [])
    summary_parts = [r.get("result", "") for r in results if r.get("result")]
    return {"summary": "\n---\n".join(summary_parts)}


# ── Verify ──────────────────────────────────────────────────────────────────


def node_verify(state: TaskState) -> dict:
    """验证整体任务完成度。"""
    subtasks = state.get("subtasks", [])
    results = state.get("results", [])
    summary = state.get("summary", "")

    resp = GLM.invoke(
        [
            SystemMessage(
                content="根据任务执行结果，判断任务是否完成。回复：完成 或 未完成（原因）。"
            ),
            HumanMessage(
                content=f"原始任务: {state.get('intent', '')}\n\n执行结果:\n{summary}"
            ),
        ]
    )

    verified = "完成" in resp.content
    return {"verified": verified}


# ── 路由函数 ────────────────────────────────────────────────────────────────


def route_decompose(state: TaskState) -> list[Send]:
    """从 Decompose 结果生成 Send() 并行任务。"""
    subtasks = state.get("subtasks", [])
    if not subtasks:
        return [
            Send(
                "execute_subtask",
                {"subtask": {"id": 0, "type": "info", "description": "空任务"}},
            )
        ]
    return [Send("execute_subtask", {"subtask": st}) for st in subtasks]


def route_verify(state: TaskState) -> str:
    return END


# ── 构建图 ─────────────────────────────────────────────────────────────────


def build_graph():
    """构建任务分解 StateGraph。"""
    graph = StateGraph(TaskState)

    graph.add_node("parse_intent", node_parse_intent)
    graph.add_node("decompose", node_decompose)
    graph.add_node("execute_subtask", node_execute_subtask)
    graph.add_node("aggregate", node_aggregate)
    graph.add_node("verify", node_verify)

    graph.add_edge(START, "parse_intent")
    graph.add_edge("parse_intent", "decompose")
    graph.add_conditional_edges("decompose", route_decompose, ["execute_subtask"])
    graph.add_edge("execute_subtask", "aggregate")
    graph.add_edge("aggregate", "verify")
    graph.add_edge("verify", END)

    return graph.compile()


# ── 结果收集（需要在子任务节点后聚合）─────────────────────────────────────
# LangGraph Send 子图返回后需要手动合并
# 使用 reducer 来收集子任务结果


# 重写 State 以支持 results 的 reducer
class TaskStateV2(TypedDict):
    user_input: str
    intent: str
    subtasks: list[dict]
    results: Annotated[list[dict], lambda old, new: old + new if old else new]
    summary: str
    verified: bool


def build_graph_v2():
    """构建任务分解 StateGraph（带 reducer 收集子任务结果）。"""
    graph = StateGraph(TaskStateV2)

    graph.add_node("parse_intent", node_parse_intent)
    graph.add_node("decompose", node_decompose)
    graph.add_node("execute_subtask", node_execute_subtask)
    graph.add_node("aggregate", node_aggregate)
    graph.add_node("verify", node_verify)

    graph.add_edge(START, "parse_intent")
    graph.add_edge("parse_intent", "decompose")
    graph.add_conditional_edges("decompose", route_decompose, ["execute_subtask"])
    graph.add_edge("execute_subtask", "aggregate")
    graph.add_edge("aggregate", "verify")
    graph.add_edge("verify", END)

    return graph.compile()


if __name__ == "__main__":
    import sys as _sys

    task = " ".join(_sys.argv[1:]) if len(_sys.argv) > 1 else "检查系统磁盘和服务状态"
    app = build_graph_v2()
    result = app.invoke({"user_input": task})
    print(f"意图: {result.get('intent', '')}")
    print(f"子任务数: {len(result.get('subtasks', []))}")
    print(f"验证: {'通过' if result.get('verified') else '未通过'}")
    print(f"\n--- 执行结果 ---\n{result.get('summary', '')}")
