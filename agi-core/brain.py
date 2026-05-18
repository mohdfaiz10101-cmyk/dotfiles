"""
brain.py — AGI Brain 主循环
Why: 实现 Sense→Think→Act 三环自主循环，每60秒感知系统状态并执行相应行动
What: 定期采集系统指标 → LLM 分析 → 写任务/发通知/更新状态文件
Test: 运行后检查 /tmp/agi-brain-status.json 被创建且包含 summary 字段
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from think import analyze
from proactive import generate_proactive_message
from audit_log import log_tasks_queued, log_brain_cycle

STATUS_FILE = os.environ.get("STATUS_FILE", "/tmp/agi-brain-status.json")


class RateGuard:
    """LLM 模型调用频率守卫 — 每模型 per-minute 滑动窗口计数。
    Why: 防止异常循环导致 LLM API 被快速耗尽
    What: 超阈值暂停该模型 + 写告警到 op-tasks.md
    Test: 连续调用 check() 超过 max_calls 后返回 False
    """

    def __init__(self, max_calls: int = 20, window: int = 60, pause_duration: int = 60):
        self.max_calls = max_calls
        self.window = window
        self.pause_duration = pause_duration
        self._calls: dict[str, deque] = {}  # model -> deque of timestamps
        self._paused: dict[str, float] = {}  # model -> pause_until timestamp

    def record(self, model: str) -> None:
        if model not in self._calls:
            self._calls[model] = deque()
        self._calls[model].append(time.time())

    def check(self, model: str) -> bool:
        """返回 True 表示允许调用，False 表示被限流。"""
        # 检查是否在暂停期
        if model in self._paused:
            if time.time() < self._paused[model]:
                return False
            del self._paused[model]

        # 清理过期记录
        cutoff = time.time() - self.window
        if model in self._calls:
            while self._calls[model] and self._calls[model][0] < cutoff:
                self._calls[model].popleft()
            return len(self._calls[model]) < self.max_calls
        return True

    def pause(self, model: str) -> None:
        """暂停某模型调用 pause_duration 秒。"""
        self._paused[model] = time.time() + self.pause_duration

    def is_paused(self, model: str) -> bool:
        return model in self._paused and time.time() < self._paused[model]


_rate_guard = RateGuard()
OP_TASKS_FILE = os.environ.get(
    "OP_TASKS_FILE", "/home/charlie/.claude/projects/-home-charlie/memory/op-tasks.md"
)
OP_STATUS_FILE = os.environ.get("OP_STATUS_FILE", "/tmp/op-status.json")
OP_TASK_RESULTS_FILE = os.environ.get(
    "OP_TASK_RESULTS_FILE", "/tmp/op-task-results.json"
)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_ALERTS_CHANNEL_ID = os.environ.get("DISCORD_ALERTS_CHANNEL_ID", "")

LOOP_INTERVAL = 60  # 主循环间隔（秒，自适应：无变化时逐步延长）
PROACTIVE_INTERVAL = 2 * 60 * 60  # 主动推送间隔（秒，2小时）
ADAPTIVE_MAX_INTERVAL = 300  # 自适应最大间隔（5分钟）
ADAPTIVE_NOCHANGE_THRESHOLD = 5  # 连续N次无变化后开始延长间隔
TRIGGER_FILE = "/tmp/agi-brain-trigger"  # 热触发文件：touch此文件立即执行一轮

_last_proactive_time: float = 0.0
_last_sense_hash: str = ""
_alert_last_sent: dict = {}  # key → timestamp，告警去重
_ALERT_COOLDOWN = {
    "letta": 900,      # 15分钟
    "litellm": 900,    # 15分钟
    "default": 3600    # 1小时
}
# 上次已知服务状态（用于检测恢复）
_last_known_service_status: dict = {}
# 不推 Telegram 的噪声告警关键词（仅记日志）
_ALERT_SUPPRESS_PATTERNS = (
    # 网络/限速
    "429", "Too Many Requests", "rate limit", "RateLimit",
    "timeout", "timed out", "Connection", "connect",
    # CPU/内存正常波动
    "CPU 占用", "CPU占用", "CPU 占用率", "CPU 数据未知", "内存数据未知",
    "服务列表为空", "无法获取CPU", "ps 进程",
    # 磁盘/存储（低于90%为正常波动，不推送）
    "磁盘", "disk", "df -h", "du -sh", "清理", "空间", "storage",
    "/mnt/ai", "/mnt/data", "/mnt/pool",
    # 认知/假阳性
    "fe评分", "cognitive", "ne_div",
    # 泛化检查
    "任务跟进", "op-tasks", "进展", "dec",
)


def _sense_hash(data: dict) -> str:
    """计算感知数据的关键字段 hash（忽略时间戳等噪声）。

    Why: 状态未变化时跳过 LLM 调用，节省 token
    What: 对 service_status/cpu_hogs/alerts/disk_ai/cognitive 做 MD5
    Test: 相同数据返回相同 hash，数据变化后 hash 不同
    """
    import hashlib

    key = {k: data[k] for k in ["services", "cpu_hogs", "alerts", "disk_ai", "cognitive"] if k in data}
    return hashlib.md5(json.dumps(key, sort_keys=True).encode()).hexdigest()


# ── Sense 阶段 ────────────────────────────────────────────────────────────────


def _run_cmd(cmd: str, timeout: int = 5) -> str:
    """执行 shell 命令，返回输出字符串。

    Why: 封装命令执行，统一处理超时和错误
    What: subprocess.run，失败返回错误描述
    Test: _run_cmd("echo hello") 返回 "hello"
    """
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"超时({timeout}s)"
    except Exception as e:
        return f"错误:{e}"


def _quick_service_check(service_name: str) -> str:
    """快速检查 Docker 容器或 systemd 服务当前状态。

    Why: 推送告警前二次验证，避免推送已修复的过时告警
    What: 优先查 Docker，再查 systemd user service
    Test: _quick_service_check("letta") → "running" 或 "exited" 或 "unknown"
    """
    # Docker 容器
    r = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}", service_name],
        capture_output=True, text=True, timeout=3,
    )
    if r.returncode == 0:
        status = r.stdout.strip()
        if status:
            return status
    # systemd user service
    r2 = subprocess.run(
        ["systemctl", "--user", "is-active", f"{service_name}.service"],
        capture_output=True, text=True, timeout=3,
    )
    if r2.returncode == 0:
        return r2.stdout.strip()
    return "unknown"


def _extract_service_from_alert(alert: str) -> str | None:
    """从告警文本中提取服务名。

    Why: 推送前二次验证需要知道告警涉及哪个服务
    What: 匹配 "service:xxx=down" 或 "xxx 异常" 等模式
    Test: _extract_service_from_alert("service:letta=down") → "letta"
    """
    import re
    # 匹配 service:name=status 格式
    m = re.match(r"service:(\S+?)=", alert)
    if m:
        return m.group(1)
    # 匹配 "xxx 服务异常" 或 "xxx is down"
    m = re.search(r"(\w+)\s*(服务异常|is down|failed|unhealthy)", alert, re.I)
    if m:
        return m.group(1)
    return None

def _run_sensors() -> dict:
    """遍历 sensors/ 下所有 .py（排除 __init__.py），subprocess 执行并合并 JSON。"""
    sensors_dir = Path(__file__).parent / "sensors"
    merged = {}
    for script in sorted(sensors_dir.glob("*.py")):
        if script.name.startswith("_") or script.name == "test_sensor.py":
            continue
        try:
            r = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout.strip())
                merged.update(data)
        except Exception:
            pass
    return merged


def sense() -> dict:
    """采集系统感知数据。

    Why: 为 Think 阶段提供原始环境数据
    What: 通过 sensors/ 插件 + 内置采集合并数据
    Test: 验证返回 dict 包含 cpu_usage/services/timestamp 字段
    """
    now = datetime.now().isoformat()

    # 插件化传感器采集（sensors/*.py subprocess）
    sensor_data = _run_sensors()

    # 读取 OP 状态
    op_status: dict = {}
    op_path = Path(OP_STATUS_FILE)
    if op_path.exists():
        try:
            op_status = json.loads(op_path.read_text())
        except Exception:
            op_status = {"error": "读取失败"}

    # 读取 OP 任务结果
    op_results: dict = {}
    op_results_path = Path(OP_TASK_RESULTS_FILE)
    if op_results_path.exists():
        try:
            op_results = json.loads(op_results_path.read_text())
        except Exception:
            pass

    # 读取 WeChat Agent 状态
    wechat_status: dict = {}
    wechat_path = Path("/tmp/wechat-agent-status.json")
    if wechat_path.exists():
        try:
            wechat_status = json.loads(wechat_path.read_text())
        except Exception:
            pass

    # Android 手机传感器（USB 连接时采集，断连时返回 offline 标记）
    android_data: dict = {"status": "offline"}
    try:
        from android_sensor import sense_android

        android_data = sense_android()
        android_data["status"] = "online"
    except Exception as e:
        android_data["error"] = str(e)

    # 浏览器感知数据（browser_sense 模块）
    browser_data: dict = {}
    try:
        from browser_sense import get_browser_context

        browser_data = get_browser_context()
    except Exception:
        browser_data = {"status": "unavailable"}

    # 认知引擎评分（八维认知函数，由 cognitive_engine.py 计算）
    cognitive_data: dict = {}
    try:
        from cognitive_engine import score_cognitive_functions

        cognitive_data = score_cognitive_functions()
    except Exception as e:
        cognitive_data = {"error": str(e)}

    return {
        "timestamp": now,
        **sensor_data,
        "op_status": op_status,
        "op_results": op_results,
        "wechat": wechat_status,
        "android": android_data,
        "cognitive": cognitive_data,
        "browser": browser_data,
    }


# ── Act 阶段 ──────────────────────────────────────────────────────────────────

_ALERT_COOLDOWN_FILE = Path(OP_TASKS_FILE).parent / "alert_cooldown.json"
ALERT_COOLDOWN_SECS = 14400  # 4小时，防止进程重启后重复告警


def _load_cooldown() -> dict:
    try:
        import json
        return json.loads(_ALERT_COOLDOWN_FILE.read_text()) if _ALERT_COOLDOWN_FILE.exists() else {}
    except Exception:
        return {}


def _save_cooldown(m: dict) -> None:
    try:
        import json
        # 只保留4小时内的记录，防止文件膨胀
        cutoff = time.time() - ALERT_COOLDOWN_SECS
        trimmed = {k: v for k, v in m.items() if v > cutoff}
        _ALERT_COOLDOWN_FILE.write_text(json.dumps(trimmed))
    except Exception:
        pass


def _should_trigger_alert(key: str) -> bool:
    now = time.time()
    m = _load_cooldown()
    if now - m.get(key, 0) < ALERT_COOLDOWN_SECS:
        return False
    m[key] = now
    _save_cooldown(m)
    return True


def _is_duplicate_task(task_text: str, existing_content: str) -> bool:
    """检查是否为重复任务（关键词相似度 > 50%）。

    Why: 防止同类告警反复写入相同任务，避免 op-tasks.md 膨胀
    What: 提取任务关键词，与现有待执行任务和已跳过任务对比
    """
    import re

    # 提取关键词（去除日期、标签、停用词）
    def keywords(text: str) -> set:
        t = re.sub(r"\[.*?\]|\d{4}-\d{2}-\d{2}|\d{2}:\d{2}", "", text)
        t = re.sub(r'[，。！？、：；""' "（）]+", " ", t)
        t = re.sub(r"\s+", " ", t)
        words = set(t.strip().split())
        stopwords = {"的", "了", "以", "并", "且", "在", "到", "上", "中", "已", "未"}
        return words - stopwords

    new_kw = keywords(task_text)
    if not new_kw:
        return False

    # 检查现有待执行（- [ ]）和已跳过（- [x] [SKIP]）任务
    for line in existing_content.splitlines():
        if "- [ ]" not in line and "[SKIP" not in line:
            continue
        existing_kw = keywords(line)
        if not existing_kw:
            continue
        overlap = len(new_kw & existing_kw) / max(len(new_kw), len(existing_kw))
        if overlap >= 0.5:
            return True
    return False


# 永久黑名单：这些任务 Brain 无法通过 OP 解决，永远不写入
_TASK_BLACKLIST = [
    "cpu",
    "内存",
    "监控",
    "采集",
    "数据获取",
    "修复监控",
    "系统监控",
    "opencode",
    "ps 进程",
    "pid",
    "卡死",
    "死循环",
    "无响应",
    "高负载",
    "python3",           # python3.13 系统服务假阳性
    "corepack",          # paperclip server 正常进程
    "rg 进程",           # ripgrep 瞬时搜索命令
    "检查进程",          # 泛化进程检查（非具体故障）
    "bash 进程",         # 瞬时 shell 命令
    "异常进程",          # 泛化异常告警
    "nix 进程",          # nix-daemon 正常构建
    "堆栈",              # 收集堆栈调试
    "fe评分",            # 模板变量未渲染 {fe_score}
    "终止",              # kill/terminate 泛化任务
    "重启 letta",
    "重启 charlie",
    "启动 letta",
    "启动 charlie",
    "letta 服务以恢复",
    "charlie-hub 服务以恢复",
    "夜间运行",
    "排查监控",
    "修复脚本",
    "数据缺失",
    "数据返回",
    "数据为空",
    "采集为空",
    # 磁盘检查 — OP 自动处理，不应生成人工任务
    "磁盘ai",            # 磁盘AI分区检查
    "磁盘空间",          # 泛化磁盘空间
    "disk_ai",
    "mnt/ai.*清理",
    "/mnt/ai.*占用",
    "分区.*清理",
    "清理.*磁盘",
    "扩容",              # 扩容建议不派给OP
    "释放.*存储",
    "存储空间",
    # 任务跟进 — 不应递归生成跟进任务
    "任务跟进",
    "op-tasks.*进展",
    "未完成任务.*进展",
    "标记.*decay",
]


def _write_op_tasks(actions: list[dict]) -> None:
    """将高优先级行动写入 op-tasks.md，写入前去重 + 黑名单过滤。

    Why: AGI Brain 通过文件接口向 OP 派发需要执行的任务
    What: 过滤 assign_to==op 的行动，去重 + 黑名单后追加到 op-tasks.md
    Test: 传入相似任务两次，验证第二次不重复写入
    """
    op_actions = [a for a in actions if a.get("assign_to") == "op"]
    if not op_actions:
        return

    op_tasks_path = Path(OP_TASKS_FILE)
    op_tasks_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 读取现有内容用于去重
    existing = (
        op_tasks_path.read_text(encoding="utf-8") if op_tasks_path.exists() else ""
    )

    written = 0
    skipped = 0
    with open(op_tasks_path, "a", encoding="utf-8") as f:
        for action in op_actions:
            priority = action.get("priority", "medium")
            task = action.get("task", "未知任务")
            # 黑名单过滤（硬规则，无论措辞如何变化）
            task_lower = task.lower()
            if any(bl in task_lower for bl in _TASK_BLACKLIST):
                skipped += 1
                continue
            if _is_duplicate_task(task, existing):
                skipped += 1
                continue
            alert_key = task[:50]
            if not _should_trigger_alert(alert_key):
                skipped += 1
                continue
            line = f"- [ ] [AGI→OP] [{now}] [{priority}] {task}\n"
            f.write(line)
            existing += line  # 更新内存中的内容，防止同批次重复
            written += 1

    if written:
        print(f"[ACT] 写入 {written} 个任务到 op-tasks.md（跳过 {skipped} 个重复）")
    elif skipped:
        print(f"[ACT] 全部 {skipped} 个任务已存在，跳过写入")


async def _send_telegram(message: str) -> None:
    """发送 Telegram 通知（仅在有 token 时生效）。

    Why: 主动推送重要告警给用户，不依赖用户主动查询
    What: 调用 Telegram Bot API sendMessage
    Test: mock httpx，验证调用参数包含正确的 chat_id 和 message
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import httpx

    try:
        async with httpx.AsyncClient(
            timeout=10.0, proxy="http://127.0.0.1:7890"
        ) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )
    except Exception as e:
        print(f"[ACT] Telegram 发送失败：{e}")


