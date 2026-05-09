#!/usr/bin/env python3
"""Skill Watcher — 自动监控 memory/ 目录变更，发现新知识后生成 Skill 候选

运行模式：
  1. 单次扫描：python3 skill-watcher.py --scan
  2. 持续守护：python3 skill-watcher.py --daemon（每 10 分钟扫描一次）

Why: 将 memory/ 中积累的经验知识自动转化为可复用的 Skill，减少人工维护。
What: 扫描 md 文件变更 → 提取条目 → 去重 → 写入候选队列 → 可选自动创建。
Test: python3 skill-watcher.py --scan，assert 无报错且 .watcher-state.json 更新。
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Paths ──────────────────────────────────────────────────────────────────

SKILLS_DIR = Path.home() / ".claude" / "skills"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-home-charlie" / "memory"
STATE_FILE = SKILLS_DIR / ".watcher-state.json"
PENDING_FILE = SKILLS_DIR / ".pending-skills.json"
LOG_FILE = SKILLS_DIR / ".watcher.log"
CREATE_SKILL = SKILLS_DIR / "create-skill.py"

# Category mapping by source filename
CATEGORY_MAP: dict[str, str] = {
    "lessons-learned.md": "troubleshooting",
    "troubleshooting.md": "troubleshooting",
    "nixos-config.md": "configuration",
    "ai-tools.md": "tools",
    "ideas-roadmap.md": "planning",
    "codebase-map.md": "architecture",
    "setup-plan.md": "setup",
    "pending-tasks.md": "tasks",
    "MEMORY.md": "reference",
}

# Topic keywords for intent/subject extraction
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "proxy": ["代理", "xray", "mihomo", "vless", "proxy", "vpn", "clash"],
    "docker": ["docker", "容器", "image", "container", "compose"],
    "nixos": ["nixos", "nix", "flake", "rebuild", "module", "configuration.nix"],
    "disk": ["磁盘", "disk", "空间", "storage", "mergerfs", "snapraid", "ntfs"],
    "memory_system": ["记忆", "memory", "letta", "distill", "lessons-learned"],
    "service": ["服务", "service", "systemd", "timer", "daemon"],
    "security": ["安全", "security", "ssh", "firewall", "sops", "age", "credential"],
    "ai_tools": ["ai", "llm", "ollama", "litellm", "claude", "deepseek", "glm"],
    "browser": ["浏览器", "browser", "floorp", "chrome", "zen"],
    "network": ["网络", "network", "tailscale", "dns", "wifi", "ethernet"],
}

MAX_PENDING = 20
SCAN_INTERVAL_SECONDS = 600  # 10 minutes


# ── State persistence ──────────────────────────────────────────────────────

def load_state() -> dict[str, Any]:
    """Load watcher state (last scan timestamp per file).

    Why: Tracks which files have been scanned to avoid reprocessing.
    What: Returns dict with file mtimes and last_scan timestamp.
    Test: Fresh state returns {"last_scan": "", "files": {}}.
    """
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_scan": "", "files": {}}


def save_state(state: dict[str, Any]) -> None:
    """Persist watcher state to disk.

    Why: Ensures scan progress survives restarts.
    What: Atomically writes JSON state file.
    Test: save then load returns identical dict.
    """
    try:
        STATE_FILE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        log(f"[WARN] Cannot save state: {exc}")


# ── Pending queue ──────────────────────────────────────────────────────────

def load_pending() -> list[dict[str, Any]]:
    """Load pending skill candidates.

    Why: Persists candidates between scans for batch review.
    What: Returns list of candidate dicts, sorted by detected_at.
    Test: Empty file returns [].
    """
    if PENDING_FILE.exists():
        try:
            data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_pending(pending: list[dict[str, Any]]) -> None:
    """Save pending candidates, enforcing max size.

    Why: Prevents unbounded growth of candidate queue.
    What: Trims oldest entries beyond MAX_PENDING, writes JSON.
    Test: Insert 25 items, assert only 20 remain after save.
    """
    # Trim to MAX_PENDING, oldest first
    if len(pending) > MAX_PENDING:
        pending.sort(key=lambda x: x.get("detected_at", ""))
        pending = pending[-MAX_PENDING:]
    try:
        PENDING_FILE.write_text(
            json.dumps(pending, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        log(f"[WARN] Cannot save pending: {exc}")


# ── Logging ────────────────────────────────────────────────────────────────

def log(message: str) -> None:
    """Append timestamped message to watcher log.

    Why: Enables post-hoc debugging without console output noise.
    What: Writes ISO timestamp + message to .watcher.log.
    Test: Call log("test"), assert LOG_FILE contains "test".
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {message}\n"
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass  # Non-critical


# ── Knowledge extraction ───────────────────────────────────────────────────

