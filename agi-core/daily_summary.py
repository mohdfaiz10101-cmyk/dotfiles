#!/usr/bin/env python3
"""每日消息摘要 — 汇总微信+Telegram，推送到 Telegram 私聊"""
import json, os, sys, sqlite3, time, subprocess, logging
from pathlib import Path
from datetime import datetime, date
import urllib.request, urllib.error

# ── 配置 ────────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("TG_BOT_TOKEN", "8797063873:AAGvApEP9frmA74b6nmxODHshzo1TwJR5ks")
CHAT_ID    = os.getenv("TG_CHAT_ID",   "5036541266")
PROXY      = os.getenv("https_proxy", os.getenv("HTTPS_PROXY", "http://127.0.0.1:7890"))
LITELLM    = "http://localhost:4000/v1"
LITELLM_KEY= "sk-litellm-charlie-2026"
MODEL      = "glm-5-turbo"

TG_INBOX   = Path.home() / "agi/data/tg-inbox.jsonl"
CRM_DB     = Path("/mnt/ai/apps/wechat-agent/data/crm.db")

# 复用 wechat_agent 的解密函数
sys.path.insert(0, str(Path.home() / "agi"))
try:
    from wechat_agent import find_uos_message_dbs, decrypt_uos_db
    _WECHAT_AGENT_OK = True
except Exception as _e:
    log.warning(f"无法导入 wechat_agent: {_e}")
    _WECHAT_AGENT_OK = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("daily-summary")
TODAY = date.today().strftime("%Y-%m-%d")

# ── Telegram 推送 ────────────────────────────────────────────────────
def tg_send(text: str):
    subprocess.run(
        [str(Path.home() / ".local/bin/tg-push"), text],
        capture_output=True
    )

# ── Telegram 消息读取 ────────────────────────────────────────────────
def load_tg_today() -> list[dict]:
    if not TG_INBOX.exists():
        return []
    msgs = []
    for line in TG_INBOX.read_text().splitlines():
        try:
            r = json.loads(line)
            if r.get("date") == TODAY:
                msgs.append(r)
        except:
            pass
    return msgs

# ── 联系人/群名缓存（从 contact.db 构建）────────────────────────────
_contact_cache: dict[str, str] = {}

def build_contact_cache() -> dict[str, str]:
    """返回 wxid → 显示名 映射（含群聊群名）"""
    global _contact_cache
    if _contact_cache:
        return _contact_cache
    if not _WECHAT_AGENT_OK:
        return {}
    try:
        from wechat_agent import decrypt_uos_db, UOS_KEYS_CACHE, UOS_DB_BASE
        import json as _json
        keys = _json.loads(UOS_KEYS_CACHE.read_text())
        key_info = keys.get("contact/contact.db", {})
        key_hex = key_info.get("enc_key", "") if isinstance(key_info, dict) else key_info
        if not key_hex:
            return {}
        for wxid_dir in UOS_DB_BASE.iterdir():
            db = wxid_dir / "db_storage/contact/contact.db"
            if not db.exists():
                continue
            tmp = decrypt_uos_db(db, key_hex)
            if not tmp:
                continue
            try:
                conn = sqlite3.connect(str(tmp))
                for row in conn.execute("SELECT username, remark, nick_name FROM contact").fetchall():
                    wxid, remark, nick = row
                    if wxid:
                        _contact_cache[wxid] = (remark or nick or wxid).strip() or wxid
                conn.close()
            finally:
                tmp.unlink(missing_ok=True)
            log.info(f"联系人缓存: {len(_contact_cache)} 条")
            break
    except Exception as e:
        log.warning(f"build_contact_cache: {e}")
    return _contact_cache