async def _send_discord(message: str) -> None:
    """发送 Discord 告警到 alerts 频道。

    Why: AGI Brain 告警同时推送 Telegram 和 Discord，双通道覆盖
    What: 调用 Discord Bot API 发消息到 alerts 频道
    Test: 确认 DISCORD_BOT_TOKEN 和 DISCORD_ALERTS_CHANNEL_ID 已配置后调用
    """
    if not DISCORD_BOT_TOKEN or not DISCORD_ALERTS_CHANNEL_ID:
        return
    import httpx

    try:
        async with httpx.AsyncClient(
            timeout=10.0, proxy="http://127.0.0.1:7890"
        ) as client:
            await client.post(
                f"https://discord.com/api/v10/channels/{DISCORD_ALERTS_CHANNEL_ID}/messages",
                headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
                json={"content": message},
            )
    except Exception as e:
        print(f"[ACT] Discord 发送失败：{e}")


def _write_status(sense_data: dict, think_result: dict) -> None:
    """将最新状态写入状态文件。

    Why: 让其他模块（Telegram Bot、对话接口）能读取当前 Brain 状态
    What: 合并 sense 和 think 数据，写入 /tmp/agi-brain-status.json
    Test: 调用后验证状态文件存在且包含 summary 字段
    """
    status = {
        "updated_at": datetime.now().isoformat(),
        "sense": sense_data,
        "summary": think_result.get("summary", ""),
        "alerts": think_result.get("alerts", []),
        "actions_count": len(think_result.get("actions", [])),
    }
    Path(STATUS_FILE).write_text(json.dumps(status, ensure_ascii=False, indent=2))

    # 广播到对话室（port 9800 hub-api /api/dialogue/post）
    summary = think_result.get("summary", "")
    if summary and summary not in ("（无变化）",):
        try:
            import httpx

            httpx.post(
                "http://localhost:9800/api/dialogue/post",
                json={
                    "from": "BRAIN",
                    "content": f"[脑循环] {summary[:150]}",
                    "type": "action",
                },
                timeout=3,
            )
        except Exception:
            pass


