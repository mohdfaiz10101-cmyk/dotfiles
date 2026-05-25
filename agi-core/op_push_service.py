#!/run/current-system/sw/bin/python3
"""OP 任务推送服务 — 监控 op-tasks.md 变化，推送到 Telegram/Discord"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# ── 配置 ───────────────────────────────────────────
OP_TASKS_FILE = "/home/charlie/.claude/projects/-home-charlie/memory/op-tasks.md"
OP_RESULTS_FILE = Path.home() / ".local/state/op-task-results.json"
STATE_FILE = "/home/charlie/.local/share/op-push/state.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# 推送间隔（秒）
POLL_INTERVAL = 30
# 去抖窗口（秒）：文件变化后等待这么久再推送，期间变化合并
DEBOUNCE_SECONDS = 60
# 最小推送间隔（秒）：两次推送之间至少间隔
MIN_PUSH_INTERVAL = 300  # 5分钟


def _read_file_hash(filepath: str) -> Optional[str]:
    """读取文件内容并生成 hash（用于检测变化）"""
    try:
        import hashlib

        content = Path(filepath).read_text()
        return hashlib.md5(content.encode()).hexdigest()
    except Exception:
        return None


def _load_state() -> dict:
    """加载上一次的状态"""
    try:
        if Path(STATE_FILE).exists():
            return json.loads(Path(STATE_FILE).read_text())
    except Exception:
        pass
    return {"last_hash": None, "last_pushed_tasks": []}


def _save_state(state: dict) -> None:
    """保存状态"""
    try:
        Path(STATE_FILE).write_text(json.dumps(state, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[OP-PUSH] 保存状态失败: {e}")


def _parse_op_tasks(content: str) -> list[dict]:
    """解析 op-tasks.md，提取完成/失败的任务

    Returns:
        list of {"line": int, "status": "ok"|"fail"|"skip", "text": str, "result": str}
    """
    tasks = []
    lines = content.split("\n")

    for i, line in enumerate(lines, start=1):
        # 匹配: - [x] [完成 2026-04-26 12:00] TASK-001 — 结果
        # 或: - [!] TASK-002 — 失败原因
        match = re.search(r"^-\s+\[(x|!| )\]\s*(?:\[[^\]]+\]\s*)?(.+)$", line)
        if match:
            status_char, task_text = match.groups()
            status = {"x": "ok", "!": "fail", " ": "pending"}.get(
                status_char, "unknown"
            )

            # 提取结果部分（如果有）
            result = ""
            if " — " in task_text:
                task_id, result = task_text.split(" — ", 1)
            else:
                task_id = task_text

            tasks.append(
                {
                    "line": i,
                    "status": status,
                    "task_id": task_id.strip(),
                    "text": line.strip(),
                    "result": result.strip(),
                }
            )

    return tasks


def _format_message(tasks: list[dict]) -> str:
    """格式化推送消息"""
    if not tasks:
        return ""

    msg_parts = ["📋 OP 任务更新"]

    for task in tasks:
        if task["status"] == "ok":
            icon = "✅"
            title = "已完成"
        elif task["status"] == "fail":
            icon = "❌"
            title = "失败"
        elif task["status"] == "pending":
            icon = "⏳"
            title = "待处理"
        else:
            continue

        task_id = task["task_id"][:50]  # 限制长度
        result = task["result"][:100] if task["result"] else "无详情"

        msg_parts.append(f"\n{icon} {title}: {task_id}")
        if result:
            msg_parts.append(f"   └ {result}")

    msg_parts.append(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
    return "\n".join(msg_parts)


async def _push_to_telegram(message: str) -> bool:
    """推送到 Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[OP-PUSH] Telegram 配置缺失", flush=True)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        # 使用代理（从环境变量读取）
        proxy = os.environ.get("HTTPS_PROXY", "")
        if proxy:
            mounts = {
                "http://": httpx.AsyncHTTPTransport(proxy=proxy),
                "https://": httpx.AsyncHTTPTransport(proxy=proxy),
            }
            async with httpx.AsyncClient(timeout=60, mounts=mounts) as client:
                resp = await client.post(url, json=payload)
                print(f"[OP-PUSH] Telegram 响应: {resp.status_code}", flush=True)
                return resp.status_code == 200
        else:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=payload)
                print(f"[OP-PUSH] Telegram 响应: {resp.status_code}", flush=True)
                return resp.status_code == 200
    except Exception as e:
        import traceback

        print(f"[OP-PUSH] Telegram 推送失败: {e}", flush=True)
        traceback.print_exc()
        return False


