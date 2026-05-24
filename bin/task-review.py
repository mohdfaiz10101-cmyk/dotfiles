#!/run/current-system/sw/bin/python3
"""
Task Review Analyzer — 解析 op-tasks.md，分类任务并输出 JSON 报告。

Why: 自动化识别哪些任务可以转 systemd timer、哪些需要写 SOP、哪些可以归档。
What: 解析任务行 → 计算频率/日期 → 按规则分类 → 写入 task-review.json。
Test: python3 task-review.py，检查 ~/Desktop/巡检报告/task-review.json 生成正确。
"""

import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────────
TASKS_FILE = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
LESSONS_FILE = Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"
OUTPUT_DIR = Path.home() / "Desktop/巡检报告"
OUTPUT_FILE = OUTPUT_DIR / "task-review.json"

# ── 关键词分类 ────────────────────────────────────────────────
AUTOMATABLE_KEYWORDS = ["巡检", "健康", "重启", "backup", "清理", "定时", "监控", "检查", "health", "check", "clean", "backup"]
PROCESSABLE_KEYWORDS = ["部署", "配置", "迁移", "升级", "修复", "deploy", "config", "migrate", "upgrade", "fix"]
PERIODIC_KEYWORDS = ["periodic", "timer", "repeat", "每日", "每周", "定时", "cron"]

# ── 日期解析 ──────────────────────────────────────────────────
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
TASK_PATTERN = re.compile(r"^[-*]\s+\[([ x!])\]\s+(.+)$", re.MULTILINE)
TYPE_TAG_PATTERN = re.compile(r"\[(OP|CC|low|high|mid)\]")


def parse_date(text: str) -> date | None:
    """Why: 从任务文本提取最近日期用于归档判断。"""
    matches = DATE_PATTERN.findall(text)
    if not matches:
        return None
    dates = []
    for m in matches:
        try:
            dates.append(datetime.strptime(m, "%Y-%m-%d").date())
        except ValueError:
            pass
    return max(dates) if dates else None


def has_keywords(text: str, keywords: list[str]) -> list[str]:
    """Why: 检测任务名称是否包含分类关键词。"""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def extract_task_name(raw: str) -> str:
    """Why: 去除类型标签、日期、多余空白，提取干净的任务名。"""
    name = TYPE_TAG_PATTERN.sub("", raw).strip()
    name = DATE_PATTERN.sub("", name).strip()
    # 去除末尾标点
    name = re.sub(r"[：:。，,]+$", "", name).strip()
    return name[:120]  # 限制长度


def parse_tasks(content: str) -> list[dict]:
    """
    Why: 将 markdown checklist 行解析为结构化任务列表。
    What: 提取状态、名称、类型标签、日期。
    Test: 给一段 op-tasks.md 片段，验证返回列表长度和字段正确。
    """
    tasks = []
    for match in TASK_PATTERN.finditer(content):
        status_char = match.group(1)  # ' ', 'x', '!'
        raw_text = match.group(2).strip()

        status = {"x": "done", " ": "pending", "!": "failed"}.get(status_char, "pending")
        type_tags = TYPE_TAG_PATTERN.findall(raw_text)
        task_date = parse_date(raw_text)
        name = extract_task_name(raw_text)

        if not name:
            continue

        tasks.append({
            "name": name,
            "raw": raw_text,
            "status": status,
            "type_tags": type_tags,
            "date": task_date.isoformat() if task_date else None,
        })
    return tasks


def compute_frequency(tasks: list[dict]) -> dict[str, int]:
    """
    Why: 通过关键词匹配计算同类任务出现频率，识别可自动化候选。
    What: 对任务名做关键词归组，返回 {归一化名: 频率} 映射。
    Test: 输入包含3条"服务健康检查"的任务，期望频率≥3。
    """
    # 提取核心词（去停用词后取前4个有意义词）
    stop_words = {"进行", "执行", "处理", "完成", "检查一下", "一下", "一次", "已", "并", "后"}

    def normalize(name: str) -> str:
        words = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", name)
        words = [w for w in words if w not in stop_words]
        return " ".join(words[:4]).lower()

    freq: dict[str, int] = defaultdict(int)
    norm_map: dict[str, str] = {}  # normalized → representative name

    for t in tasks:
        norm = normalize(t["name"])
        if norm:
            freq[norm] += 1
            if norm not in norm_map:
                norm_map[norm] = t["name"]

    # 返回 {representative_name: count}
    return {norm_map[k]: v for k, v in freq.items()}