# ── Letta 强制快照 ──────────────────────────────────────────────────────────

LETTA_SNAPSHOT_INTERVAL = 10  # 每10轮写一次快照（约10分钟）
LETTA_AGENT_ID = "agent-8651643c-e753-47ed-9759-bd955c6ac240"  # nixos-sysadmin


def _write_letta_snapshot(sense_data: dict) -> None:
    """每 N 轮强制写系统快照到 Letta archival memory。

    Why: 让 Letta agent 持续拥有最新系统状态，支持语义检索历史
    What: POST CPU/内存/服务摘要到 Letta archival API
    Test: 调用后检查 Letta archival 新增一条 [SNAPSHOT] 前缀记录
    """
    try:
        import urllib.request
        import urllib.parse

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        cpu = sense_data.get("cpu_usage", "?")
        mem = sense_data.get("memory_usage", "?")
        services = sense_data.get("services", {})
        svc_summary = []
        if isinstance(services, dict):
            for svc, info in list(services.items())[:5]:
                status = info if isinstance(info, str) else info.get("status", "?")
                svc_summary.append(f"{svc}={status}")

        content = (
            f"[SNAPSHOT] [{ts}] CPU={cpu}% MEM={mem}% "
            f"Services: {', '.join(svc_summary) if svc_summary else 'N/A'}"
        )
        if len(content) > 500:
            content = content[:500]

        url = f"http://localhost:8283/v1/agents/{LETTA_AGENT_ID}/archival-memory/"
        payload = json.dumps({"content": content}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"[LETTA] 快照已写入: {content[:80]}")
            else:
                print(f"[LETTA] 写入失败: HTTP {resp.status}")
    except Exception as e:
        print(f"[LETTA] 快照写入异常: {e}")


