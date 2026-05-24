#!/home/charlie/bin/.notify-venv/bin/python3
"""
tg_healer.py — L4 自主修复定时脚本
systemd timer 每5分钟运行，扫描失败服务并自动修复

用法:
  python3 tg_healer.py              # 扫描+修复+通知
  python3 tg_healer.py --dry-run    # 仅扫描不修复
  python3 tg_healer.py --report     # 仅报告当前状态
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / "dotfiles/agi-core"))
from tg_pilot import scan_and_heal, format_heal_results
from tg_group_router import get_router, Category

STATE_FILE = Path.home() / ".local/state/tg-pilot/healer_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": None, "total_heals": 0, "failed_heals": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def main():
    dry_run = "--dry-run" in sys.argv
    report_only = "--report" in sys.argv

    state = load_state()

    if report_only:
        # 仅报告失败服务
        router = get_router()
        status = await router.status()
        print(status)
        return

    if dry_run:
        print("[DRY-RUN] 扫描模式，不执行修复")
        results = await scan_and_heal()
        for r in results:
            print(f"  {r['service']}: {r['final_diagnosis'][:50]}")
        return

    # 正常模式：扫描+修复+通知
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始自主修复扫描...")
    results = await scan_and_heal()

    if not results:
        print("  无失败服务，跳过")
        return

    healed = [r for r in results if r["healed"]]
    failed = [r for r in results if not r["healed"]]

    state["last_run"] = datetime.now().isoformat()
    state["total_heals"] += len(healed)

    if failed:
        state["failed_heals"].append({
            "time": datetime.now().isoformat(),
            "services": [r["service"] for r in failed],
            "diagnosis": [r["final_diagnosis"][:50] for r in failed],
        })
        # 只保留最近20条
        state["failed_heals"] = state["failed_heals"][-20:]

    save_state(state)

    # 通知
    router = get_router()
    report = format_heal_results(results)
    category = "system" if healed else "task"

    try:
        await router.route_message(report, category)
        print(f"  通知已发送: {len(healed)}个修复, {len(failed)}个失败")
    except Exception as e:
        print(f"  通知发送失败: {e}")

    await router.cleanup()


if __name__ == "__main__":
    asyncio.run(main())