def extract_entries(file_path: Path) -> list[str]:
    """Extract dated entries from a markdown file.

    Why: Parses the standard `- [date]` format used across all memory files.
    What: Returns list of raw entry strings (full block until next entry).
    Test: File with 3 dated entries returns list of length 3.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return []

    # Match entries starting with `- [YYYY-MM-DD]`
    pattern = re.compile(r"^- \[\d{4}-\d{2}-\d{2}\]", re.MULTILINE)
    entries: list[str] = []

    matches = list(pattern.finditer(text))
    for i, match in enumerate(matches):
        start = match.start()
        # Entry extends to next match or end of file
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        entry = text[start:end].strip()
        if len(entry) >= 20:  # Skip trivially short entries
            entries.append(entry)

    return entries


def content_hash(text: str) -> str:
    """Generate short hash for deduplication.

    Why: Fast content fingerprinting without storing full text.
    What: Returns first 12 chars of SHA-256 hex digest.
    Test: Same text always returns same hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# ── Topic extraction ──────────────────────────────────────────────────────

def extract_topics(text: str) -> list[str]:
    """Extract topic tags from entry text via keyword matching.

    Why: Enables maintenance-learner to detect trending subjects across memory files.
    What: Returns list of matching topic keys, or ["general"] if none match.
    Test: Text containing "docker" and "compose" returns ["docker"].
    """
    text_lower = text.lower()
    topics: list[str] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            topics.append(topic)
    return topics or ["general"]


def update_topic_frequency(topics: list[str], date: str) -> None:
    """Update shared topic frequency state for maintenance-learner.

    Why: Provides cross-session topic statistics without coupling to learner internals.
    What: Increments count per topic, updates first_seen/last_seen dates.
    Test: Call twice with same topic, assert count == 2 and last_seen updated.
    """
    state_file = Path.home() / ".claude/skills/.maintenance-state.json"
    state: dict[str, Any] = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    freq = state.setdefault("topic_frequency", {})
    for topic in topics:
        if topic not in freq:
            freq[topic] = {"count": 0, "first_seen": date, "last_seen": date}
        freq[topic]["count"] += 1
        freq[topic]["last_seen"] = date

    try:
        state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        log(f"[WARN] Cannot save topic state: {exc}")


# ── Similarity ────────────────────────────────────────────────────────────

SIMILARITY_THRESHOLD = 0.6  # Jaccard coefficient threshold for fuzzy match

# Stop words to ignore during tokenization
_STOP_WORDS = frozenset({
    "的", "了", "是", "在", "和", "与", "或", "也", "都", "有", "不",
    "the", "and", "for", "that", "this", "with", "from", "has", "are", "was",
    "not", "but", "may", "can", "all", "its", "need",
})


def tokenize(text: str) -> set[str]:
    """Extract meaningful tokens for fuzzy similarity comparison.

    Why: Enables detecting semantically similar entries despite wording differences.
    What: Strips markdown/dates/tags, splits into Chinese words + English words (>=3 chars).
    Test: 'Paperclip Dispatcher error' and 'Paperclip Agents Dispatcher error' share tokens.
    """
    # Remove date prefix like "- [2026-04-08]"
    clean = re.sub(r"- \[\d{4}-\d{2}-\d{2}\]\s*", "", text)
    # Remove operator tags like [Sonnet], [AGI-Brain]
    clean = re.sub(r"\[\w+[-\w]*\]\s*", "", clean)
    # Remove markdown formatting
    clean = re.sub(r"[#*`_\[\](){}]", " ", clean)
    # Extract Chinese character sequences (2+ chars) and English words (3+ chars)
    tokens: set[str] = set()
    for m in re.finditer(r"[\u4e00-\u9fff]{2,}", clean):
        tokens.add(m.group())
    for m in re.finditer(r"[a-zA-Z]{3,}", clean):
        tokens.add(m.group().lower())
    # Remove stop words
    return tokens - _STOP_WORDS


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two token sets.

    Why: Standard set-similarity metric, O(n) complexity.
    What: Returns 0.0-1.0 where 1.0 = identical token sets.
    Test: jaccard_similarity({'a','b','c'}, {'a','b','c'}) == 1.0.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ── Deduplication ──────────────────────────────────────────────────────────

def load_existing_skill_hashes() -> set[str]:
    """Collect content hashes from all existing skills.

    Why: Prevents creating duplicate skills for already-covered knowledge.
    What: Reads all SKILL.md files, returns set of content hashes.
    Test: Empty skills dir returns empty set.
    """
    hashes: set[str] = set()
    if not SKILLS_DIR.exists():
        return hashes

    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            try:
                text = skill_md.read_text(encoding="utf-8")
                hashes.add(content_hash(text))
            except OSError:
                continue
    return hashes