# ── 微信消息读取（直接从源头解密，不依赖缓存）────────────────────────
def _query_uos_db_by_time(db_path: Path, since_ts: int, name2id: dict) -> list[dict]:
    """从解密后的 UOS DB 按时间范围查消息"""
    messages = []
    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        conn.row_factory = sqlite3.Row

        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        # Name2Id: rowid → wxid 显示名映射
        local_name2id: dict[int, str] = dict(name2id)
        if "Name2Id" in tables:
            for r in conn.execute("SELECT rowid, user_name FROM Name2Id").fetchall():
                local_name2id[r[0]] = r[1]

        msg_tables = sorted(t for t in tables if t.startswith("Msg_"))
        for tbl in msg_tables:
            try:
                cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
                if "create_time" not in cols or "message_content" not in cols:
                    continue
                sender_col = "real_sender_id" if "real_sender_id" in cols else "NULL"
                rows = conn.execute(
                    f"SELECT create_time, message_content, {sender_col} "
                    f"FROM {tbl} WHERE create_time >= ? AND message_content IS NOT NULL "
                    f"ORDER BY create_time LIMIT 1000",
                    (since_ts,)
                ).fetchall()
                for r in rows:
                    text = (r[1] or "").strip()
                    if not text or len(text) < 2:
                        continue
                    sender_raw = r[2]
                    # numeric ID → wxid → 显示名
                    wxid_str = local_name2id.get(sender_raw, str(sender_raw)) if sender_raw else ""
                    sender = _contact_cache.get(wxid_str, wxid_str) or "对方"
                    # 群名：conv_wxid 结尾是 @chatroom → 查 contact 缓存
                    conv_wxid = next(
                        (v for k, v in local_name2id.items()
                         if isinstance(k, str) and k == tbl.replace("Msg_", "")),
                        ""
                    )
                    group_name = _contact_cache.get(conv_wxid, "") if conv_wxid.endswith("@chatroom") else ""
                    messages.append({
                        "ts":       datetime.fromtimestamp(r[0]).strftime("%m-%d %H:%M"),
                        "sender":   sender,
                        "group":    group_name,
                        "text":     text[:300],
                    })
            except Exception as e:
                log.debug(f"{tbl}: {e}")
        conn.close()
    except Exception as e:
        log.warning(f"query {db_path.name}: {e}")
    return messages


def load_wechat_recent(hours: int = 48) -> list[dict]:
    """从源头 UOS DB 解密读取最近 N 小时消息，不依赖任何缓存"""
    if not _WECHAT_AGENT_OK:
        log.warning("wechat_agent 未加载，跳过微信消息读取")
        return []

    since_ts = int(time.time()) - hours * 3600
    build_contact_cache()   # 预加载联系人/群名
    pairs = find_uos_message_dbs()
    if not pairs:
        log.warning("未找到 UOS message DB 或 keys.json")
        return []

    all_msgs = []
    for enc_path, key_hex in pairs:
        log.info(f"解密 {enc_path.name}...")
        tmp = decrypt_uos_db(enc_path, key_hex)
        if tmp is None:
            log.warning(f"解密失败: {enc_path.name}")
            continue
        try:
            msgs = _query_uos_db_by_time(tmp, since_ts, {})
            log.info(f"  → {len(msgs)} 条消息（最近{hours}h）")
            all_msgs.extend(msgs)
        finally:
            tmp.unlink(missing_ok=True)

    # 按时间排序
    all_msgs.sort(key=lambda m: m["ts"])
    return all_msgs

def load_wechat_crm_today() -> str:
    """CRM 今日活跃联系人摘要（备用，无需解密）"""
    if not CRM_DB.exists():
        return ""
    try:
        conn = sqlite3.connect(str(CRM_DB))
        rows = conn.execute(
            "SELECT COALESCE(remark,nickname,wxid), intent_history, last_contact FROM contacts "
            "WHERE last_contact LIKE ? ORDER BY last_contact DESC LIMIT 20",
            (f"{TODAY}%",)
        ).fetchall()
        conn.close()
        if not rows:
            return ""
        lines = [f"- {r[0]}: {(r[1] or '')[:60]}" for r in rows]
        return "今日活跃微信联系人：\n" + "\n".join(lines)
    except Exception as e:
        log.warning(f"CRM read: {e}")
        return ""

# ── GLM 摘要 ─────────────────────────────────────────────────────────
FALLBACK_MODELS = ["glm-5-turbo", "deepseek-v3.2", "glm-4-plus", "cerebras-llama-8b"]

