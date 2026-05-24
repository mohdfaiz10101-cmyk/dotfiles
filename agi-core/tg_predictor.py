#!/home/charlie/bin/.notify-venv/bin/python3
"""
tg_predictor.py — L5 预判感知定时脚本
systemd timer 每30分钟运行，采集指标+异常检测+提前预警

用法:
  python3 tg_predictor.py              # 采集+检测+预警
  python3 tg_predictor.py --collect    # 仅采集指标
  python3 tg_predictor.py --check      # 仅检测不通知
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / "dotfiles/agi-core"))
from tg_pilot import init_metrics_db, collect_metrics, detect_anomalies
from tg_group_router import get_router, Category


async def main():
    collect_only = "--collect" in sys.argv
    check_only = "--check" in sys.argv

    init_metrics_db()

    # 采集指标
    metrics = collect_metrics()
    ts = datetime.now().strftime("%H:%M:%S")

    if collect_only:
        print(f"[{ts}] CPU:{metrics['cpu']:.0f}% MEM:{metrics['mem']:.0f}% "
              f"LOAD:{metrics['load_1m']:.1f} DISK:/={metrics['disk_root']}% "
              f"/mnt/ai={metrics['disk_ai']}% FAIL:{metrics['failed']}")
        return

    # 检测异常
    alerts = detect_anomalies()

    if not alerts:
        print(f"[{ts}] 无异常趋势")
        return

    if check_only:
        print(f"[{ts}] 检测到 {len(alerts)} 个异常:")
        for a in alerts:
            print(f"  ⚠️ {a}")
        return

    # 发送预警通知
    router = get_router()
    alert_text = (
        "🔮 <b>预判预警 — 异常趋势检测</b>\n\n"
        + "\n".join(f"⚠️ {a}" for a in alerts)
        + "\n\n"
        f"📊 <i>当前: CPU {metrics['cpu']:.0f}% | "
        f"MEM {metrics['mem']:.0f}% | "
        f"LOAD {metrics['load_1m']:.1f} | "
        f"失败服务 {metrics['failed']}</i>"
    )

    try:
        await router.route_message(alert_text, "system")
        print(f"[{ts}] 预警已发送: {len(alerts)}个异常")
    except Exception as e:
        print(f"[{ts}] 预警发送失败: {e}")

    await router.cleanup()


if __name__ == "__main__":
    asyncio.run(main())