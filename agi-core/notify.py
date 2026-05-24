#!/usr/bin/env python3
"""notify.py — AGI 统一通知中心

架构设计（参考社区最佳实践）:
  - 单例模式：全进程共享一个 Notifier 实例
  - 指数退避限流：同类消息越频繁，冷却越长
  - 消息合并窗口：短时间多条消息合并为一条发送
  - 多通道统一接口：Telegram + Discord + notify-send
  - 内存去重：相同内容 N 秒内不重复发送
  - 静默时段：深夜自动降级为仅日志

替代: brain._send_telegram, brain._send_discord,
      op_push_service._push_to_telegram, report_generator._send_telegram,
      report_generator._send_discord, discord_cc_push.discord_send
"""

import asyncio
import json
import os
import time
import hashlib
import subprocess
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# ── 通道配置 ──────────────────────────────────────────────────────────

_TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
_DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
_DISCORD_ALERTS_CH = os.environ.get("DISCORD_ALERTS_CHANNEL_ID", "")
_DISCORD_CC_CH = "1490986400747884585"

_PROXY = "http://127.0.0.1:7890"


class Channel(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    DESKTOP = "desktop"       # notify-send
    DISCORD_CC = "discord_cc" # Discord #cc 频道


# ── 限流配置 ──────────────────────────────────────────────────────────

class Priority(Enum):
    LOW = "low"           # 信息性：合并+长冷却
    NORMAL = "normal"     # 常规告警
    HIGH = "high"         # 重要告警：短冷却
    CRITICAL = "critical" # 紧急：立即发送，不合并


# 基础冷却（秒）— 同 hash 消息最小发送间隔
_BASE_COOLDOWN: dict[Priority, int] = {
    Priority.LOW: 3600,        # 1h
    Priority.NORMAL: 1800,     # 30min
    Priority.HIGH: 600,        # 10min
    Priority.CRITICAL: 60,     # 1min
}

# 指数退避上限 — 连续同类消息达到此值后不再缩短
_MAX_COOLDOWN: dict[Priority, int] = {
    Priority.LOW: 21600,       # 6h
    Priority.NORMAL: 10800,    # 3h
    Priority.HIGH: 7200,       # 2h
    Priority.CRITICAL: 3600,   # 1h
}

# 合并窗口（秒）— 窗口内同类消息合并为一条
_MERGE_WINDOW = 30

# 静默时段（0-5点）：只记日志不推送
_SILENT_HOURS = range(0, 6)


# ── 消息数据 ──────────────────────────────────────────────────────────

@dataclass
class Message:
    text: str
    priority: Priority = Priority.NORMAL
    channels: list[Channel] = field(default_factory=lambda: [Channel.TELEGRAM, Channel.DISCORD])
    group: str = ""           # 合并分组 key（空=不合并）
    dedup_key: str = ""       # 去重 key（空=自动用 text[:80]）
    category: str = ""        # TG 分类路由 key（空=自动分类）


# ── 核心通知器 ────────────────────────────────────────────────────────

class Notifier:
    """统一通知中心 — 全局单例"""

    _instance: Optional["Notifier"] = None

    def __new__(cls) -> "Notifier":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._sent_log: dict[str, float] = {}         # dedup_key → last_sent_ts
        self._consecutive: dict[str, int] = defaultdict(int)  # group → 连续次数
        self._merge_buffer: dict[str, list[Message]] = defaultdict(list)
        self._merge_timer: Optional[asyncio.Task] = None
        self._desktop_last: float = 0                  # notify-send 限流

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def _current_cooldown(self, key: str, priority: Priority) -> int:
        """指数退避冷却时间：连续发送越多，冷却越长"""
        base = _BASE_COOLDOWN[priority]
        cap = _MAX_COOLDOWN[priority]
        n = self._consecutive.get(key, 0)
        cooldown = min(base * (2 ** min(n, 4)), cap)  # 最多 ×16
        return int(cooldown)

    def _should_send(self, msg: Message) -> bool:
        """去重 + 冷却检查"""
        now = time.time()
        hour = time.localtime().tm_hour

        # 静默时段：LOW/NORMAL 不发送
        if hour in _SILENT_HOURS and msg.priority in (Priority.LOW, Priority.NORMAL):
            return False

        key = msg.dedup_key or msg.text[:80]
        cooldown = self._current_cooldown(key, msg.priority)
        last = self._sent_log.get(key, 0)

        if now - last < cooldown:
            return False
        return True

    def _mark_sent(self, key: str, priority: Priority) -> None:
        """记录发送，更新退避计数器"""
        now = time.time()
        self._sent_log[key] = now
        self._consecutive[key] += 1

    def _decay_consecutive(self) -> None:
        """定期衰减连续计数（每30分钟）"""
        for key in list(self._consecutive.keys()):
            if self._consecutive[key] > 0:
                self._consecutive[key] = max(0, self._consecutive[key] - 1)
        # 清理过期 sent_log（>24h）
        cutoff = time.time() - 86400
        self._sent_log = {k: v for k, v in self._sent_log.items() if v > cutoff}

    # ── 合并窗口 ──────────────────────────────────────────────────────

    async def _flush_merge(self, group: str) -> None:
        """合并窗口到期，批量发送"""
        if group not in self._merge_buffer:
            return
        messages = self._merge_buffer.pop(group)
        if not messages:
            return

        # 取最高优先级
        top_priority = max(m.priority for m in messages)

        # 合并文本
        if len(messages) == 1:
            combined = messages[0].text
        else:
            lines = []
            # 按内容去重
            seen = set()
            for m in messages:
                short = m.text[:80]
                if short not in seen:
                    seen.add(short)
                    lines.append(m.text)
            combined = "\n".join(lines)

        merged_msg = Message(
            text=combined,
            priority=top_priority,
            channels=messages[0].channels,
            dedup_key=f"merge:{group}",
        )
        await self.send(merged_msg)

    async def _schedule_flush(self, group: str) -> None:
        """延迟 _MERGE_WINDOW 秒后刷新"""
        if self._merge_timer and not self._merge_timer.done():
            self._merge_timer.cancel()
        self._merge_timer = asyncio.create_task(
            asyncio.sleep(_MERGE_WINDOW)
        )
        try:
            await self._merge_timer
        except asyncio.CancelledError:
            pass
        await self._flush_merge(group)

    # ── 公开 API ──────────────────────────────────────────────────────

    async def send(self, msg: Message) -> bool:
        """发送一条消息（经过去重+限流）"""
        if not msg.text or not msg.text.strip():
            return False

        key = msg.dedup_key or msg.text[:80]

        # 需要合并？
        if msg.group:
            self._merge_buffer[msg.group].append(msg)
            asyncio.create_task(self._schedule_flush(msg.group))
            return True

        # 去重检查
        if not self._should_send(msg):
            return False

        self._mark_sent(key, msg.priority)

        # 并发发送所有通道
        tasks = []
        if Channel.TELEGRAM in msg.channels:
            tasks.append(_send_telegram(msg.text, msg.category))
        if Channel.DISCORD in msg.channels:
            tasks.append(_send_discord(msg.text, _DISCORD_ALERTS_CH))
        if Channel.DISCORD_CC in msg.channels:
            tasks.append(_send_discord(msg.text, _DISCORD_CC_CH))
        if Channel.DESKTOP in msg.channels:
            tasks.append(asyncio.to_thread(_send_desktop, msg.text[:80], msg.text[:200]))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        return True

    async def alert(self, text: str, group: str = "alert", channels: list[Channel] | None = None) -> bool:
        """快捷方法：发送告警（NORMAL 优先级，自动合并）"""
        ch = channels or [Channel.TELEGRAM, Channel.DISCORD]
        return await self.send(Message(
            text=text,
            priority=Priority.HIGH,
            channels=ch,
            group=group,
        ))

    async def info(self, text: str, channels: list[Channel] | None = None) -> bool:
        """快捷方法：发送信息（LOW 优先级，不合并）"""
        ch = channels or [Channel.TELEGRAM]
        return await self.send(Message(
            text=text,
            priority=Priority.LOW,
            channels=ch,
        ))

    async def critical(self, text: str, channels: list[Channel] | None = None) -> bool:
        """快捷方法：紧急通知（立即发送）"""
        ch = channels or [Channel.TELEGRAM, Channel.DISCORD]
        return await self.send(Message(
            text=text,
            priority=Priority.CRITICAL,
            channels=ch,
        ))

    def maintenance(self) -> None:
        """清理过期记录（可定期调用）"""
        self._decay_consecutive()


# ── 底层传输层 ────────────────────────────────────────────────────────

async def _send_telegram(text: str, category: str = "info") -> None:
    """Telegram Bot API 发送 — 自动分类路由到 Forum 话题"""
    if not _TELEGRAM_TOKEN:
        return
    try:
        # 优先使用 TG Router（支持 Forum 话题分类）
        from tg_group_router import route_message as tg_route
        ok = await tg_route(text, category)
        if ok:
            print(f"[NOTIFY] Telegram OK ({len(text)} chars) → {category}")
            return
    except ImportError:
        pass
    
    # 降级：直接发送到私聊
    import httpx
    if not _TELEGRAM_CHAT:
        return
    try:
        async with httpx.AsyncClient(timeout=15.0, proxy=_PROXY) as c:
            resp = await c.post(
                f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": _TELEGRAM_CHAT, "text": text[:4096]},
            )
            if resp.status_code == 200:
                print(f"[NOTIFY] Telegram OK ({len(text)} chars)")
            else:
                print(f"[NOTIFY] Telegram {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"[NOTIFY] Telegram 失败: {e}")


async def _send_discord(text: str, channel_id: str) -> None:
    """Discord Bot API 发送（分片支持长消息）"""
    if not _DISCORD_TOKEN or not channel_id:
        return
    import httpx
    # Discord 限制 2000 字符
    chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
    try:
        async with httpx.AsyncClient(timeout=15.0, proxy=_PROXY) as c:
            for chunk in chunks:
                await c.post(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers={"Authorization": f"Bot {_DISCORD_TOKEN}"},
                    json={"content": chunk},
                )
        print(f"[NOTIFY] Discord OK ({len(chunks)} chunks)")
    except Exception as e:
        print(f"[NOTIFY] Discord 失败: {e}")


def _send_desktop(title: str, body: str) -> None:
    """notify-send 桌面通知（限流：同分钟内最多1条）"""
    now = time.time()
    global _desktop_last
    # 同分钟内不重复
    if now - _desktop_last < 60:
        return
    _desktop_last = now
    try:
        subprocess.Popen(
            ["notify-send", "-t", "5000", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[NOTIFY] Desktop OK: {title[:30]}")
    except Exception:
        pass


# ── 全局快捷访问 ──────────────────────────────────────────────────────

_notifier: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """获取全局单例"""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


# 兼容旧代码的快捷函数
async def notify_telegram(text: str) -> None:
    await get_notifier().info(text, [Channel.TELEGRAM])

async def notify_discord(text: str, channel_id: str = "") -> None:
    ch = channel_id or _DISCORD_ALERTS_CH
    await _send_discord(text, ch)

async def notify_desktop(title: str, body: str) -> None:
    await asyncio.to_thread(_send_desktop, title, body)
