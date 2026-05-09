#!/usr/bin/env python3
"""智能维护学习系统 — 从对话历史中自动提取维护模式并生成计划。

Why: NixOS 系统维护操作频繁重复，通过分析 memory 条目频率自动发现模式，
     主动建议创建 skill/timer，减少手动排查和重复劳动。
What: 扫描 memory/ → 提取主题 → 统计频率 → 生成维护建议 → 可选自动执行。
Test: python3 maintenance-learner.py --scan
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── 路径常量 ──────────────────────────────────────────────────
SKILLS_DIR = Path.home() / ".claude" / "skills"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-home-charlie" / "memory"
STATE_FILE = SKILLS_DIR / ".maintenance-state.json"
FEEDBACK_FILE = SKILLS_DIR / ".maintenance-feedback.json"
LOG_FILE = SKILLS_DIR / ".maintenance-learner.log"

# ── LiteLLM 配置（DeepSeek 增强） ─────────────────────────────
LITELLM_URL = "http://localhost:4000/v1/chat/completions"
LITELLM_KEY = "sk-litellm-charlie-2026"
LITELLM_MODEL = "silicon/deepseek-v3.2"
LLM_TIMEOUT = 30

# ── 主题关键词映射 ─────────────────────────────────────────────
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "proxy": ["代理", "xray", "mihomo", "vless", "proxy", "vpn", "clash"],
    "docker": ["docker", "容器", "image", "container", "compose"],
    "nixos": ["nixos", "nix", "flake", "rebuild", "module", "nixpkgs"],
    "disk": ["磁盘", "disk", "空间", "storage", "mergerfs", "zfs", "btrfs"],
    "memory_system": ["记忆", "memory", "letta", "distill", "chromadb"],
    "service": ["服务", "service", "systemd", "timer", "oneshot"],
    "security": ["安全", "security", "ssh", "firewall", "sops", "age"],
    "ai_tools": ["ai", "llm", "ollama", "litellm", "claude", "deepseek", "glm"],
    "browser": ["浏览器", "browser", "floorp", "chrome", "firefox"],
    "network": ["网络", "network", "tailscale", "dns", "wifi"],
    "gpu": ["nvidia", "gpu", "cuda", "驱动", "driver"],
    "backup": ["备份", "backup", "rsync", "borg", "snapshot"],
}

# ── 频率阈值 ────────────────────────────────────────────────────
FREQ_HIGH_THRESHOLD = 3   # 7天内 >=3 → 高频
FREQ_MID_THRESHOLD = 2    # 14天内 >=2 → 中频
FREQ_LOW_THRESHOLD = 1    # 30天内 >=1 → 低频

# ── 反馈权重 ────────────────────────────────────────────────────
FEEDBACK_WEIGHTS = {"accepted": 0.2, "rejected": -0.3, "ignored": -0.1}
FEEDBACK_MIN_WEIGHT = 0.2  # 低于此值降级

# ── 日志配置 ────────────────────────────────────────────────────
logger = logging.getLogger("maintenance-learner")


def setup_logging(verbose: bool = False) -> None:
    """初始化日志，输出到文件 + 可选 stderr。

    Why: 持久化运行日志方便排查问题，verbose 模式方便调试。
    What: 配置 logging 模块，写入 LOG_FILE。
    Test: setup_logging() 后 logger.info() 不报错。
    """
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(fh)

    if verbose:
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)


# ═══════════════════════════════════════════════════════════════
# 数据层：状态文件读写
# ═══════════════════════════════════════════════════════════════

def load_state() -> dict[str, Any]:
    """读取维护状态文件，不存在则返回初始结构。

    Why: 持久化频率追踪和已执行操作，跨会话保持连续性。
    What: 返回 dict 含 topics, suggestions, last_scan 等字段。
    Test: 空状态文件返回 {"topics": {}, "suggestions": [], ...}。
    """
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("状态文件损坏，重新初始化: %s", exc)
    return {
        "topics": {},          # topic → {dates: [...], weight: float}
        "suggestions": [],     # 历史建议
        "created_skills": [],  # 已自动创建的 skill
        "last_scan": None,
    }


def save_state(state: dict[str, Any]) -> None:
    """原子写入状态文件。

    Why: 防止写入中途崩溃导致数据丢失。
    What: 写入临时文件再 rename。
    Test: save_state() 后 load_state() 数据一致。
    """
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(STATE_FILE)


def load_feedback() -> dict[str, list[dict[str, str]]]:
    """读取反馈记录。

    Why: 用户反馈影响主题权重，需要持久化。
    What: 返回 {topic: [{action, date}]}。
    Test: 空文件返回空 dict。
    """
    if FEEDBACK_FILE.exists():
        try:
            return json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_feedback(data: dict[str, list[dict[str, str]]]) -> None:
    """写入反馈文件。"""
    FEEDBACK_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════
# 数据源扫描
# ═══════════════════════════════════════════════════════════════

def scan_memory_files() -> list[dict[str, str]]:
    """扫描 memory/ 下所有 .md 文件，提取带日期的条目。

    Why: memory/ 是用户维护操作的核心记录源。
    What: 返回 [{"date": "YYYY-MM-DD", "content": "...", "file": "..."}]。
    Test: 非空 memory 目录返回非空列表。
    """
    entries: list[dict[str, str]] = []
    date_pattern = re.compile(r"-\s*\[(\d{4}-\d{2}-\d{2})\]")

    if not MEMORY_DIR.exists():
        logger.warning("memory 目录不存在: %s", MEMORY_DIR)
        return entries

    for md_file in sorted(MEMORY_DIR.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("无法读取 %s: %s", md_file.name, exc)
            continue

        for line in text.splitlines():
            m = date_pattern.search(line)
            if m:
                entries.append({
                    "date": m.group(1),
                    "content": line.strip(),
                    "file": md_file.name,
                })

    logger.info("扫描完成: %d 个条目来自 %d 个文件", len(entries), len(list(MEMORY_DIR.glob("*.md"))))
    return entries


def filter_by_window(entries: list[dict[str, str]], days: int) -> list[dict[str, str]]:
    """过滤最近 N 天的条目。

    Why: 滑动窗口统计需要按时间范围筛选。
    What: 返回日期在 [today - days, today] 范围内的条目。
    Test: days=7 只返回一周内的条目。
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [e for e in entries if e["date"] >= cutoff]


