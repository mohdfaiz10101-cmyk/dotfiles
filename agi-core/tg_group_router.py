#!/usr/bin/env python3
"""
tg_group_router.py — Telegram 消息分类路由器

功能:
  1. 自动发现/创建 Forum 超级群组
  2. 8 个预定义话题（系统告警/服务状态/安全/微信/巡检/代理/任务/一般）
  3. 基于规则的消息自动分类
  4. 将消息路由到正确的话题

架构:
  - 纯 Bot API，无需 telethon
  - 群组创建：通过 deep link (t.me/bot?startgroup=1) 引导用户一键创建
  - 话题管理：createForumTopic / editForumTopic
  - 路由：sendMessage + message_thread_id

使用:
  python3 tg_group_router.py                    # 初始化（首次创建群组）
  python3 tg_group_router.py --send "CPU 使用率 95%"   # 自动分类并发送
  python3 tg_group_router.py --send "微信新消息" --cat wechat  # 指定分类
  python3 tg_group_router.py --status           # 查看群组/话题状态
  python3 tg_group_router.py --classify "Docker容器异常"  # 仅分类
"""

import asyncio
import json
import os
import re
import sys
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── 配置 ──────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get(
    "TG_BOT_TOKEN",
    "8797063873:AAGvApEP9frmA74b6nmxODHshzo1TwJR5ks"
)
PRIVATE_CHAT_ID = os.environ.get("TG_CHAT_ID", "5036541266")
PROXY = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 注册表保存路径
REGISTRY_FILE = Path(os.environ.get(
    "TG_ROUTER_REGISTRY",
    str(Path.home() / ".local/state/tg-group-registry.json")
))

# ── 分类系统 ──────────────────────────────────────────────────────────

class Category:
    """预定义的通知分类"""
    
    CATEGORIES = {
        "system": {
            "emoji": "🖥",
            "name": "系统告警",
            "icon_custom_emoji_id": "",
            "desc": "CPU/内存/磁盘/温度/OOM/systemd失败",
            "keywords": [
                "cpu", "内存", "磁盘", "温度", "oom", "systemd", "swap",
                "负载", "load", "disk", "memory", "过热", "out of memory",
                "磁盘空间", "inode", "僵尸进程", "内核", "kernel",
            ],
        },
        "service": {
            "emoji": "⚙️",
            "name": "服务状态",
            "icon_custom_emoji_id": "",
            "desc": "Docker容器/API端点/端口可达性/systemd服务",
            "keywords": [
                "docker", "容器", "container", "端口", "port", "服务",
                "service", "api", "endpoint", "health", "健康检查",
                "重启", "restart", "启动", "停止", "stop", "start",
                "healthy", "unhealthy", "exited", "dead",
            ],
        },
        "security": {
            "emoji": "🔒",
            "name": "安全事件",
            "icon_custom_emoji_id": "",
            "desc": "SSH登录/异常进程/防火墙/入侵检测",
            "keywords": [
                "ssh", "登录", "login", "防火墙", "firewall", "ufw",
                "入侵", "intrusion", "扫描", "scan", "端口扫描",
                "暴力破解", "brute", "密码", "password", "权限",
                "root", "sudo", "异常进程",
            ],
        },
        "wechat": {
            "emoji": "💬",
            "name": "微信消息",
            "icon_custom_emoji_id": "",
            "desc": "微信通知/CRM/客户消息/自动回复",
            "keywords": [
                "微信", "wechat", "weixin", "联系人", "contact",
                "crm", "客户", "消息", "message", "群聊", "自动回复",
                "filehelper", "朋友圈",
            ],
        },
        "patrol": {
            "emoji": "📊",
            "name": "巡检报告",
            "icon_custom_emoji_id": "",
            "desc": "定期巡检/健康报告/日报/周报",
            "keywords": [
                "巡检", "报告", "report", "日报", "周报", "月报",
                "健康", "health", "汇总", "summary", "统计", "stats",
                "dashboard", "看板",
            ],
        },
        "proxy": {
            "emoji": "🌐",
            "name": "代理状态",
            "icon_custom_emoji_id": "",
            "desc": "VPN/代理节点/网络连接/mihomo/xray",
            "keywords": [
                "代理", "proxy", "vpn", "节点", "node", "mihomo",
                "clash", "xray", "机场", "订阅", "subscription",
                "延迟", "latency", "带宽", "bandwidth", "tailscale",
                "frp", "隧道", "tunnel", "穿透",
            ],
        },
        "task": {
            "emoji": "📋",
            "name": "任务执行",
            "icon_custom_emoji_id": "",
            "desc": "OP/CC任务状态/构建/部署",
            "keywords": [
                "op", "cc", "任务", "task", "构建", "build", "部署",
                "deploy", "完成", "失败", "success", "failed",
                "编译", "compile", "test", "测试", "ci/cd",
            ],
        },
        "info": {
            "emoji": "ℹ️",
            "name": "一般通知",
            "icon_custom_emoji_id": "",
            "desc": "信息性消息/其他未分类",
            "keywords": [],  # 兜底分类
        },
    }

    @classmethod
    def classify(cls, text: str) -> str:
        """基于关键词匹配自动分类。返回 category key"""
        text_lower = text.lower()
        scores = {}
        
        for cat_key, cat_info in cls.CATEGORIES.items():
            score = 0
            for kw in cat_info["keywords"]:
                if kw in text_lower:
                    score += 1
                    # 标题/开头匹配加权
                    if text_lower.startswith(kw):
                        score += 2
            if score > 0:
                scores[cat_key] = score
        
        if not scores:
            return "info"
        
        # 返回最高分分类
        return max(scores, key=scores.get)

    @classmethod
    def get_emoji(cls, category: str) -> str:
        return cls.CATEGORIES.get(category, {}).get("emoji", "ℹ️")

    @classmethod
    def get_name(cls, category: str) -> str:
        return cls.CATEGORIES.get(category, {}).get("name", "一般通知")


