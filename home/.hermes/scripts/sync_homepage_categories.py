#!/usr/bin/env python3
"""
sync_homepage_categories.py — 修复 Hermes Web UI homepage 的 session category_id。

数据来源:
- Hermes Web UI API: GET /api/hermes/sessions?limit=200&source=cli
- Hermes Web UI API: POST /api/hermes/sessions/{id}/category

规则:
- 最近 180 天内、source=cli 的会话
- 标题命中关键词 -> 对应 category_id
- 未命中 -> 不修改（保留未分类/人工处理）
"""
from __future__ import annotations
import re, sys
from datetime import datetime, timedelta

import requests

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "default"
API_BASE = "http://127.0.0.1:19999"

RULES = [
    ("工作|Hermes|模型接入|netbird|adb|ssh|监控|脚本|cron|升级|opencode|aider", 2),
    ("手机|健康|我我身体|termux|package|apk|远控", 3),
    ("bug|修复|失败|error|停止|中断|连接|未完成", 4),
]


def classify(title: str) -> int | None:
    for pattern, cid in RULES:
        if re.search(pattern, title, re.IGNORECASE):
            return cid
    return None


def get_sessions(limit: int = 200) -> list[dict]:
    r = requests.get(f"{API_BASE}/api/hermes/sessions", params={"limit": limit, "source": "cli"}, timeout=20)
    r.raise_for_status()
    return r.json().get("sessions", [])


def set_category(session_id: str, category_id: int | None) -> bool:
    r = requests.post(f"{API_BASE}/api/hermes/sessions/{session_id}/category", json={"category_id": category_id}, timeout=20)
    data = r.json()
    return data.get("ok") is True and data.get("category_id") == category_id


def get_session(session_id: str) -> dict:
    r = requests.get(f"{API_BASE}/api/hermes/sessions/{session_id}", timeout=20)
    r.raise_for_status()
    return r.json().get("session", {})


def main() -> int:
    sessions = get_sessions()
    cutoff = datetime.now() - timedelta(days=180)
    updated = 0; skipped = 0; failed = 0; total = 0
    for s in sessions:
        sid = s["id"]
        started = datetime.fromtimestamp(s.get("started_at", 0))
        if started < cutoff:
            continue
        total += 1
        if s.get("category_id") is not None:
            skipped += 1
            continue
        cid = classify(s.get("title", ""))
        if cid is None:
            skipped += 1
            continue
        ok = set_category(sid, cid)
        if not ok:
            failed += 1
            continue
        verify = get_session(sid)
        if verify.get("category_id") != cid:
            failed += 1
            continue
        updated += 1
    print(f"total={total} updated={updated} skipped={skipped} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
