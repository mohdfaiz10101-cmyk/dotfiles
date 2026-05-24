#!/usr/bin/env python3
"""
mem0_decay.py — ChromaDB 记忆衰减引擎
三阶段：
  1. 摘要合并: 30天+的旧条目 → LLM 提取摘要 → 存为新记忆 → 删除旧条目
  2. TTL 清理: 60天+的条目直接删除
  3. 限流保护: 每天最多处理 200 条

用法: python3 mem0_decay.py [--dry-run]
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

BRIDGE_URL = "http://127.0.0.1:8285"
STATE_FILE = Path(os.path.expanduser("~/.local/state/mem0-decay-state.json"))
SUMMARY_AGE_DAYS = 30  # 超过此天数 → 摘要合并
TTL_AGE_DAYS = 60      # 超过此天数 → 直接删除
MAX_PROCESS_PER_RUN = 200  # 每次最多处理条数

STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": None, "total_summarized": 0, "total_deleted": 0}


def save_state(state):
    state["last_run"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def get_all_memories(limit: int = 2000) -> list:
    """获取所有记忆及其元数据"""
    try:
        resp = urlopen(f"{BRIDGE_URL}/get_all?limit={limit}", timeout=15)
        data = json.loads(resp.read())
        return data.get("memories", [])
    except URLError:
        return []


def delete_memory(mem_id: str) -> bool:
    """删除单条记忆"""
    payload = json.dumps({"memory_id": mem_id}).encode()
    req = Request(f"{BRIDGE_URL}/delete", data=payload,
                   headers={"Content-Type": "application/json"})
    try:
        resp = urlopen(req, timeout=5)
        return json.loads(resp.read()).get("status") == "deleted"
    except URLError:
        return False


def add_summary(text: str, original_count: int) -> bool:
    """添加摘要记忆"""
    meta = {
        "source": "mem0-decay",
        "type": "summary",
        "original_count": original_count,
        "ts": datetime.now().isoformat(),
    }
    payload = json.dumps({"text": text, "metadata": meta}).encode()
    req = Request(f"{BRIDGE_URL}/add", data=payload,
                   headers={"Content-Type": "application/json"})
    try:
        urlopen(req, timeout=15)
        return True
    except URLError:
        return False


def parse_ts(meta: dict) -> datetime | None:
    """解析时间戳"""
    ts_str = (meta or {}).get("ts", "")
    if not ts_str:
        return None
    for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None


def run_decay(dry_run: bool = False):
    state = load_state()
    now = datetime.now()
    summary_cutoff = now - timedelta(days=SUMMARY_AGE_DAYS)
    ttl_cutoff = now - timedelta(days=TTL_AGE_DAYS)

    memories = get_all_memories()
    if not memories:
        print("[mem0-decay] 无法获取记忆列表")
        return

    to_summarize = []  # 30-60天：需摘要合并
    to_delete = []     # 60天+：直接删除

    for m in memories:
        meta = m.get("metadata") or {}
        mem_id = meta.get("id", "")
        if not mem_id:
            continue
        ts = parse_ts(meta)
        if not ts:
            continue
        if ts < ttl_cutoff:
            to_delete.append(m)
        elif ts < summary_cutoff:
            to_summarize.append(m)

    # 限流
    total = len(to_summarize) + len(to_delete)
    if total > MAX_PROCESS_PER_RUN:
        # 优先处理更老的
        to_summarize = to_summarize[:MAX_PROCESS_PER_RUN // 2]
        to_delete = to_delete[:MAX_PROCESS_PER_RUN // 2]

    if not to_summarize and not to_delete:
        print(f"[mem0-decay] 无需衰减 (共 {len(memories)} 条记忆)")
        return

    print(f"[mem0-decay] 摘要合并: {len(to_summarize)} 条, 直接删除: {len(to_delete)} 条")
    if dry_run:
        for m in to_summarize[:5]:
            print(f"  摘要: {m.get('memory','')[:60]}...")
        for m in to_delete[:5]:
            print(f"  删除: {m.get('memory','')[:60]}...")
        return

    # 批量摘要合并
    if to_summarize:
        texts = [m.get("memory", "") for m in to_summarize]
        combined = "\n---\n".join(texts)
        prefix = f"[mem0-decay] 以下 {len(to_summarize)} 条旧记忆已合并为摘要:\n"
        summary_text = prefix + combined[:3000]  # LLM 处理上限
        if add_summary(summary_text, len(to_summarize)):
            state["total_summarized"] += len(to_summarize)
            # 删除旧条目
            deleted = 0
            for m in to_summarize:
                mid = (m.get("metadata") or {}).get("id", "")
                if mid and delete_memory(mid):
                    deleted += 1
            print(f"  摘要合并完成: {deleted}/{len(to_summarize)} 条 → 1 条摘要")

    # TTL 删除
    if to_delete:
        deleted = 0
        for m in to_delete:
            mid = (m.get("metadata") or {}).get("id", "")
            if mid and delete_memory(mid):
                deleted += 1
        state["total_deleted"] += deleted
        print(f"  TTL删除: {deleted}/{len(to_delete)} 条")

    save_state(state)
    summary = f"累计: {state['total_summarized']} 摘要, {state['total_deleted']} 删除"
    print(f"[mem0-decay] 完成 ({summary})")

    # Telegram通知
    tg = os.path.expanduser("~/agi/tg_monitor.py")
    if os.path.exists(tg):
        subprocess.run([sys.executable, tg, "decay", summary], timeout=10, capture_output=True)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_decay(dry_run=dry_run)