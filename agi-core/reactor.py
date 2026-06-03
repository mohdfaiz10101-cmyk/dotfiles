"""
reactor.py — AGI Brain 事件驱动 Reactor 层
替代 60s 轮询 → systemd journal + inotify + docker events 事件驱动
保留 5min heartbeat 作为兜底

架构:
    EventSource (journal/inotify/docker/heartbeat/timer)
        → EventBus (asyncio.Queue + fanout)
        → EventHandler (sense_delta → think → act)

Why: 60s轮询在无变化时浪费CPU/LLM token，事件驱动只在状态变化时触发
What: 多源事件汇聚 → 去重合并 → 触发 Think→Act
Test: 发送模拟事件后验证 handler 被调用
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ── Event 定义 ─────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    SYSTEMD_CHANGE = "systemd_change"      # systemd unit state changed
    DOCKER_EVENT = "docker_event"          # docker container event
    FILE_CHANGE = "file_change"            # inotify file change (op-tasks, status files)
    HEARTBEAT = "heartbeat"                # periodic health check (5min)
    TRIGGER = "trigger"                    # manual trigger (agi-brain-trigger file)
    THRESHOLD = "threshold"                # metric threshold crossed (CPU/disk/memory)
    NETWORK = "network"                    # network connectivity change


@dataclass
class Event:
    type: EventType
    source: str          # "journal-watcher", "docker-events", "inotify", "heartbeat-timer"
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0    # 0=normal, 1=high, 2=critical

    @property
    def key(self) -> str:
        """去重键：相同 source + payload 核心字段 = 重复事件"""
        p = self.payload
        if self.type == EventType.SYSTEMD_CHANGE:
            return f"sysd:{p.get('unit', '')}:{p.get('new_state', '')}"
        elif self.type == EventType.DOCKER_EVENT:
            return f"docker:{p.get('container', '')}:{p.get('action', '')}"
        elif self.type == EventType.THRESHOLD:
            return f"thresh:{p.get('metric', '')}:{p.get('value', '')}"
        return f"{self.type}:{self.source}"


# ── EventBus ──────────────────────────────────────────────────────────────────

class EventBus:
    """异步事件总线 — 多源汇聚 + 去重 + fanout 到 handler"""

    def __init__(self, dedup_window: float = 5.0, max_queue: int = 100):
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue)
        self._dedup_window = dedup_window
        self._recent: dict[str, float] = {}  # key → timestamp
        self._handlers: list[Callable[[Event], Coroutine]] = []

    def subscribe(self, handler: Callable[[Event], Coroutine]) -> None:
        self._handlers.append(handler)

    async def publish(self, event: Event) -> bool:
        """发布事件（去重），返回 True 表示入队成功"""
        # 去重：5秒内相同 key 的事件只保留第一个
        now = time.time()
        key = event.key
        if key in self._recent and now - self._recent[key] < self._dedup_window:
            return False
        self._recent[key] = now

        # 清理过期去重记录
        if len(self._recent) > 1000:
            cutoff = now - self._dedup_window * 2
            self._recent = {k: v for k, v in self._recent.items() if v > cutoff}

        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("EventBus queue full, dropping event: %s", event.key)
            return False

    async def dispatch_loop(self) -> None:
        """持续从队列取出事件，fanout 到所有 handler"""
        while True:
            event = await self._queue.get()
            for handler in self._handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error("Event handler error: %s → %s", handler.__name__, e)


# ── Event Sources ─────────────────────────────────────────────────────────────

class HeartbeatSource:
    """定时心跳源 — 每 N 秒发送 HEARTBEAT 事件（兜底感知）"""

    def __init__(self, bus: EventBus, interval: int = 300):
        self._bus = bus
        self._interval = interval

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self._bus.publish(Event(
                type=EventType.HEARTBEAT,
                source="heartbeat-timer",
                payload={"interval": self._interval},
                priority=0,
            ))


class TriggerFileSource:
    """热触发文件源 — inotify 监听 agi-brain-trigger 文件"""

    def __init__(self, bus: EventBus, trigger_path: Path | None = None):
        self._bus = bus
        self._trigger = trigger_path or Path.home() / ".local/state/agi-brain-trigger"

    async def run(self) -> None:
        while True:
            await asyncio.sleep(1)
            if self._trigger.exists():
                try:
                    self._trigger.unlink()
                except OSError:
                    pass
                await self._bus.publish(Event(
                    type=EventType.TRIGGER,
                    source="trigger-file",
                    payload={"path": str(self._trigger)},
                    priority=2,
                ))


class DockerEventSource:
    """Docker 事件源 — 监听容器 start/die/health_status 事件"""

    def __init__(self, bus: EventBus):
        self._bus = bus

    async def run(self) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "events",
                "--filter", "event=start",
                "--filter", "event=die",
                "--filter", "event=health_status",
                "--format", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            if proc.stdout is None:
                return
            async for line in proc.stdout:
                try:
                    data = json.loads(line.decode().strip())
                    action = data.get("Action", data.get("status", ""))
                    container = data.get("Actor", {}).get("Attributes", {}).get("name", data.get("id", "")[:12])
                    await self._bus.publish(Event(
                        type=EventType.DOCKER_EVENT,
                        source="docker-events",
                        payload={"container": container, "action": action, "raw": data},
                        priority=2 if action == "die" else 1,
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue
        except FileNotFoundError:
            logger.debug("docker CLI not found, skipping DockerEventSource")
        except Exception as e:
            logger.debug("DockerEventSource error: %s", e)


class JournalWatchSource:
    """systemd journal 事件源 — 监听 unit 状态变化（Failed/Activating/Active）"""

    KEYWORDS = ("Failed", "failed", "Stopped", "Started", "inactive", "degraded")

    def __init__(self, bus: EventBus):
        self._bus = bus

    async def run(self) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "journalctl", "--user", "-f", "--output=json",
                "--since", "now",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            if proc.stdout is None:
                return
            async for line in proc.stdout:
                text = line.decode(errors="replace").strip()
                if not text:
                    continue
                if any(kw in text for kw in self.KEYWORDS):
                    try:
                        data = json.loads(text)
                        unit = data.get("UNIT", data.get("_SYSTEMD_UNIT", ""))
                        msg = data.get("MESSAGE", "")
                        if unit:
                            await self._bus.publish(Event(
                                type=EventType.SYSTEMD_CHANGE,
                                source="journal-watcher",
                                payload={"unit": unit, "message": msg[:200]},
                                priority=2 if "Failed" in msg or "failed" in msg else 1,
                            ))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            logger.debug("journalctl not found, skipping JournalWatchSource")
        except Exception as e:
            logger.debug("JournalWatchSource error: %s", e)


class FileWatchSource:
    """文件变更源 — inotify 监听关键文件变化"""

    def __init__(self, bus: EventBus, paths: list[Path] | None = None):
        self._bus = bus
        self._paths = paths or [
            Path.home() / ".local/state/op-status.json",
            Path.home() / ".local/state/wechat-agent-status.json",
        ]

    async def run(self) -> None:
        """轮询检查文件修改时间（轻量方案，无需 inotify 依赖）"""
        mtimes: dict[str, float] = {}
        while True:
            for p in self._paths:
                if not p.exists():
                    continue
                try:
                    mtime = p.stat().st_mtime
                    key = str(p)
                    if key in mtimes and mtime > mtimes[key]:
                        await self._bus.publish(Event(
                            type=EventType.FILE_CHANGE,
                            source="file-watch",
                            payload={"path": str(p), "mtime": mtime},
                            priority=0,
                        ))
                    mtimes[key] = mtime
                except OSError:
                    continue
            await asyncio.sleep(5)


# ── Reactor 主类 ──────────────────────────────────────────────────────────────

class Reactor:
    """事件驱动 Reactor — 启动所有事件源，分发到 handler"""

    def __init__(
        self,
        on_event: Callable[[Event], Coroutine],
        heartbeat_interval: int = 300,
        enable_journal: bool = True,
        enable_docker: bool = True,
    ):
        self._bus = EventBus()
        self._bus.subscribe(on_event)
        self._sources: list[Any] = [
            HeartbeatSource(self._bus, heartbeat_interval),
            TriggerFileSource(self._bus),
            FileWatchSource(self._bus),
        ]
        if enable_journal:
            self._sources.append(JournalWatchSource(self._bus))
        if enable_docker:
            self._sources.append(DockerEventSource(self._bus))

    async def run(self) -> None:
        """启动所有事件源 + dispatch loop"""
        tasks = [asyncio.create_task(src.run()) for src in self._sources]
        tasks.append(asyncio.create_task(self._bus.dispatch_loop()))
        logger.info("[REACTOR] 启动 %d 个事件源", len(self._sources))
        await asyncio.gather(*tasks)