# ═══════════════════════════════════════════════════════════════
# 主题提取（双模式）
# ═══════════════════════════════════════════════════════════════

def extract_topics_fast(entries: list[dict[str, str]]) -> dict[str, list[str]]:
    """快速模式：正则 + 关键词映射提取主题。

    Why: 零成本本地分析，适合日常定时运行。
    What: 返回 {topic: [date1, date2, ...]}。
    Test: 包含 "代理" 的条目映射到 "proxy" 主题。
    """
    topic_hits: dict[str, list[str]] = {}

    for entry in entries:
        content_lower = entry["content"].lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                topic_hits.setdefault(topic, []).append(entry["date"])

    return topic_hits


def extract_topics_deep(entries: list[dict[str, str]]) -> dict[str, Any]:
    """增强模式：调用 DeepSeek 分析条目内容和主题。

    Why: 关键词匹配可能遗漏语义相关条目，DeepSeek 能理解上下文。
    What: 返回 {topic: {dates: [...], urgency, suggestion}}。
    Test: 需要 LiteLLM 在线，返回比快速模式更丰富的分析。
    """
    # 先用快速模式获取基础主题
    fast_hits = extract_topics_fast(entries)

    # 取最近 14 天的内容发给 DeepSeek 分析
    recent = filter_by_window(entries, 14)
    if not recent:
        return {t: {"dates": ds, "urgency": "low", "suggestion": ""} for t, ds in fast_hits.items()}

    # 限制 token 数量，最多取 50 条
    sample = recent[:50]
    content_batch = "\n".join(
        f"[{e['date']}] ({e['file']}) {e['content'][:200]}" for e in sample
    )

    prompt = (
        "分析以下系统维护日志条目，返回 JSON 格式分析结果。\n"
        "返回格式：{\"analysis\": [{\"topic\": \"主题名\", "
        "\"urgency\": \"high|medium|low\", "
        "\"suggestion\": \"维护建议（中文）\"}]}\n\n"
        f"条目内容：\n{content_batch}"
    )

    payload = json.dumps({
        "model": LITELLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1000,
    }).encode()

    req = Request(
        LITELLM_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(req, timeout=LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"]["content"]
        # 从可能的 markdown code fence 中提取 JSON
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            result = json.loads(text)

        # 合并 DeepSeek 分析与快速模式结果
        merged: dict[str, Any] = {}
        for item in result.get("analysis", []):
            topic = item.get("topic", "unknown")
            merged[topic] = {
                "dates": fast_hits.get(topic, []),
                "urgency": item.get("urgency", "low"),
                "suggestion": item.get("suggestion", ""),
            }
        # 补充快速模式中未被 DeepSeek 覆盖的主题
        for topic, dates in fast_hits.items():
            if topic not in merged:
                merged[topic] = {"dates": dates, "urgency": "low", "suggestion": ""}

        return merged

    except (HTTPError, URLError, json.JSONDecodeError, KeyError, TimeoutError, OSError) as exc:
        logger.warning("DeepSeek 增强分析失败 (%s)，回退到快速模式", exc)
        return {t: {"dates": ds, "urgency": "low", "suggestion": ""} for t, ds in fast_hits.items()}


# ═══════════════════════════════════════════════════════════════
# 频率追踪
# ═══════════════════════════════════════════════════════════════

def compute_frequency(topic_dates: list[str]) -> dict[str, int]:
    """计算滑动窗口内的主题出现次数。

    Why: 频率决定维护优先级和自动化建议。
    What: 返回 {"d7": n, "d14": n, "d30": n}。
    Test: 指定日期列表返回正确的窗口计数。
    """
    now = datetime.now()
    d7_cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    d14_cutoff = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    d30_cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    return {
        "d7": sum(1 for d in topic_dates if d >= d7_cutoff),
        "d14": sum(1 for d in topic_dates if d >= d14_cutoff),
        "d30": sum(1 for d in topic_dates if d >= d30_cutoff),
    }


def classify_frequency(freq: dict[str, int]) -> str:
    """根据频率阈值分类。

    Why: 频率等级决定建议的 action 类型。
    What: 返回 "high" / "medium" / "low"。
    Test: d7=3 返回 "high"。
    """
    if freq["d7"] >= FREQ_HIGH_THRESHOLD:
        return "high"
    if freq["d14"] >= FREQ_MID_THRESHOLD:
        return "medium"
    if freq["d30"] >= FREQ_LOW_THRESHOLD:
        return "low"
    return "inactive"


# ═══════════════════════════════════════════════════════════════
# Skill 覆盖检查
# ═══════════════════════════════════════════════════════════════

def scan_existing_skills() -> dict[str, dict[str, str]]:
    """扫描现有 skill，提取名称和描述。

    Why: 避免重复创建已覆盖的 skill。
    What: 返回 {slug: {name, description}}。
    Test: proxy-diagnose 存在时返回其信息。
    """
    skills: dict[str, dict[str, str]] = {}
    if not SKILLS_DIR.exists():
        return skills

    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue

        # 提取 name 和 description
        name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        desc_match = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
        if name_match:
            skills[skill_dir.name] = {
                "name": name_match.group(1).strip(),
                "description": desc_match.group(1).strip() if desc_match else "",
            }

    return skills


def find_skill_for_topic(topic: str, skills: dict[str, dict[str, str]]) -> str | None:
    """查找是否已有 skill 覆盖该主题。

    Why: 建议生成需要知道现有覆盖情况。
    What: 返回 skill slug 或 None。
    Test: topic="proxy" 返回 "proxy-diagnose"。
    """
    # 直接匹配 topic 名
    topic_variants = TOPIC_KEYWORDS.get(topic, [topic])
    for slug, info in skills.items():
        name_lower = info["name"].lower()
        desc_lower = info.get("description", "").lower()
        for variant in topic_variants:
            if variant in name_lower or variant in slug.lower():
                return slug
            if variant in desc_lower:
                return slug
    return None


def check_timer_exists(skill_slug: str) -> bool:
    """检查 NixOS timers.nix 中是否有相关 timer。

    Why: 高频主题需要 timer 自动执行，确认是否已配置。
    What: 在 timers.nix 中搜索 skill slug 或其主题关键词。
    Test: docker-cleanup 对应 docker-prune timer 应返回 True。
    """
    timers_file = Path("/etc/nixos/modules/services/timers.nix")
    if not timers_file.exists():
        return False
    try:
        text = timers_file.read_text(encoding="utf-8")
    except OSError:
        return False

    # 直接匹配 skill slug
    if skill_slug in text:
        return True

    # 模糊匹配：从 skill slug 中提取关键词，在 timer 名中搜索
    # 如 docker-cleanup → 搜索 "docker"，能匹配到 docker-prune timer
    slug_parts = skill_slug.replace("-", " ").split()
    for part in slug_parts:
        if len(part) >= 3 and f"{part}" in text.lower():
            return True

    return False


# ═══════════════════════════════════════════════════════════════
# 维护计划生成
# ═══════════════════════════════════════════════════════════════

def generate_suggestions(
    all_entries: list[dict[str, str]],
    topic_data: dict[str, Any],
    use_deep: bool = False,
) -> list[dict[str, Any]]:
    """分析主题频率，生成维护建议。

    Why: 核心逻辑 — 将频率数据转化为可操作建议。
    What: 返回建议列表，每条含 topic/frequency/action/reason。
    Test: 高频无覆盖主题 → action=create_skill_and_timer。
    """
    skills = scan_existing_skills()
    state = load_state()
    feedback = load_feedback()
    suggestions: list[dict[str, Any]] = []

    for topic, data in topic_data.items():
        dates = data.get("dates", data) if isinstance(data, dict) else data
        if isinstance(dates, str):
            continue
        freq = compute_frequency(dates)
        level = classify_frequency(freq)

        if level == "inactive":
            continue

        # 计算反馈权重
        weight = 1.0
        for fb in feedback.get(topic, []):
            weight += FEEDBACK_WEIGHTS.get(fb.get("action", ""), 0.0)

        # 权重低于阈值 → 降级
        if weight < FEEDBACK_MIN_WEIGHT and level != "low":
            level = "low"

        existing_skill = find_skill_for_topic(topic, skills)
        has_timer = check_timer_exists(existing_skill) if existing_skill else False

        # 判断 action
        if existing_skill and has_timer:
            action = "none"
            reason = f"已有 skill + timer 覆盖 ({existing_skill})"
        elif existing_skill and not has_timer and level == "high":
            action = "create_timer"
            reason = f"已有 skill ({existing_skill})，缺少 timer"
        elif not existing_skill and level == "high":
            action = "create_skill_and_timer"
            reason = f"{topic} 7天内出现{freq['d7']}次，无覆盖 skill"
        elif not existing_skill and level == "medium":
            action = "create_skill"
            reason = f"{topic} 14天内出现{freq['d14']}次，建议创建 skill"
        else:
            action = "none"
            reason = "低频关注" if level == "low" else "已覆盖"

        # 建议调度时间
        schedule = None
        if action in ("create_timer", "create_skill_and_timer"):
            schedule = "Mon *-*-* 10:00:00"  # 默认周一上午

        suggestion = {
            "topic": topic,
            "frequency": {"level": level, **freq},
            "weight": round(weight, 2),
            "existing_skill": existing_skill,
            "has_timer": has_timer,
            "action": action,
            "suggested_schedule": schedule,
            "reason": reason,
        }

        # DeepSeek 增强的建议
        if use_deep and isinstance(data, dict) and data.get("suggestion"):
            suggestion["deep_suggestion"] = data["suggestion"]
        if use_deep and isinstance(data, dict) and data.get("urgency"):
            suggestion["deep_urgency"] = data["urgency"]

        suggestions.append(suggestion)

    # 按频率等级排序：high > medium > low
    order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: order.get(s["frequency"]["level"], 3))

    # 更新状态（合并到现有 state，不覆盖 topics）
    state["suggestions"] = suggestions
    state["last_scan"] = datetime.now().isoformat()
    # 确保 topics 键存在
    if "topics" not in state:
        state["topics"] = {}
    if "created_skills" not in state:
        state["created_skills"] = []
    save_state(state)

    return suggestions


# ═══════════════════════════════════════════════════════════════
# 自动执行
# ═══════════════════════════════════════════════════════════════

def auto_execute(suggestions: list[dict[str, Any]]) -> list[dict[str, str]]:
    """对需要创建 skill/timer 的建议执行自动创建。

    Why: 高频主题应自动生成维护 skill，减少手动操作。
    What: 调用 create-skill.py 创建 skill，记录结果。
    Test: action=create_skill_and_timer 的建议被处理后返回成功状态。
    """
    state = load_state()
    results: list[dict[str, str]] = []

    for sug in suggestions:
        if sug["action"] not in ("create_skill", "create_skill_and_timer"):
            continue

        topic = sug["topic"]
        skill_name = f"auto-{topic}-check"

        # 防止重复创建
        if skill_name in state.get("created_skills", []):
            results.append({"topic": topic, "status": "skip", "reason": "已创建"})
            continue

        # 调用 create-skill.py
        create_script = SKILLS_DIR / "create-skill.py"
        if not create_script.exists():
            results.append({"topic": topic, "status": "fail", "reason": "create-skill.py 不存在"})
            continue

        content = (
            f"自动生成的 {topic} 巡检 skill。"
            f"基于最近维护频率分析：{sug['reason']}"
        )
        cmd = [
            sys.executable, str(create_script),
            "--name", skill_name,
            "--content", content,
            "--category", "system",
            "--tags", f"auto,{topic},maintenance",
            "--no-llm",
        ]

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                state.setdefault("created_skills", []).append(skill_name)
                results.append({"topic": topic, "status": "ok", "reason": proc.stdout.strip()})
                logger.info("自动创建 skill: %s", skill_name)
            else:
                results.append({"topic": topic, "status": "fail", "reason": proc.stderr.strip()[:200]})
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            results.append({"topic": topic, "status": "fail", "reason": str(exc)})

    save_state(state)
    return results


# ═══════════════════════════════════════════════════════════════
# 反馈处理
# ═══════════════════════════════════════════════════════════════

def record_feedback(topic: str, action: str) -> None:
    """记录用户对建议的反馈。

    Why: 反馈影响未来建议的权重，避免反复推荐被拒绝的主题。
    What: 追加到 feedback 文件，更新 state 中的 weight。
    Test: 反馈后 load_feedback() 能读取到新记录。
    """
    if action not in FEEDBACK_WEIGHTS:
        print(f"[FAIL] 无效反馈类型: {action}，可选: {list(FEEDBACK_WEIGHTS.keys())}")
        return

    data = load_feedback()
    data.setdefault(topic, []).append({
        "action": action,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    save_feedback(data)
    print(f"[OK] 已记录反馈: {topic} → {action}")


# ═══════════════════════════════════════════════════════════════
# 输出格式化
# ═══════════════════════════════════════════════════════════════

def format_status(state: dict[str, Any], suggestions: list[dict[str, Any]]) -> str:
    """格式化终端输出报告。

    Why: 可读性强的输出方便用户快速决策。
    What: 返回彩色终端格式的分析报告。
    Test: 建议列表非空时输出包含主题行。
    """
    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"\033[1m  智能维护分析报告 ({now})\033[0m",
        "  " + "━" * 50,
        f"  {'主题':<14} {'7天':>4} {'14天':>5} {'30天':>5}   {'状态'}",
    ]

    for sug in suggestions:
        freq = sug["frequency"]
        d7, d14, d30 = freq["d7"], freq["d14"], freq["d30"]
        level = freq["level"]

        if sug["action"] == "none" and sug["existing_skill"]:
            status = f"\033[32m[OK] 已覆盖 ({sug['existing_skill']})\033[0m"
        elif sug["action"] in ("create_skill", "create_skill_and_timer"):
            status = f"\033[33m[建议] {sug['reason']}\033[0m"
        elif level == "medium":
            status = f"\033[36m[观察] 中频关注\033[0m"
        else:
            status = f"\033[90m[低频] 按需检查\033[0m"

        topic_display = sug["topic"][:14]
        lines.append(f"  {topic_display:<14} {d7:>4} {d14:>5} {d30:>5}   {status}")

    # 建议汇总
    actionable = [s for s in suggestions if s["action"] != "none"]
    if actionable:
        lines.append("")
        for s in actionable:
            lines.append(f"  \033[33m💡\033[0m {s['reason']}")

    # 自动执行结果
    if state.get("_auto_results"):
        lines.append("")
        lines.append("  自动执行结果:")
        for r in state["_auto_results"]:
            icon = "\033[32m[OK]\033[0m" if r["status"] == "ok" else f"\033[31m[{r['status'].upper()}]\033[0m"
            lines.append(f"    {icon} {r['topic']}: {r['reason']}")

    return "\n".join(lines)


def format_json(suggestions: list[dict[str, Any]]) -> str:
    """JSON 格式输出，供其他工具解析。"""
    return json.dumps({"suggestions": suggestions}, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════
# 持续运行模式
# ═══════════════════════════════════════════════════════════════

def daemon_loop(interval_min: int = 10) -> None:
    """持续运行模式，定期扫描。

    Why: 配合 systemd service 使用，自动追踪维护模式。
    What: 每 interval_min 分钟执行一次 scan。
    Test: 手动启动后 Ctrl+C 可退出。
    """
    logger.info("守护模式启动，间隔 %d 分钟", interval_min)
    print(f"[OK] 守护模式运行中，每 {interval_min} 分钟扫描一次 (Ctrl+C 退出)")

    while True:
        try:
            entries = scan_memory_files()
            topic_data = extract_topics_fast(entries)
            suggestions = generate_suggestions(entries, topic_data)

            high_count = sum(1 for s in suggestions if s["frequency"]["level"] == "high")
            if high_count > 0:
                logger.info("发现 %d 个高频主题", high_count)

            time.sleep(interval_min * 60)
        except KeyboardInterrupt:
            logger.info("守护模式停止")
            print("\n[OK] 守护模式已停止")
            break
        except Exception as exc:
            logger.error("守护循环异常: %s", exc)
            time.sleep(60)


# ═══════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="智能维护学习系统 — 从 memory 条目自动学习维护模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scan", action="store_true", help="扫描+分析+输出建议")
    parser.add_argument("--deep", action="store_true", help="DeepSeek 增强分析")
    parser.add_argument("--auto", action="store_true", help="扫描+自动执行建议")
    parser.add_argument("--status", action="store_true", help="显示当前状态和频率")
    parser.add_argument("--feedback", nargs=2, metavar=("TOPIC", "ACTION"),
                        help="记录反馈: accepted/rejected/ignored")
    parser.add_argument("--daemon", action="store_true", help="持续运行模式")
    parser.add_argument("--interval", type=int, default=10, help="守护模式间隔（分钟）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志")
    return parser.parse_args()


def main() -> int:
    """入口函数。"""
    args = parse_args()
    setup_logging(args.verbose)

    # 反馈记录（独立操作）
    if args.feedback:
        record_feedback(args.feedback[0], args.feedback[1])
        return 0

    # 显示当前状态（不重新扫描）
    if args.status:
        state = load_state()
        if not state.get("suggestions"):
            print("  无历史建议，请先运行 --scan")
            return 0
        print(format_status(state, state["suggestions"]))
        return 0

    # 守护模式
    if args.daemon:
        daemon_loop(args.interval)
        return 0

    # 扫描模式（--scan / --deep / --auto 共用扫描逻辑）
    if not (args.scan or args.deep or args.auto):
        print("请指定操作: --scan / --deep / --auto / --status / --feedback / --daemon")
        return 1

    # 步骤 1: 扫描数据源
    entries = scan_memory_files()
    if not entries:
        print("[SKIP] 未扫描到任何 memory 条目")
        return 0

    # 步骤 2: 主题提取
    if args.deep:
        topic_data = extract_topics_deep(entries)
    else:
        topic_data = extract_topics_fast(entries)

    if not topic_data:
        print("[OK] 未发现显著主题模式")
        return 0

    # 步骤 3: 更新 state 中的 topic 日期记录
    state = load_state()
    # 确保完整结构
    state.setdefault("topics", {})
    state.setdefault("suggestions", [])
    state.setdefault("created_skills", [])
    for topic, data in topic_data.items():
        dates = data.get("dates", data) if isinstance(data, dict) else data
        if isinstance(dates, list):
            existing = state["topics"].get(topic, {}).get("dates", [])
            merged = list(set(existing + dates))
            merged.sort(reverse=True)
            state["topics"][topic] = {"dates": merged}
    save_state(state)

    # 步骤 4: 生成建议
    suggestions = generate_suggestions(entries, topic_data, use_deep=args.deep)

    # 步骤 5: 可选自动执行
    state = load_state()
    if args.auto:
        results = auto_execute(suggestions)
        state["_auto_results"] = results
        save_state(state)

    # 步骤 6: 输出
    if args.json:
        print(format_json(suggestions))
    else:
        print(format_status(state, suggestions))

    return 0


if __name__ == "__main__":
    sys.exit(main())