def call_llm(prompt: str, max_tokens: int = 1200) -> str:
    for model in FALLBACK_MODELS:
        for attempt in range(2):
            try:
                req_data = json.dumps({
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                }).encode()
                req = urllib.request.Request(
                    f"{LITELLM}/chat/completions",
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {LITELLM_KEY}",
                    }
                )
                resp = urllib.request.urlopen(req, timeout=90)
                result = json.loads(resp.read())
                content = result["choices"][0]["message"]["content"].strip()
                log.info(f"LLM 成功: {model}")
                return content
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 20 * (attempt + 1)
                    log.warning(f"{model} 限速，等待 {wait}s...")
                    time.sleep(wait)
                else:
                    log.warning(f"{model} HTTP {e.code}，尝试下一个模型")
                    break
            except Exception as e:
                log.warning(f"{model} 失败: {e}，尝试下一个模型")
                break
    raise RuntimeError("所有模型均失败")


def summarize(wechat_msgs: list, tg_msgs: list, crm_summary: str) -> str:
    wechat_part = ""
    if wechat_msgs:
        sample = wechat_msgs[:150]
        wechat_part = f"【微信消息（最近48小时，共 {len(wechat_msgs)} 条，取前 {len(sample)} 条）】\n"
        wechat_part += "\n".join(
            f"[{m['ts']}] {'【'+m['group']+'】' if m.get('group') else ''}{m['sender']}: {m['text']}"
            for m in sample
        )
    elif crm_summary:
        wechat_part = f"【微信 CRM 今日活跃联系人】\n{crm_summary}"

    tg_part = ""
    if tg_msgs:
        tg_part = f"\n\n【Telegram 原始消息 {len(tg_msgs)} 条】\n"
        tg_part += "\n".join(
            f"[{m['ts']}] {m['from']} @ {m['chat']}: {m['text']}" for m in tg_msgs[:80]
        )

    if not wechat_part and not tg_part:
        return f"📊 *{TODAY} 每日消息总结*\n\n今日暂无微信或 Telegram 新消息。"

    prompt = f"""你是一个高效的助理，帮用户梳理今天的微信和Telegram消息。

请按以下结构输出，**严格用中文**，不要省略细节：

---
📅 {TODAY} 消息日报

**一、时间线（按时间顺序，列出重要事件）**
格式：HH:MM — [人名] [做了什么/说了什么关键内容]
要求：每条20字内，挑重要的，最多15条

**二、人物互动梳理**
格式：
- [人名A]：今天做了…/说了…/问了… → [结果/状态]
- [人名A] ↔ [人名B]：双方讨论了…
要求：按人物归组，不重复，突出动作和结论

**三、待办 & 跟进事项**
- 需要回复/处理的消息
- 有明确要求的事项
- 未解决的问题
无则写"无"

**四、数据统计**
微信：X条消息，涉及X人
Telegram：X条消息，涉及X人/群

---
原始数据：
{wechat_part}
{tg_part}

注意：若某人出现多次，合并在一个条目里描述。时间线只取有实质内容的消息。"""

    try:
        summary = call_llm(prompt, max_tokens=1200)
    except Exception as e:
        log.warning(f"GLM failed: {e}")
        wc_count = len(wechat_msgs)
        tg_count = len(tg_msgs)
        # 降级：直接拼接原始消息摘要
        lines = [f"微信 {wc_count} 条 | Telegram {tg_count} 条（AI不可用）\n"]
        if wechat_msgs:
            lines.append("微信消息摘要：")
            for m in wechat_msgs[:10]:
                lines.append(f"  [{m['ts']}] {m['sender']}: {m['text'][:60]}")
        if tg_msgs:
            lines.append("Telegram消息：")
            for m in tg_msgs[:5]:
                lines.append(f"  [{m['ts']}] {m['from']}: {m['text'][:60]}")
        summary = "\n".join(lines)

    return f"📊 *{TODAY} 每日消息总结*\n\n{summary}"

# ── 主流程 ────────────────────────────────────────────────────────────
def main():
    log.info(f"开始生成 {TODAY} 每日摘要（读取最近48小时微信消息）")

    wechat_msgs = load_wechat_recent(hours=48)
    log.info(f"微信消息: {len(wechat_msgs)} 条（最近48h）")

    crm_summary = ""
    if not wechat_msgs:
        crm_summary = load_wechat_crm_today()
        log.info(f"CRM备用: {'有' if crm_summary else '无'}数据")

    tg_msgs = load_tg_today()
    log.info(f"Telegram消息: {len(tg_msgs)} 条")

    text = summarize(wechat_msgs, tg_msgs, crm_summary)
    log.info("摘要生成完成，推送中...")
    tg_send(text)
    log.info("推送完成")

if __name__ == "__main__":
    main()
