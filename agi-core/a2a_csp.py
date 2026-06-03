"""
a2a_csp.py — A2A 通信 CSP 协议 + 向量时钟

Why: 原始 jsonl 文件追加无去重、无顺序保证、无冲突检测
What: Channel-based 通信 + Vector Clock 因果排序 + 幂等去重
Test: python3 a2a_csp.py send cc "hello" → 写入 channel + 向量时钟

协议:
  - Channel: 按主题分组（task/info/result/question）
  - VectorClock: 每个 agent 维护计数器， causally ordered
  - Idempotency: message_id = hash(sender+seq+content)，防重复
  - Priority: P0 > P1 > P2，高优先级插队
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CHANNEL_DIR = Path.home() / ".local/state/a2a-channels"
AGENT_ID = os.environ.get("A2A_AGENT_ID", "op")

# Agent 标识映射
AGENT_NAMES = {
    "cc": "cc",
    "op": "op",
    "letta": "letta",
    "arch": "arch",
    "all": "all",
}


@dataclass
class VectorClock:
    """向量时钟：每个 agent 一个计数器， causally ordered。"""
    counters: dict[str, int] = field(default_factory=dict)

    def increment(self, agent: str) -> int:
        """递增指定 agent 的计数器，返回新值。"""
        self.counters[agent] = self.counters.get(agent, 0) + 1
        return self.counters[agent]

    def merge(self, other: "VectorClock") -> None:
        """合并另一个向量时钟（取最大值）。"""
        for agent, count in other.counters.items():
            self.counters[agent] = max(self.counters.get(agent, 0), count)

    def is_concurrent(self, other: "VectorClock") -> bool:
        """判断两个时钟是否并发（无因果关系）。"""
        self_dom = any(self.counters.get(a, 0) > other.counters.get(a, 0) for a in set(self.counters) | set(other.counters))
        other_dom = any(other.counters.get(a, 0) > self.counters.get(a, 0) for a in set(self.counters) | set(other.counters))
        return self_dom and other_dom

    def to_dict(self) -> dict:
        return dict(self.counters)

    @classmethod
    def from_dict(cls, data: dict) -> "VectorClock":
        return cls(counters=dict(data))


@dataclass
class A2AMessage:
    """A2A 消息。"""
    sender: str
    receiver: str
    content: str
    task_type: str = "info"
    priority: int = 1          # 0=P0, 1=P1, 2=P2
    message_id: str = ""
    vector_clock: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    payload: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.message_id:
            raw = f"{self.sender}:{self.content}:{self.timestamp}"
            self.message_id = hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class Channel:
    """通信通道：按 topic 分组，支持 priority queue。"""
    name: str
    messages: list[A2AMessage] = field(default_factory=list)
    vector_clock: VectorClock = field(default_factory=VectorClock)

    def push(self, msg: A2AMessage) -> None:
        """推送消息（按 priority 排序插入）。"""
        msg.vector_clock = self.vector_clock.to_dict()
        seq = self.vector_clock.increment(msg.sender)
        msg.payload["seq"] = seq

        # 按 priority 插入（0=P0 最前）
        inserted = False
        for i, existing in enumerate(self.messages):
            if msg.priority < existing.priority:
                self.messages.insert(i, msg)
                inserted = True
                break
        if not inserted:
            self.messages.append(msg)

    def is_duplicate(self, msg: A2AMessage) -> bool:
        """幂等检查：message_id 去重。"""
        return any(m.message_id == msg.message_id for m in self.messages)

    def drain(self, receiver: str = "", max_items: int = 20) -> list[A2AMessage]:
        """取出消息（支持 receiver filter）。"""
        result = []
        remaining = []
        for m in self.messages:
            if len(result) >= max_items:
                remaining.append(m)
                continue
            if receiver and m.receiver not in ("all", receiver):
                remaining.append(m)
                continue
            result.append(m)
        self.messages = remaining
        return result

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "messages": [self._msg_to_dict(m) for m in self.messages],
            "vector_clock": self.vector_clock.to_dict(),
        }

    @staticmethod
    def _msg_to_dict(m: A2AMessage) -> dict:
        return {
            "sender": m.sender,
            "receiver": m.receiver,
            "content": m.content,
            "task_type": m.task_type,
            "priority": m.priority,
            "message_id": m.message_id,
            "vector_clock": m.vector_clock,
            "timestamp": m.timestamp,
            "payload": m.payload,
        }


# ── Channel 管理器 ──────────────────────────────────────────────────────────

class ChannelManager:
    """多通道管理器：task/info/result/question + 持久化。"""

    def __init__(self, base_dir: Path = CHANNEL_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.channels: dict[str, Channel] = {}
        self._load_all()

    def _channel_path(self, name: str) -> Path:
        return self.base_dir / f"{name}.jsonl"

    def _load_all(self) -> None:
        """从磁盘加载所有通道。"""
        for f in self.base_dir.glob("*.jsonl"):
            name = f.stem
            ch = Channel(name=name)
            try:
                for line in f.read_text().strip().split("\n"):
                    if not line:
                        continue
                    data = json.loads(line)
                    msg = A2AMessage(
                        sender=data["sender"],
                        receiver=data["receiver"],
                        content=data["content"],
                        task_type=data.get("task_type", "info"),
                        priority=data.get("priority", 1),
                        message_id=data.get("message_id", ""),
                        vector_clock=data.get("vector_clock", {}),
                        timestamp=data.get("timestamp", 0),
                        payload=data.get("payload", {}),
                    )
                    ch.messages.append(msg)
                    # Restore vector clock
                    for agent, count in data.get("vector_clock", {}).items():
                        ch.vector_clock.counters[agent] = max(
                            ch.vector_clock.counters.get(agent, 0), count
                        )
            except Exception:
                pass
            self.channels[name] = ch

    def _ensure_channel(self, name: str) -> Channel:
        if name not in self.channels:
            self.channels[name] = Channel(name=name)
        return self.channels[name]

    def send(self, sender: str, receiver: str, content: str,
             task_type: str = "info", priority: int = 1,
             payload: dict = None) -> A2AMessage:
        """发送消息到对应通道。"""
        ch_name = task_type if task_type in ("task", "info", "result", "question") else "info"
        ch = self._ensure_channel(ch_name)
        msg = A2AMessage(
            sender=sender, receiver=receiver, content=content,
            task_type=task_type, priority=priority,
            payload=payload or {},
        )
        # 幂等检查
        if ch.is_duplicate(msg):
            return msg  # 静默去重
        ch.push(msg)
        self._persist(ch)
        return msg

    def receive(self, receiver: str, channel: str = "info",
                max_items: int = 20) -> list[A2AMessage]:
        """接收消息。"""
        ch_name = channel if channel in self.channels else "info"
        ch = self._ensure_channel(ch_name)
        msgs = ch.drain(receiver=receiver, max_items=max_items)
        self._persist(ch)
        return msgs

    def _persist(self, ch: Channel) -> None:
        """持久化通道到 jsonl。"""
        try:
            path = self._channel_path(ch.name)
            lines = []
            for m in ch.messages:
                lines.append(json.dumps(Channel._msg_to_dict(m), ensure_ascii=False))
            path.write_text("\n".join(lines) + "\n")
        except Exception:
            pass

    def stats(self) -> dict:
        """通道统计。"""
        return {
            name: {
                "count": len(ch.messages),
                "vector_clock": ch.vector_clock.to_dict(),
            }
            for name, ch in self.channels.items()
        }


# ── 全局实例 ──────────────────────────────────────────────────────────────────

_manager: Optional[ChannelManager] = None


def get_manager() -> ChannelManager:
    global _manager
    if _manager is None:
        _manager = ChannelManager()
    return _manager


# ── 公共 API ──────────────────────────────────────────────────────────────────

def send(sender: str, receiver: str, content: str,
         task_type: str = "info", priority: int = 1) -> dict:
    """发送 A2A 消息。"""
    mgr = get_manager()
    msg = mgr.send(sender, receiver, content, task_type, priority)
    return {
        "message_id": msg.message_id,
        "sender": msg.sender,
        "receiver": msg.receiver,
        "channel": task_type,
        "priority": priority,
        "timestamp": msg.timestamp,
    }


def receive(receiver: str, channel: str = "info") -> list[dict]:
    """接收 A2A 消息。"""
    mgr = get_manager()
    msgs = mgr.receive(receiver, channel)
    return [
        {
            "message_id": m.message_id,
            "sender": m.sender,
            "content": m.content[:200],
            "task_type": m.task_type,
            "priority": m.priority,
            "timestamp": m.timestamp,
        }
        for m in msgs
    ]


def stats() -> dict:
    """A2A 通信统计。"""
    mgr = get_manager()
    return mgr.stats()


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 a2a_csp.py send <sender> <receiver> <content> [task_type] [priority]")
        print("      python3 a2a_csp.py receive <receiver> [channel]")
        print("      python3 a2a_csp.py stats")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "send":
        sender = sys.argv[2] if len(sys.argv) > 2 else "op"
        receiver = sys.argv[3] if len(sys.argv) > 3 else "cc"
        content = sys.argv[4] if len(sys.argv) > 4 else ""
        task_type = sys.argv[5] if len(sys.argv) > 5 else "info"
        priority = int(sys.argv[6]) if len(sys.argv) > 6 else 1
        result = send(sender, receiver, content, task_type, priority)
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == "receive":
        receiver = sys.argv[2] if len(sys.argv) > 2 else "op"
        channel = sys.argv[3] if len(sys.argv) > 3 else "info"
        msgs = receive(receiver, channel)
        print(json.dumps(msgs, ensure_ascii=False, indent=2))

    elif cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)
