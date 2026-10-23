#!/usr/bin/env python3
"""
aider-hermes.py — Hermes 可调用的 Aider 包装脚本。

用法:
  python aider-hermes.py --task "把 utils.py 里的 parse_config 改成支持 yaml" --out /tmp/aider-result.md
  python aider-hermes.py --task-file /tmp/task.txt --out /tmp/aider-result.md

行为:
  - 在固定 tmux session 里串行执行 aider
  - 自动注入 .aider.conf.yaml 模型配置
  - 超时 20 分钟后强制退出，避免 runaway
  - 结果写到指定输出文件，Hermes 直接读取
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_TMUX_SESSION = "aider-hermes"
DEFAULT_TIMEOUT = 20 * 60
DEFAULT_MODEL = "aider/agent"
AIDER_CONF = Path.home() / ".aider.conf.yaml"
TASK_TEMPLATE = """\
请只做以下任务，不要偏离：

{task}

完成后，把结果摘要写到 {out}。
"""


def ensure_task_file(task: str, task_file: Path) -> Path:
    if task_file:
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(task, encoding="utf-8")
        return task_file
    p = Path("/tmp") / f"aider-task-{int(time.time())}.txt"
    p.write_text(task, encoding="utf-8")
    return p


def build_command(task_file: Path, out: Path, model: str, timeout: int) -> list[str]:
    message = TASK_TEMPLATE.format(task=task_file.read_text(encoding="utf-8"), out=out)
    cmd = [
        "tmux",
        "new-session",
        "-d",
        "-s",
        DEFAULT_TMUX_SESSION,
        "aider",
        "--model",
        model,
        "--yes",
        "--message",
        message,
    ]
    if AIDER_CONF.exists():
        cmd.extend(["--aider-config", str(AIDER_CONF)])
    return cmd


def wait_for_tmux(timeout: int) -> str:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        time.sleep(5)
        try:
            out = subprocess.run(
                ["tmux", "capture-pane", "-pt", DEFAULT_TMUX_SESSION, "-S", "-200"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
        except FileNotFoundError:
            return "tmux not found"
        last = out.strip()
        if any(s in last for s in ["Aider退出", "Aider exit", "completed", "finished", "error", "Traceback"]):
            return last
    return last or "timeout"


def main() -> int:
    parser = argparse.ArgumentParser(description="Aider Hermes wrapper")
    parser.add_argument("--task", help="任务文本")
    parser.add_argument("--task-file", type=Path, help="任务文件路径")
    parser.add_argument("--out", required=True, type=Path, help="结果输出文件")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Aider 模型")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="超时秒数")
    args = parser.parse_args()

    if not args.task and not args.task_file:
        print("ERROR: --task or --task-file required", file=sys.stderr)
        return 2

    task_file = ensure_task_file(args.task or Path(args.task_file).read_text(encoding="utf-8"), args.task_file)  # type: ignore[arg-type]
    args.out.parent.mkdir(parents=True, exist_ok=True)

    # kill stale session if exists
    subprocess.run(["tmux", "kill-session", "-t", DEFAULT_TMUX_SESSION], check=False)

    cmd = build_command(task_file, args.out, args.model, args.timeout)
    subprocess.run(cmd, check=False)

    result = wait_for_tmux(args.timeout)
    print(result)
    if not args.out.exists():
        args.out.write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
