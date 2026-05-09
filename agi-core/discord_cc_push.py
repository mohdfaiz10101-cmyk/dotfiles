#!/usr/bin/env python3
"""CC Session → Discord #cc 推送
读取：今日完成任务 + op-task-results + Letta会话记忆
推送：Discord #cc 频道
用法：python3 discord_cc_push.py [--session-end "会话主题描述"]
"""
import json, os, sys, re, time, subprocess, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, date

DISCORD_TOKEN   = "MTQ5MDY0MTY3ODEzNzAzMjg0NA.G7dnjb.8XnDoykFr9O8SRsQH1nnCXiV0Ge2LEOGTI47f8"
CC_CHANNEL_ID   = "1490986400747884585"
PROXY           = os.getenv("https_proxy", os.getenv("HTTPS_PROXY", "http://127.0.0.1:7890"))
LITELLM         = "http://localhost:4000/v1"
LITELLM_KEY     = "sk-litellm-charlie-2026"
MODEL           = "glm-5-turbo"

OP_TASKS        = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
OP_RESULTS      = Path("/tmp/op-task-results.json")
LESSONS         = Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"
TODAY           = date.today().strftime("%Y-%m-%d")

# ── Discord 发消息 ────────────────────────────────────────────────────
def discord_send(content: str) -> dict:
    chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
    last = {}
    for chunk in chunks:
        payload = json.dumps({"content": chunk})
        result = subprocess.run([
            "curl", "-s", "--proxy", PROXY,
            "-X", "POST",
            f"https://discord.com/api/v10/channels/{CC_CHANNEL_ID}/messages",
            "-H", f"Authorization: Bot {DISCORD_TOKEN}",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ], capture_output=True, text=True, timeout=20)
        try:
            last = json.loads(result.stdout)
        except:
            print(f"[discord_send] curl stdout: {result.stdout[:200]}", file=sys.stderr)
    return last

# ── 读取今日完成任务 ──────────────────────────────────────────────────
def get_completed_tasks() -> list[str]:
    if not OP_TASKS.exists():
        return []
    text = OP_TASKS.read_text()
    tasks = []
    for line in text.splitlines():
        # 匹配 [x] 或 [完成] 开头的任务行，且包含今日日期
        if re.search(r'\[x\]|\[完成', line, re.I):
            if TODAY in line or len(tasks) < 20:  # 取今日完成 or 最近20条
                clean = re.sub(r'^\s*[-*]\s*\[.+?\]\s*', '', line).strip()
                clean = re.sub(r'\[完成.*?\].*$', '', clean).strip()
                if clean and len(clean) > 5:
                    tasks.append(clean[:100])
    return tasks[-15:]  # 最近15条

# ── 读取 OP 任务结果 ──────────────────────────────────────────────────
def get_op_results() -> list[dict]:
    for path in [OP_RESULTS, Path.home() / "op-task-results.json"]:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if isinstance(data, list):
                    return [r for r in data if isinstance(r, dict)][-10:]
                return []
            except:
                pass
    return []

# ── 读取今日 lessons-learned ──────────────────────────────────────────
def get_today_lessons() -> list[str]:
    if not LESSONS.exists():
        return []
    lines, capturing = [], False
    for line in LESSONS.read_text().splitlines():
        if TODAY in line:
            capturing = True
        if capturing and line.startswith("- ") and TODAY in lines[-1] if lines else False:
            lines.append(line.strip())
        elif capturing and line.startswith("- [") and TODAY in line:
            lines.append(re.sub(r'^- \[.*?\]\s*', '', line).strip())
    return lines[:5]

# ── GLM 生成对话摘要 ──────────────────────────────────────────────────
def llm_summarize(topic: str, tasks: list, results: list, lessons: list) -> str:
    tasks_text = "\n".join(f"• {t}" for t in tasks) if tasks else "（无记录）"
    results_text = "\n".join(
        f"• [{r.get('status','?')}] {r.get('task','')[:60]}" for r in results
    ) if results else "（无记录）"
    lessons_text = "\n".join(f"• {l}" for l in lessons) if lessons else "（无）"

    prompt = f"""将以下 CC（Claude Code）会话信息整理成简洁的中文摘要，用于 Discord 推送。

会话主题：{topic}
今日完成任务：
{tasks_text}

OP执行结果：
{results_text}

今日新增经验：
{lessons_text}

要求：
- 用3-5句话总结今天做了什么、完成了什么
- 突出重要成果（哪些功能上线了、哪些问题解决了）
- 提及还有什么未完成
- 语气简洁专业，不废话
- 100字以内"""

    try:
        req_data = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
        }).encode()
        req = urllib.request.Request(
            f"{LITELLM}/chat/completions",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LITELLM_KEY}",
            }
        )
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"（AI摘要不可用: {e}）"

# ── 构建纯文本 Discord 消息 ───────────────────────────────────────────
def build_message(topic: str, summary: str, tasks: list, results: list) -> str:
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    done = sum(1 for r in results if "完成" in r.get("status", ""))
    fail = sum(1 for r in results if "失败" in r.get("status", ""))

    lines = [
        f"## 🤖 CC Session · {now}",
        f"**主题：** {topic}",
        "",
        f"### 💬 会话摘要",
        summary,
        "",
    ]
    if tasks:
        lines += [f"### ✅ 今日完成（{len(tasks)}项）"]
        lines += [f"- {t[:80]}" for t in tasks[:10]]
        lines.append("")
    if results:
        lines += [f"### ⚙️ OP执行结果（{done}成功 / {fail}失败）"]
        for r in results[:6]:
            icon = "✅" if "完成" in r.get("status","") else "❌"
            lines.append(f"{icon} {r.get('task','')[:60]}")
        lines.append("")

    return "\n".join(lines)

# ── 主流程 ────────────────────────────────────────────────────────────
def main():
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "今日工作汇报"
    print(f"[CC Push] 推送主题: {topic}")

    tasks   = get_completed_tasks()
    results = get_op_results()
    lessons = get_today_lessons()
    print(f"[CC Push] 任务:{len(tasks)} OP结果:{len(results)}")

    summary = llm_summarize(topic, tasks, results, lessons)
    content = build_message(topic, summary, tasks, results)

    msg = discord_send(content)
    if msg.get("id"):
        print(f"[CC Push] ✅ 推送成功 → msg:{msg['id']}")
    else:
        print(f"[CC Push] ❌ 失败: {msg}")

if __name__ == "__main__":
    main()
