#!/usr/bin/env python3
"""巡查结果聚合器 - 收集多个 Agent 的巡检结果并统一发送到 Discord

用法: python3 ~/bin/aggregate-inspection.py

支持聚合的 Agent:
- security-watchdog (安全看门狗)
- proxy-guardian (代理守护者)
- service-nurse (服务护士)
- discord-butler (Discord 管家)
- cost-accountant (成本会计师)
- memory-curator (记忆策展人)
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 导入 notify-discord 的发送函数
BIN_DIR = Path(__file__).parent
sys.path.insert(0, str(BIN_DIR))
sys.path.insert(
    0, str(BIN_DIR / ".notify-venv" / "lib" / "python3.12" / "site-packages")
)

# ── 配置 ────────────────────────────────────────────────────────

AGENTS = {
    "security-watchdog": {"name": "🛡️ 安全看门狗", "emoji": "🔒"},
    "proxy-guardian": {"name": "🌐 代理守护者", "emoji": "🔀"},
    "service-nurse": {"name": "🏥 服务护士", "emoji": "💊"},
    "discord-butler": {"name": "🎩 Discord 管家", "emoji": "🤖"},
    "cost-accountant": {"name": "💰 成本会计师", "emoji": "📊"},
    "memory-curator": {"name": "📚 记忆策展人", "emoji": "🗃️"},
}

STATE_FILE = Path(Path.home() / ".local/state/inspection-aggregate-state.json")

# ── 状态管理 ────────────────────────────────────────────────────


def load_state() -> Dict:
    """加载聚合状态"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {"reports": []}


def save_state(state: Dict) -> None:
    """保存聚合状态"""
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ── 聚合逻辑 ────────────────────────────────────────────────────


def add_report(agent_name: str, content: str, status: str = "OK") -> None:
    """添加单条巡检报告"""
    state = load_state()
    report = {
        "agent": agent_name,
        "content": content,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }
    state["reports"].append(report)
    save_state(state)
    print(f"[OK] {agent_name} 报告已添加")


async def send_aggregated_report(channel: str = "daily-digest") -> bool:
    """发送聚合后的巡检报告到 Discord"""
    state = load_state()
    reports = state.get("reports", [])

    if not reports:
        print("[SKIP] 无巡检报告可发送")
        return False

    # 按 Agent 分组
    grouped: Dict[str, List[str]] = {}
    for report in reports:
        agent = report["agent"]
        if agent not in grouped:
            grouped[agent] = []
        grouped[agent].append(report["content"])

    # 构建嵌入内容
    lines = [f"**巡检时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    lines.append("**巡检摘要**:\n")

    total_ok = 0
    total_warn = 0
    total_fail = 0

    for agent_name, contents in grouped.items():
        agent_info = AGENTS.get(agent_name, {"name": agent_name, "emoji": "🔹"})
        lines.append(f"\n{agent_info['emoji']} **{agent_info['name']}**")

        # 统计状态
        for content in contents:
            if "[OK]" in content:
                total_ok += 1
            elif "[WARN]" in content or "[⚠️]" in content:
                total_warn += 1
            elif "[FAIL]" in content or "[❌]" in content:
                total_fail += 1

            # 提取关键信息（去除重复的标题）
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("=") and not line.startswith("─"):
                    lines.append(f"  {line}")

    # 添加统计
    lines.append(f"\n**统计**: ✓{total_ok} ⚠️{total_warn} ✗{total_fail}")

    content = "\n".join(lines)

    # 发送到 Discord
    level = "P0" if total_fail > 0 else ("P1" if total_warn > 0 else "P2")
    success = await send_message(content, "📋 巡检聚合报告", level, channel)

    if success:
        # 清空已发送的报告
        state["reports"] = []
        save_state(state)
        print(f"[OK] 聚合报告已发送到 #{channel}")

    return success


# ── 命令行接口 ──────────────────────────────────────────────────


async def send_discord_message(content, title, level, channel_name="alerts"):
    """发送消息到 Discord（调用 notify-discord）"""
    import subprocess

    # 使用 subprocess 调用 notify-discord
    cmd = [str(BIN_DIR / "notify-discord.py"), level, title, channel_name]
    result = subprocess.run(
        cmd,
        input=content,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode == 0


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n用法:")
        print(
            "  添加报告: python3 aggregate-inspection.py add <agent> <content> [status]"
        )
        print("  发送报告: python3 aggregate-inspection.py send [channel]")
        print("\n示例:")
        print(
            "  python3 aggregate-inspection.py add service-nurse 'Docker 全正常，24 服务失败' WARN"
        )
        print("  python3 aggregate-inspection.py send daily-digest")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 4:
            print("[FAIL] 用法: add <agent> <content> [status]")
            sys.exit(1)
        agent = sys.argv[2]
        content = sys.argv[3]
        status = sys.argv[4] if len(sys.argv) > 4 else "OK"
        add_report(agent, content, status)

    elif command == "send":
        channel = sys.argv[2] if len(sys.argv) > 2 else "daily-digest"
        # 使用替代的发送函数
        original_send = globals().get("send_message")
        globals()["send_message"] = send_discord_message
        try:
            success = await send_aggregated_report(channel)
            sys.exit(0 if success else 1)
        finally:
            if original_send:
                globals()["send_message"] = original_send

    else:
        print(f"[FAIL] 未知命令: {command}")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 4:
            print("[FAIL] 用法: add <agent> <content> [status]")
            sys.exit(1)
        agent = sys.argv[2]
        content = sys.argv[3]
        status = sys.argv[4] if len(sys.argv) > 4 else "OK"
        add_report(agent, content, status)

    elif command == "send":
        channel = sys.argv[2] if len(sys.argv) > 2 else "daily-digest"
        success = await send_aggregated_report(channel)
        sys.exit(0 if success else 1)

    else:
        print(f"[FAIL] 未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
