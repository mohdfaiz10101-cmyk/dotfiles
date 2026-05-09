#!/usr/bin/env python3
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
OP_RESULTS_FILE = "/tmp/op-task-results.json"
STATE_FILE = "/tmp/op-push-state.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# 推送间隔（秒）
POLL_INTERVAL = 30


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

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        # 不使用代理，直接连接
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.post(url, json=payload)
            print(
                f"[OP-PUSH] Telegram 响应: {resp.status_code} {resp.text[:100]}",
                flush=True,
            )
            return resp.status_code == 200
    except Exception as e:
        import traceback

        print(f"[OP-PUSH] Telegram 推送失败: {e}", flush=True)
        traceback.print_exc()
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        print(f"[OP-PUSH] Telegram 推送失败: {e}")
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
    print(f"[OP-PUSH] 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sys.stdout.flush()

    if not Path(OP_TASKS_FILE).exists():
        print(f"[OP-PUSH] 错误：文件不存在 {OP_TASKS_FILE}")
        sys.stdout.flush()
        return

    state = _load_state()
    last_hash = state["last_hash"]
    print(f"[OP-PUSH] 初始状态: last_hash={last_hash}")
    sys.stdout.flush()

    while True:
        try:
            # 检测文件变化
            current_hash = _read_file_hash(OP_TASKS_FILE)
            print(
                f"[OP-PUSH] 检查: current={current_hash[:8] if current_hash else 'None'}, last={last_hash[:8] if last_hash else 'None'}",
                flush=True,
            )
            if current_hash and current_hash != last_hash:
                print(f"[OP-PUSH] 检测到文件变化: {current_hash[:8]}", flush=True)

                # 解析任务
                content = Path(OP_TASKS_FILE).read_text()
                tasks = _parse_op_tasks(content)
                print(f"[OP-PUSH] 解析到 {len(tasks)} 个任务", flush=True)

                # 过滤：只推送刚完成/失败的任务（不在 last_pushed_tasks 中）
                all_new_tasks = [
                    t
                    for t in tasks
                    if t["status"] in ("ok", "fail")
                    and t["task_id"] not in state["last_pushed_tasks"]
                ]
                # 限制最多推送 5 个，避免历史任务刷屏
                new_tasks = sorted(
                    all_new_tasks, key=lambda x: x["line"], reverse=True
                )[:5]
                print(
                    f"[OP-PUSH] 新任务: {len(all_new_tasks)} 个（推送最新 {len(new_tasks)} 个）",
                    flush=True,
                )

                if new_tasks:
                    message = _format_message(new_tasks)
                    print(f"[OP-PUSH] 推送 {len(new_tasks)} 个任务", flush=True)
                    print(f"[OP-PUSH] 消息预览: {message[:100]}...", flush=True)

                    # 推送到 Telegram 和 Discord
                    tg_ok = await _push_to_telegram(message)
                    print(f"[OP-PUSH] Telegram: {'✅' if tg_ok else '❌'}", flush=True)
                    dc_ok = await _push_to_discord(message)
                    print(f"[OP-PUSH] Discord: {'✅' if dc_ok else '❌'}", flush=True)

                    if tg_ok or dc_ok:
                        # 更新状态
                        state["last_hash"] = current_hash
                        state["last_pushed_tasks"].extend(
                            [t["task_id"] for t in new_tasks]
                        )
                        _save_state(state)
                    else:
                        print("[OP-PUSH] 推送全部失败，保留状态等待下次重试")
                else:
                    print("[OP-PUSH] 无新任务需要推送")
                    state["last_hash"] = current_hash
                    _save_state(state)

            await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            print(f"[OP-PUSH] 错误: {e}")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
