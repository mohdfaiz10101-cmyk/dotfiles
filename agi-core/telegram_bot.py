"""
telegram_bot.py — AGI Brain Telegram 双向交互层
P3升级: 从单向通知→双向对话，用户可通过Telegram指挥Brain
"""

import asyncio
import json
import logging
import os
import sys
import time
import httpx
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# 命令处理器（可扩展）
COMMAND_HANDLERS: dict = {}  # 在 brain.py 中注册

# 最后处理的 update_id，防止重复
_last_update_id = 0
_restart_notify = True  # 重启时通知一次


async def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """发送 Telegram 消息。"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0, proxy="http://127.0.0.1:7890") as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
            return resp.status_code == 200
    except Exception as e:
        logger.warning("Telegram发送失败: %s", e)
        return False


async def poll_updates() -> list[dict]:
    """轮询 Telegram 新消息，返回未处理的消息列表。"""
    global _last_update_id
    try:
        params = {"timeout": 5, "offset": _last_update_id + 1, "allowed_updates": ["message"]}
        async with httpx.AsyncClient(timeout=15.0, proxy="http://127.0.0.1:7890") as client:
            resp = await client.get(f"{TELEGRAM_API}/getUpdates", params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if not data.get("ok"):
                return []
            results = data.get("result", [])
            for update in results:
                _last_update_id = max(_last_update_id, update.get("update_id", 0))
            return results
    except Exception as e:
        logger.debug("Telegram轮询异常(可忽略): %s", e)
        return []


def parse_command(text: str) -> tuple[str, str]:
    """解析用户消息，返回 (命令类型, 参数)。
    
    支持格式:
    - /status → ("status", "")
    - /check litellm → ("check", "litellm")
    - /restart musetalk → ("restart", "musetalk")
    - /ask 今天天气 → ("ask", "今天天气")
    - 普通文本 → ("chat", "原文")
    """
    text = text.strip()
    if not text:
        return ("", "")
    
    if text.startswith("/"):
        parts = text[1:].split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        return (cmd, arg)
    
    # 普通文本当闲聊
    return ("chat", text)


async def handle_message(text: str, message_id: int) -> str | None:
    """处理用户消息，调用已注册的命令处理器。
    
    Returns: 回复文本，或 None（不回复）
    """
    cmd, arg = parse_command(text)
    
    # 🏠 启动通知
    global _restart_notify
    if _restart_notify and cmd in ("status", "start", ""):
        _restart_notify = False
        return "👋 AGI Brain v2 已启动\n/status 状态 /check 检查 /restart 重启 /ask 提问"
    
    if cmd == "status":
        return await _handle_status()
    elif cmd == "check":
        return await _handle_check(arg)
    elif cmd == "restart":
        return await _handle_restart(arg)
    elif cmd == "ask":
        return await _handle_ask(arg)
    elif cmd == "chat":
        return await _handle_ask(text)
    elif cmd == "help":
        return "📋 命令:\n/status 状态\n/check <服务> 检查\n/restart 重启\n任意文本 → supervisor 调度\n/help 帮助"
    
    # 普通文本消息 → 走 supervisor（不要求 /ask 前缀）
    return await _handle_ask(text)


async def _handle_status() -> str:
    """处理 /status 命令：返回系统快照。"""
    import subprocess
    
    try:
        # CPU
        cpu = subprocess.run(
            ["vmstat", "1", "1"], capture_output=True, text=True, timeout=3
        )
        cpu_idle = cpu.stdout.strip().split("\n")[-1].split()[-2] if cpu.stdout else "?"
        
        # 内存
        mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=3)
        mem_line = mem.stdout.split("\n")[1] if mem.stdout else ""
        mem_parts = mem_line.split()
        mem_used = mem_parts[2] if len(mem_parts) > 2 else "?"
        mem_total = mem_parts[1] if len(mem_parts) > 1 else "?"
        
        # 磁盘
        disk = subprocess.run(
            ["df", "-h", "/mnt/ai"], capture_output=True, text=True, timeout=3
        )
        disk_line = disk.stdout.split("\n")[1] if disk.stdout else ""
        disk_parts = disk_line.split()
        disk_use = disk_parts[4] if len(disk_parts) > 4 else "?"
        disk_avail = disk_parts[3] if len(disk_parts) > 3 else "?"
        
        # 关键服务
        services = []
        for svc, name in [("litellm-litellm", "LiteLLM"), ("letta", "Letta"), ("musetalk", "MuseTalk")]:
            r = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", svc],
                capture_output=True, text=True, timeout=3,
            )
            s = r.stdout.strip() if r.returncode == 0 else "?"
            emoji = "✅" if s == "running" else "⚠️" if s == "?" else "❌"
            services.append(f"{emoji} {name}: {s}")
        
        now = datetime.now().strftime("%H:%M")
        return (
            f"🖥 AGI Brain v2 — {now}\n"
            f"CPU空闲: {cpu_idle}% | 内存: {mem_used}/{mem_total}\n"
            f"/mnt/ai: {disk_use} ({disk_avail}可用)\n"
            + "\n".join(services)
        )
    except Exception as e:
        return f"状态获取失败: {e}"


async def _handle_check(service: str) -> str:
    """处理 /check 命令：检查指定服务。"""
    if not service:
        return "用法: /check <服务名>  如 /check litellm"
    
    import subprocess
    results = []
    
    # Docker检查
    r = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}} {{.Status}}", "--filter", f"name={service}"],
        capture_output=True, text=True, timeout=5,
    )
    if r.stdout.strip():
        results.append(f"🐳 Docker: {r.stdout.strip()}")
    else:
        # 尝试 curl 健康检查
        port_map = {"litellm": "4000", "letta": "8283", "musetalk": "8001", "chromadb": "8000"}
        port = port_map.get(service, "")
        if port:
            r2 = subprocess.run(
                ["curl", "-s", "--max-time", "3", f"http://localhost:{port}/"],
                capture_output=True, text=True, timeout=5,
            )
            results.append(f"🌐 HTTP {port}: {'OK' if r2.returncode == 0 else 'FAIL'}")
        else:
            results.append("❓ 未知服务")
    
    return "\n".join(results) if results else f"未找到服务: {service}"


async def _handle_restart(container: str) -> str:
    """处理 /restart 命令：重启Docker容器。"""
    if not container:
        return "用法: /restart <容器名>  如 /restart musetalk"
    
    import subprocess
    try:
        r = subprocess.run(
            ["docker", "restart", container],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            return f"✅ 容器 {container} 已重启"
        else:
            return f"❌ 重启失败: {r.stderr[:100]}"
    except subprocess.TimeoutExpired:
        return f"⏰ 重启 {container} 超时"
    except Exception as e:
        return f"❌ 错误: {e}"


async def _handle_ask(question: str) -> str:
    """处理 /ask 命令：路由到 macg.py supervisor（LangGraph 多 Agent 调度）。
    supervisor 会自动判断：简单问题→GLM直接答，运维→call_op，架构→call_cc，协作→call_crewai"""
    if not question:
        return "用法: /ask <问题>"
    
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(Path(__file__).parent / "macg.py"),
            "-p", question, "--thread", "telegram",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path(__file__).parent),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode == 0:
            # 记录 supervisor 最后成功调用时间（供 waybar 调度呼吸灯检测）
            try:
                Path(Path.home() / ".local/state/macg-supervisor-last-ok").write_text(str(int(time.time())))
            except Exception:
                pass
            result = stdout.decode().strip()
            return result[:4000] if result else "(supervisor 无输出)"
        else:
            return f"[supervisor error] {stderr.decode().strip()[:300]}"
    except asyncio.TimeoutError:
        return "[supervisor 超时 120s]"
    except Exception as e:
        # 降级：supervisor 不可用时直接调 LLM
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "http://localhost:4000/v1/chat/completions",
                    headers={"Authorization": "Bearer sk-litellm-charlie-2026"},
                    json={
                        "model": "glm-5-turbo",
                        "messages": [
                            {"role": "system", "content": "你是Charlie的AGI Brain助手。用中文简洁回复，不超过3行。"},
                            {"role": "user", "content": question},
                        ],
                        "max_tokens": 300,
                        "temperature": 0.5,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return f"supervisor 不可用，LLM 降级也失败: {e}"


async def listener_loop() -> None:
    """Telegram 监听主循环（作为 brain.py 的后台任务运行）。
    
    启动时发送上线通知，然后持续轮询新消息。
    """
    global _restart_notify
    _restart_notify = True
    
    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM] 未配置 TELEGRAM_BOT_TOKEN，监听已禁用")
        return
    
    print("[TELEGRAM] 双向监听已启动")
    
    while True:
        try:
            updates = await poll_updates()
            for update in updates:
                msg = update.get("message", {})
                text = msg.get("text", "")
                from_user = msg.get("from", {})
                username = from_user.get("username", from_user.get("first_name", "?"))
                chat_id = str(msg.get("chat", {}).get("id", ""))
                
                # 只响应用户本人
                if chat_id != TELEGRAM_CHAT_ID:
                    continue
                
                print(f"[TELEGRAM] 📩 {username}: {text[:50]}")
                
                reply = await handle_message(text, msg.get("message_id", 0))
                if reply:
                    await send_message(reply)
            
            # 避免CPU空转，长轮询自带timeout
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error("Telegram监听异常: %s", e)
            await asyncio.sleep(10)


def register_command(cmd: str, handler):
    """注册自定义命令处理器。"""
    COMMAND_HANDLERS[cmd] = handler
