#!/usr/bin/env python3
"""
mem0_watchdog.py — 记忆完整性看门狗
每15分钟检查三层记忆健康，发现漂移自动修复，无法修复则告警。

检查项:
  1. ChromaDB 可达 + 搜索可用（非假健康）
  2. 文件→ChromaDB 同步无漂移（已修改未索引）
  3. 文件层完整性（MEMORY.md/lessons-learned.md 存在）
  4. Letta MCP fallback 可用

用法: python3 mem0_watchdog.py [--once]
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

MEMORY_DIR = Path(os.path.expanduser("~/.claude/projects/-home-charlie/memory"))
CHROMADB_URL = "http://127.0.0.1:8285"
LETTA_URL = "http://127.0.0.1:8284"
SYNC_STATE = Path(os.path.expanduser("~/.local/state/mem0-file-sync.json"))
WATCHDOG_STATE = Path(os.path.expanduser("~/.local/state/mem0-watchdog.json"))
SYNC_SCRIPT = Path(os.path.expanduser("~/agi/mem0_file_sync.py"))

# Telegram通知（延迟导入，避免依赖）
TG_MONITOR = Path(os.path.expanduser("~/agi/tg_monitor.py"))

WATCHDOG_STATE.parent.mkdir(parents=True, exist_ok=True)
REQUIRED_FILES = ["lessons-learned.md", "MEMORY.md", "op-tasks.md"]


def tg_notify(module: str, msg: str, silent: bool = True):
    """通过 tg_monitor.py 发通知（静默模式，告警除外）"""
    if not TG_MONITOR.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(TG_MONITOR), module, msg],
            timeout=10, capture_output=True,
            env={**os.environ, "http_proxy": "http://127.0.0.1:7890"},
        )
    except Exception:
        pass


def load_state():
    if WATCHDOG_STATE.exists():
        try:
            return json.loads(WATCHDOG_STATE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"failures": {}, "last_ok": None, "autoheal_count": 0}


def save_state(state):
    state["last_check"] = datetime.now().isoformat()
    WATCHDOG_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def check_chromadb() -> dict:
    """检查 ChromaDB: 健康 + 搜索可用（真检查，非假阳性）"""
    # 1. 健康检查
    try:
        resp = urlopen(f"{CHROMADB_URL}/health", timeout=5)
        health = json.loads(resp.read())
        if health.get("status") != "ok":
            return {"ok": False, "reason": "health非ok", "detail": health}
    except URLError as e:
        return {"ok": False, "reason": f"不可达: {e}"}

    # 2. 搜索可用性（验证向量搜索真的工作）
    try:
        from urllib.parse import quote
        resp = urlopen(f"{CHROMADB_URL}/search?q={quote('memory')}&limit=1", timeout=5)
        data = json.loads(resp.read())
        if not data.get("results"):
            return {"ok": False, "reason": "搜索返回空（可能索引损坏）"}
    except URLError as e:
        return {"ok": False, "reason": f"搜索失败: {e}"}

    return {"ok": True, "count": health.get("count", 0)}


def check_file_sync_drift() -> dict:
    """检查文件→ChromaDB同步漂移"""
    drift_files = []
    sync_state = {}
    if SYNC_STATE.exists():
        try:
            sync_state = json.loads(SYNC_STATE.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    md_files = [f for f in MEMORY_DIR.glob("**/*.md")
                if f.is_file() and ".backup" not in f.name and ".bak" not in f.name]

    for fp in md_files:
        rel = str(fp.relative_to(MEMORY_DIR))
        stat = fp.stat()
        fhash = hashlib.md5(
            f"{fp}:{stat.st_mtime}:{stat.st_size}".encode()
        ).hexdigest()[:12]

        cached = sync_state.get(rel)
        if cached != fhash:
            # 检查是否最近修改（<5分钟的可能是正在写入）
            age_min = (time.time() - stat.st_mtime) / 60
            drift_files.append({
                "file": rel,
                "cached": cached or "无",
                "current": fhash,
                "age_min": round(age_min, 1),
                "fresh": age_min < 5,
            })

    return {
        "ok": len(drift_files) == 0,
        "total_files": len(md_files),
        "drift_count": len(drift_files),
        "drift_files": drift_files[:10],
    }


def check_file_integrity() -> dict:
    """检查关键文件存在且非空"""
    missing = []
    empty = []
    for fname in REQUIRED_FILES:
        fp = MEMORY_DIR / fname
        if not fp.exists():
            missing.append(fname)
        elif fp.stat().st_size < 10:
            empty.append(fname)
    return {"ok": not missing and not empty, "missing": missing, "empty": empty}


def check_letta() -> dict:
    """检查 Letta MCP fallback"""
    try:
        resp = urlopen(f"{LETTA_URL}/health", timeout=3)
        data = json.loads(resp.read())
        return {"ok": data.get("status") == "healthy"}
    except URLError:
        return {"ok": False, "reason": "不可达"}


def autoheal(drift: dict) -> bool:
    """自动修复：触发文件同步"""
    stale = [f for f in drift.get("drift_files", []) if not f.get("fresh")]
    if not stale:
        return True  # 没有需要修复的（都是刚修改的）

    print(f"[watchdog] 自动修复: {len(stale)} 个文件不同步，触发 sync...")
    try:
        r = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT)],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            return True
        else:
            print(f"[watchdog] sync 失败: {r.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("[watchdog] sync 超时")
        return False
    except Exception as e:
        print(f"[watchdog] sync 异常: {e}")
        return False


def run():
    state = load_state()
    results = {}
    all_ok = True
    healed = False

    # 1. ChromaDB
    r = check_chromadb()
    results["chromadb"] = r
    if not r["ok"]:
        all_ok = False

    # 2. 文件同步漂移
    r = check_file_sync_drift()
    results["file_sync"] = r
    if not r["ok"]:
        stale = [f for f in r.get("drift_files", []) if not f.get("fresh")]
        if stale:
            print(f"[watchdog] 检测到 {len(stale)} 个文件漂移: {[f['file'] for f in stale[:5]]}")
            if autoheal(r):
                healed = True
                state["autoheal_count"] = state.get("autoheal_count", 0) + 1
                results["file_sync"]["ok"] = True  # 自愈成功，标记OK
            else:
                all_ok = False

    # 3. 文件完整性
    r = check_file_integrity()
    results["file_integrity"] = r
    if not r["ok"]:
        all_ok = False

    # 4. Letta
    r = check_letta()
    results["letta"] = r
    if not r["ok"]:
        all_ok = False  # Letta挂了也报，但不致命（Chromadb优先）

    # 更新状态
    if all_ok:
        state["last_ok"] = datetime.now().isoformat()
        for k in list(state.get("failures", {}).keys()):
            state["failures"][k] = 0  # 重置连续失败计数
    else:
        failures = state.setdefault("failures", {})
        for k, v in results.items():
            if not v.get("ok"):
                failures[k] = failures.get(k, 0) + 1

    save_state(state)

    # 计算失败列表（必须在 Telegram 通知之前定义）
    failed = [k for k, v in results.items() if not v.get("ok")]

    # Telegram通知（只发异常/自愈/连续失败）
    if healed:
        tg_notify("autoheal", f"自动同步完成，修复 {len(stale)} 个漂移文件")
    elif not all_ok:
        fails_str = ", ".join(f"{k}:{results[k].get('reason','fail')}" for k in failed)
        consecutive = max(state["failures"].get(k, 0) for k in failed)
        if consecutive == 1:
            tg_notify("alert", f"故障检测: {fails_str}", silent=False)
        elif consecutive >= 3:
            tg_notify("alert", f"持续故障(连续{consecutive}次): {fails_str}", silent=False)

    # 输出
    status_line = "OK" if all_ok else (f"DEGRADED{'(已自愈)' if healed else ''}")
    print(f"[mem0-watchdog] {status_line} | chromadb={results['chromadb'].get('count','?')} "
          f"files={results['file_sync'].get('total_files','?')} "
          f"drift={results['file_sync'].get('drift_count','?')} "
          f"letta={'ok' if results['letta'].get('ok') else 'down'}")

    if failed:
        fails_str = ", ".join(f"{k}:{results[k].get('reason','fail')}" for k in failed)
        print(f"[mem0-watchdog] 故障: {fails_str}")
        consecutive = max(state["failures"].get(k, 0) for k in failed)
        if consecutive >= 3:
            print(f"[mem0-watchdog] ALERT: {fails_str} 连续{consecutive}次失败！")


if __name__ == "__main__":
    run()