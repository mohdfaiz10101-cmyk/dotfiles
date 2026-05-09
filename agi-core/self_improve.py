#!/usr/bin/env python3
"""每日自我改进 Agent — 用 GLM 免费额度自动审查代码，产出改进建议写入 op-tasks"""

import json, urllib.request, urllib.error, datetime, pathlib, os, sys, subprocess

TARGETS = [
    ("brain.py", "~/agi/brain.py"),
    ("think.py", "~/agi/think.py"),
    ("kanban.html", "~/launcher/kanban.html"),
    ("launcher-server.py", "~/launcher/launcher-server.py"),
    ("hub-api.py", "~/hub/hub-api.py"),
]
LITELLM = "http://localhost:4000/v1/chat/completions"
API_KEY = os.environ.get("LITELLM_KEY", "sk-litellm-charlie-2026")
MODEL = "glm-5-turbo"
OP_TASKS = pathlib.Path(
    "~/.claude/projects/-home-charlie/memory/op-tasks.md"
).expanduser()
MAX_CHARS = 3000


def review_file(name: str, path: str) -> str | None:
    p = pathlib.Path(path).expanduser()
    if not p.exists():
        return None
    code = p.read_text(errors="replace")[:MAX_CHARS]
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是代码审查员。审查以下代码，找出最重要的1个改进点。"
                        "用一句话描述，格式：- [ ] [SELF-IMPROVE] {文件名}: {改进建议}。"
                        "只输出这行，不要解释。"
                    ),
                },
                {"role": "user", "content": f"# {name}\n```\n{code}\n```"},
            ],
            "max_tokens": 150,
        }
    ).encode()

    req = urllib.request.Request(
        LITELLM,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if content and "SELF-IMPROVE" in content:
                return content
            return None
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TimeoutError) as e:
        print(f"[SKIP] {name}: {e}", file=sys.stderr)
        return None


def _write_to_letta(suggestions: list[str]) -> None:
    try:
        from pathlib import Path

        agent_id = os.environ.get("LETTA_AGENT_ID", "")
        if not agent_id:
            req = urllib.request.Request(
                "http://localhost:8283/v1/agents/",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                agents = json.loads(resp.read())
                if agents:
                    agent_id = agents[0].get("id", "")
        if not agent_id:
            print("[LETTA] 无法获取 agent_id，跳过回流", file=sys.stderr)
            return

        content = (
            f"[SELF-IMPROVE] [{datetime.date.today().isoformat()}] 审查结论：\n"
            + "\n".join(suggestions)
        )
        payload = json.dumps({"content": content[:1000]}).encode()
        req = urllib.request.Request(
            f"http://localhost:8283/v1/agents/{agent_id}/archival-memory/",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"[LETTA] 审查结论已写入 archival ({len(suggestions)}条)")
            else:
                print(f"[LETTA] 写入失败: HTTP {resp.status}", file=sys.stderr)
    except Exception as e:
        print(f"[LETTA] 回流异常: {e}", file=sys.stderr)


def _trigger_evolve() -> None:
    try:
        flow_file = pathlib.Path(__file__).parent / "flows" / "evolve.py"
        if not flow_file.exists():
            print("[EVOLVE] evolve.py 不存在，跳过触发", file=sys.stderr)
            return
        proc = subprocess.run(
            [sys.executable, str(flow_file)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        idx = pathlib.Path(__file__).parent / "flows" / "index.json"
        if idx.exists():
            data = json.loads(idx.read_text())
            for f in data.get("flows", []):
                if f["name"] == "evolve":
                    f["runs"] = f.get("runs", 0) + 1
                    break
            idx.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"[EVOLVE] flow 已触发 (exit={proc.returncode})")
    except TimeoutError:
        print("[EVOLVE] 超时120s，跳过", file=sys.stderr)
    except Exception as e:
        print(f"[EVOLVE] 触发失败: {e}", file=sys.stderr)


def run():
    today = datetime.date.today().isoformat()
    suggestions = []
    for name, path in TARGETS:
        result = review_file(name, path)
        if result:
            suggestions.append(result)
            print(f"[OK] {name}: {result}")

    if not suggestions:
        print(f"[SELF-IMPROVE {today}] 无改进建议（所有审查均跳过或无建议）")
        return

    with open(OP_TASKS, "a") as f:
        f.write(f"\n### [SELF-IMPROVE {today}] GLM 自动代码审查\n")
        for s in suggestions:
            f.write(s + "\n")
    print(f"[SELF-IMPROVE {today}] 写入 {len(suggestions)} 条改进建议 → op-tasks.md")

    # 回流：审查结论→Letta archival + 触发 evolve flow
    _write_to_letta(suggestions)
    _trigger_evolve()


if __name__ == "__main__":
    run()
