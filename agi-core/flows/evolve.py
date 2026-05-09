"""
evolve.py — L2 自动优化层
读取 metrics.json 节点执行指标，检测低成功率节点，输出优化建议
不自动修改代码，只输出建议到 /tmp/evolve-suggestions.json

Usage:
    cd ~/agi && python3 -m flows.evolve
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

METRICS_PATH = Path.home() / ".local/share/macg/metrics.json"
SUGGESTIONS_PATH = "/tmp/evolve-suggestions.json"
LESSONS_PATH = Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"
SUCCESS_THRESHOLD = 0.60


def load_metrics() -> list[dict]:
    """加载 metrics.json 执行指标。"""
    if not METRICS_PATH.exists():
        return []
    try:
        return json.loads(METRICS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def analyze_nodes(metrics: list[dict]) -> list[dict]:
    """分析各节点成功率，返回低成功率节点建议。"""
    node_stats: dict[str, dict[str, Any]] = {}

    for entry in metrics:
        flow = entry.get("flow_name", "unknown")
        node = entry.get("node_name", "unknown")
        key = f"{flow}/{node}"

        if key not in node_stats:
            node_stats[key] = {
                "total": 0,
                "success": 0,
                "fail": 0,
                "errors": [],
                "flow": flow,
                "node": node,
            }

        node_stats[key]["total"] += 1
        if entry.get("success", False):
            node_stats[key]["success"] += 1
        else:
            node_stats[key]["fail"] += 1
            err = entry.get("error", "")
            if err:
                node_stats[key]["errors"].append(err[:200])

    suggestions = []
    for key, stats in node_stats.items():
        if stats["total"] < 3:
            continue
        rate = stats["success"] / stats["total"]
        if rate < SUCCESS_THRESHOLD:
            suggestions.append(
                {
                    "node": key,
                    "success_rate": round(rate, 3),
                    "total_runs": stats["total"],
                    "fail_count": stats["fail"],
                    "recent_errors": stats["errors"][-3:],
                    "suggestion": _gen_suggestion(stats["node"], stats["errors"]),
                }
            )

    return suggestions


def _gen_suggestion(node: str, errors: list[str]) -> str:
    """根据节点类型生成优化建议。"""
    error_summary = "\n".join(errors[:2]) if errors else "无具体错误"

    hint_map = {
        "DiskFix": "检查磁盘修复命令有效性，考虑增加更精细的清理策略",
        "ServiceFix": "服务频繁重启失败，建议检查依赖关系和启动顺序",
        "ProxyFix": "代理修复失败，建议增加备用节点自动切换逻辑",
        "Classify": "分类准确率低，建议优化分类 prompt 或增加判断条件",
        "Verify": "验证判断不准，建议增加更具体的验证指标阈值",
        "CodeGen": "代码生成质量不足，建议在 prompt 中加入约束和示例",
        "RunTests": "测试执行失败，建议检查测试环境和依赖",
        "ParseIntent": "意图解析不准确，建议优化 prompt 模板",
        "Decompose": "子任务拆分不合理，建议增加拆分约束",
    }

    for pattern, hint in hint_map.items():
        if pattern.lower() in node.lower():
            return hint

    return f"节点 {node} 成功率低。建议: 检查最近错误日志并优化节点逻辑。\n最近错误:\n{error_summary}"


def write_suggestions(suggestions: list[dict]) -> None:
    """写入优化建议。"""
    output = {
        "generated_at": datetime.now().isoformat(),
        "threshold": SUCCESS_THRESHOLD,
        "total_suggestions": len(suggestions),
        "suggestions": suggestions,
    }
    Path(SUGGESTIONS_PATH).write_text(json.dumps(output, ensure_ascii=False, indent=2))


def main():
    """主函数。"""
    print("[evolve] L2 自动优化层")
    metrics = load_metrics()
    print(f"[evolve] 加载 {len(metrics)} 条执行指标")

    if not metrics:
        print("[evolve] 无指标数据，跳过分析")
        write_suggestions([])
        return

    suggestions = analyze_nodes(metrics)

    if not suggestions:
        print("[evolve] 所有节点成功率正常（≥60%）")
        write_suggestions([])
        return

    print(f"[evolve] 发现 {len(suggestions)} 个低成功率节点:")
    for s in suggestions:
        print(
            f"  - {s['node']} — {s['success_rate']:.1%} ({s['fail_count']}/{s['total_runs']} 失败)"
        )
        print(f"    建议: {s['suggestion'][:80]}")

    write_suggestions(suggestions)
    print(f"[evolve] 已写入 {SUGGESTIONS_PATH}")


if __name__ == "__main__":
    main()
