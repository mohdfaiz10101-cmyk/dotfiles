#!/usr/bin/env python3
"""Chronos Subconscious — Idle dream analysis + nix precheck."""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

STATE_DIR = Path(Path.home() / ".local/state/chronos")
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "subconscious_state.json"

MEMORY_DIR = Path.home() / ".claude/projects/-home-charlie/memory"
REPORTS_DIR = Path.home() / ".cache/chronos-subconscious/reports"
MAX_REPORTS = 20

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "qwen3:8b-nothink"
MAX_INPUT_CHARS = 8000


def is_idle() -> bool:
    try:
        r = subprocess.run(
            ["loginctl", "show-session", "2", "-p", "IdleHint"],
            capture_output=True, text=True, timeout=5,
        )
        return "IdleHint=yes" in r.stdout
    except Exception:
        return False


def collect_memory() -> dict[str, str]:
    """Collect memory files within token budget."""
    priority = [
        "MEMORY.md", "lessons-learned.md", "ideas-roadmap.md",
        "pending-tasks.md", "troubleshooting.md",
        "nixos-config.md", "ai-tools.md", "setup-plan.md",
    ]
    files = {}
    total = 0
    for fname in priority:
        fpath = MEMORY_DIR / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        remaining = MAX_INPUT_CHARS - total
        if remaining <= 0:
            break
        if len(content) > remaining:
            content = content[:remaining]
        files[fname] = content
        total += len(content)
    return files


def call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 1500},
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("message", {}).get("content", "")


def analyze_patterns(files: dict[str, str]) -> str:
    context = "\n\n".join(
        f"=== {name} ===\n{content}" for name, content in files.items()
    )

    prompt = f"""你是系统潜意识分析器。分析以下用户的记忆文件集合，找出跨文件的隐藏模式。

输出格式：
## 模式发现
（跨文件重复出现的主题和技术关键词）

## 风险预警
（可能需要关注的系统问题，如 NVIDIA 驱动、磁盘、依赖冲突）

## 行动建议
（基于模式的具体下一步操作）

## 配置健康度
（基于 troubleshooting 和 nixos-config 内容的评估）

记忆文件：
{context}"""

    return call_ollama(prompt)


def precheck_nix() -> dict:
    try:
        proc = subprocess.run(
            ["nix", "flake", "check", "/etc/nixos", "--no-build-log"],
            capture_output=True, text=True, timeout=300,
        )
        output = (proc.stderr or proc.stdout)[-500:]
        return {"ok": proc.returncode == 0, "exit_code": proc.returncode, "tail": output}
    except subprocess.TimeoutExpired:
        return {"ok": None, "error": "timeout"}
    except Exception as e:
        return {"ok": None, "error": str(e)}


def write_state(status: str, details: dict = None):
    state = {
        "status": status,
        "timestamp": time.time(),
        "details": details or {},
    }
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def cleanup_old_reports():
    reports = sorted(REPORTS_DIR.glob("dream-*.md"))
    for old in reports[:-MAX_REPORTS]:
        old.unlink(missing_ok=True)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not is_idle():
        write_state("skipped_not_idle")
        return

    write_state("running")
    print("[RUNNING] Subconscious dream analysis...", file=sys.stderr)

    files = collect_memory()
    if not files:
        write_state("skipped_no_files")
        return

    # AI analysis
    try:
        report_text = analyze_patterns(files)
        ts = time.strftime("%Y%m%d-%H%M%S")
        report_file = REPORTS_DIR / f"dream-{ts}.md"
        report_file.write_text(report_text, encoding="utf-8")
        print(f"[OK] Report → {report_file}", file=sys.stderr)
    except Exception as e:
        write_state("error", {"message": str(e)})
        print(f"[FAILED] Analysis: {e}", file=sys.stderr)
        return

    # Nix precheck
    precheck = precheck_nix()
    print(f"[{'OK' if precheck.get('ok') else 'WARN'}] Nix precheck: {precheck.get('ok')}",
          file=sys.stderr)

    write_state("completed", {
        "report_file": str(report_file),
        "files_analyzed": list(files.keys()),
        "precheck": precheck,
    })

    cleanup_old_reports()


if __name__ == "__main__":
    main()