async def _push_to_discord(message: str) -> bool:
    """推送到 Discord"""
    if not DISCORD_WEBHOOK_URL:
        return False

    payload = {"content": message, "username": "OP Task Pusher"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(DISCORD_WEBHOOK_URL, json=payload)
            return resp.status_code in (200, 204)
    except Exception as e:
        print(f"[OP-PUSH] Discord 推送失败: {e}")
        return False


async def main():
    """主循环：监控 op-tasks.md 变化并推送"""
    import time

    print(f"[OP-PUSH] 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sys.stdout.flush()

    if not Path(OP_TASKS_FILE).exists():
        print(f"[OP-PUSH] 错误：文件不存在 {OP_TASKS_FILE}")
        sys.stdout.flush()
        return

    state = _load_state()
    last_hash = state.get("last_hash")
    last_push_time = state.get("last_push_time", 0)
    pending_hash = None  # 去抖：等待合并的 hash
    debounce_until = 0   # 去抖截止时间
    print(f"[OP-PUSH] 初始状态: last_hash={last_hash}, last_push={last_push_time}", flush=True)

    while True:
        try:
            now = time.time()
            current_hash = _read_file_hash(OP_TASKS_FILE)

            if current_hash and current_hash != last_hash:
                # 有变化 — 进入去抖窗口
                if pending_hash is None:
                    print(f"[OP-PUSH] 检测到变化: {current_hash[:8]}，进入去抖 {DEBOUNCE_SECONDS}s", flush=True)
                    debounce_until = now + DEBOUNCE_SECONDS
                    pending_hash = current_hash
                elif current_hash != pending_hash:
                    # 去抖窗口内文件又变了，重置计时器
                    pending_hash = current_hash
                    debounce_until = now + DEBOUNCE_SECONDS
                # else: 同一个 hash，不重置计时器

            # 去抖窗口结束，执行推送
            if pending_hash and now >= debounce_until:
                content = Path(OP_TASKS_FILE).read_text()
                tasks = _parse_op_tasks(content)
                print(f"[OP-PUSH] 去抖结束，解析到 {len(tasks)} 个任务", flush=True)

                # 只推送新完成的任务
                all_new_tasks = [
                    t for t in tasks
                    if t["status"] in ("ok", "fail")
                    and t["task_id"] not in state["last_pushed_tasks"]
                ]
                # 最新5条
                new_tasks = sorted(all_new_tasks, key=lambda x: x["line"], reverse=True)[:5]
                print(f"[OP-PUSH] 新任务: {len(all_new_tasks)} 个（推送最新 {len(new_tasks)} 个）", flush=True)

                # 最小推送间隔检查
                time_since_last = now - last_push_time
                if new_tasks and time_since_last >= MIN_PUSH_INTERVAL:
                    message = _format_message(new_tasks)
                    print(f"[OP-PUSH] 推送 {len(new_tasks)} 个任务", flush=True)

                    tg_ok = await _push_to_telegram(message)
                    dc_ok = await _push_to_discord(message)

                    if tg_ok or dc_ok:
                        state["last_hash"] = pending_hash
                        state["last_pushed_tasks"].extend([t["task_id"] for t in new_tasks])
                        state["last_push_time"] = now
                        last_hash = pending_hash
                        last_push_time = now
                        _save_state(state)
                    else:
                        print("[OP-PUSH] 推送失败，保留状态", flush=True)
                        last_hash = pending_hash
                elif new_tasks:
                    skip = int(MIN_PUSH_INTERVAL - time_since_last)
                    print(f"[OP-PUSH] 跳过推送（距上次仅 {int(time_since_last)}s，需等 {skip}s）", flush=True)
                    last_hash = pending_hash
                    state["last_hash"] = pending_hash
                    _save_state(state)
                else:
                    print("[OP-PUSH] 无新任务需要推送", flush=True)
                    last_hash = pending_hash
                    state["last_hash"] = pending_hash
                    _save_state(state)

                pending_hash = None

            await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            print(f"[OP-PUSH] 错误: {e}")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