def classify_tasks(tasks: list[dict], freq_map: dict[str, int]) -> dict:
    """
    Why: 按频率+关键词规则将任务分入四个桶，驱动前端展示和用户决策。
    What: 返回 automatable/processable/archivable/pending 四列表。
    Test: 验证完成≥3次+巡检关键词的任务出现在 automatable 中。
    """
    today = date.today()
    threshold_archive = today - timedelta(days=14)

    automatable: list[dict] = []
    processable: list[dict] = []
    archivable: list[dict] = []
    pending: list[dict] = []

    # 去重：同名任务只保留最新
    seen_names: set[str] = set()
    unique_tasks = []
    for t in reversed(tasks):  # 逆序让最新的先被看到
        if t["name"] not in seen_names:
            seen_names.add(t["name"])
            unique_tasks.append(t)
    unique_tasks.reverse()

    for t in unique_tasks:
        name = t["name"]
        frequency = freq_map.get(name, 1)
        done_date = date.fromisoformat(t["date"]) if t["date"] else None
        auto_kws = has_keywords(name, AUTOMATABLE_KEYWORDS)
        proc_kws = has_keywords(name, PROCESSABLE_KEYWORDS)
        is_periodic = bool(has_keywords(name, PERIODIC_KEYWORDS))

        if t["status"] == "pending" or t["status"] == "failed":
            # 确定优先级
            priority = "high" if t["status"] == "failed" else (
                "high" if "high" in t["type_tags"] else
                "low" if "low" in t["type_tags"] else "normal"
            )
            pending.append({
                "name": name,
                "type": f"[{t['type_tags'][0]}]" if t["type_tags"] else "",
                "priority": priority,
                "date": t["date"],
            })
            continue

        # done 任务分类
        if frequency >= 3 and auto_kws:
            automatable.append({
                "name": name,
                "frequency": frequency,
                "last_done": t["date"],
                "keywords": auto_kws[:3],
                "suggestion": "转为 systemd timer 自动执行",
            })
        elif frequency >= 2 and proc_kws and not auto_kws:
            processable.append({
                "name": name,
                "frequency": frequency,
                "last_done": t["date"],
                "keywords": proc_kws[:3],
                "suggestion": "写 SOP 到 ~/.claude/skills/",
            })
        elif (
            frequency == 1
            and t["status"] == "done"
            and done_date is not None
            and done_date < threshold_archive
            and not is_periodic
        ):
            archivable.append({
                "name": name,
                "frequency": frequency,
                "last_done": t["date"],
                "keywords": [],
            })
        # else: 不足归档条件，暂时忽略（已完成但不满足其他条件）

    return {
        "automatable": automatable,
        "processable": processable,
        "archivable": archivable,
        "pending": pending,
    }


def main() -> None:
    """Why: 入口函数，解析→分类→合并历史→写出。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not TASKS_FILE.exists():
        print(f"[FAIL] 找不到任务文件: {TASKS_FILE}", file=sys.stderr)
        sys.exit(1)

    content = TASKS_FILE.read_text(encoding="utf-8")
    tasks = parse_tasks(content)
    freq_map = compute_frequency(tasks)
    buckets = classify_tasks(tasks, freq_map)

    stats = {
        "total": len(tasks),
        "automatable": len(buckets["automatable"]),
        "processable": len(buckets["processable"]),
        "archivable": len(buckets["archivable"]),
        "pending": len(buckets["pending"]),
    }

    # 读取现有历史
    review_history: list[dict] = []
    feedbacks: list[dict] = []
    if OUTPUT_FILE.exists():
        try:
            existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            review_history = existing.get("review_history", [])
            feedbacks = existing.get("feedbacks", [])
        except (json.JSONDecodeError, KeyError):
            pass

    # 追加本次记录
    review_history.append({
        "date": date.today().isoformat(),
        "stats": stats,
    })
    # 只保留最近 30 条
    review_history = review_history[-30:]

    output = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "stats": stats,
        **buckets,
        "feedbacks": feedbacks,
        "review_history": review_history,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] 写入 {OUTPUT_FILE}")
    print(f"     总任务: {stats['total']} | 可自动化: {stats['automatable']} | "
          f"需流程化: {stats['processable']} | 可归档: {stats['archivable']} | "
          f"待处理: {stats['pending']}")


if __name__ == "__main__":
    main()