def is_duplicate(
    entry_text: str,
    existing_hashes: set[str],
    pending: list[dict[str, Any]],
) -> bool:
    """Check if entry duplicates existing skill or pending candidate.

    Why: Prevents both exact and fuzzy duplicates in candidate queue.
    What: Returns True if exact hash matches OR similarity > threshold vs pending.
    Test: Similar AGI-Brain entries about same topic return True.
    """
    h = content_hash(entry_text)

    # Exact match against existing skills
    if h in existing_hashes:
        return True

    # Exact match against pending candidates
    for candidate in pending:
        if content_hash(candidate.get("content", "")) == h:
            return True

    # Fuzzy match against pending candidates
    entry_tokens = tokenize(entry_text)
    if not entry_tokens:
        return False

    for candidate in pending:
        cand_tokens = tokenize(candidate.get("content", ""))
        if not cand_tokens:
            continue
        sim = jaccard_similarity(entry_tokens, cand_tokens)
        if sim >= SIMILARITY_THRESHOLD:
            log(f"[DEDUP] Fuzzy match (sim={sim:.2f}): {suggest_name(entry_text)[:40]} ≈ {suggest_name(candidate.get('content', ''))[:40]}")
            return True

    return False


def dedupe_pending() -> int:
    """Remove fuzzy-duplicate entries from the existing pending queue.

    Why: Cleans up accumulated duplicates from before fuzzy dedup was added.
    What: Compares all pairs, keeps the longest entry per similarity cluster.
    Test: Queue of 15 similar AGI-Brain entries reduces to 1-2.
    """
    pending = load_pending()
    if len(pending) <= 1:
        return 0

    kept: list[dict[str, Any]] = []
    removed = 0

    for candidate in pending:
        cand_tokens = tokenize(candidate.get("content", ""))
        is_dup = False

        for existing in kept:
            exist_tokens = tokenize(existing.get("content", ""))
            sim = jaccard_similarity(cand_tokens, exist_tokens)
            if sim >= SIMILARITY_THRESHOLD:
                # Keep the longer (more detailed) entry
                if len(candidate.get("content", "")) > len(existing.get("content", "")):
                    kept.remove(existing)
                    kept.append(candidate)
                is_dup = True
                removed += 1
                break

        if not is_dup:
            kept.append(candidate)

    if removed > 0:
        save_pending(kept)
        msg = f"[DEDUP] 候选队列去重：{len(pending)} → {len(kept)}（移除 {removed} 条相似条目）"
        print(msg)
        log(msg)

    return removed


# ── Auto-naming ────────────────────────────────────────────────────────────

def suggest_name(entry_text: str) -> str:
    """Generate a candidate skill name from entry content.

    Why: Provides human-readable default names for candidates.
    What: Extracts key topic from first line, slugifies it.
    Test: Entry about "NixOS NVIDIA driver" suggests related name.
    """
    # Take first line, strip date prefix
    first_line = entry_text.split("\n")[0]
    clean = re.sub(r"^- \[\d{4}-\d{2}-\d{2}\]\s*", "", first_line)
    # Remove operator tag like [Sonnet], [Opus]
    clean = re.sub(r"\[\w+\]\s*", "", clean)
    # Remove markdown bold markers
    clean = clean.strip().strip("*").strip()
    # Truncate to reasonable length
    if len(clean) > 60:
        clean = clean[:60].rsplit(" ", 1)[0]
    # Slugify
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", clean.lower()).strip("-")
    if not slug:
        slug = f"knowledge-{content_hash(entry_text)[:6]}"
    return slug


# ── Core scan logic ────────────────────────────────────────────────────────