def _letta_log(message: str) -> None:
    """简短写入 Letta archival（用于自主执行结果记录）。
    
    Why: 形成操作闭环，让 Letta 记忆包含执行结果供下次检索
    """
    import urllib.request, urllib.error
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        payload = json.dumps({"text": f"[{ts}] [AUTO] {message}"}).encode()
        req = urllib.request.Request(
            "http://localhost:8283/v1/agents/agent-8651643c-e753-47ed-9759-bd955c6ac240/archival-memory/",
            data=payload,
            headers={"Authorization": "Bearer letta", "Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # 静默失败，不阻塞主循环


FLOWS_INDEX = Path(__file__).parent / "flows" / "index.json"


def _increment_flow_runs(flow_name: str) -> None:
    """更新 flows/index.json 中对应 flow 的 runs 计数。"""
    try:
        if not FLOWS_INDEX.exists():
            return
        data = json.loads(FLOWS_INDEX.read_text())
        for f in data.get("flows", []):
            if f["name"] == flow_name:
                f["runs"] = f.get("runs", 0) + 1
                break
        FLOWS_INDEX.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[FLOW] 更新 index.json 失败: {e}")


async def _auto_trigger_flows(sense_data: dict, loop_count: int) -> None:
    """基于感知数据模式自动触发 LangGraph Flow。

    Why: 让 Flow 从手动调用变为数据驱动自动触发，提升模块关联性
    What: 每30轮检查服务→self_heal，每60轮检查微信→social_intelligence
    Test: 服务异常时观察 self_heal flow 是否被触发，index.json runs 递增
    """
    flows_dir = Path(__file__).parent / "flows"

    # 每30轮检查服务状态，有异常→触发 self_heal
    if loop_count % 30 == 0:
        services = sense_data.get("services", {})
        has_failure = False
        if isinstance(services, dict):
            for svc, info in services.items():
                status = info if isinstance(info, str) else info.get("status", "")
                if status in ("failed", "dead", "stopped"):
                    has_failure = True
                    break
        if has_failure:
            flow_file = flows_dir / "self_heal.py"
            if flow_file.exists():
                print("[FLOW] 检测到服务异常，触发 self_heal flow")
                try:
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable,
                        str(flow_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await asyncio.wait_for(proc.wait(), timeout=120)
                    _increment_flow_runs("self_heal")
                    print(f"[FLOW] self_heal 完成 (exit={proc.returncode})")
                except asyncio.TimeoutError:
                    print("[FLOW] self_heal 超时120s，跳过")
                except Exception as e:
                    print(f"[FLOW] self_heal 执行失败: {e}")

    # 每60轮触发 social_intelligence 分析（低频，避免资源浪费）
    if loop_count % 60 == 0:
        flow_file = flows_dir / "social_intelligence.py"
        if flow_file.exists():
            print("[FLOW] 定时触发 social_intelligence flow")
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(flow_file),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.wait(), timeout=180)
                _increment_flow_runs("social_intelligence")
                print(f"[FLOW] social_intelligence 完成 (exit={proc.returncode})")
            except asyncio.TimeoutError:
                print("[FLOW] social_intelligence 超时180s，跳过")
            except Exception as e:
                print(f"[FLOW] social_intelligence 执行失败: {e}")


# ── 主循环 ────────────────────────────────────────────────────────────────────


async def main_loop(once: bool = False) -> None:
    """AGI Brain 主循环：Sense → Think → Act（v2自适应 + 事件驱动）。
    
    v2升级:
    - 自适应间隔：连续N次无变化后自动延长间隔（省CPU/token）
    - 热触发文件：touch /tmp/agi-brain-trigger 立即执行一轮
    - --once模式：单次执行后退出（配合 systemd path units）
    
    Why: 持续感知并响应系统状态变化，实现自主运行
    What: 每60秒执行一次 Sense→Think→Act，每30分钟主动推送
    Test: 运行10秒后验证状态文件已更新，无崩溃
    """
    global _last_proactive_time
    global _last_sense_hash
    import time
    
    # 自适应间隔状态
    current_interval = LOOP_INTERVAL
    nochange_streak = 0
    
    print(f"[BRAIN] AGI Brain v2 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[BRAIN] 基础间隔：{LOOP_INTERVAL}s，最大：{ADAPTIVE_MAX_INTERVAL}s，热触发：{TRIGGER_FILE}")
    if once:
        print("[BRAIN] --once 模式：执行一轮后退出")
    
    loop_count = 0
    while True:
        loop_count += 1
        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"\n[BRAIN] 第 {loop_count} 轮 — {now_str} (间隔{current_interval}s)")

        # ── Sense ────────────────────────────────────
        print("[SENSE] 采集系统数据...")
        sense_data = sense()
        print(
            f"[SENSE] CPU:{sense_data.get('cpu_usage')} MEM:{sense_data.get('memory_usage')}"
        )

        # ── Think ────────────────────────────────────
        h = _sense_hash(sense_data)
        if h == _last_sense_hash:
            nochange_streak += 1
            # 自适应间隔：连续 N 次无变化后延长间隔
            if nochange_streak >= ADAPTIVE_NOCHANGE_THRESHOLD:
                current_interval = min(current_interval * 2, ADAPTIVE_MAX_INTERVAL)
                print(f"[ADAPTIVE] 连续 {nochange_streak} 次无变化 → 间隔延长至 {current_interval}s")
            else:
                print(f"[THINK] 状态无变化 (连续{nochange_streak}/{ADAPTIVE_NOCHANGE_THRESHOLD})，跳过 LLM")
            _write_status(
                sense_data, {"summary": "（无变化）", "alerts": [], "actions": []}
            )
            log_brain_cycle("（无变化）", [])
            # Letta 快照：即使无变化也写入
            if loop_count % LETTA_SNAPSHOT_INTERVAL == 0:
                _write_letta_snapshot(sense_data)
            await _sleep_or_trigger(current_interval, loop_count)
            if once:
                break
            continue
        # 状态有变化 → 重置自适应间隔
        if nochange_streak >= ADAPTIVE_NOCHANGE_THRESHOLD:
            print(f"[ADAPTIVE] 检测到变化 → 间隔重置为 {LOOP_INTERVAL}s")
        nochange_streak = 0
        current_interval = LOOP_INTERVAL
        _last_sense_hash = h
        print("[THINK] 调用 LLM 分析...")
        # RateGuard: 检查模型调用频率
        _model = os.environ.get("DEFAULT_MODEL", "glm-5.1")
        if not _rate_guard.check(_model):
            print(f"[THINK] RateGuard: {_model} 被限流，跳过本轮")
            _write_status(
                sense_data,
                {"summary": f"RateGuard: {_model} 被限流", "alerts": [], "actions": []},
            )
            await asyncio.sleep(LOOP_INTERVAL)
            continue
        _rate_guard.record(_model)
        think_result = await analyze(sense_data)
        # 超阈值告警（记录到 op-tasks）
        call_count = len(_rate_guard._calls.get(_model, []))
        if call_count >= _rate_guard.max_calls * 0.8:
            _rate_guard.pause(_model)
            _write_op_tasks(
                [
                    {
                        "priority": "high",
                        "task": f"RateGuard: {_model} 调用频率接近阈值({call_count}/{_rate_guard.max_calls}次/分)，已暂停60s",
                        "assign_to": "op",
                    }
                ]
            )
        summary = think_result.get("summary", "")
        alerts = think_result.get("alerts", [])
        actions = think_result.get("actions", [])
        print(f"[THINK] {summary}")
        if alerts:
            print(f"[THINK] 告警：{alerts}")

        # ── Cognitive Modulation（认知调制）──────────
        cognitive = sense_data.get("cognitive", {})
        ne_div = cognitive.get("ne_divergence", 0)
        comp_rate = cognitive.get("completion_rate", 0)
        fe_score = cognitive.get("Fe", 75)
        hour = datetime.now().hour

        # Ne 发散 > 0.8 且完成率 < 0.3 → 限流任务创建（防止 op-tasks 膨胀）
        if ne_div > 0.8 and comp_rate < 0.3:
            actions = [a for a in actions if a.get("priority") == "high"]
            if actions:
                print(
                    f"[COGNITIVE] Ne发散={ne_div:.2f} 完成率={comp_rate:.2f} → 仅保留 high 优先级任务"
                )

        # 深夜(0-5) → 降级告警，不发 Telegram/Discord
        suppress_alerts = 0 <= hour <= 5

        # Fe < 40 → 提醒休息
        if fe_score < 40 and loop_count % 30 == 0:
            print(f"[COGNITIVE] Fe={fe_score}，推送休息提醒")
            _write_op_tasks(
                [
                    {
                        "priority": "low",
                        "task": "Fe评分过低({fe_score})，建议用户休息",
                        "assign_to": "op",
                    }
                ]
            )

        # ── Act ──────────────────────────────────────
        # 更新状态文件
        _write_status(sense_data, think_result)

        # Letta 强制快照（每10轮）
        if loop_count % LETTA_SNAPSHOT_INTERVAL == 0:
            _write_letta_snapshot(sense_data)

        # 自动 Flow 触发（基于感知数据模式）
        await _auto_trigger_flows(sense_data, loop_count)

        # ── P2 自主执行：低风险操作直接执行 ────────────
        from think import execute_autonomous
        auto_actions = []
        manual_actions = []
        for a in actions:
            task_lower = a.get("task", "").lower()
            # 检测可自主执行的关键词
            if any(k in task_lower for k in ["docker restart", "docker logs", "systemctl", "curl", "journalctl", "df -h", "du -sh"]):
                auto_actions.append(a)
            else:
                manual_actions.append(a)
        
        auto_results = []
        for a in auto_actions:
            result = await execute_autonomous(a)
            auto_results.append(f"{a['task'][:50]} → {'OK' if result['success'] else 'FAIL: '+result['error'][:30]}")
        
        if auto_actions:
            print(f"[AUTO] 自主执行 {len(auto_actions)} 个操作: {auto_results}")
            # 结果写回 Letta 记忆闭环
            for r in auto_results:
                _letta_log(r)
        
        # 非自主操作 → 派 OP 任务（去重写入 + 审计日志）
        if manual_actions:
            _write_op_tasks(manual_actions)
            log_tasks_queued(manual_actions)

        # 记录本轮摘要到审计日志
        log_brain_cycle(summary, alerts)

        # 有告警 → 过滤噪声 + 推送前实时验证 + 去重后发 Telegram + Discord
        if alerts:
            now_ts = time.time()
            actionable = []
            recovered_services = []  # 检测到恢复的服务

            for a in alerts:
                # 过滤限速/超时等非用户可处理的噪声
                if any(p.lower() in a.lower() for p in _ALERT_SUPPRESS_PATTERNS):
                    print(f"[ALERT_SKIP] 噪声告警已过滤（不推送）: {a[:80]}")
                    continue

                # 方案A：推送前实时验证服务状态
                svc_name = _extract_service_from_alert(a)
                if svc_name:
                    current_status = _quick_service_check(svc_name)
                    if current_status in ("running", "active", "online", "ok"):
                        print(f"[ALERT_SKIP] 服务已恢复，跳过推送: {a[:80]}")
                        # 方案B：检测到恢复 → 清除冷却 + 记录恢复状态
                        _alert_last_sent.pop(a[:60], None)
                        _last_known_service_status[svc_name] = current_status
                        recovered_services.append(svc_name)
                        continue
                    _last_known_service_status[svc_name] = current_status

                # 方案C：差异化冷却时间
                cooldown = _ALERT_COOLDOWN.get("default")
                if svc_name:
                    cooldown = _ALERT_COOLDOWN.get(svc_name, _ALERT_COOLDOWN["default"])
                key = a[:60]
                val = _alert_last_sent.get(key, 0)
                if not isinstance(val, (int, float)): val = 0
                if now_ts - val < cooldown:
                    print(f"[ALERT_SKIP] 冷却中（{int(now_ts - val)}s/{cooldown}s）: {key}")
                    continue
                _alert_last_sent[key] = now_ts
                actionable.append(a)

            # 方案D：推送恢复通知
            if recovered_services:
                recovery_msg = "✅ 服务恢复通知\n" + "\n".join(f"• {s} 已恢复正常" for s in recovered_services)
                await _send_telegram(recovery_msg)
                await _send_discord(recovery_msg)

            if actionable:
                alert_msg = "🧠 AGI Brain 告警\n" + "\n".join(f"• {a}" for a in actionable)
                await _send_telegram(alert_msg)
                await _send_discord(alert_msg)

        # 主动推送（每30分钟）
        now_ts = time.time()
        if now_ts - _last_proactive_time >= PROACTIVE_INTERVAL:
            proactive_msg = generate_proactive_message()
            if proactive_msg:
                print(f"[PROACTIVE] {proactive_msg}")
                await _send_telegram(f"📡 AGI 主动推送\n{proactive_msg}")
                await _send_discord(f"📡 AGI 主动推送\n{proactive_msg}")
            _last_proactive_time = now_ts

        if once:
            print("[BRAIN] --once 完成，退出")
            break
        
        await _sleep_or_trigger(current_interval, loop_count)


async def _sleep_or_trigger(interval: int, loop_count: int) -> None:
    """等待 interval 秒，期间检测热触发文件。
    
    Why: 支持事件驱动——touch 触发文件立即执行，无需等定时器
    What: 每2秒检查一次触发文件是否存在
    """
    import os
    check_interval = 2
    for _ in range(interval // check_interval):
        await asyncio.sleep(check_interval)
        if os.path.exists(TRIGGER_FILE):
            try:
                os.remove(TRIGGER_FILE)
            except OSError:
                pass
            print(f"[TRIGGER] 热触发文件检测到！立即执行第 {loop_count + 1} 轮")
            return


if __name__ == "__main__":
    import argparse
    from telegram_bot import listener_loop
    
    parser = argparse.ArgumentParser(description="AGI Brain v2")
    parser.add_argument("--once", action="store_true", help="单次执行后退出")
    parser.add_argument("--no-telegram", action="store_true", help="禁用Telegram监听")
    args = parser.parse_args()
    
    async def run():
        if args.no_telegram:
            await main_loop(once=args.once)
        else:
            # 并行运行：主循环 + Telegram监听
            await asyncio.gather(
                main_loop(once=args.once),
                listener_loop(),
            )
    
    asyncio.run(run())
