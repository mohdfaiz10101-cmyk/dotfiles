#!/usr/bin/env python3
"""微信 Agent 状态采集"""

import json
from pathlib import Path


def run() -> dict:
    wechat_status = {}
    wechat_path = Path("/tmp/wechat-agent-status.json")
    if wechat_path.exists():
        try:
            wechat_status = json.loads(wechat_path.read_text())
        except Exception:
            wechat_status = {"error": "读取失败"}
    return {"wechat": wechat_status}


if __name__ == "__main__":
    print(json.dumps(run()))
