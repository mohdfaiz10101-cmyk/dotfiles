#!/usr/bin/env python3
"""巡查结果聚合器
读取多个 agent 的巡查结果，合并后通过 Discord 发送
"""

import json
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 状态文件目录
STATE_DIR = Path(Path.home() / ".local/state/inspection-results")
STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_result(agent_name: str) -> dict:
    """加载单个 agent 的巡查结果"""
    result_file = STATE_DIR / f"{agent_name}.json"
    if not result_file.exists():
        return None

    try:
        data = json.loads(result_file.read_text())
        # 检查结果是否过期（超过 1 小时）
        result_time = datetime.fromisoformat(data.get("timestamp", "1970-01-01"))
        if (datetime.now() - result_time).total_seconds() > 3600:
            return None
        return data
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def aggregate_results() -> dict:
    """聚合所有 agent 的巡查结果"""
    # 预定义的巡查 agent 列表
    agents = [
        "security-watchdog",
        "proxy-guardian",
        "service-nurse",
        "discord-butler",
        "cost-accountant",
        "memory-curator",
    ]

    results = {}
    for agent in agents:
        result = load_result(agent)
        if result:
            results[agent] = result

    return results


def format_summary(results: dict) -> str:
    """格式化汇总信息"""
    total = len(results)
    ok_count = sum(1 for r in results.values() if r.get("status") == "OK")
    fail_count = total - ok_count

    summary_lines = [
        f"**巡查汇总** — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"总代理: {total} | 正常: {ok_count} | 异常: {fail_count}\n",
    ]

    for agent, result in results.items():
        status = result.get("status", "UNKNOWN")
        emoji = "✅" if status == "OK" else "⚠️"
        summary_lines.append(f"{emoji} **{agent}**: {result.get('summary', '无数据')}")

        # 如果有详细异常信息
        if result.get("status") != "OK" and result.get("details"):
            summary_lines.append(f"   └─ {result['details']}")

    return "\n".join(summary_lines)


async def send_to_discord(content: str):
    """通过 notify-discord.py 发送消息"""
    notify_script = Path.home() / "bin" / "notify-discord.py"
    if not notify_script.exists():
        print(f"[FAIL] notify-discord.py 不存在", file=sys.stderr)
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            str(notify_script),
            "P1",
            "巡查结果汇总",
            "ops",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(content.encode())

        if proc.returncode == 0:
            print("[OK] 已发送到 Discord")
            return True
        else:
            print(f"[FAIL] 发送失败: {stderr.decode()}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[FAIL] 执行异常: {e}", file=sys.stderr)
        return False


async def main():
    """主函数"""
    results = aggregate_results()

    if not results:
        print("[SKIP] 无可用的巡查结果")
        return

    # 输出聚合结果到控制台（供其他脚本调用）
    summary = format_summary(results)
    print(summary)

    # 发送到 Discord（如果指定了 --discord 参数）
    if "--discord" in sys.argv:
        await send_to_discord(summary)


if __name__ == "__main__":
    asyncio.run(main())
