"""
proactive.py — AGI Brain 主动推送生成器
Why: 根据系统状态和目标进度，每30分钟主动推送有价值的信息给用户
What: 读取状态文件 + OP 执行结果，生成中文推送消息
Test: mock 状态文件包含高 CPU 告警，验证返回非空推送消息
"""

import json
import os
from pathlib import Path
from datetime import datetime

STATUS_FILE = os.environ.get("STATUS_FILE", "/tmp/agi-brain-status.json")
OP_STATUS_FILE = os.environ.get("OP_STATUS_FILE", "/tmp/op-status.json")
OP_TASK_RESULTS_FILE = os.environ.get(
    "OP_TASK_RESULTS_FILE", "/tmp/op-task-results.json"
)


def _read_json_file(path: str) -> dict | list:
    """安全读取 JSON 文件。

    Why: 集中处理文件不存在/损坏的边界情况
    What: 读取并解析 JSON，失败返回空字典
    Test: 不存在路径返回 {}，损坏 JSON 返回 {}
    """
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def generate_proactive_message() -> str:
    """生成主动推送消息。

    Why: 让用户不需要主动询问就能获知重要系统事件
    What: 综合分析状态数据和 OP 执行结果，返回中文推送文本（空字符串表示无需推送）
    Test: 注入含 alerts 的状态数据，验证返回包含告警内容的消息
    """
    brain_status = _read_json_file(STATUS_FILE)
    op_status = _read_json_file(OP_STATUS_FILE)
    op_results = _read_json_file(OP_TASK_RESULTS_FILE)

    messages: list[str] = []
    now = datetime.now().strftime("%H:%M")

    # 检查 Brain 告警（过滤 429/限速/超时噪声）
    _NOISE = ("429", "Too Many Requests", "rate limit", "timeout", "timed out", "Connection")
    alerts = brain_status.get("alerts", [])
    real_alerts = [a for a in alerts if not any(n.lower() in a.lower() for n in _NOISE)]
    if real_alerts:
        alert_text = "、".join(real_alerts[:3])
        messages.append(f"⚠️ 系统告警：{alert_text}")

    # 检查 OP 执行结果（兼容 list 和 dict 两种格式）
    if op_results:
        if isinstance(op_results, list):
            # list 格式：每项是 {task, result, status, time}
            completed = [r for r in op_results if r.get("status") == "完成"]
            failed = [r for r in op_results if r.get("status") == "失败"]
        else:
            completed = op_results.get("completed", [])
            failed = op_results.get("failed", [])
        if completed:
            messages.append(f"✅ OP 完成任务：{len(completed)} 项")
        if failed:
            messages.append(f"❌ OP 任务失败：{len(failed)} 项，需要关注")

    # 检查 OP 当前状态
    if op_status.get("status") == "error":
        messages.append(f"🔴 OP 运行异常：{op_status.get('message', '未知错误')}")

    # 定期状态摘要（整点触发）
    current_minute = datetime.now().minute
    if current_minute < 5:  # 每小时整点前5分钟内
        summary = brain_status.get("summary", "")
        if summary:
            messages.append(f"📊 {now} 状态：{summary}")

    if not messages:
        return ""

    return "\n".join(messages)
