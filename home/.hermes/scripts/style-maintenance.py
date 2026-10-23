#!/usr/bin/env python3
"""
Hermes SOUL/style/preference auto-maintenance helper.

Goals:
- Collect explicit feedback from soul-optimization-log / memory / session_search.
- Detect repeated style/preference signals.
- Produce a small, reviewable diff for SOUL.md / USER.md / user-preferences.md.
- Do NOT auto-apply risky rewrites; prefer additive small patches and require review for removals.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

try:
    from hermes_tools import session_search, memory  # type: ignore
except Exception:  # pragma: no cover - herm
    session_search = None  # type: ignore
    memory = None  # type: ignore


HERMES_HOME = Path.home() / ".hermes"
SOUL_PATH = HERMES_HOME / "SOUL.md"
USER_MD_PATH = HERMES_HOME / "memories" / "USER.md"
USER_PREFS_PATH = HERMES_HOME / "memories" / "categories" / "user-preferences.md"
OPT_LOG_PATH = HERMES_HOME / "memories" / "categories" / "soul-optimization-log.md"
REPORT_PATH = Path("/tmp/hermes-style-maintenance-report.md")


@dataclass
class Finding:
    category: str
    signal: str
    evidence: str
    suggestion: str
    priority: str  # low / medium / high


def _read(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def _today() -> datetime:
    return datetime.utcnow()


def _window_days(days: int = 7) -> datetime:
    return _today() - timedelta(days=days)


def _append_block(path: Path, block: str) -> None:
    text = _read(path)
    sep = "\n\n" if text.strip() else ""
    path.write_text(text + sep + block.strip() + "\n")


def collect_explicit_feedback(days: int = 7) -> list[Finding]:
    findings: list[Finding] = []
    opt_text = _read(OPT_LOG_PATH)
    if not opt_text:
        return findings

    since = _window_days(days)
    current_block: list[str] = []
    in_backlog = False
    for line in opt_text.splitlines():
        if line.strip().startswith("## 待办"):
            in_backlog = True
            current_block = []
            continue
        if line.strip().startswith("## 变更记录"):
            in_backlog = False
            continue
        current_block.append(line)

    block = "\n".join(current_block)
    for m in re.finditer(r"- \[ \] (.+)", block):
        item = m.group(1).strip()
        if not item:
            continue
        findings.append(
            Finding(
                category="explicit-feedback",
                signal="user backlog item",
                evidence=item,
                suggestion="Review whether SOUL.md needs a small patch or just observation.",
                priority="medium",
            )
        )

    return findings


def collect_memory_signals(days: int = 30) -> list[Finding]:
    findings: list[Finding] = []
    if memory is None:
        return findings

    try:
        mem_path = HERMES_HOME / "memories" / "memory-index.json"
        if not mem_path.exists():
            return findings
        data = json.loads(mem_path.read_text())
        entries = data if isinstance(data, list) else data.get("entries", [])
        since = _window_days(days)
        count = 0
        for entry in entries:
            text = entry.get("text") or entry.get("content") or ""
            accessed = entry.get("last_accessed_at") or entry.get("created_at") or ""
            if not text:
                continue
            if accessed:
                try:
                    dt = datetime.fromisoformat(accessed.replace("Z", "+00:00"))
                    if dt < since:
                        continue
                except Exception:
                    pass
            if any(k in text for k in ["不要", "禁止", "must", "only", "always", "never", "默认", "偏好", "prefers"]):
                count += 1
                findings.append(
                    Finding(
                        category="memory-signal",
                        signal="preference/rule memory",
                        evidence=text[:280],
                        suggestion="If this is a durable preference, mirror it into USER.md and consider SOUL.md wording.",
                        priority="low",
                    )
                )
            if count >= 20:
                break
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(
            Finding(
                category="memory-signal",
                signal="memory read error",
                evidence=str(exc),
                suggestion="Fix memory indexing before optimization.",
                priority="high",
            )
        )
    return findings


def collect_session_signals(queries: Iterable[str], limit: int = 8) -> list[Finding]:
    findings: list[Finding] = []
    if session_search is None:
        return findings

    for query in queries:
        try:
            result = session_search(query=query, limit=limit)
            sessions = result if isinstance(result, list) else []
        except Exception as exc:  # pragma: no cover - defensive
            findings.append(
                Finding(
                    category="session-signal",
                    signal="session search error",
                    evidence=str(exc),
                    suggestion="Check Hermes session tool availability.",
                    priority="high",
                )
            )
            continue

        for session in sessions:
            title = session.get("title") or session.get("session_id") or ""
            snippet = ""
            messages = session.get("messages") or []
            if messages:
                snippet = messages[0].get("content") or messages[0].get("text") or ""
            text = f"{title}\n{snippet}"
            if any(k in text.lower() for k in ["style", "回复", "输出", "太啰嗦", "模板", "格式", "prefer", "偏好", "concise", "verbose"]):
                findings.append(
                    Finding(
                        category="session-signal",
                        signal="style/preference mention",
                        evidence=text[:320],
                        suggestion="If repeated, promote to a concrete SOUL.md rule or backlog item.",
                        priority="medium",
                    )
                )
    return findings


def build_soul_health(feedback: list[Finding]) -> list[Finding]:
    soul_text = _read(SOUL_PATH)
    health = []
    if not soul_text.strip():
        health.append(Finding(category="soul-health", signal="empty", evidence="SOUL.md is empty", suggestion="Restore baseline identity/output contract.", priority="high"))
    if "## User Preferences" in soul_text and "Output contract" not in soul_text:
        health.append(Finding(category="soul-health", signal="legacy", evidence="Legacy user-pref block without modern output contract", suggestion="Migrate to shorter Output contract + Anti-patterns.", priority="medium"))
    if soul_text.count("\n- ") > 60:
        health.append(Finding(category="soul-health", signal="rule-bloat", evidence=f"SOUL.md has {soul_text.count(chr(10))} lines", suggestion="Trim rules; promote durable items to memory/skills.", priority="medium"))
    health.extend([f for f in feedback if f.category == "soul-health"])
    return health


def render_report(findings: list[Finding]) -> str:
    now = _today().isoformat()
    lines = [f"# Hermes style/preference maintenance report\n\nGenerated: {now}\n"]
    if not findings:
        lines.append("No actionable signals in the current window.\n")
        return "\n".join(lines)

    lines.append("## Findings\n")
    for idx, f in enumerate(findings, 1):
        lines.append(f"{idx}. [{f.category}] {f.signal} ({f.priority})")
        lines.append(f"- evidence: {f.evidence}")
        lines.append(f"- suggestion: {f.suggestion}")
        lines.append("")
    lines.append("## Suggested next actions\n")
    lines.append("- Review high-priority findings first.")
    lines.append("- Prefer 1-2 small SOUL.md edits per cycle.")
    lines.append("- Move durable preferences into USER.md or user-preferences.md.")
    return "\n".join(lines)


def main() -> int:
    days = int(os.getenv("HERMES_STYLE_REVIEW_DAYS", "7"))
    queries = [
        "回复风格",
        "输出格式",
        "偏好",
        "concise",
        "style",
    ]
    explicit = collect_explicit_feedback(days=days)
    memory_sigs = collect_memory_signals(days=30)
    session_sigs = collect_session_signals(queries=queries, limit=8)
    findings: list[Finding] = []
    seen: set[str] = set()
    for item in explicit + memory_sigs + session_sigs + build_soul_health(explicit):
        key = " | ".join([item.category, item.signal, item.evidence])
        if key in seen:
            continue
        seen.add(key)
        findings.append(item)

    report = render_report(findings)
    REPORT_PATH.write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
