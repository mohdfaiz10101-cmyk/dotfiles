"""
code_loop.py — 代码变更闭环工作流
LangGraph StateGraph: Spec → CodeGen(GLM) → RunTests(bash) → FixLoop(最多3次) → Deploy(op_delegate)

Usage:
    cd ~/agi && python3 -m flows.code_loop --spec "创建一个读取JSON配置文件的Python函数"
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).parent.parent))

from safe_tools import bash_safe
from macg import op_delegate

FLOW_NAME = "code_loop"
MAX_FIX_ATTEMPTS = 3

GLM = ChatOpenAI(
    model="glm-5-turbo",
    base_url="http://localhost:4000/v1",
    api_key="sk-litellm-charlie-2026",
    max_tokens=4000,
)


class CodeState(TypedDict):
    """代码变更闭环状态。"""

    spec: str
    code: str
    test_code: str
    test_result: str
    error_log: str
    fix_count: int
    output_file: str
    success: bool
    report: str


# ── Spec ────────────────────────────────────────────────────────────────────


def node_spec(state: CodeState) -> dict:
    """解析规格描述，生成代码生成 prompt。"""
    spec = state.get("spec", "")
    output_dir = Path.home() / "agi" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(output_dir / "latest_output.py")
    return {"spec": spec, "fix_count": 0, "success": False, "output_file": output_file}


# ── CodeGen ─────────────────────────────────────────────────────────────────


def node_codegen(state: CodeState) -> dict:
    """用 GLM 生成代码。"""
    spec = state.get("spec", "")
    error_log = state.get("error_log", "")
    fix_count = state.get("fix_count", 0)

    prompt = f"任务: {spec}\n"
    if error_log and fix_count > 0:
        prompt += f"\n上次生成代码运行出错（第{fix_count}次修复）:\n{error_log}\n\n请修复错误后重新生成完整代码。"

    prompt += """
要求:
1. 输出完整的 Python 代码（可独立运行）
2. 包含 if __name__ == '__main__' 测试入口
3. 代码简洁，有中文注释
4. 只输出代码，不要其他文字"""

    resp = GLM.invoke(
        [
            SystemMessage(
                content="你是一个 Python 代码生成专家。只输出代码，不要 markdown 包裹。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    code = resp.content.strip()
    # 去除可能的 markdown 包裹
    if code.startswith("```python"):
        code = code[len("```python") :].rstrip("```").strip()
    elif code.startswith("```"):
        code = code[3:].rstrip("```").strip()

    return {"code": code}


# ── RunTests ────────────────────────────────────────────────────────────────


def node_run_tests(state: CodeState) -> dict:
    """执行生成的代码进行测试。"""
    code = state.get("code", "")
    if not code:
        return {
            "test_result": "[FAIL] 无代码可执行",
            "error_log": "无代码",
            "success": False,
        }

    # 写入临时文件执行
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = bash_safe(
            f"python3 {tmp_path}", timeout=30, flow=FLOW_NAME, node="RunTests"
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    success = "[FAIL]" not in result and "[超时" not in result
    error_log = result if not success else ""
    test_result = result

    # 如果成功，写入输出文件
    if success:
        output_file = state.get("output_file", "")
        if output_file:
            Path(output_file).write_text(code)

    return {"test_result": test_result, "error_log": error_log, "success": success}


# ── FixLoop 路由 ────────────────────────────────────────────────────────────


def route_after_test(state: CodeState) -> str:
    """测试通过则部署，否则重试。"""
    if state.get("success", False):
        return "deploy"
    if state.get("fix_count", 0) >= MAX_FIX_ATTEMPTS:
        return "fail"
    return "codegen"


def node_increment_fix(state: CodeState) -> dict:
    """递增修复计数。"""
    return {"fix_count": state.get("fix_count", 0) + 1}


# ── Deploy ──────────────────────────────────────────────────────────────────


def node_deploy(state: CodeState) -> dict:
    """部署成功代码，用 op_delegate 委托后续工作。"""
    output_file = state.get("output_file", "")
    spec = state.get("spec", "")
    report = f"[代码闭环] 生成成功\n规格: {spec}\n输出: {output_file}\n修复次数: {state.get('fix_count', 0)}"

    # 委托 OP 做后续工作（如果有需要）
    try:
        op_delegate(f"代码已生成: {output_file}，请验证", priority="medium")
    except Exception:
        pass

    return {"report": report, "success": True}


# ── Fail ────────────────────────────────────────────────────────────────────


def node_fail(state: CodeState) -> dict:
    """超过最大修复次数，记录教训。"""
    spec = state.get("spec", "")
    error = state.get("error_log", "")[:500]
    report = f"[代码闭环] 生成失败\n规格: {spec}\n原因: 超过{MAX_FIX_ATTEMPTS}次修复仍未通过\n最后错误: {error}"

    # 写入 lessons-learned.md
    try:
        lessons_path = (
            Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"
        )
        lessons_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lessons_path, "a") as f:
            f.write(
                f"\n- [2026-04-18] [GLM] code_loop失败: {spec[:100]} | 错误: {error[:200]}\n"
            )
    except Exception:
        pass

    return {"report": report, "success": False}


# ── 构建图 ─────────────────────────────────────────────────────────────────


def build_graph():
    """构建代码变更闭环 StateGraph。"""
    graph = StateGraph(CodeState)

    graph.add_node("spec", node_spec)
    graph.add_node("codegen", node_codegen)
    graph.add_node("run_tests", node_run_tests)
    graph.add_node("increment_fix", node_increment_fix)
    graph.add_node("deploy", node_deploy)
    graph.add_node("fail", node_fail)

    graph.add_edge(START, "spec")
    graph.add_edge("spec", "codegen")
    graph.add_edge("codegen", "run_tests")
    graph.add_conditional_edges(
        "run_tests",
        route_after_test,
        {"deploy": "deploy", "codegen": "increment_fix", "fail": "fail"},
    )
    graph.add_edge("increment_fix", "codegen")
    graph.add_edge("deploy", END)
    graph.add_edge("fail", END)

    return graph.compile()


if __name__ == "__main__":
    spec = "--spec"
    task = ""
    args = sys.argv[1:]
    if spec in args:
        idx = args.index(spec)
        task = " ".join(args[idx + 1 :]) if idx + 1 < len(args) else ""
    elif args:
        task = " ".join(args)

    if not task:
        task = "写一个读取 JSON 配置文件并打印键值的函数"

    app = build_graph()
    result = app.invoke({"spec": task})
    print(result.get("report", "无报告"))
    if result.get("success"):
        print(f"\n输出文件: {result.get('output_file', '')}")
