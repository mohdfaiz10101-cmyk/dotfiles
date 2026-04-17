#!/usr/bin/env python3
"""轻量级启动器后端 - 接收 HTTP 请求启动桌面应用"""
import subprocess
import urllib.parse
import json
import glob
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import re
import urllib.request as ureq

PORT = 9875
LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
CHRONOS_DIR = "/tmp/chronos"
MEMORY_DIR = os.path.expanduser("~/.claude/projects/-home-charlie/memory")
DREAM_DIR = os.path.expanduser("~/.cache/chronos-subconscious/reports")

class LauncherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=LAUNCHER_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/chronos-data":
            self._serve_chronos_data()
            return

        if parsed.path == "/kanban-data":
            self._serve_kanban_data()
            return

        if parsed.path == "/op-status":
            self._serve_op_status()
            return

        if parsed.path == "/todo-data":
            todo_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/pending-tasks.md")
            try:
                with open(todo_file, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"No tasks file")
            return

        if parsed.path == "/api/cc-op-dialog":
            params = urllib.parse.parse_qs(parsed.query)
            n = int(params.get("n", ["20"])[0])
            self._serve_cc_op_dialog(n)
            return

        if parsed.path == "/api/cc-op-discuss-history":
            f = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-discuss.jsonl")
            msgs = []
            last_session = None
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try:
                                m = json.loads(line)
                                if last_session is None: last_session = m.get("session","")
                                if m.get("session","") == last_session: msgs.append(m)
                            except Exception: pass
            except FileNotFoundError: pass
            self._json_response({"messages": msgs[-30:]})
            return

        if parsed.path == "/api/orchestrate-history":
            f = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-orchestrate.jsonl")
            decisions = []
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try: decisions.append(json.loads(line))
                            except Exception: pass
            except FileNotFoundError: pass
            self._json_response({"decisions": decisions[-10:]})
            return

        if parsed.path == "/api/desktop-tree":
            desktop = os.path.expanduser("~/Desktop")
            usage_file = os.path.expanduser("~/.local/share/desktop-tree-usage.json")
            usage = {}
            try:
                with open(usage_file, 'r') as uf:
                    usage = json.load(uf)
            except Exception:
                pass
            tree = {}
            try:
                for folder in sorted(os.listdir(desktop)):
                    folder_path = os.path.join(desktop, folder)
                    if os.path.isdir(folder_path):
                        items = []
                        for f in sorted(os.listdir(folder_path)):
                            name = f
                            if f.endswith('.desktop'):
                                fp = os.path.join(folder_path, f)
                                try:
                                    with open(fp, 'r', encoding='utf-8') as df:
                                        for line in df:
                                            m = re.match(r'^Name\[zh_CN\]=(.+)', line)
                                            if m:
                                                name = m.group(1).strip()
                                                break
                                            m = re.match(r'^Name=(.+)', line)
                                            if m:
                                                name = m.group(1).strip()
                                except Exception:
                                    pass
                            elif f.endswith('.md') or f.endswith('.html'):
                                name = f.rsplit('.', 1)[0]
                            else:
                                name = f
                            count = usage.get(f, 0)
                            items.append({"name": name, "file": f, "count": count})
                        # Sort by usage frequency (high first), then alphabetically
                        items.sort(key=lambda x: (-x["count"], x["name"]))
                        tree[folder] = items
            except Exception:
                pass
            data = json.dumps(tree, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return

        if parsed.path == "/memory-search":
            params = urllib.parse.parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            if not query:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "missing q parameter"}).encode())
                return
            results = []
            for fname in os.listdir(MEMORY_DIR):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(MEMORY_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            if query.lower() in line.lower():
                                results.append({
                                    "file": fname,
                                    "line": i,
                                    "content": line.strip()[:200],
                                })
                                if len(results) >= 50:
                                    break
                except Exception:
                    pass
                if len(results) >= 50:
                    break
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"query": query, "results": results}, ensure_ascii=False).encode())
            return

        if parsed.path == "/launch":
            params = urllib.parse.parse_qs(parsed.query)
            app = params.get("app", [None])[0]
            if app and app.endswith(".desktop"):
                try:
                    subprocess.Popen(
                        ["gtk-launch", app],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    # Track usage frequency
                    usage_file = os.path.expanduser("~/.local/share/desktop-tree-usage.json")
                    try:
                        with open(usage_file, 'r') as uf:
                            usage = json.load(uf)
                    except Exception:
                        usage = {}
                    usage[app] = usage.get(app, 0) + 1
                    try:
                        with open(usage_file, 'w') as uf:
                            json.dump(usage, uf)
                    except Exception:
                        pass
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(f"OK: {app}".encode())
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad app name")
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if parsed.path == "/kanban-move":
            try:
                data = json.loads(body)
                self._kanban_move(data["line_text"], data["new_status"])
                self._json_response({"ok": True})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/api/chat":
            try:
                data = json.loads(body)
                reply = self._proxy_chat(data.get("messages", []), data.get("context", ""))
                self._json_response({"reply": reply})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/kanban-delegate":
            try:
                data = json.loads(body)
                self._kanban_delegate(data["text"], data.get("raw",""), data["target"])
                self._json_response({"ok": True})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/api/chat-route":
            try:
                data = json.loads(body)
                result = self._route_chat(data.get("messages", []), data.get("context", ""), data.get("agent", "auto"))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e), "type": "text"}, 500)
            return

        if parsed.path == "/api/exec":
            try:
                data = json.loads(body)
                result = self._exec_command(data.get("cmd", ""))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e), "ok": False}, 500)
            return

        if parsed.path == "/api/trigger-op":
            try:
                data = json.loads(body)
                result = self._trigger_op_job(data.get("job", ""))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e), "ok": False}, 500)
            return

        if parsed.path == "/api/review":
            try:
                data = json.loads(body)
                result = self._run_review(data.get("task_text",""), data.get("source","CC"), data.get("raw",""))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e), "verdict": "error"}, 500)
            return

        if parsed.path == "/api/cc-op-speak":
            try:
                data = json.loads(body)
                result = self._cc_op_speak(data.get("rounds", 1))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/api/cc-op-discuss":
            try:
                data = json.loads(body)
                result = self._cc_op_discuss(data.get("topic",""), data.get("rounds", 2))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/api/orchestrate":
            try:
                data = json.loads(body)
                result = self._orchestrate(data.get("topic",""), data.get("context",""))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/api/op-notify":
            try:
                data = json.loads(body)
                result = self._op_notify(data)
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()

    def _json_response(self, data, code=200):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _proxy_chat(self, messages, context=""):
        sys_msg = "你是一个智能助手，帮助用户分析和处理任务。请用中文回复，简洁直接。"
        if context:
            sys_msg += f"\n\n当前任务上下文：{context}"
        payload = json.dumps({
            "model": "glm-4.7",
            "messages": [{"role": "system", "content": sys_msg}] + messages,
            "max_tokens": 300
        }).encode()
        req = ureq.Request("http://localhost:4000/v1/chat/completions", data=payload, headers={
            "Authorization": "Bearer sk-litellm-charlie-2026",
            "Content-Type": "application/json"
        })
        with ureq.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
            content = d["choices"][0]["message"]["content"]
            if not content:  # reasoning model fallback
                content = d["choices"][0]["message"].get("reasoning_content", "（无回复）")
            return content

    def _kanban_delegate(self, text, raw, target):
        """移交任务给 op 或 cc"""
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        if target == "op":
            # 写入 op-tasks.md
            op_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")
            with open(op_file, "a", encoding="utf-8") as f:
                f.write(f"- [ ] [CC→OP] [{ts}] {text}\n")
        else:
            # 写入 pending-tasks.md（CC 处理）
            todo_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/pending-tasks.md")
            with open(todo_file, "a", encoding="utf-8") as f:
                f.write(f"\n- [ ] [OP→CC] [{ts}] {text}\n")

    def _kanban_move(self, line_text, new_status):
        """更新 pending-tasks.md 中某行的状态；移入进行中时若为 op 任务自动加入队列"""
        from datetime import datetime
        todo_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/pending-tasks.md")
        op_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")
        with open(todo_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        marker = {"todo": "[ ]", "doing": "[>]", "done": "[x]"}[new_status]
        matched_line = ""
        for i, line in enumerate(lines):
            if line_text.strip() in line.strip():
                lines[i] = re.sub(r'\[[ x>]\]', marker, line, count=1)
                matched_line = line.strip()
                break
        with open(todo_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        # 移入"进行中"且是 op 任务 → 写入 op-tasks.md 队列
        if new_status == "doing" and matched_line:
            is_op = "[CC→OP]" in matched_line or "[OP]" in matched_line
            clean = re.sub(r'- \[.\]|\[CC→OP\]|\[OP→CC\]|\*\*|\d{4}-\d{2}-\d{2} \d{2}:\d{2}', '', matched_line).strip()
            if is_op and clean:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                with open(op_file, "a", encoding="utf-8") as f:
                    f.write(f"- [ ] [CC→OP] [{ts}] [看板移入进行中] {clean}\n")

    def _serve_op_status(self):
        import subprocess, datetime
        LOG_DIR = os.path.expanduser("~/.config/opencode/logs/scheduler/charlie-b445f233ebb8")
        JOBS_DIR = os.path.expanduser("~/.config/opencode/scheduler/scopes/charlie-b445f233ebb8/jobs")
        OP_TASKS = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")

        # 获取 systemd timer 状态
        timers = {}
        try:
            out = subprocess.check_output(
                ["systemctl", "--user", "list-timers", "opencode-job-*", "--no-legend", "--no-pager"],
                text=True, timeout=5
            )
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) < 6: continue
                # 格式: NEXT DATE TIME  LAST DATE TIME  UNIT ACTIVATES
                unit_idx = next((i for i,p in enumerate(parts) if p.startswith("opencode-job-")), None)
                if unit_idx is None: continue
                unit = parts[unit_idx]
                job = re.sub(r'^opencode-job-charlie-[a-z0-9]+-', '', unit).replace('.timer','')
                timers[job] = {"unit": unit, "next": " ".join(parts[:3]), "last": " ".join(parts[3:6])}
        except Exception:
            pass

        # 读取每个 job 日志最后几行
        jobs = []
        try:
            for fname in os.listdir(JOBS_DIR):
                if not fname.endswith(".json"): continue
                job = fname[:-5]
                log_path = os.path.join(LOG_DIR, f"{job}.log")
                last_lines = []
                status = "unknown"
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    last_lines = [l.strip() for l in lines[-5:] if l.strip()]
                    # 解析状态
                    for l in reversed(last_lines):
                        if "status=success" in l: status = "success"; break
                        if "status=fail" in l or "FAIL" in l: status = "failed"; break
                        if "[OK]" in l: status = "success"; break
                        if "[FAIL]" in l or "error" in l.lower(): status = "failed"; break
                except FileNotFoundError:
                    status = "no_log"

                timer_info = timers.get(job, {})
                jobs.append({
                    "job": job,
                    "status": status,
                    "last_log": last_lines[-2:] if last_lines else [],
                    "next": timer_info.get("next", "—"),
                    "last_run": timer_info.get("last", "—"),
                })
        except Exception:
            pass

        # op-tasks.md 待执行任务
        op_pending = []
        try:
            with open(OP_TASKS, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'^-\s+\[ \]\s+(.*)', line.strip())
                    if m: op_pending.append(m.group(1)[:100])
        except Exception:
            pass

        payload = json.dumps({"jobs": jobs, "op_pending": op_pending}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_kanban_data(self):
        todo_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/pending-tasks.md")
        op_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")
        tasks = {"todo": [], "doing": [], "done": []}

        # Step 1: 读取 op-tasks.md 已完成的文本集合（用于跨文件去重）
        op_done_texts = set()
        try:
            with open(op_file, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'^-\s+\[x\]\s+(.*)', line.strip())
                    if m:
                        clean = re.sub(r'\[CC→OP\]|\[OP→CC\]|\d{4}-\d{2}-\d{2} \d{2}:\d{2}|\[看板移入进行中\]', '', m.group(1)).strip()
                        op_done_texts.add(clean[:60])
        except FileNotFoundError:
            pass

        # Step 2: 同步 pending-tasks.md 中 [>] 任务若已在 op_done 则写回 [x]
        try:
            with open(todo_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            changed = False
            for i, line in enumerate(lines):
                m = re.match(r'^-\s+\[>\]\s+(.*)', line.strip())
                if m:
                    clean = re.sub(r'\[CC→OP\]|\[OP→CC\]|\*\*|\d{4}-\d{2}-\d{2} \d{2}:\d{2}', '', m.group(1)).strip()[:60]
                    if any(clean in d or d in clean for d in op_done_texts if d):
                        lines[i] = line.replace('[>]', '[x]', 1)
                        changed = True
            if changed:
                with open(todo_file, "w", encoding="utf-8") as f:
                    f.writelines(lines)
        except FileNotFoundError:
            pass

        # Step 3: 读取两个文件构建看板数据
        for fpath in [todo_file, op_file]:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                source = "OP" if "op-tasks" in fpath else "CC"
                for line in lines:
                    m = re.match(r'^-\s+\[([ x>])\]\s+(.*)', line.strip())
                    if not m:
                        continue
                    state, text = m.group(1), m.group(2)
                    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # strip bold
                    task = {"text": text[:120], "raw": line.strip(), "source": source}
                    if state == "x":
                        tasks["done"].append(task)
                    elif state == ">":
                        tasks["doing"].append(task)
                    else:
                        tasks["todo"].append(task)
            except FileNotFoundError:
                pass
        payload = json.dumps(tasks, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _classify_intent(self, text):
        """分类用户意图"""
        t = text.strip().lower()
        # 命令执行意图
        cmd_patterns = [r'^(运行|执行|跑|run)\s+', r'^(ls|ps|df|cat|grep|curl|docker|systemctl|git)\s', r'`[^`]+`', r'^\$\s']
        for p in cmd_patterns:
            if re.search(p, text): return "exec"
        # 触发 op job
        if any(k in t for k in ['service-nurse','proxy-guardian','discord-butler','task-check','watchdog']): return "trigger_op"
        # 普通对话
        return "chat"

    def _route_chat(self, messages, context="", agent="auto"):
        """智能路由对话到合适的模型"""
        last_msg = messages[-1]["content"] if messages else ""
        intent = self._classify_intent(last_msg)

        if intent == "exec":
            # 提取命令并执行
            m = re.search(r'`([^`]+)`', last_msg)
            cmd = m.group(1) if m else re.sub(r'^(运行|执行|跑|run)\s+', '', last_msg).strip()
            exec_result = self._exec_command(cmd)
            return {"type": "exec", "cmd": cmd, "output": exec_result.get("output",""), "ok": exec_result.get("ok", False)}

        # 根据 agent 选择模型
        model_map = {
            "auto": "glm-4.7",
            "qwen": "local/qwen3-8b",  # 降级备用
            "deepseek": "silicon/deepseek-v3.2",
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-6",
        }
        model = model_map.get(agent, "glm-4.7")

        sys_msg = "你是 Claude Hub 智能助手，帮助用户分析任务、排查问题。简洁直接，用中文回复。"
        if context:
            sys_msg += f"\n\n当前任务上下文：{context}"
        if agent in ("haiku", "sonnet"):
            # Anthropic API
            payload = json.dumps({
                "model": model,
                "system": sys_msg,
                "messages": messages,
                "max_tokens": 500
            }).encode()
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            req = ureq.Request("https://api.anthropic.com/v1/messages", data=payload, headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            })
        else:
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "system", "content": sys_msg}] + messages,
                "max_tokens": 500
            }).encode()
            req = ureq.Request("http://localhost:4000/v1/chat/completions", data=payload, headers={
                "Authorization": "Bearer sk-litellm-charlie-2026",
                "Content-Type": "application/json"
            })
        try:
            with ureq.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
                if agent in ("haiku","sonnet"):
                    content = d["content"][0]["text"] if d.get("content") else "（无回复）"
                else:
                    content = d["choices"][0]["message"]["content"]
                    if not content:
                        content = d["choices"][0]["message"].get("reasoning_content", "（无回复）")
                return {"type": "text", "reply": content, "model": model}
        except Exception as e:
            return {"type": "text", "reply": f"[错误] {e}", "model": model}

    def _exec_command(self, cmd):
        """安全执行 shell 命令（只读命令白名单）"""
        import subprocess
        if not cmd: return {"ok": False, "output": "命令为空"}
        # 白名单：只允许查询类命令
        safe_prefixes = ("ls","ps","df","cat","grep","curl","docker ps","systemctl status","systemctl list","journalctl","git log","git status","echo","which","find","tail","head","stat","ss","netstat","ping","nix")
        cmd_stripped = cmd.strip()
        allowed = any(cmd_stripped.startswith(p) for p in safe_prefixes)
        if not allowed:
            return {"ok": False, "output": f"[BLOCKED] 命令 `{cmd}` 不在白名单。如需执行，请在终端中运行。"}
        try:
            result = subprocess.run(cmd_stripped, shell=True, capture_output=True, text=True, timeout=15)
            output = (result.stdout + result.stderr).strip()
            return {"ok": result.returncode==0, "output": output[:2000] or "(无输出)"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "output": "超时（15s）"}
        except Exception as e:
            return {"ok": False, "output": str(e)}

    def _trigger_op_job(self, job):
        """触发指定 op scheduler job"""
        import subprocess
        valid_jobs = ["service-nurse","discord-butler","proxy-guardian","heartbeat-task-check","security-watchdog","heartbeat-check","heartbeat-system-sentry","marketing-scan"]
        if job not in valid_jobs:
            return {"ok": False, "msg": f"未知 job: {job}"}
        unit = f"opencode-job-charlie-b445f233ebb8-{job}.service"
        try:
            r = subprocess.run(["systemctl","--user","start",unit], capture_output=True, text=True, timeout=5)
            return {"ok": r.returncode==0, "msg": r.stdout.strip() or r.stderr.strip() or f"已触发 {job}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def _run_review(self, task_text, source, raw):
        """互评：CC 评审 op 任务，op 评审 CC 任务。基于 git diff + LLM 分析。"""
        import subprocess, time
        DOTFILES = os.path.expanduser("~/dotfiles")
        review_branch = "op" if source == "OP" else "cc"
        reviewer = "CC" if source == "OP" else "op"

        # 1. 获取 git diff（评审方评被评方的最新提交）
        diff_output = ""
        diff_lines = 0
        config_change = False
        try:
            result = subprocess.run(
                ["git", "diff", "main", review_branch, "--stat", "--no-color"],
                capture_output=True, text=True, timeout=10, cwd=DOTFILES
            )
            diff_stat = result.stdout.strip()
            result2 = subprocess.run(
                ["git", "diff", "main", review_branch, "--no-color"],
                capture_output=True, text=True, timeout=10, cwd=DOTFILES
            )
            diff_output = result2.stdout[:3000]
            diff_lines = diff_output.count('\n+') + diff_output.count('\n-')
            config_change = any(ext in diff_output for ext in ['.nix', '.json', '.yaml', '.yml', '.toml', '.env'])
        except Exception as e:
            diff_stat = f"[git error] {e}"

        # 2. 路由决策（token 成本控制）
        if diff_lines <= 10 and not config_change:
            verdict = "pass"
            summary = f"变更 <= 10 行，无配置文件改动，自动通过。\n\n{diff_stat}"
            model_used = "无需AI"
        else:
            # GLM-4.7 评审
            model = "glm-4.7"

            prompt = f"""你是代码评审员（{reviewer}），正在评审 {review_branch} 分支的最新改动。

任务背景：{task_text[:200]}

Git Diff（前3000字符）：
{diff_output[:2000] if diff_output else diff_stat}

请用3-5句话评审：
1. 改动是否正确实现了任务目标？
2. 是否有明显 bug 或风险？
3. 结论：[PASS] 通过 / [FAIL] 需要修改 / [WARN] 有疑虑但可接受

用中文，简洁。"""

            try:
                payload = json.dumps({
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400
                }).encode()
                req = ureq.Request("http://localhost:4000/v1/chat/completions", data=payload, headers={
                    "Authorization": "Bearer sk-litellm-charlie-2026",
                    "Content-Type": "application/json"
                })
                with ureq.urlopen(req, timeout=30) as r:
                    d = json.loads(r.read())
                    reply = d["choices"][0]["message"]["content"] or d["choices"][0]["message"].get("reasoning_content","")
                    summary = reply
                    model_used = model
                    verdict = "pass" if "[PASS]" in reply.upper() else "fail" if "[FAIL]" in reply.upper() else "warn"
            except Exception as e:
                summary = f"[评审失败] {e}\n\n{diff_stat}"
                verdict = "error"
                model_used = model

        # 3. 写评审报告到 memory
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        report_line = f"- [{ts}] [{reviewer}评审{review_branch}] {verdict.upper()}: {summary[:150]}\n"
        try:
            report_path = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-review-report.md")
            with open(report_path, "a", encoding="utf-8") as f:
                f.write(report_line)
        except Exception:
            pass

        return {
            "verdict": verdict,       # pass / fail / warn / error
            "summary": summary,
            "reviewer": reviewer,
            "branch": review_branch,
            "diff_lines": diff_lines,
            "model": model_used,
        }

    def _serve_cc_op_dialog(self, n=20):
        dialog_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-dialog.jsonl")
        messages = []
        try:
            with open(dialog_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            messages.append(json.loads(line))
                        except Exception:
                            pass
        except FileNotFoundError:
            pass
        payload = json.dumps({"messages": messages[-n:]}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _cc_op_speak(self, rounds=1):
        """触发 CC 和 op 通过 GLM-4.7 互相对话 rounds 轮，结果写入 cc-op-dialog.jsonl"""
        from datetime import datetime
        dialog_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-dialog.jsonl")
        pending_md = os.path.expanduser("~/.claude/projects/-home-charlie/memory/pending-tasks.md")
        op_tasks_md = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")

        # 收集当前任务上下文
        pending_summary = ""
        try:
            with open(pending_md, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if re.match(r'^-\s+\[[ >]\]', l.strip())][:5]
            pending_summary = "\n".join(lines) or "（无待办任务）"
        except Exception:
            pending_summary = "（无法读取待办）"

        op_pending = ""
        try:
            with open(op_tasks_md, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if re.match(r'^-\s+\[ \]', l.strip())][:3]
            op_pending = "\n".join(lines) or "（无待执行任务）"
        except Exception:
            op_pending = "（无法读取）"

        # 读取最近对话历史（最后5条）
        recent_msgs = []
        try:
            with open(dialog_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            recent_msgs.append(json.loads(line))
                        except Exception:
                            pass
            recent_msgs = recent_msgs[-5:]
        except FileNotFoundError:
            pass

        history_text = "".join(f"[{m['from']}] {m['content']}\n" for m in recent_msgs)

        new_messages = []

        def call_glm(system_msg, user_msg):
            payload = json.dumps({
                "model": "deepseek-v3.2",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "max_tokens": 80,
                "temperature": 0.8,
                "stream": False
            }).encode()
            req = ureq.Request("http://localhost:4000/v1/chat/completions", data=payload, headers={
                "Authorization": "Bearer sk-litellm-charlie-2026",
                "Content-Type": "application/json"
            })
            with ureq.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
                text = d["choices"][0]["message"]["content"]
                if not text:
                    text = d["choices"][0]["message"].get("reasoning_content", "（无回复）")
                return text.strip()

        for _ in range(rounds):
            ts = datetime.now().strftime("%H:%M")

            # CC 发言 — 自然语言，专业同事口吻
            cc_sys = (
                "你是 CC，一名有主见的 AI 项目负责人，正在和运维同事 op 口头沟通。"
                "说话风格：专业但口语化，像两个工程师开站会一样自然。"
                "不用敬语，不用汇报格式，就是正常说话。中文。1-2句，40字以内。"
            )
            pending_short = pending_summary[:120] if pending_summary else "暂无待办"
            op_short = op_pending[:80] if op_pending else "队列为空"
            ctx = f"当前待办：{pending_short}。op队列：{op_short}。"
            if history_text:
                ctx += f"\n刚才说到：{history_text[-120:]}"
            cc_usr = ctx + "\nCC现在说："

            try:
                cc_content = call_glm(cc_sys, cc_usr)
            except Exception as e:
                cc_content = f"[CC连接异常: {e}]"

            cc_msg = {"time": ts, "from": "CC", "to": "OP", "content": cc_content}
            new_messages.append(cc_msg)
            history_text += f"CC：{cc_content}\n"

            # OP 回复 — 务实的运维视角，直接说
            op_sys = (
                "你是 op，一名专注系统稳定性的运维 AI，正在和项目负责人 CC 沟通。"
                "说话风格：务实、简短、有态度，像老运维一样直接。"
                "不绕弯子，直接说当前状态或问题。中文。1-2句，40字以内。"
            )
            op_usr = f'CC刚说："{cc_content}"\n你的情况：{op_short}\nop回应：'

            try:
                op_content = call_glm(op_sys, op_usr)
            except Exception as e:
                op_content = f"[OP连接异常: {e}]"

            op_msg = {"time": ts, "from": "OP", "to": "CC", "content": op_content}
            new_messages.append(op_msg)
            history_text += f"[OP] {op_content}\n"

        # 写入对话文件
        try:
            with open(dialog_file, "a", encoding="utf-8") as f:
                for msg in new_messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        except Exception as e:
            return {"ok": False, "error": str(e), "messages": new_messages}

        return {"ok": True, "messages": new_messages}

    def _cc_op_discuss(self, topic, rounds=2):
        """CC 和 op 就某个议题进行多轮深度讨论，写入 cc-op-discuss.jsonl"""
        from datetime import datetime
        discuss_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-discuss.jsonl")
        pending_md = os.path.expanduser("~/.claude/projects/-home-charlie/memory/pending-tasks.md")

        pending_summary = ""
        try:
            with open(pending_md, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if re.match(r'^-\s+\[[ >x]\]', l.strip())][:6]
            pending_summary = "\n".join(lines) or "（无待办任务）"
        except Exception:
            pending_summary = "（无法读取）"

        def call_glm(prompt, system_msg="你是AI助手，用中文简洁回答"):
            payload = json.dumps({
                "model": "deepseek-v3.2",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "stream": False
            }).encode()
            req = ureq.Request("http://localhost:4000/v1/chat/completions", data=payload, headers={
                "Authorization": "Bearer sk-litellm-charlie-2026",
                "Content-Type": "application/json"
            })
            with ureq.urlopen(req, timeout=45) as r:
                d = json.loads(r.read())
                text = d["choices"][0]["message"]["content"]
                if not text:
                    text = d["choices"][0]["message"].get("reasoning_content", "（无回复）")
                return text.strip()

        session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        new_messages = []
        history_text = ""

        # 写入讨论标题
        title_msg = {
            "session": session_id,
            "time": datetime.now().strftime("%H:%M"),
            "from": "SYSTEM",
            "content": f"【议题】{topic}",
            "type": "title"
        }
        new_messages.append(title_msg)

        for round_i in range(rounds):
            ts = datetime.now().strftime("%H:%M")

            # CC 观点 — 像资深工程师讨论技术方案，口语化但有深度
            cc_sys = (
                "你是 CC，一个有产品感的 AI 工程师，正在和运维同事 op 讨论技术方案。"
                "说话像真实的工程师开技术评审会：有观点、有逻辑、但不说废话，不用列点。"
                "直接表达你的判断，可以有保留意见，语气自然。中文，80-120字。"
            )
            prior = f"之前说到：{history_text[-200:]}\n\n" if history_text else ""
            cc_prompt = f"{prior}现在讨论：{topic}\n\nCC（第{round_i+1}轮）："

            try:
                cc_content = call_glm(cc_sys, cc_prompt)
            except Exception as e:
                cc_content = f"[CC连接异常: {e}]"

            cc_msg = {"session": session_id, "time": ts, "from": "CC", "content": cc_content, "type": "discuss", "round": round_i + 1}
            new_messages.append(cc_msg)
            history_text += f"CC：{cc_content}\n\n"

            # OP 观点 — 老运维的实际顾虑和经验
            op_sys = (
                "你是 op，一个经验丰富的系统运维 AI，正在和产品工程师 CC 讨论方案可行性。"
                "说话像老运维：务实、直接，会提出别人没想到的实施细节和风险。"
                "不迎合，有自己的判断。中文，80-120字。"
            )
            op_prompt = f"讨论议题：{topic}\n\n{history_text[-300:]}\nop（第{round_i+1}轮）："

            op_sys = op_sys
            try:
                op_content = call_glm(op_prompt, op_sys)
            except Exception as e:
                op_content = f"[OP连接异常: {e}]"

            op_msg = {"session": session_id, "time": ts, "from": "OP", "content": op_content, "type": "discuss", "round": round_i + 1}
            new_messages.append(op_msg)
            history_text += f"[OP 第{round_i+1}轮] {op_content}\n\n"

        # 写入文件
        try:
            with open(discuss_file, "a", encoding="utf-8") as f:
                for msg in new_messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        except Exception as e:
            return {"ok": False, "error": str(e), "messages": new_messages, "session": session_id}

        return {"ok": True, "messages": new_messages, "session": session_id, "history": history_text}

    def _orchestrate(self, topic, context=""):
        """Orchestrator：综合 CC 和 OP 的讨论，输出最终决策和角色分配"""
        from datetime import datetime
        discuss_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-discuss.jsonl")
        orch_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-orchestrate.jsonl")
        pending_md = os.path.expanduser("~/.claude/projects/-home-charlie/memory/pending-tasks.md")
        op_tasks_md = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")

        # 读取最近讨论（最后一个 session）
        recent_discuss = []
        last_session = None
        try:
            with open(discuss_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            if last_session is None:
                                last_session = msg.get("session", "")
                            if msg.get("session") == last_session or last_session == "":
                                recent_discuss.append(msg)
                        except Exception:
                            pass
        except FileNotFoundError:
            pass

        discussion_text = ""
        for m in recent_discuss[-20:]:
            if m.get("type") == "title":
                discussion_text += f"\n=== {m['content']} ===\n"
            else:
                discussion_text += f"[{m['from']} 第{m.get('round',1)}轮] {m['content']}\n\n"

        # 读取当前任务摘要
        tasks_summary = ""
        try:
            lines = []
            with open(pending_md, "r", encoding="utf-8") as f:
                for l in f:
                    m2 = re.match(r'^-\s+\[[ >]\]\s+(.*)', l.strip())
                    if m2:
                        lines.append(f"  待做: {m2.group(1)[:60]}")
            with open(op_tasks_md, "r", encoding="utf-8") as f:
                for l in f:
                    m2 = re.match(r'^-\s+\[ \]\s+(.*)', l.strip())
                    if m2:
                        lines.append(f"  op队列: {m2.group(1)[:60]}")
            tasks_summary = "\n".join(lines[:8]) or "（无待办）"
        except Exception:
            tasks_summary = "（无法读取）"

        orch_prompt = f"""你是 Orchestrator（多 Agent 调度器），负责综合 CC 和 OP 两个 agent 的讨论，做出最终决策并分配角色和任务。

议题/上下文：{topic or "综合调度"}
{("额外背景：" + context) if context else ""}

讨论记录：
{discussion_text or "（无讨论记录，基于当前任务状态决策）"}

当前任务状态：
{tasks_summary}

请输出以下结构的决策报告（中文，严格按格式）：

**核心决策**：[一句话总结最终决定]

**CC 职责**：[CC agent 需要完成的1-3项具体任务]

**OP 职责**：[op agent 需要完成的1-3项具体任务]

**优先级**：[P0/P1/P2] + 原因

**协作机制**：[两者如何协作、交接、验证]

**风险提示**：[需要注意的1-2个关键风险]"""

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            payload = json.dumps({
                "model": "deepseek-v3.2",
                "messages": [{"role": "user", "content": orch_prompt}],
                "max_tokens": 500,
                "stream": False
            }).encode()
            req = ureq.Request("http://localhost:4000/v1/chat/completions", data=payload, headers={
                "Authorization": "Bearer sk-litellm-charlie-2026",
                "Content-Type": "application/json"
            })
            with ureq.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
                decision = d["choices"][0]["message"]["content"]
                if not decision:
                    decision = d["choices"][0]["message"].get("reasoning_content", "（无回复）")
                decision = decision.strip()
        except Exception as e:
            decision = f"[Orchestrator异常: {e}]"

        result = {
            "time": ts,
            "topic": topic,
            "decision": decision,
            "session": last_session or ts,
        }

        # 写入 orchestrate 文件
        try:
            with open(orch_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # 解析并写入 op-tasks.md（OP 职责部分）
        op_tasks_added = []
        try:
            import re as _re
            op_match = _re.search(r'\*\*OP 职责\*\*[：:]\s*(.+?)(?=\*\*|$)', decision, _re.DOTALL)
            if op_match:
                op_block = op_match.group(1).strip()
                for item in _re.findall(r'[-\d]+[.、）)]\s*(.+)', op_block):
                    task_text = item.strip()[:100]
                    if task_text:
                        op_tasks_added.append(task_text)
                        with open(op_tasks_md, "a", encoding="utf-8") as f:
                            f.write(f"- [ ] [ORCH→OP] [{ts}] {task_text}\n")
        except Exception:
            pass

        # 解析并写入 pending-tasks.md（CC 职责部分）
        cc_tasks_added = []
        try:
            cc_match = _re.search(r'\*\*CC 职责\*\*[：:]\s*(.+?)(?=\*\*|$)', decision, _re.DOTALL)
            if cc_match:
                cc_block = cc_match.group(1).strip()
                for item in _re.findall(r'[-\d]+[.、）)]\s*(.+)', cc_block):
                    task_text = item.strip()[:100]
                    if task_text:
                        cc_tasks_added.append(task_text)
                        with open(pending_md, "a", encoding="utf-8") as f:
                            f.write(f"- [ ] [ORCH→CC] [{ts}] {task_text}\n")
        except Exception:
            pass

        return {
            "ok": True,
            "decision": decision,
            "session": last_session or ts,
            "op_tasks_added": op_tasks_added,
            "cc_tasks_added": cc_tasks_added,
        }

    def log_message(self, format, *args):
        pass  # 静默日志

    def _serve_chronos_data(self):
        data = {}
        # Read Chronos state files
        for name in ("sensory", "biofeedback", "subconscious"):
            path = os.path.join(CHRONOS_DIR, f"{name}_state.json")
            try:
                with open(path, "r") as f:
                    data[name] = json.load(f)
            except Exception:
                data[name] = {}

        # Memory stats: line counts
        memory_stats = {}
        for fname in os.listdir(MEMORY_DIR):
            if fname.endswith(".md"):
                try:
                    with open(os.path.join(MEMORY_DIR, fname), "r") as f:
                        memory_stats[fname] = sum(1 for _ in f)
                except Exception:
                    memory_stats[fname] = 0
        data["memory_stats"] = memory_stats

        # Recent lessons
        lessons_file = os.path.join(MEMORY_DIR, "lessons-learned.md")
        recent = []
        try:
            with open(lessons_file, "r") as f:
                lines = f.readlines()
            for line in reversed(lines):
                line = line.strip()
                if line.startswith("- ["):
                    recent.append(line)
                    if len(recent) >= 10:
                        break
        except Exception:
            pass
        data["recent_lessons"] = recent

        # Dream reports
        reports = []
        try:
            for p in sorted(os.listdir(DREAM_DIR), reverse=True):
                if p.startswith("dream-") and p.endswith(".md"):
                    reports.append(p)
                    if len(reports) >= 10:
                        break
        except Exception:
            pass
        data["dream_reports"] = reports

        # AGI Brain status
        agi_status_file = "/tmp/agi-brain-status.json"
        try:
            with open(agi_status_file, "r") as f:
                agi_data = json.load(f)
                data["agi_brain"] = agi_data
        except Exception:
            data["agi_brain"] = {"running": False}

        # AGI Brain recent perceptions (last 10)
        agi_db = os.path.expanduser("~/agi/agi.db")
        recent_perceptions = []
        perception_strength = {}  # source -> count
        try:
            import sqlite3
            conn = sqlite3.connect(agi_db)
            cursor = conn.execute(
                'SELECT source, summary, severity, created_at FROM perceptions '
                'ORDER BY id DESC LIMIT 10'
            )
            for row in cursor:
                recent_perceptions.append({
                    "source": row[0],
                    "summary": row[1],
                    "severity": row[2],
                    "time": row[3]
                })
            # Calculate perception strength (last 100 perceptions)
            strength_cursor = conn.execute(
                'SELECT source, COUNT(*) as cnt FROM perceptions '
                'WHERE id > (SELECT MAX(id) - 100 FROM perceptions) '
                'GROUP BY source'
            )
            for row in strength_cursor:
                perception_strength[row[0]] = row[1]
            conn.close()
        except Exception:
            pass
        data["agi_perceptions"] = recent_perceptions
        data["perception_strength"] = perception_strength

        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _op_notify(self, data):
        """OP 完成任务后的 webhook：接收 OP 报告，自动生成 CC 响应写入对话"""
        from datetime import datetime
        import subprocess as sp

        source = data.get("source", "unknown")
        status = data.get("status", "unknown")
        summary = data.get("summary", "")
        completed_count = data.get("completed_count", 0)

        dialog_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/cc-op-dialog.jsonl")
        op_status_file = "/tmp/op-status.json"
        op_results_file = "/tmp/op-task-results.json"

        # 读取 OP 最新状态数据（文件优先，POST body 补充）
        op_status = {}
        try:
            with open(op_status_file, "r") as f:
                op_status = json.load(f)
        except Exception:
            pass
        # 用 POST body 中的字段补充（OP job 可以直接在 notify 里传递关键字段）
        for key in ("fixes_failed", "disk_warn", "ports_down", "alerts", "fixes_applied"):
            if key in data and data[key]:
                op_status.setdefault(key, data[key])

        op_results = []
        try:
            with open(op_results_file, "r") as f:
                content = f.read().strip()
                if content:
                    op_results = json.loads(content) if content.startswith('[') else [json.loads(l) for l in content.splitlines() if l.strip()]
        except Exception:
            pass

        # 构建 CC 决策 prompt（基于真实数据）
        alerts = op_status.get("alerts", [])
        fixes_failed = op_status.get("fixes_failed", [])
        disk_warn = op_status.get("disk_warn", [])
        ports_down = op_status.get("ports_down", [])

        context_parts = []
        if source == "service-nurse":
            context_parts.append(f"OP service-nurse 巡检完成，状态: {op_status.get('status','unknown')}")
            if fixes_failed:
                context_parts.append(f"修复失败: {', '.join(fixes_failed)}")
            if disk_warn:
                context_parts.append(f"磁盘告警: {', '.join(disk_warn)}")
            if ports_down:
                context_parts.append(f"端口宕机: {', '.join(str(p) for p in ports_down)}")
        elif source == "task-check":
            context_parts.append(f"OP 完成了 {completed_count} 个 CC 委托任务")
            if summary:
                context_parts.append(f"摘要: {summary}")

        if not context_parts:
            context_parts = [f"OP 通知来自 {source}"]

        op_report = "；".join(context_parts)

        # 用 DeepSeek 生成 CC 的真实响应
        cc_sys = (
            "你是 CC，项目负责人，刚收到运维同事 OP 的工作汇报。"
            "根据汇报内容给出一句具体的决策或指示。"
            "如果有故障需要处理，指出优先级；如果一切正常，确认并说下一步。"
            "专业口语化，1句话，≤30字，中文。"
        )
        cc_usr = f"OP 汇报：{op_report}"

        def call_deepseek(sys_msg, usr_msg):
            payload = json.dumps({
                "model": "deepseek-v3.2",
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": usr_msg}
                ],
                "max_tokens": 80,
                "temperature": 0.7
            }).encode()
            req = ureq.Request("http://localhost:4000/v1/chat/completions", data=payload, headers={
                "Authorization": "Bearer sk-litellm-charlie-2026",
                "Content-Type": "application/json"
            })
            try:
                with ureq.urlopen(req, timeout=15) as resp:
                    r = json.loads(resp.read())
                    return r["choices"][0]["message"]["content"].strip()
            except Exception as e:
                return f"[CC] 收到 OP 报告（{source}）"

        cc_content = call_deepseek(cc_sys, cc_usr)

        # 写入对话
        now = datetime.now()
        entry = {
            "time": now.strftime("%H:%M"),
            "from": "CC",
            "to": "OP",
            "content": cc_content,
            "type": "auto-response",
            "trigger": source
        }
        with open(dialog_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 如果有严重故障，自动生成后续任务
        new_tasks = []
        if fixes_failed:
            for svc in fixes_failed:
                task = f"- [ ] [CC→OP] [{now.strftime('%Y-%m-%d %H:%M')}] [P1] 人工介入修复 {svc}（自动修复失败，需检查日志）"
                new_tasks.append(task)
        if disk_warn:
            task = f"- [ ] [CC→OP] [{now.strftime('%Y-%m-%d %H:%M')}] [P2] 清理磁盘空间（目标<80%），受影响分区：{', '.join(disk_warn)}"
            new_tasks.append(task)

        if new_tasks:
            op_tasks_file = os.path.expanduser("~/.claude/projects/-home-charlie/memory/op-tasks.md")
            try:
                with open(op_tasks_file, "a", encoding="utf-8") as f:
                    f.write("\n".join(new_tasks) + "\n")
            except Exception:
                pass

        return {
            "ok": True,
            "cc_response": cc_content,
            "new_tasks": len(new_tasks),
            "source": source
        }

if __name__ == "__main__":
    print(f"启动器服务运行在 http://localhost:{PORT}")
    print(f"打开 http://localhost:{PORT}/launcher.html")
    HTTPServer(("0.0.0.0", PORT), LauncherHandler).serve_forever()