def scan() -> tuple[int, int, int]:
    """Execute a single scan cycle.

    Why: Core function that detects new knowledge and queues candidates.
    What: Returns (files_checked, new_entries, new_candidates).
    Test: scan() on unchanged files returns (N, 0, 0).
    """
    state = load_state()
    pending = load_pending()
    existing_hashes = load_existing_skill_hashes()
    last_scan = state.get("last_scan", "")

    files_checked = 0
    new_entries = 0
    new_candidates = 0

    if not MEMORY_DIR.exists():
        log(f"[WARN] Memory dir not found: {MEMORY_DIR}")
        print(f"[SCAN] Memory dir not found: {MEMORY_DIR}")
        return (0, 0, 0)

    md_files = sorted(MEMORY_DIR.glob("*.md"))
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for md_file in md_files:
        # Skip archive subdirectories and hidden files
        if md_file.name.startswith(".") or "archive" in str(md_file):
            continue

        files_checked += 1
        mtime_iso = datetime.fromtimestamp(
            md_file.stat().st_mtime, tz=timezone.utc
        ).isoformat(timespec="seconds")

        # Skip if file hasn't changed since last scan
        prev_mtime = state.get("files", {}).get(md_file.name, "")
        if prev_mtime == mtime_iso and last_scan:
            continue

        # Extract entries from modified file
        entries = extract_entries(md_file)
        category = CATEGORY_MAP.get(md_file.name, "general")

        for entry_text in entries:
            if is_duplicate(entry_text, existing_hashes, pending):
                continue

            new_entries += 1
            candidate: dict[str, Any] = {
                "id": content_hash(entry_text),
                "source_file": md_file.name,
                "content": entry_text,
                "detected_at": now_iso,
                "status": "pending",
                "suggested_name": suggest_name(entry_text),
                "suggested_category": category,
            }
            pending.append(candidate)
            new_candidates += 1
            existing_hashes.add(content_hash(entry_text))

            # Extract topics and update shared frequency state
            topics = extract_topics(entry_text)
            candidate["topics"] = topics
            update_topic_frequency(topics, now_iso)

        # Update file mtime in state
        if "files" not in state:
            state["files"] = {}
        state["files"][md_file.name] = mtime_iso

    # Dedupe pending queue after adding new candidates
    if new_candidates > 0:
        dedupe_pending()

    # Persist state and pending
    state["last_scan"] = now_iso
    save_state(state)

    summary = (
        f"[SCAN] 检查 {files_checked} 个文件，"
        f"发现 {new_entries} 条新知识，"
        f"{new_candidates} 条候选"
    )
    print(summary)
    log(summary)

    return (files_checked, new_entries, new_candidates)


# ── Auto-create ────────────────────────────────────────────────────────────

def auto_create_pending() -> int:
    """Process pending candidates via create-skill.py --no-llm.

    Why: Enables fully automated skill creation for trusted candidates.
    What: Returns count of successfully created skills.
    Test: auto_create_pending() with 3 pending creates 3 skill dirs.
    """
    pending = load_pending()
    if not pending:
        print("[CREATE] 无待处理候选")
        return 0

    if not CREATE_SKILL.exists():
        print(f"[FAIL] create-skill.py not found: {CREATE_SKILL}")
        return 0

    created = 0
    remaining: list[dict[str, Any]] = []

    for candidate in pending:
        if candidate.get("status") != "pending":
            remaining.append(candidate)
            continue

        name = candidate.get("suggested_name", f"auto-{candidate['id']}")
        content = candidate.get("content", "")
        category = candidate.get("suggested_category", "general")

        cmd = [
            sys.executable,
            str(CREATE_SKILL),
            "--name", name,
            "--content", content[:500],
            "--category", category,
            "--no-llm",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                created += 1
                log(f"[CREATE] Created skill: {name}")
            else:
                log(f"[WARN] create-skill failed for {name}: {result.stderr[:200]}")
                remaining.append(candidate)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            log(f"[WARN] create-skill error for {name}: {exc}")
            remaining.append(candidate)

    save_pending(remaining)
    print(f"[CREATE] 创建 {created} 个 skill，剩余 {len(remaining)} 候选")
    return created


# ── Daemon mode ────────────────────────────────────────────────────────────

def daemon_loop() -> None:
    """Run scan in a loop with configurable interval.

    Why: Provides continuous monitoring without systemd timer dependency.
    What: Calls scan() every SCAN_INTERVAL_SECONDS until interrupted.
    Test: SIGTERM or KeyboardInterrupt stops the loop cleanly.
    """
    print(f"[DAEMON] Starting, interval={SCAN_INTERVAL_SECONDS}s")
    log(f"[DAEMON] Started with interval={SCAN_INTERVAL_SECONDS}s")

    try:
        while True:
            scan()
            time.sleep(SCAN_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[DAEMON] Stopped by user")
        log("[DAEMON] Stopped by KeyboardInterrupt")


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Why: Supports both one-shot and daemon modes from the same script.
    What: Returns namespace with scan/daemon/auto_create flags.
    Test: --scan flag sets namespace.scan=True.
    """
    parser = argparse.ArgumentParser(description="Skill Watcher — knowledge monitor")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", action="store_true", help="Single scan cycle")
    group.add_argument("--daemon", action="store_true", help="Continuous daemon mode")
    group.add_argument("--dedupe", action="store_true", help="Deduplicate pending queue")
    parser.add_argument(
        "--auto-create", action="store_true",
        help="Auto-create skills from pending candidates (use with --scan)",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point.

    Why: Orchestrates scan/auto-create/daemon based on CLI flags.
    What: Returns 0 on success.
    Test: --scan returns 0 and updates state file.
    """
    args = parse_args()

    if args.scan:
        scan()
        if args.auto_create:
            auto_create_pending()
    elif args.daemon:
        daemon_loop()
    elif args.dedupe:
        dedupe_pending()

    return 0


if __name__ == "__main__":
    sys.exit(main())
