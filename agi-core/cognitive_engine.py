"""
cognitive_engine.py — 八维认知评分器
Why: 量化 AI 系统的认知能力分布，为调度决策提供数据支撑
What: 读取 op-tasks/audit.log/lessons-learned，计算 Ti/Ne/Si/Fe 等维度评分
Test: python3 cognitive_engine.py → 输出 JSON 到 /tmp/cognitive-profile.json
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from datetime import datetime
from pathlib import Path

# ── 路径常量 ────────────────────────────────────────────────────────────────────

OP_TASKS = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
AUDIT_LOG = Path.home() / ".local/share/macg/audit.log"
LESSONS = Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"
OUTPUT = Path("/tmp/cognitive-profile.json")


def _read_file(path: Path) -> str:
    """安全读取文件，不存在返回空字符串。"""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _score_ne(tasks_text: str) -> tuple[int, float, float]:
    """Ne（外倾直觉）: 扩散率 = 待办/总数，burst = 单日新建任务峰值。"""
    lines = tasks_text.strip().splitlines()
    pending = [l for l in lines if re.search(r"^- \[ \]", l)]
    done = [l for l in lines if re.search(r"^- \[x\]", l)]
    total = len(pending) + len(done)

    if total == 0:
        return 50, 0.0, 0.0

    ne_divergence = len(pending) / total  # 越高 = 越发散（新想法多，完成少）
    completion_rate = len(done) / total

    # 单日新建任务峰值（从日期戳统计）
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}")
    all_dates = [date_pattern.search(l) for l in lines]
    all_dates = [m.group(1) for m in all_dates if m]
    date_counts = Counter(all_dates)
    burst = max(date_counts.values()) if date_counts else 0

    # Ne 评分: 高扩散 + 高 burst = 高 Ne
    ne_score = int(min(100, 40 + ne_divergence * 40 + min(burst, 10) * 2))
    return ne_score, ne_divergence, completion_rate


def _score_te(audit_text: str) -> tuple[int, float]:
    """Te（外倾思考）: bash 命令成功率 + 服务操作频率。"""
    if not audit_text:
        return 50, 0.0

    lines = [l for l in audit_text.splitlines() if l.strip()]
    if not lines:
        return 50, 0.0

    success_count = sum(
        1
        for l in lines
        if "[FAIL]" not in l and "[ERR]" not in l and "error" not in l.lower()
    )
    te_execution = success_count / len(lines)

    # systemctl/服务类命令频率
    svc_count = sum(
        1 for l in lines if "systemctl" in l or "docker" in l or "service" in l
    )
    svc_frequency = svc_count / max(len(lines), 1)

    te_score = int(min(100, 30 + te_execution * 50 + svc_frequency * 20))
    return te_score, te_execution


def _score_si(lessons_text: str) -> int:
    """Si（内倾感觉）: 记忆密度 = 经验条目数 + 内容丰富度。"""
    if not lessons_text:
        return 50

    # 统计有效条目数（以 "- [日期]" 开头的行）
    entries = [l for l in lessons_text.splitlines() if re.match(r"^- \[\d{4}", l)]
    entry_count = len(entries)

    # 内容丰富度（平均每条行数）
    entry_blocks = lessons_text.split("\n- [")
    avg_depth = len(lessons_text.splitlines()) / max(len(entry_blocks), 1)

    # 引用率（被其他记忆文件引用的频率，近似用子项行数）
    sub_items = sum(
        1 for l in lessons_text.splitlines() if l.strip().startswith(("  -", "  *"))
    )

    si_score = int(
        min(
            100,
            20 + min(entry_count, 50) * 1.2 + min(avg_depth, 8) * 5 + sub_items * 0.3,
        )
    )
    return si_score


def _score_fe(hour: int) -> int:
    """Fe（外倾情感）: 基于时间的社会交互能力推断。
    深夜(0-5): Fe 降低（休息信号），白天正常。"""
    if 0 <= hour <= 5:
        return int(20 + hour * 8)  # 20-60 区间
    elif 22 <= hour <= 23:
        return 55
    elif 9 <= hour <= 18:
        return 75
    else:
        return 65


def _score_ti(si_score: int, te_score: int) -> int:
    """Ti（内倾思考）: 基于记忆深度(Si)和执行力(Te)的综合内省能力。"""
    return int(min(100, (si_score * 0.5 + te_score * 0.3 + 15)))


def score_cognitive_functions() -> dict:
    """主评分函数：读取数据源，计算八维认知评分，写入 JSON 文件。"""
    now = datetime.now()
    hour = now.hour

    tasks_text = _read_file(OP_TASKS)
    audit_text = _read_file(AUDIT_LOG)
    lessons_text = _read_file(LESSONS)

    ne_score, ne_divergence, completion_rate = _score_ne(tasks_text)
    te_score, te_execution = _score_te(audit_text)
    si_score = _score_si(lessons_text)
    fe_score = _score_fe(hour)
    ti_score = _score_ti(si_score, te_score)

    # 时间影响因子
    time_factor = "深夜" if 0 <= hour <= 5 else "白天"

    result = {
        "Ti": ti_score,
        "Ne": ne_score,
        "Si": si_score,
        "Te": te_score,
        "Fe": fe_score,
        "ne_divergence": round(ne_divergence, 3),
        "completion_rate": round(completion_rate, 3),
        "te_execution": round(te_execution, 3),
        "time_factor": time_factor,
        "hour": hour,
        "last_updated": now.isoformat(),
    }

    # 写入输出文件
    try:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        pass  # /tmp 不可写时静默失败

    return result


def reflect_and_recommend() -> dict:
    """读取 agi-feedback-bus，输出调度建议（闭环反思层）"""
    bus_file = Path("/tmp/agi-feedback-bus.json")
    if not bus_file.exists():
        return {}
    try:
        bus = json.loads(bus_file.read_text())
    except Exception:
        return {}

    recommendations = []
    task_rates = bus.get("task_success_rate", {})
    op = bus.get("op_tasks", {})
    crashes = bus.get("crashes", [])
    health = bus.get("service_health", {})

    # 分析任务成功率
    for tag, rate in task_rates.items():
        if rate < 0.5:
            recommendations.append({
                "type": "task_strategy",
                "source": tag,
                "action": "reduce_frequency",
                "reason": f"{tag}→OP 成功率 {rate:.0%}，建议降低频率或改变策略",
            })

    # 积压过多
    pending = op.get("pending", 0)
    if pending > 10:
        recommendations.append({
            "type": "backlog_alert",
            "action": "prioritize",
            "reason": f"待处理任务积压 {pending} 条，建议优先处理高优先级",
        })

    # 崩溃记录
    if len(crashes) > 3:
        recommendations.append({
            "type": "stability",
            "action": "investigate_crashes",
            "reason": f"近期崩溃事件 {len(crashes)} 次，建议检查相关服务",
        })

    # 服务健康
    unhealthy = [s for s, r in health.items() if r not in ("success", "unknown")]
    if unhealthy:
        recommendations.append({
            "type": "service_health",
            "action": "restart",
            "targets": unhealthy,
            "reason": f"服务异常: {', '.join(unhealthy)}",
        })

    result = {
        "timestamp": datetime.now().isoformat(),
        "recommendations": recommendations,
        "summary": f"成功率分析完成，{len(recommendations)} 条建议",
        "op_completion_rate": op.get("completion_rate", 0),
        "pending_tasks": pending,
        "crash_count": len(crashes),
    }

    # 写入反思输出
    reflect_out = Path("/tmp/agi-reflect.json")
    reflect_out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    profile = score_cognitive_functions()
    reflect = reflect_and_recommend()
    merged = {**profile, "reflection": reflect}
    print(json.dumps(merged, ensure_ascii=False, indent=2))
