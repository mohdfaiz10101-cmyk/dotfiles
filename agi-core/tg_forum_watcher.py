#!/usr/bin/env python3
"""
tg_forum_watcher.py — 自动检测 bot 被加入新群组并初始化 Forum 话题

运行方式:
  - systemd timer: 每 30 秒检查一次
  - 手动: python3 tg_forum_watcher.py

工作原理:
  1. 轮询 getUpdates
  2. 检测 my_chat_member 事件（bot 被拉入群组）
  3. 发现新 supergroup 时自动调用 setup_forum_group
  4. 初始化完成后退出（由 systemd timer 重启）
"""

import asyncio, json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tg_group_router import get_router, Category, BOT_TOKEN, PROXY, API, REGISTRY_FILE

CHECK_INTERVAL = 30  # 秒

async def check_updates(router) -> int | None:
    """检查最近的更新，返回新发现的 group_id 或 None"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=15.0, proxy=PROXY) as client:
            resp = await client.get(f"{API}/getUpdates", params={
                "limit": 50, "timeout": 5,
                "allowed_updates": ["message", "my_chat_member"],
            })
            data = resp.json()
            
            if not data.get("ok"):
                return None
            
            seen_groups = set()
            for update in data.get("result", []):
                # 检查 my_chat_member 事件
                member_update = update.get("my_chat_member", {})
                if member_update:
                    chat = member_update.get("chat", {})
                    if chat.get("type") == "supergroup":
                        new_status = member_update.get("new_chat_member", {}).get("status", "")
                        if new_status == "administrator" or new_status == "member":
                            gid = chat.get("id")
                            seen_groups.add(gid)
                            print(f"[Watcher] 发现 bot 被加入群组: {chat.get('title', gid)} (id={gid})")
                
                # 也检查普通消息中的群组
                msg = update.get("message", {})
                chat = msg.get("chat", {})
                if chat.get("type") == "supergroup":
                    gid = chat.get("id")
                    # 检查是否是已初始化的
                    registry = json.loads(REGISTRY_FILE.read_text()) if REGISTRY_FILE.exists() else {}
                    if not registry.get("forum_group_id") or registry.get("forum_group_id") != gid:
                        seen_groups.add(gid)
            
            # 返回第一个未初始化的群组
            registry = json.loads(REGISTRY_FILE.read_text()) if REGISTRY_FILE.exists() else {}
            for gid in seen_groups:
                if gid != registry.get("forum_group_id"):
                    return gid
            
            return None
    except Exception as e:
        print(f"[Watcher] 检查失败: {e}", file=sys.stderr)
        return None


async def main():
    print("[Watcher] TG Forum 自动发现已启动")
    
    # 检查是否已经初始化
    if REGISTRY_FILE.exists():
        registry = json.loads(REGISTRY_FILE.read_text())
        if registry.get("forum_group_id"):
            print(f"[Watcher] 已初始化: group_id={registry['forum_group_id']}")
            print(f"[Watcher] 话题数: {len(registry.get('topics', {}))}")
            return  # 已完成，不重复初始化
    
    router = get_router()
    
    try:
        while True:
            gid = await check_updates(router)
            
            if gid:
                print(f"[Watcher] 开始初始化群组 {gid}...")
                ok = await router.setup_forum_group(gid)
                if ok:
                    print(f"[Watcher] ✅ 群组 {gid} 初始化完成！")
                    # 通知用户
                    await router.route_message(
                        "🎉 Telegram 通知中心已就绪！\n所有系统通知将自动分类到对应话题。",
                        category="info"
                    )
                    break
                else:
                    print(f"[Watcher] ❌ 初始化失败，将在下次检查时重试")
            
            await asyncio.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        pass
    finally:
        await router.cleanup()


if __name__ == "__main__":
    asyncio.run(main())