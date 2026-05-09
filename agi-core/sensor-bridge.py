"""
sensor-bridge.py — Android 传感器桥接守护进程
每5分钟采集 Android 传感器数据，写入 /tmp/android-telemetry.jsonl
同时维护 decision-log.db 记录 brain 决策历史

Usage:
    python3 sensor-bridge.py           # 守护进程模式（每5分钟采集）
    python3 sensor-bridge.py --once    # 单次采集后退出
"""

import argparse
import json
import os
import signal
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# 将 agi/ 加入 sys.path，确保能 import 兄弟模块
sys.path.insert(0, str(Path(__file__).parent))

TELEMETRY_FILE = "/tmp/android-telemetry.jsonl"
DB_PATH = Path(__file__).parent / "decision-log.db"
COLLECT_INTERVAL = 300  # 5 分钟

_running = True


def _init_db() -> sqlite3.Connection:
    """初始化 decision-log.db，创建 decisions 表。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            sense_summary TEXT,
            think_summary TEXT,
            actions TEXT,
            cognitive_profile TEXT
        )
    """)
    conn.commit()
    return conn


def collect_android_data() -> dict:
    """采集 Android 传感器数据。复用 android_sensor.sense_android()。"""
    try:
        from android_sensor import sense_android

        data = sense_android()
        data["bridge_status"] = "ok"
        data["collected_at"] = datetime.now().isoformat()
        return data
    except Exception as e:
        return {
            "bridge_status": "error",
            "error": str(e),
            "collected_at": datetime.now().isoformat(),
        }


def append_telemetry(data: dict) -> None:
    """追加一行 JSON 到 /tmp/android-telemetry.jsonl。"""
    line = json.dumps(data, ensure_ascii=False)
    with open(TELEMETRY_FILE, "a") as f:
        f.write(line + "\n")


def record_decision(
    conn: sqlite3.Connection,
    sense_summary: str,
    think_summary: str,
    actions: str,
    cognitive_profile: str = "",
) -> None:
    """记录一条 brain 决策到 decision-log.db。"""
    conn.execute(
        "INSERT INTO decisions (timestamp, sense_summary, think_summary, actions, cognitive_profile) VALUES (?,?,?,?,?)",
        (
            datetime.now().isoformat(),
            sense_summary,
            think_summary,
            actions,
            cognitive_profile,
        ),
    )
    conn.commit()


def _signal_handler(signum, frame):
    """优雅退出信号处理。"""
    global _running
    print(f"\n[bridge] 收到信号 {signum}，优雅退出...")
    _running = False


def main_loop():
    """守护进程主循环。"""
    global _running
    conn = _init_db()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"[bridge] 传感器桥接启动，间隔 {COLLECT_INTERVAL}s")

    while _running:
        data = collect_android_data()
        append_telemetry(data)
        print(
            f"[bridge] {datetime.now().strftime('%H:%M:%S')} 采集完成: {data.get('bridge_status', '?')}"
        )

        # 等待间隔，但每秒检查退出信号
        for _ in range(COLLECT_INTERVAL):
            if not _running:
                break
            time.sleep(1)

    conn.close()
    print("[bridge] 已退出")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Android 传感器桥接")
    parser.add_argument("--once", action="store_true", help="只采集一次后退出")
    args = parser.parse_args()

    if args.once:
        data = collect_android_data()
        append_telemetry(data)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        main_loop()
