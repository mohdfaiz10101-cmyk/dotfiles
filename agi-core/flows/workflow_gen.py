"""
workflow_gen.py — L3 工作流生成器
监听 flows/requests/ 目录，读取用户需求 → GLM 生成 LangGraph 图代码
安全检查通过 → 写入 flows/auto_{name}.py 并注册 index.json

Usage:
    cd ~/agi && python3 -m flows.workflow_gen
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).parent.parent))

from safe_tools import bash_safe, check_generated_code

FLOW_NAME = "workflow_gen"
REQUESTS_DIR = Path(__file__).parent / "requests"
FLOWS_DIR = Path(__file__).parent
INDEX_PATH = FLOWS_DIR / "index.json"
LESSONS_PATH = Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"

GLM = ChatOpenAI(
    model="glm-5-turbo",
    base_url="http://localhost:4000/v1",
    api_key="sk-litellm-charlie-2026",
    max_tokens=4000,
)


def load_index() -> dict:
    """加载 index.json。"""
    if not INDEX_PATH.exists():
        return {"flows": [], "last_updated": datetime.now().strftime("%Y-%m-%d")}
    try:
        return json.loads(INDEX_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"flows": [], "last_updated": datetime.now().strftime("%Y-%m-%d")}


def save_index(index: dict) -> None:
    """保存 index.json。"""
    index["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2))


def register_flow(name: str, filename: str, triggers: list[str]) -> None:
    """注册新工作流到 index.json。"""
    index = load_index()
    # 检查是否已存在
    existing = [f for f in index["flows"] if f["name"] == name]
    if existing:
        existing[0]["file"] = filename
        existing[0]["trigger"] = triggers
        existing[0]["created"] = datetime.now().strftime("%Y-%m-%d")
    else:
        index["flows"].append(
            {
                "name": name,
                "file": filename,
                "trigger": triggers,
                "created": datetime.now().strftime("%Y-%m-%d"),
                "success_rate": 0.0,
                "runs": 0,
            }
        )
    save_index(index)


def generate_workflow(name: str, description: str) -> tuple[bool, str, str]:
    """用 GLM 生成 LangGraph 工作流代码。
    返回 (success, filepath_or_reason, code)。
    """
    prompt = f"""生成一个 LangGraph 工作流 Python 文件。

要求:
1. 文件名: auto_{name}.py
2. 使用 langgraph.graph.StateGraph 构建图
3. 包含 docstring 和 if __name__ == "__main__" 入口
4. 所有 bash 执行必须用: from safe_tools import bash_safe
5. 模型配置: ChatOpenAI(model="glm-5-turbo", base_url="http://localhost:4000/v1", api_key="sk-litellm-charlie-2026")
6. 不要使用危险命令（rm -rf, systemctl stop 等）
7. 只输出 Python 代码，不要解释

工作流需求: {description}

参考现有工作流结构:
- StateGraph 状态定义（TypedDict）
- 节点函数（每个节点一个函数）
- 条件路由（conditional_edges）
- 编译图（compile）
"""

    resp = GLM.invoke(
        [
            SystemMessage(
                content="你是一个 LangGraph 工作流代码生成器。只输出 Python 代码。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    code = resp.content.strip()
    if code.startswith("```python"):
        code = code[len("```python") :].rstrip("```").strip()
    elif code.startswith("```"):
        code = code[3:].rstrip("```").strip()

    # 写入临时文件进行安全检查
    tmp_path = FLOWS_DIR / f"auto_{name}.py"
    tmp_path.write_text(code)

    # 安全检查
    is_safe, reason = check_generated_code(str(tmp_path))
    if not is_safe:
        tmp_path.unlink(missing_ok=True)
        return False, reason, code

    # 语法检查
    syntax_result = bash_safe(
        f"python3 -m py_compile {tmp_path}",
        timeout=10,
        flow=FLOW_NAME,
        node="SyntaxCheck",
    )
    if "[FAIL]" in syntax_result or "Error" in syntax_result:
        tmp_path.unlink(missing_ok=True)
        return False, f"语法错误: {syntax_result[:200]}", code

    return True, str(tmp_path), code


def log_failure_to_lessons(name: str, description: str, reason: str) -> None:
    """生成失败记录到 lessons-learned.md。"""
    try:
        LESSONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = f"\n- [{datetime.now().strftime('%Y-%m-%d')}] [GLM] workflow_gen生成失败: auto_{name} | 原因: {reason[:200]}\n  需求: {description[:100]}\n"
        with open(LESSONS_PATH, "a") as f:
            f.write(entry)
    except Exception:
        pass


def process_request(request_path: Path) -> None:
    """处理单个请求文件。"""
    print(f"[workflow_gen] 处理请求: {request_path.name}")

    try:
        data = json.loads(request_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[workflow_gen] 请求文件格式错误: {e}")
        return

    name = data.get("name", "unnamed")
    description = data.get("description", "")
    triggers = data.get("triggers", [])

    # 清理文件名（只保留字母数字下划线）
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()

    if not description:
        print(f"[workflow_gen] 缺少 description，跳过")
        return

    print(f"[workflow_gen] 生成工作流: auto_{name}.py")
    success, result, code = generate_workflow(name, description)

    if success:
        register_flow(f"auto_{name}", f"auto_{name}.py", triggers)
        print(f"[workflow_gen] [OK] 已生成并注册: auto_{name}.py")

        # 重命名 processed
        processed_dir = REQUESTS_DIR / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        request_path.rename(processed_dir / request_path.name)
    else:
        print(f"[workflow_gen] [FAIL] 生成失败: {result[:200]}")
        log_failure_to_lessons(name, description, result)

        # 重命名 failed
        failed_dir = REQUESTS_DIR / "failed"
        failed_dir.mkdir(parents=True, exist_ok=True)
        request_path.rename(failed_dir / request_path.name)


def main():
    """主循环：监听 requests/ 目录。"""
    print(f"[workflow_gen] L3 工作流生成器启动")
    print(f"[workflow_gen] 监听目录: {REQUESTS_DIR}")
    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)

    # 检查初始请求
    request_files = sorted(REQUESTS_DIR.glob("request_*.json"))
    for rf in request_files:
        process_request(rf)

    if not request_files:
        print("[workflow_gen] 无待处理请求，退出（单次模式）")


if __name__ == "__main__":
    main()