# ── 路由核心 ──────────────────────────────────────────────────────────

class TGRouter:
    """Telegram 消息分类路由器 — 全局单例"""

    _instance: Optional["TGRouter"] = None

    def __new__(cls) -> "TGRouter":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._registry = self._load_registry()
        self._client: Optional[httpx.AsyncClient] = None

    def _load_registry(self) -> dict:
        """加载群组注册表"""
        if REGISTRY_FILE.exists():
            try:
                return json.loads(REGISTRY_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"forum_group_id": None, "topics": {}, "created_at": None}

    def _save_registry(self) -> None:
        """保存群组注册表"""
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_FILE.write_text(json.dumps(self._registry, indent=2, ensure_ascii=False))

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0, proxy=PROXY)
        return self._client

    async def _api(self, method: str, data: dict) -> dict:
        """调用 Telegram Bot API"""
        client = await self._get_client()
        resp = await client.post(f"{API}/{method}", json=data)
        resp.raise_for_status()
        return resp.json()

    # ── 群组发现与管理 ────────────────────────────────────────────────

    async def find_forum_group(self) -> Optional[int]:
        """扫描 bot 所在的对话，查找可作为通知中心的 Forum 超级群组"""
        try:
            client = await self._get_client()
            resp = await client.get(f"{API}/getUpdates", params={"limit": 100})
            data = resp.json()
            
            if not data.get("ok"):
                return None
            
            group_ids = set()
            for update in data.get("result", []):
                msg = update.get("message") or update.get("channel_post") or {}
                chat = msg.get("chat", {})
                
                # 只关注 supergroup
                if chat.get("type") == "supergroup":
                    gid = chat.get("id")
                    # 检查是否是 forum
                    try:
                        info_resp = await client.get(f"{API}/getChat", params={"chat_id": gid})
                        info = info_resp.json()
                        if info.get("ok") and info.get("result", {}).get("is_forum"):
                            group_ids.add(gid)
                    except Exception:
                        pass
            
            # 检查是否有新成员加入事件（用户刚把 bot 拉入群组）
            for update in data.get("result", []):
                msg = update.get("message") or update.get("my_chat_member") or {}
                chat = msg.get("chat", {})
                if chat.get("type") == "supergroup":
                    group_ids.add(chat.get("id"))
            
            return list(group_ids)[0] if group_ids else None
        except Exception as e:
            print(f"[TG-Router] 查找群组失败: {e}", file=sys.stderr)
            return None

    async def send_group_invite(self) -> bool:
        """通过私聊发送群组创建链接（引导用户一键创建 Forum）"""
        text = (
            "🏗 <b>通知中心初始化</b>\n\n"
            "请点击下方按钮创建一个通知群组，"
            "我会在里面自动建立话题分类：\n\n"
            "📋 <b>话题分类</b>：\n"
            "• 🖥 系统告警 — CPU/内存/磁盘\n"
            "• ⚙️ 服务状态 — Docker/API/端口\n"
            "• 🔒 安全事件 — SSH/防火墙/入侵\n"
            "• 💬 微信消息 — 联系人/CRM\n"
            "• 📊 巡检报告 — 日报/周报/统计\n"
            "• 🌐 代理状态 — VPN/节点/网络\n"
            "• 📋 任务执行 — OP/CC 状态\n"
            "• ℹ️ 一般通知 — 其他信息\n"
        )
        
        try:
            client = await self._get_client()
            # 发送创建群组的 deep link
            resp = await client.post(f"{API}/sendMessage", json={
                "chat_id": PRIVATE_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": {
                    "inline_keyboard": [[
                        {
                            "text": "➕ 创建通知群组",
                            "url": f"https://t.me/{(await self._get_bot_username())}?startgroup=1"
                        }
                    ]]
                }
            })
            return resp.status_code == 200
        except Exception as e:
            print(f"[TG-Router] 发送邀请失败: {e}", file=sys.stderr)
            return False

    async def _get_bot_username(self) -> str:
        """获取 bot 用户名"""
        try:
            client = await self._get_client()
            resp = await client.get(f"{API}/getMe")
            data = resp.json()
            return data.get("result", {}).get("username", "AGI_Brain_Bot")
        except Exception:
            return "AGI_Brain_Bot"

    async def setup_forum_group(self, group_id: int) -> bool:
        """在指定超级群组中启用 Forum 模式并创建所有话题"""
        try:
            client = await self._get_client()
            
            # 检查是否已是 forum
            info_resp = await client.get(f"{API}/getChat", params={"chat_id": group_id})
            info = info_resp.json()
            
            if not info.get("ok"):
                print(f"[TG-Router] 无法访问群组 {group_id}", file=sys.stderr)
                return False
            
            chat_info = info.get("result", {})
            if not chat_info.get("is_forum"):
                print(f"[TG-Router] 群组不是 Forum 模式，请手动开启", file=sys.stderr)
                # 发送提示消息
                await client.post(f"{API}/sendMessage", json={
                    "chat_id": group_id,
                    "text": (
                        "⚙️ 请将此群组切换为 <b>话题模式（Forum）</b>：\n"
                        "群组设置 → 话题 → 开启\n\n"
                        "开启后我将自动创建所有分类话题。"
                    ),
                    "parse_mode": "HTML",
                })
                return False
            
            # 保存群组 ID
            self._registry["forum_group_id"] = group_id
            self._registry["created_at"] = datetime.now().isoformat()
            
            # 创建所有话题
            print(f"[TG-Router] 开始在群组 {group_id} 创建话题...")
            
            for cat_key, cat_info in Category.CATEGORIES.items():
                try:
                    topic_name = f"{cat_info['emoji']} {cat_info['name']}"
                    resp = await client.post(f"{API}/createForumTopic", json={
                        "chat_id": group_id,
                        "name": topic_name,
                        "icon_color": 0x6FB9F0,  # 蓝色
                    })
                    result = resp.json()
                    if result.get("ok"):
                        topic_id = result["result"]["message_thread_id"]
                        self._registry["topics"][cat_key] = topic_id
                        print(f"  ✅ {topic_name} → topic_id={topic_id}")
                    else:
                        print(f"  ❌ {topic_name}: {result.get('description', 'unknown error')}")
                except Exception as e:
                    print(f"  ❌ {cat_info['name']}: {e}")
            
            self._save_registry()
            
            # 发送初始化完成通知
            topic_list = "\n".join(
                f"• {Category.get_emoji(cat)} {Category.get_name(cat)}"
                for cat in Category.CATEGORIES
            )
            await client.post(f"{API}/sendMessage", json={
                "chat_id": group_id,
                "text": (
                    f"✅ <b>通知中心初始化完成</b>\n\n"
                    f"以下话题已自动创建：\n{topic_list}\n\n"
                    f"所有系统通知将自动分类到对应话题中。"
                ),
                "parse_mode": "HTML",
                "message_thread_id": self._registry["topics"].get("info", 0),
            })
            
            return True
        except Exception as e:
            print(f"[TG-Router] 初始化失败: {e}", file=sys.stderr)
            return False

    # ── 消息路由 ────────────────────────────────────────────────────────

    async def route_message(
        self, text: str, category: Optional[str] = None,
        priority: str = "normal", analyze: bool = False
    ) -> bool:
        """
        发送消息到正确的分类话题。
        
        Args:
            text: 消息内容
            category: 分类（None=自动分类）
            priority: 优先级 "low"/"normal"/"high"/"critical"
            analyze: 是否启用 AI 分析 + 内联按钮（L3）
        
        Returns: 是否发送成功
        """
        # 自动分类
        if category is None:
            category = Category.classify(text)
        
        # 确保分类有效
        if category not in Category.CATEGORIES:
            category = "info"
        
        group_id = self._registry.get("forum_group_id")
        topic_id = self._registry.get("topics", {}).get(category)
        
        emoji = Category.get_emoji(category)
        cat_name = Category.get_name(category)
        tag = f"[{emoji} {cat_name}]"
        
        if priority == "critical":
            tag = f"🔴 {tag}"
        
        try:
            client = await self._get_client()
            
            # L3: AI 分析 + 内联按钮
            reply_markup = None
            formatted_text = f"{tag}\n{text[:4000]}"
            
            if analyze:
                try:
                    from tg_pilot import analyze_notification, format_notification_with_analysis
                    analysis = await analyze_notification(text)
                    formatted_text, keyboard = format_notification_with_analysis(text, analysis)
                    if keyboard:
                        reply_markup = keyboard
                except ImportError:
                    pass  # 降级：不发按钮
            
            if group_id and topic_id:
                payload = {
                    "chat_id": group_id,
                    "text": formatted_text,
                    "message_thread_id": topic_id,
                    "parse_mode": "HTML",
                }
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                resp = await client.post(f"{API}/sendMessage", json=payload)
            else:
                payload = {
                    "chat_id": PRIVATE_CHAT_ID,
                    "text": formatted_text,
                    "parse_mode": "HTML",
                }
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                resp = await client.post(f"{API}/sendMessage", json=payload)
            
            return resp.status_code == 200
        except Exception as e:
            print(f"[TG-Router] 发送失败 ({category}): {e}", file=sys.stderr)
            return False

    async def route_raw(self, chat_id: int, text: str, topic_id: int = 0) -> bool:
        """直接发送到指定 chat + topic（无分类标签）"""
        try:
            client = await self._get_client()
            payload = {"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"}
            if topic_id:
                payload["message_thread_id"] = topic_id
            resp = await client.post(f"{API}/sendMessage", json=payload)
            return resp.status_code == 200
        except Exception as e:
            print(f"[TG-Router] raw发送失败: {e}", file=sys.stderr)
            return False

    # ── 状态查询 ────────────────────────────────────────────────────────

    async def status(self) -> str:
        """返回群组和话题状态"""
        lines = ["📋 <b>TG Router 状态</b>\n"]
        
        group_id = self._registry.get("forum_group_id")
        if group_id:
            lines.append(f"🏠 Forum 群组: <code>{group_id}</code>")
            lines.append(f"📅 创建时间: {self._registry.get('created_at', '?')}")
            lines.append("")
            lines.append("<b>话题映射:</b>")
            for cat_key in Category.CATEGORIES:
                topic_id = self._registry.get("topics", {}).get(cat_key)
                emoji = Category.get_emoji(cat_key)
                name = Category.get_name(cat_key)
                status_icon = "✅" if topic_id else "❌"
                lines.append(f"  {status_icon} {emoji} {name}: topic_id={topic_id}")
        else:
            lines.append("⚠️ 尚未配置 Forum 群组")
            lines.append(f"当前回退到私聊: <code>{PRIVATE_CHAT_ID}</code>")
            lines.append("")
            lines.append("运行 <code>python3 tg_group_router.py --setup</code> 初始化")
        
        return "\n".join(lines)

    async def cleanup(self) -> None:
        """清理 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


# ── 全局快捷函数 ──────────────────────────────────────────────────────

_router: Optional[TGRouter] = None

def get_router() -> TGRouter:
    global _router
    if _router is None:
        _router = TGRouter()
    return _router


async def route_message(text: str, category: Optional[str] = None,
                       priority: str = "normal", analyze: bool = False) -> bool:
    """快捷函数：分类路由一条消息"""
    return await get_router().route_message(text, category, priority, analyze)


async def classify_and_send(text: str) -> dict:
    """分类并发送，返回 {category, sent}"""
    cat = Category.classify(text)
    sent = await get_router().route_message(text, cat)
    return {"category": cat, "category_name": Category.get_name(cat), "sent": sent}


# ── CLI ────────────────────────────────────────────────────────────────

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Telegram 消息分类路由器")
    parser.add_argument("--setup", action="store_true", help="初始化 Forum 群组和话题")
    parser.add_argument("--send", type=str, help="发送消息（自动分类）")
    parser.add_argument("--cat", type=str, help="指定分类（配合 --send 使用）")
    parser.add_argument("--classify", type=str, help="仅分类一段文字")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--find", action="store_true", help="查找现有 Forum 群组")
    parser.add_argument("--invite", action="store_true", help="发送群组创建邀请")
    parser.add_argument("--priority", type=str, default="normal", 
                        choices=["low", "normal", "high", "critical"])
    args = parser.parse_args()

    router = get_router()

    try:
        if args.setup:
            # 先查找现有群组
            group_id = await router.find_forum_group()
            if group_id:
                print(f"找到现有群组: {group_id}，开始初始化...")
                ok = await router.setup_forum_group(group_id)
            else:
                print("未找到现有 Forum 群组，发送创建邀请...")
                ok = await router.send_group_invite()
                if ok:
                    print("邀请已发送。请在 Telegram 中点击按钮创建群组，然后重新运行 --setup")
                else:
                    print("邀请发送失败，请检查网络/代理")
            
            sys.exit(0 if ok else 1)

        elif args.send:
            sent = await router.route_message(args.send, args.cat, args.priority)
            if sent:
                cat = args.cat or Category.classify(args.send)
                print(f"[OK] → {Category.get_emoji(cat)} {Category.get_name(cat)}")
            else:
                print("[FAIL] 发送失败")
            sys.exit(0 if sent else 1)

        elif args.classify:
            cat = Category.classify(args.classify)
            print(f"{Category.get_emoji(cat)} {Category.get_name(cat)}: {args.classify[:50]}")
        
        elif args.status:
            print(await router.status())
        
        elif args.find:
            gid = await router.find_forum_group()
            if gid:
                print(f"找到 Forum 群组: {gid}")
            else:
                print("未找到 Forum 群组")
        
        elif args.invite:
            ok = await router.send_group_invite()
            print("邀请已发送" if ok else "发送失败")

        else:
            parser.print_help()

    finally:
        await router.cleanup()


if __name__ == "__main__":
    asyncio.run(main())