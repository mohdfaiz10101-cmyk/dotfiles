#!/usr/bin/env python3
"""
wechat_agent.py — 双微信实例自动AI回复守护进程

Why: 监控 UOS WeChat + Wine WeChat 两个实例，自动识别未读消息并通过 LLM 回复
What: 解密消息DB → 分类 → LLM处理 → 队列回复 → xdotool 自动发送
Test: 设置 DRY_RUN=1 跑一轮 poll_cycle，检查 /tmp/wechat-reply-queue.jsonl 有输出即可
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac as hmac_mod
import json
import logging
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any

import httpx

# ─── 配置 ───────────────────────────────────────────────────────────────────

LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-charlie-2026")
WHISPER_URL = "http://localhost:8178/asr"

MODEL_PRIMARY = "glm-4.7"
MODEL_FALLBACK = "cerebras-llama-8b"
_glm_failed_until: float = 0.0  # epoch时间戳，0=正常
MODEL_VISION = "doubao-1-5-vision-pro-32k"

# UOS WeChat
UOS_DB_BASE = Path.home() / "文档/xwechat_files"
UOS_KEYS_CACHE = Path.home() / ".cache/wechat-finance/keys.json"
UOS_DECRYPTED = Path.home() / ".cache/wechat-finance/decrypted"

# Wine WeChat（两个账号）
WINE_ACCOUNTS = [
    Path("/mnt/data/WeChat Files/w422417869/Msg/ChatMsg.db"),
    Path("/mnt/data/WeChat Files/wxid_gcyys3q9z3tk12/Msg/ChatMsg.db"),
]

# 状态 / 队列文件
STATE_FILE = Path("/tmp/wechat-agent-state.json")
QUEUE_FILE = Path("/tmp/wechat-reply-queue.jsonl")
COUNTER_FILE = Path("/tmp/wechat-send-counter.json")
STATUS_FILE = Path("/tmp/wechat-agent-status.json")
AGI_STATUS = Path("/tmp/agi-brain-status.json")

# CRM
CRM_DB = Path("/mnt/ai/apps/wechat-agent/data/crm.db")

# 安全限制
DAILY_LIMIT = 200
COOLDOWN_SEC = 5
SILENT_HOUR_START = 2
SILENT_HOUR_END = 8
POLL_INTERVAL = 30

DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
# COMMAND_ONLY=1: 只响应 # 开头的命令，不做 AI 闲聊回复
COMMAND_ONLY = os.environ.get("COMMAND_ONLY", "0") == "1"

# 系统提示（内嵌所有角色规则，不依赖外部 skill）
SYSTEM_PROMPT = """你是用户的微信AI助理。

规则：
- 私聊客户：识别意图（询价/技术支持/售后/物流/投诉/闲聊），给出专业简短回复（≤200字）
- 群聊@提及：简洁回应，不主动展开话题
- 禁止：不承诺具体价格/折扣，不发链接（除非对方要求）
- 语气：专业、礼貌、中文
- 回复直接输出正文，不加"您好，"等无意义开头
- 每条回复结尾必须加一行：「[AI自动回复] 主人已收到您的消息，稍后会亲自回复您」"""

# ─── X11 环境自动探测（systemd service 缺少 XAUTHORITY）────────────────────────
def _setup_x11_env() -> None:
    """自动探测 XAUTHORITY 并设置到进程环境，确保 xdotool 能访问 XWayland。"""
    if os.environ.get("XAUTHORITY"):
        return
    import glob
    # KDE/Plasma 登录后 xauth 文件在 /run/user/{uid}/xauth_*
    uid = os.getuid()
    patterns = [
        f"/run/user/{uid}/xauth_*",
        f"/run/user/{uid}/.mutter-Xwaylandauth.*",
        os.path.expanduser("~/.Xauthority"),
    ]
    for pat in patterns:
        matches = glob.glob(pat)
        if matches:
            os.environ["XAUTHORITY"] = matches[0]
            return

_setup_x11_env()

# ─── 日志 ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("wechat-agent")

# ─── 状态管理 ────────────────────────────────────────────────────────────────


def load_state() -> dict[str, Any]:
    """加载轮询状态（last_id、每日计数等）。"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_ids": {}, "daily_count": 0, "daily_date": ""}


def save_state(state: dict[str, Any]) -> None:
    """持久化状态到临时文件。"""
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ─── 发送计数器 ──────────────────────────────────────────────────────────────


class SendCounter:
    """每日发送计数，重置日期切换。
    Test: 实例化 → send() × 201 → 第201次 allow() 返回 False
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {"date": "", "count": 0}
        self._cooldown: dict[str, float] = {}  # wxid → last_send_ts
        self._load()

    def _load(self) -> None:
        if COUNTER_FILE.exists():
            try:
                self._data = json.loads(COUNTER_FILE.read_text())
            except Exception:
                pass
        today = date.today().isoformat()
        if self._data.get("date") != today:
            self._data = {"date": today, "count": 0}

    def _save(self) -> None:
        COUNTER_FILE.write_text(json.dumps(self._data))

    def allow(self, wxid: str) -> tuple[bool, str]:
        """检查是否允许发送（冷却+日限+静默时段）。返回 (ok, reason)。"""
        h = datetime.now().hour
        if SILENT_HOUR_START <= h < SILENT_HOUR_END:
            return False, f"静默时段 {h:02d}:xx"
        last = self._cooldown.get(wxid, 0)
        if time.time() - last < COOLDOWN_SEC:
            return False, "冷却中"
        today = date.today().isoformat()
        if self._data.get("date") != today:
            self._data = {"date": today, "count": 0}
        if self._data["count"] >= DAILY_LIMIT:
            return False, "已达日限"
        return True, ""

    def record(self, wxid: str) -> None:
        """记录一次成功发送。"""
        self._cooldown[wxid] = time.time()
        self._data["count"] = self._data.get("count", 0) + 1
        self._save()


counter = SendCounter()

# ─── 消息读取 ────────────────────────────────────────────────────────────────

# UOS WeChat 解密常量（与 wechat-finance 保持一致）
PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80


def get_active_model() -> str:
    """动态选择模型：GLM优先，429/quota时自动切到备用，恢复后自动切回。"""
    global _glm_failed_until
    if time.time() < _glm_failed_until:
        return MODEL_FALLBACK
    return MODEL_PRIMARY


def mark_glm_failed() -> None:
    """标记GLM不可用，30分钟后重试。"""
    global _glm_failed_until
    _glm_failed_until = time.time() + 1800
    log.warning("[MODEL_FAILOVER] GLM额度耗尽，切换到 %s，30分钟后重试", MODEL_FALLBACK)


def mark_glm_ok() -> None:
    """GLM恢复，重置故障状态。"""
    global _glm_failed_until
    if _glm_failed_until > 0:
        _glm_failed_until = 0.0
        log.info("[MODEL_FAILOVER] GLM已恢复，切回 %s", MODEL_PRIMARY)


PAGE_SZ = 4096
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80  # IV(16) + HMAC(64)
SQLITE_HDR = b"SQLite format 3\x00"

def _derive_mac_key(enc_key_bytes: bytes, salt: bytes) -> bytes:
    mac_salt = bytes(b ^ 0x3A for b in salt)
    return hashlib.pbkdf2_hmac("sha512", enc_key_bytes, mac_salt, 2, dklen=KEY_SZ)

def _decrypt_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    """解密单页（pycryptodome AES-CBC）。"""
    from Crypto.Cipher import AES
    iv = page_data[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
    if pgno == 1:
        encrypted = page_data[SALT_SZ : PAGE_SZ - RESERVE_SZ]
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        return SQLITE_HDR + cipher.decrypt(encrypted) + b"\x00" * RESERVE_SZ
    else:
        encrypted = page_data[: PAGE_SZ - RESERVE_SZ]
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        return cipher.decrypt(encrypted) + b"\x00" * RESERVE_SZ

SQLCIPHER_BIN = "/run/current-system/sw/bin/sqlcipher"

# 剪贴板工具（优先 wl-copy Wayland，回退 xclip）
def _find_clipboard_tool() -> tuple[str, str] | None:
    """返回 (tool_path, tool_type) 其中 tool_type = 'wl-copy' | 'xclip'"""
    import shutil as _shutil
    # wl-copy 优先（XWayland 也能通过 Wayland↔X11 同步获取）
    for _p in ["/run/current-system/sw/bin/wl-copy", _shutil.which("wl-copy")]:
        if _p and Path(_p).exists():
            return (_p, "wl-copy")
    for _p in ["/run/current-system/sw/bin/xclip", _shutil.which("xclip"),
               "/home/charlie/.nix-profile/bin/xclip"]:
        if _p and Path(_p).exists():
            return (_p, "xclip")
    return None


def decrypt_uos_db(enc_path: Path, enc_key_hex: str) -> Path | None:
    """解密 UOS WeChat SQLite DB（自定义加密，非标准 sqlcipher）。
    使用 pycryptodome AES-CBC，与 wechat-finance 相同算法。
    """
    try:
        enc_key_bytes = bytes.fromhex(enc_key_hex)
        file_size = enc_path.stat().st_size
        total_pages = file_size // PAGE_SZ
        if total_pages == 0:
            return None

        with open(enc_path, "rb") as fin:
            page1 = fin.read(PAGE_SZ)

        # enc_key_bytes 是从内存提取的 AES 密钥，直接用于解密（不再 PBKDF2）
        # mac_key 用 PBKDF2(enc_key_bytes, mac_salt=salt^0x3A, 2轮) 验证 HMAC
        salt = page1[:SALT_SZ]
        mac_key = _derive_mac_key(enc_key_bytes, salt)

        # HMAC 验证第一页
        hmac_data = page1[SALT_SZ : PAGE_SZ - HMAC_SZ]
        stored_hmac = page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
        hm = hmac_mod.new(mac_key, hmac_data, hashlib.sha512)
        hm.update(struct.pack("<I", 1))
        if hm.digest() != stored_hmac:
            log.warning("decrypt_uos_db HMAC 验证失败: %s", enc_path.name)
            return None

        tmp = Path(tempfile.mktemp(suffix=".db"))
        with open(enc_path, "rb") as fin, open(tmp, "wb") as fout:
            fout.write(_decrypt_page(enc_key_bytes, fin.read(PAGE_SZ), 1))
            for pgno in range(2, total_pages + 1):
                page = fin.read(PAGE_SZ)
                if len(page) < PAGE_SZ:
                    break
                fout.write(_decrypt_page(enc_key_bytes, page, pgno))

        if tmp.stat().st_size > 4096:
            return tmp
        tmp.unlink(missing_ok=True)
        return None
    except Exception as e:
        log.warning("decrypt_uos_db 异常: %s", e)
        return None


def find_uos_message_dbs() -> list[tuple[Path, str]]:
    """找到 UOS 消息 DB 和对应解密密钥。
    Why: 用户可能有多个 wxid 子目录
    What: 遍历 xwechat_files，匹配 keys.json 中的条目
    Test: 有微信运行时，返回非空列表
    """
    if not UOS_KEYS_CACHE.exists():
        return []
    try:
        keys: dict[str, str] = json.loads(UOS_KEYS_CACHE.read_text())
    except Exception:
        return []

    result: list[tuple[Path, str]] = []
    for wxid_dir in UOS_DB_BASE.iterdir():
        if not wxid_dir.is_dir():
            continue
        msg_dir = wxid_dir / "db_storage" / "message"
        if not msg_dir.exists():
            continue
        for db_file in msg_dir.glob("message_*.db"):
            # keys.json key 是 "message/message_0.db" 格式的相对路径
            rel = f"message/{db_file.name}"
            if rel in keys:
                val = keys[rel]
                key_str = val["enc_key"] if isinstance(val, dict) else val
                result.append((db_file, key_str))
    return result


def read_uos_messages(last_id: int) -> list[dict[str, Any]]:
    """读取 UOS WeChat 新消息。
    Why: 需要从加密 DB 中提取自 last_id 以后的收到消息
    What: 解密 → SQLite query → 返回标准消息字典列表
    Test: last_id=0 时应返回所有消息（≥0条）
    """
    msgs: list[dict[str, Any]] = []
    pairs = find_uos_message_dbs()
    if not pairs:
        # 尝试直接读已解密缓存（若 wechat-finance 已提前解密）
        for cached in UOS_DECRYPTED.glob("*.db"):
            msgs.extend(_query_sqlite(cached, last_id, "uos"))
        return msgs

    for enc_path, key_hex in pairs:
        tmp_path = decrypt_uos_db(enc_path, key_hex)
        if tmp_path is None:
            continue
        try:
            msgs.extend(_query_sqlite(tmp_path, last_id, "uos"))
        finally:
            tmp_path.unlink(missing_ok=True)
    return msgs


def read_wine_messages(db_path: Path, last_id: int) -> list[dict[str, Any]]:
    """读取 Wine WeChat 明文（已解密）消息。
    Why: Wine WeChat DB 由 WMPF 层管理，通常已解密可读
    What: 直接 sqlite3 查询 ChatMsg 表
    Test: db_path 存在时，last_id=0 应返回所有收到消息
    """
    if not db_path.exists():
        return []
    return _query_sqlite(db_path, last_id, "wine")


def _query_sqlite(db_path: Path, last_id: int, source: str) -> list[dict[str, Any]]:
    """通用 SQLite 消息查询（只读模式）。
    支持两种 schema：
    - Wine/旧版: ChatMsg 表，列名 localId/talker/content/type/isSend
    - UOS新版: Msg_* 分表，列名 local_id/real_sender_id/message_content/local_type/create_time
    """
    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        conn.row_factory = sqlite3.Row

        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        # ── UOS 新版：Msg_* 分表（用 create_time 过滤，last_id 当作时间戳）────
        msg_tables = sorted(t for t in tables if t.startswith("Msg_"))
        if msg_tables:
            # 构建 Name2Id 映射：rowid → wxid（实际联系人 wxid）
            name2id: dict[int, str] = {}
            own_sender_id: int | None = None
            try:
                if "Name2Id" in tables:
                    n2id_rows = conn.execute(
                        "SELECT rowid, user_name FROM Name2Id"
                    ).fetchall()
                    for r in n2id_rows:
                        name2id[r[0]] = r[1]
                    # 自己的账号：从 UOS_DB_BASE 目录名推断 wxid
                    # UOS_DB_BASE = ~/文档/xwechat_files，子目录格式 wxid_xxx_suffix
                    own_sender_id = None
                    for wxid_dir in UOS_DB_BASE.iterdir():
                        if not wxid_dir.is_dir():
                            continue
                        # wxid_bjo2p0swoxm822_fe61 → wxid_bjo2p0swoxm822
                        parts = wxid_dir.name.rsplit("_", 1)
                        my_wxid = parts[0] if len(parts) == 2 else wxid_dir.name
                        own_sender_id = next(
                            (k for k, v in name2id.items() if v == my_wxid), None
                        )
                        if own_sender_id is not None:
                            break
            except Exception:
                pass

            # 构建 Msg表名 → 会话wxid 映射（Msg_<MD5(conv_wxid)>）
            import hashlib as _hashlib
            conv_map: dict[str, str] = {}
            for _conv_wxid in name2id.values():
                if _conv_wxid:
                    _h = _hashlib.md5(_conv_wxid.encode()).hexdigest()
                    conv_map[f"Msg_{_h}"] = _conv_wxid

            import time as _time
            import zstandard as _zstd

            if last_id == 0:
                last_id = int(_time.time()) - 300  # 首次启动：只看最近5分钟
            all_msgs: list[dict] = []
            for tbl in msg_tables:
                rows = conn.execute(
                    f"SELECT local_id, local_type, create_time, real_sender_id, message_content"
                    f" FROM {tbl}"
                    f" WHERE create_time > ?"
                    f"   AND local_type IN (1,3,34,43,49)"
                    f" ORDER BY create_time ASC LIMIT 10",
                    (last_id,),
                ).fetchall()
                for row in rows:
                    sender_local_id = row[3]

                    # 跳过自己发的消息（不回复自己）
                    if own_sender_id is not None and sender_local_id == own_sender_id:
                        continue
                    # 跳过系统账号（filehelper, weixin 等，通常 local_id <= 3 或 user_name 为空）
                    wxid = name2id.get(sender_local_id, "")
                    if not wxid or wxid in ("", "weixin", "newsapp", "filehelper"):
                        continue

                    raw_content = row[4]
                    content = ""
                    # 用会话 wxid 作为 talker：群聊→chatroom wxid，私聊→发送人 wxid
                    conv_wxid = conv_map.get(tbl, "")
                    talker = conv_wxid if conv_wxid.endswith("@chatroom") else wxid

                    if isinstance(raw_content, bytes):
                        # 尝试 zstd 解压（UOS WeChat 对文字消息也可能压缩）
                        try:
                            dctx = _zstd.ZstdDecompressor()
                            decoded = dctx.decompress(raw_content).decode("utf-8", errors="replace")
                            if ":\n" in decoded:
                                _, content = decoded.split(":\n", 1)
                            else:
                                content = decoded
                        except Exception:
                            content = "[媒体消息]"
                    elif isinstance(raw_content, str):
                        if ":\n" in raw_content:
                            _, content = raw_content.split(":\n", 1)
                        else:
                            content = raw_content

                    all_msgs.append({
                        "id": row[0],
                        "type": row[1],
                        "create_time": row[2],
                        "talker": talker,
                        "content": content.strip(),
                        "source": source,
                        "db_path": str(db_path),
                    })
            conn.close()
            return all_msgs

        # ── Wine / 旧版：ChatMsg 表 ──────────────────────────────
        cols = {row[1] for row in conn.execute("PRAGMA table_info(ChatMsg)").fetchall()}
        if not cols:
            conn.close()
            return []

        id_col = "localId" if "localId" in cols else "MsgLocalID"
        talker_col = "talker" if "talker" in cols else "StrTalker"
        content_col = "content" if "content" in cols else "StrContent"
        type_col = "type" if "type" in cols else "Type"
        time_col = "CreateTime"
        is_send_col = "isSend" if "isSend" in cols else "IsSender"

        rows = conn.execute(
            f"SELECT {id_col}, {type_col}, {time_col}, {talker_col}, {content_col}"
            f" FROM ChatMsg"
            f" WHERE {id_col} > ? AND {is_send_col}=0"
            f" ORDER BY {time_col} ASC LIMIT 50",
            (last_id,),
        ).fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "type": row[1],
                "create_time": row[2],
                "talker": row[3] or "",
                "content": row[4] or "",
                "source": source,
                "db_path": str(db_path),
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        log.debug("SQLite 查询失败 (%s): %s", db_path.name, e)
        return []


# ─── 消息分类 ────────────────────────────────────────────────────────────────

INTENT_KEYWORDS: dict[str, list[str]] = {
    "询价": ["多少钱", "价格", "报价", "费用", "怎么收费", "优惠", "FOB", "CIF", "EXW", "MOQ", "最低起订", "unit price", "quotation", "quote"],
    "外贸物流": ["FOB", "CIF", "EXW", "DDP", "报关", "装柜", "提单", "BL", "信用证", "LC", "T/T", "电汇", "形式发票", "PI", "装箱单", "packing list"],
    "技术支持": ["怎么用", "报错", "打不开", "不能用", "bug", "问题"],
    "售后": ["退款", "退货", "换货", "售后", "不满意"],
    "物流": ["发货", "快递", "到了吗", "物流", "运费", "到货"],
    "投诉": ["投诉", "骗人", "坑", "差评", "举报"],
}

# 复杂任务意图（需人工确认或外部操作）
COMPLEX_INTENT_KEYWORDS: dict[str, list[str]] = {
    "回邮件": ["邮件", "email", "发邮件", "回复邮件", "回信"],
    "改合同": ["合同", "签约", "协议", "条款", "修改合同"],
    "查订单": ["订单", "查单", "单号", "物流单", "快递单号"],
    "安排会议": ["会议", "预约", "见面", "拜访", "约时间", "日程"],
    "技术方案": ["方案", "报价单", "PPT", "报价方案", "技术方案"],
    "付款/发票": ["付款", "发票", "转账", "汇款", "收据", "开票"],
}


def classify_message(msg: dict[str, Any], my_nicknames: list[str]) -> dict[str, Any]:
    """本地规则分类消息（不调用 LLM）。
    Why: 节省 token，快速判断是否需要回复及回复策略
    What: 判断群聊/私聊、消息类型、是否@自己、意图关键词
    Test: 群聊消息不含我的昵称 → should_reply=False
    """
    wxid = msg["talker"]
    content = msg["content"]
    is_group = wxid.endswith("@chatroom")

    # 去除 @提及前缀（群聊 @Charles 等），避免 AI 在回复中重复 @
    import re as _re
    content = _re.sub(r'@\S+\s*', '', content).strip()
    msg = {**msg, "content": content}

    # 群聊：直接回复所有消息（用户配置为全量回复）
    # 去除 @提及格式已在上方处理

    # 消息类型
    msg_type = msg["type"]
    # 49=文件/App消息，43=视频，检测文件消息设为当前文档
    if msg_type == 49:
        # 文件消息：content 包含 XML，提取 <title> 或路径
        import re as _re
        file_path_match = _re.search(r'<title>(.*?)</title>', content)
        file_name = file_path_match.group(1) if file_path_match else content[:50]
        # 尝试在微信文件目录找到这个文件
        possible_paths = list(Path.home().glob(f"文档/xwechat_files/**/{file_name}"))
        if possible_paths:
            real_path = str(possible_paths[0])
            return {
                **msg,
                "should_reply": True,
                "intent": "文件设置",
                "_office_file": real_path,
            }
        return {
            **msg,
            "should_reply": True,
            "intent": "文件设置",
            "_office_file_name": file_name,
        }
    if msg_type not in (1, 3, 34):  # 1=文字 3=图片 34=语音
        return {
            **msg,
            "should_reply": False,
            "reason": f"不支持类型 {msg_type}",
            "intent": "ignore",
        }

    # 意图识别
    intent = "闲聊"
    for name, kws in INTENT_KEYWORDS.items():
        if any(kw in content for kw in kws):
            intent = name
            break

    needs_human = False
    complex_type = ""
    for name, kws in COMPLEX_INTENT_KEYWORDS.items():
        if any(kw in content for kw in kws):
            needs_human = True
            complex_type = name
            break

    return {
        **msg,
        "should_reply": True,
        "is_group": is_group,
        "intent": intent,
        "needs_human": needs_human,
        "complex_type": complex_type,
    }


# ─── 多模态处理 ──────────────────────────────────────────────────────────────


async def transcribe_voice(audio_path: str) -> str:
    """调用本地 Whisper 转录语音消息。
    Why: 语音消息需先转文字才能 LLM 处理
    What: POST 音频文件到 Whisper ASR 服务，返回中文文字
    Test: 发送一段普通话音频，返回非空字符串
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            with open(audio_path, "rb") as f:
                resp = await client.post(
                    WHISPER_URL,
                    files={"file": ("audio.amr", f, "audio/amr")},
                    data={"language": "zh"},
                )
            return resp.json().get("text", "")
    except Exception as e:
        log.warning("语音转写失败: %s", e)
        return ""


async def analyze_image(img_path: str) -> str:
    """调用豆包视觉模型分析图片内容。
    Why: 图片消息可能是询价截图或产品图，需理解图像才能回复
    What: base64 编码图片发给 doubao-vision，返回描述文字
    Test: 发送商品图片，返回包含"商品"或"询价"关键词的描述
    """
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(
                f"{LITELLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
                json={
                    "model": MODEL_VISION,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "描述这张图片的内容。如果是商品询价相关请特别指出。100字以内。",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_b64}"
                                    },
                                },
                            ],
                        }
                    ],
                    "max_tokens": 200,
                },
            )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning("图片分析失败: %s", e)
        return ""


# ─── Letta 记忆检索 ─────────────────────────────────────────────────────────

LETTA_BASE = "http://localhost:8283"
LETTA_CHAT_AGENT = "agent-8651643c-e753-47ed-9759-bd955c6ac240"
MEMORY_DIR = Path.home() / ".claude/projects/-home-charlie/memory"


async def _search_letta(query: str, wxid: str = "") -> str:
    search_query = f"{query[:30]} {wxid}".strip()
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(
                f"{LETTA_BASE}/v1/agents/{LETTA_CHAT_AGENT}/messages",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": f"搜索记忆：{search_query}。用一句话总结最相关的信息。",
                        }
                    ],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for msg in reversed(data):
                    if msg.get("message_type") == "assistant_message":
                        return (msg.get("content", "") or "")[:300]
    except Exception:
        pass
    return _grep_memory_fallback(search_query)


def _grep_memory_fallback(query: str) -> str:
    matches: list[str] = []
    try:
        keywords = [w for w in query.split() if len(w) >= 2][:3]
        if not keywords:
            return ""
        for md in MEMORY_DIR.glob("*.md"):
            try:
                lines = md.read_text(errors="ignore").splitlines()
            except Exception:
                continue
            for line in lines:
                if any(k in line for k in keywords):
                    matches.append(line.strip()[:120])
                    if len(matches) >= 3:
                        return " | ".join(matches)
    except Exception:
        pass
    return " | ".join(matches) if matches else ""


# ─── LLM 回复生成 ────────────────────────────────────────────────────────────


async def generate_reply(msg: dict[str, Any]) -> str:
    """根据分类结果生成 AI 回复。
    Why: 核心业务逻辑，将消息转为合适的回复
    What: 组装 prompt → 调用 GLM-4.7 → 返回回复文字
    Test: 传入意图=询价的消息，返回非空字符串且不含价格承诺
    """
    content = msg["content"]
    intent = msg.get("intent", "闲聊")
    is_group = msg.get("is_group", False)

    # ── 拖入文件 → 设为当前文档 ──────────────────────────
    if msg.get("_office_file"):
        fp = msg["_office_file"]
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post("http://localhost:9810/set-file", json={"filepath": fp})
            return f"📄 已设置当前文档：{fp}\n发送 #文档 <操作> 来编辑"
        except Exception:
            return f"已记录文件：{fp}（office-agent 未启动）"

    if msg.get("_office_file_name"):
        return f"📄 收到文件：{msg['_office_file_name']}\n请把文件放在 ~/Desktop/ 后发送：\n#文档 打开 ~/Desktop/{msg['_office_file_name']}"

    # ── 统一智能路由 ────────────────────────────────────────
    HUB = "http://localhost:9800"

    # 1. 文档控制：#文档 / #doc → office-agent
    if content.startswith("#文档") or content.startswith("#doc"):
        cmd_text = content[3:].strip() if content.startswith("#文档") else content[4:].strip()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "http://localhost:9810/command",
                    json={"text": cmd_text, "source": "wechat",
                          "talker": msg.get("talker", "")},
                )
            result = resp.json()
            return f"📄 {result.get('message', '操作完成')}"
        except Exception as e:
            return f"文档操作失败: {e}"

    # 2. CRM / 联系人查询：#crm | 查客户 | 查联系人 | 联系方式
    CRM_TRIGGERS = ("#crm", "#客户", "查客户", "查联系人", "联系方式", "查一下", "客户信息")
    if any(content.startswith(t) or t in content for t in CRM_TRIGGERS):
        # 提取搜索关键词
        import re
        kw = re.sub(r"^#crm|^#客户|查客户|查联系人|联系方式|查一下", "", content).strip()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{HUB}/api/crm/customers",
                                        params={"search": kw, "limit": 5})
                data = resp.json()
            items = data.get("customers", data.get("data", []))
            if not items:
                return f"📇 未找到「{kw}」相关客户"
            lines = []
            for c in items[:5]:
                name = c.get("name") or c.get("nickname", "")
                phone = c.get("phone", "")
                wechat = c.get("wechat_id", "")
                note = c.get("note", "")
                lines.append(f"• {name} {phone} {wechat} {note}".strip())
            return "📇 CRM结果：\n" + "\n".join(lines)
        except Exception as e:
            return f"CRM查询失败: {e}"

    # 3. 消息历史：#消息 | 最近消息 | 有什么消息
    MSG_TRIGGERS = ("#消息", "最近消息", "有什么消息", "看看消息", "未读")
    if any(content.startswith(t) or t in content for t in MSG_TRIGGERS):
        kw = re.sub(r"^#消息|最近消息|有什么消息|看看消息|未读", "", content).strip()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{HUB}/api/wechat/messages",
                                        params={"limit": 10, "talker": kw})
                data = resp.json()
            msgs = data.get("messages", data.get("data", []))
            if not msgs:
                return "📬 暂无最近消息"
            lines = [f"• [{m.get('time','')[:16]}] {m.get('name','?')}: {m.get('content','')[:40]}"
                     for m in msgs[:8]]
            return "📬 最近消息：\n" + "\n".join(lines)
        except Exception as e:
            return f"消息查询失败: {e}"

    # 4. 群聊摘要：#总结 | 摘要 | 今天聊了什么
    SUM_TRIGGERS = ("#总结", "#摘要", "总结一下", "摘要", "今天聊了", "聊了什么")
    if any(content.startswith(t) or t in content for t in SUM_TRIGGERS):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{HUB}/api/wechat/digests", params={"limit": 5})
                data = resp.json()
            digests = data.get("digests", data.get("data", []))
            if not digests:
                return "📝 暂无摘要数据"
            lines = [f"• {d.get('group','?')}: {d.get('summary','')[:60]}"
                     for d in digests[:5]]
            return "📝 群聊摘要：\n" + "\n".join(lines)
        except Exception as e:
            return f"摘要查询失败: {e}"

    if msg.get("needs_human") and msg.get("complex_type"):
        complex_type = msg["complex_type"]
        talker = msg.get("talker", "未知")
        name = msg.get("name", talker)
        _write_complex_task(talker, name, complex_type, content)
        _notify_human(name, complex_type, content)
        return (
            f"好的，您的{complex_type}需求已收到，我会尽快安排专人处理。"
            f"\n如有紧急情况请直接电话联系，谢谢！"
        )

    msg_type = msg["type"]
    if msg_type == 34:  # 语音
        # 语音文件路径规则（UOS: ~/文档/xwechat_files/…/voice/）
        # 此处只做文字占位，实际路径需要从 DB 附加信息中获取
        text_from_voice = (
            await transcribe_voice(content) if os.path.exists(content) else ""
        )
        if text_from_voice:
            content = f"[语音转写] {text_from_voice}"
        else:
            return "您好，语音消息我这边暂时无法接收，请发文字方便沟通 😊"

    elif msg_type == 3:  # 图片
        img_desc = await analyze_image(content) if os.path.exists(content) else ""
        if img_desc:
            content = f"[图片内容] {img_desc}"
        else:
            return "收到图片了，请问有什么可以帮您？"

    context = "群聊中" if is_group else "私聊"

    letta_ctx = await _search_letta(content, msg.get("talker", ""))
    ctx_block = f"\n相关背景：{letta_ctx}\n" if letta_ctx else ""

    user_prompt = (
        f"对话场景：{context}\n"
        f"客户意图：{intent}\n"
        f"客户消息：{content}\n"
        f"{ctx_block}"
        f"请给出回复："
    )

    async def _do_request(model: str) -> httpx.Response:
        async with httpx.AsyncClient(timeout=40) as client:
            return await client.post(
                f"{LITELLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
            )

    try:
        model = get_active_model()
        resp = await _do_request(model)
        resp_json = resp.json()

        # 检测 GLM 额度耗尽
        used_fallback = False
        if resp.status_code == 429 or (
            isinstance(resp_json.get("error"), dict)
            and any(
                kw in str(resp_json["error"])
                for kw in ("Exhausted", "limit", "quota")
            )
        ):
            mark_glm_failed()
            used_fallback = True
            log.warning("[MODEL_FAILOVER] 主模型 %s 失败，重试 %s", model, MODEL_FALLBACK)
            resp = await _do_request(MODEL_FALLBACK)
            resp_json = resp.json()

        result = resp_json["choices"][0]["message"]["content"].strip()
        # 只有当 GLM 本身返回成功（未经 fallback）时才恢复
        if not used_fallback and model == MODEL_PRIMARY and resp.status_code == 200:
            mark_glm_ok()
        return result
    except Exception as e:
        log.error("LLM 回复生成失败: %s", e)
        return ""


def _write_complex_task(talker: str, name: str, task_type: str, content: str) -> None:
    op_tasks = Path.home() / ".claude/projects/-home-charlie/memory/op-tasks.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    task_line = f"- [ ] [WECHAT] [{timestamp}] [{task_type}] {name}: {content[:100]}\n"
    if op_tasks.exists():
        existing = op_tasks.read_text()
        if f"[{task_type}] {name}:" in existing[-500:]:
            return
    with open(op_tasks, "a") as f:
        f.write(task_line)
    log.info("复杂任务已写入 op-tasks: %s → %s", name, task_type)


def _notify_human(name: str, task_type: str, content: str) -> None:
    try:
        msg_text = (
            f"📬 微信复杂任务\n来源: {name}\n类型: {task_type}\n内容: {content[:80]}"
        )
        subprocess.Popen(
            ["notify-send", "微信待处理", msg_text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# ─── 回复队列 ────────────────────────────────────────────────────────────────


def enqueue_reply(msg: dict[str, Any], reply: str) -> None:
    """将生成的回复追加到队列文件。
    Why: 解耦生成和发送，发送失败可重试
    What: JSONL append，sent=false 标志待发
    Test: 调用后 tail -1 队列文件应有 sent=false 记录
    """
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "wxid": msg["talker"],
        "name": msg.get("name", msg["talker"]),
        "msg": msg["content"][:200],
        "reply": reply,
        "source": msg["source"],
        "intent": msg.get("intent", ""),
        "sent": False,
    }
    with QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def lookup_display_name(wxid: str) -> str:
    """从 contact.db 查联系人显示名（备注名优先，其次昵称，最后返回原wxid）。
    Why: xdotool 搜索框需要显示名而非内部 wxid，否则无法匹配联系人
    What: 解密 contact.db → 查 remark/nickName → 返回最优名称
    Test: 传入已知 wxid，断言返回非空字符串且不含 wxid 前缀
    """
    try:
        keys = json.loads(UOS_KEYS_CACHE.read_text())
        key_data = keys.get("contact/contact.db", {})
        key_hex = key_data.get("enc_key", "") if isinstance(key_data, dict) else key_data
        if not key_hex:
            return wxid
        for wxid_dir in UOS_DB_BASE.iterdir():
            db = wxid_dir / "db_storage" / "contact" / "contact.db"
            if not db.exists():
                continue
            tmp = decrypt_uos_db(db, key_hex)
            if tmp is None:
                continue
            try:
                with sqlite3.connect(str(tmp)) as conn:
                    # UOS WeChat 4.x 列名: username, remark, nick_name
                    # 兼容旧版列名 userName/nickName
                    cols = {r[1] for r in conn.execute("PRAGMA table_info(contact)").fetchall()}
                    uname_col = "username" if "username" in cols else "userName"
                    nick_col = "nick_name" if "nick_name" in cols else "nickName"
                    row = conn.execute(
                        f"SELECT remark, {nick_col} FROM contact WHERE {uname_col}=? LIMIT 1",
                        (wxid,)
                    ).fetchone()
                    if row:
                        return row[0] if row[0] else (row[1] if row[1] else wxid)
            finally:
                tmp.unlink(missing_ok=True)
    except Exception:
        pass
    return wxid


# ─── 发送机制（xdotool --window 静默注入，XWayland 直接发送）───────────────────


def _get_wechat_window() -> tuple[str, int, int, int, int] | None:
    """获取微信窗口 (xid_hex, x, y, w, h)。
    优先选最大窗口（主窗口），返回 None 表示未找到。
    """
    try:
        result = subprocess.run(
            ["wmctrl", "-lG"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None
        best: tuple[str, int, int, int, int] | None = None
        best_area = 0
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) < 8:
                continue
            title = " ".join(parts[7:])
            if "微信" not in title:
                continue
            try:
                x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
            except ValueError:
                continue
            # 必须是合理大小的主聊天窗口（至少 600x500）
            if w < 600 or h < 500:
                continue
            # 跳过 AI 搜索/发现页窗口（宽度 > 1350）
            if w > 1350:
                continue
            if best is None or w * h > best_area:
                best_area = w * h
                best = (parts[0], x, y, w, h)  # (xid_hex, x, y, w, h)
        return best
    except Exception:
        return None


# 保留旧名以兼容
def _get_wechat_window_kwin() -> tuple[int, int, int, int] | None:
    w = _get_wechat_window()
    return (w[1], w[2], w[3], w[4]) if w else None


def _ydotool_move_click(x: int, y: int) -> None:
    """ydotool 移动鼠标并左键点击。"""
    subprocess.run(["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)],
                   timeout=3, check=False)
    time.sleep(0.08)
    subprocess.run(["ydotool", "click", "0xC0"], timeout=3, check=False)  # left click


def _xdo_key(wid: str, key: str) -> None:
    """向指定 X11 窗口发送按键（不切换焦点）。"""
    subprocess.run(["xdotool", "key", "--window", wid, key],
                   timeout=3, check=False, capture_output=True)


def _xdo_type(wid: str, text: str) -> None:
    """向指定 X11 窗口输入文本。
    优先 wl-copy --foreground（持续存活直到 kill，XWayland 桥能读到）→ xclip → xdotool type fallback。
    """
    tool = _find_clipboard_tool()
    if tool:
        tool_path, tool_type = tool
        if tool_type == "wl-copy":
            # --foreground: 进程持续存活直到被 kill，确保 XWayland 在 ctrl+v 时能读取剪贴板
            cmd = [tool_path, "--foreground", text]
            env = {**os.environ,
                   "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", "wayland-0"),
                   "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")}
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        else:  # xclip: stdin 方式
            cmd = [tool_path, "-selection", "clipboard"]
            env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, env=env)
            p.stdin.write(text.encode("utf-8")); p.stdin.close()
        time.sleep(0.25)  # 等剪贴板就绪
        subprocess.run(["xdotool", "key", "--window", wid, "ctrl+v"],
                       timeout=3, check=False, capture_output=True)
        time.sleep(0.3)   # 等粘贴完成
        p.kill()
        try: p.wait(timeout=1)
        except subprocess.TimeoutExpired: pass
    else:
        subprocess.run(
            ["xdotool", "type", "--window", wid, "--clearmodifiers", "--delay", "20", "--", text],
            timeout=10, check=False, capture_output=True,
        )
    time.sleep(0.05)


def _xdo_click(wid: str, rel_x: int, rel_y: int) -> None:
    """向指定 X11 窗口发送鼠标点击（窗口相对坐标，完全不切换焦点）。
    xdotool mousemove --window 使用窗口内部相对坐标，无需窗口在前台。
    注：不加 --sync，避免 XWayland 下永久阻塞。
    """
    subprocess.run(
        ["xdotool", "mousemove", "--window", wid, str(rel_x), str(rel_y)],
        timeout=3, check=False, capture_output=True,
    )
    time.sleep(0.08)
    subprocess.run(
        ["xdotool", "click", "--window", wid, "1"],
        timeout=3, check=False, capture_output=True,
    )


def _ydokey(*codes: str) -> None:
    """ydotool key 发送按键序列，格式: '29:1', '47:0' 等。"""
    ydotool = "/run/current-system/sw/bin/ydotool"
    subprocess.run([ydotool, "key"] + list(codes),
                   timeout=3, check=False, capture_output=True)
    time.sleep(0.2)


def _xclip_set(text: str) -> None:
    """xclip 设置 X11 CLIPBOARD 选区（给 ydotool ctrl+v 粘贴用）。"""
    xclip_paths = [
        "/run/current-system/sw/bin/xclip",
        "/nix/store/ljbwcgfwilqzhqfzpkphghn4w7mw6lqj-xclip-0.13/bin/xclip",
    ]
    xclip = next((p for p in xclip_paths if Path(p).exists()), None)
    if not xclip:
        log.warning("xclip 未找到")
        return
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
    p = subprocess.Popen(
        [xclip, "-selection", "clipboard", "-display", ":0"],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, env=env,
    )
    p.stdin.write(text.encode("utf-8")); p.stdin.close()
    time.sleep(0.3)


def send_reply_xdotool(wxid: str, reply: str, source: str) -> bool:
    """发送微信消息（xdotool X11 key events 全程，实测可用）。
    Why: xdotool key --window 直接注入 X11 事件到 XWayland WeChat，
         无需 Wayland 焦点切换，xclip + X11 ctrl+v 可靠粘贴中文
    What:
      1. wmctrl 激活 + xdotool windowfocus 获取焦点
      2. xdotool key --window ctrl+f → 打开全局搜索
      3. xclip + xdotool key --window ctrl+v → 粘贴搜索词到搜索框
      4. 等待 2s 后，功能区"文件传输助手"条目已默认高亮
      5. xdotool key --window Return → 直接打开目标聊天（不需要 Down）
      6. xclip + xdotool key --window ctrl+v → 粘贴回复
      7. xdotool key --window Return → 发送
    Test: /tmp/test_send_v13.py 验证 X11 paste 成功，Enter=0 Down 可靠打开聊天
    """
    if DRY_RUN:
        log.info("[DRY_RUN] 模拟发送 → %s: %s", wxid, reply[:50])
        return True

    if not shutil.which("wmctrl"):
        log.warning("wmctrl 未安装，跳过发送")
        return False

    win = _get_wechat_window()
    if not win:
        log.warning("未找到微信窗口，无法发送")
        return False

    xid, wx, wy, ww, wh = win
    log.info("[SEND] 开始 → wxid=%s xid=%s", wxid, xid)

    def _xkey(key: str, delay: float = 0.15) -> None:
        subprocess.run(["xdotool", "key", "--window", xid, key],
                       timeout=3, check=False, capture_output=True)
        time.sleep(delay)

    try:
        display_name = lookup_display_name(wxid)
        search_term = display_name
        log.info("[SEND] 目标: %s (search=%s)", wxid, search_term)

        # Step 1: 激活窗口（只用 wmctrl，不用 xdotool windowfocus 避免触发 KDE XTest 权限弹窗）
        subprocess.run(["wmctrl", "-ia", xid], capture_output=True, timeout=3)
        time.sleep(0.8)

        # Step 2: Escape 清空残留弹窗
        _xkey("Escape", 0.2)

        # Ctrl+F 全局搜索（纯键盘，不用 xdotool click 避免 KDE XTest 权限弹窗）
        # 截图验证：群聊和特殊联系人都在搜索结果第一位默认高亮，Enter=0 直接打开
        _xkey("ctrl+f", 0.8)
        _xclip_set(search_term)
        _xkey("ctrl+v", 0.3)
        time.sleep(2.0)
        _xkey("Return", 1.2)

        log.info("[SEND] 已进入聊天: %s", display_name)

        # Step 6: 粘贴回复（多行支持）
        lines = reply.split("\n")
        for i, line in enumerate(lines):
            _xclip_set(line)
            _xkey("ctrl+v", 0.3)
            if i < len(lines) - 1:
                _xkey("shift+Return", 0.15)   # 换行

        # Step 7: 发送
        _xkey("Return", 0.3)
        log.info("[SEND] 完成 → %s", wxid)
        return True

    except subprocess.TimeoutExpired:
        log.warning("[SEND] 操作超时")
        return False
    except Exception as e:
        log.warning("[SEND] 失败: %s", e)
        return False


# ─── CRM 同步 ────────────────────────────────────────────────────────────────


def init_crm() -> None:
    """初始化 CRM 数据库表（幂等）。"""
    CRM_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CRM_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            wxid           TEXT PRIMARY KEY,
            name           TEXT,
            source         TEXT,
            last_msg_time  INTEGER,
            msg_count      INTEGER DEFAULT 0,
            intent_history TEXT DEFAULT '[]',
            updated_at     TEXT
        )
    """)
    conn.commit()
    conn.close()


def upsert_contact(msg: dict[str, Any]) -> None:
    """更新 CRM 联系人记录。
    Why: 维护客户互动历史，供报表和人工查阅
    What: upsert 联系人，追加意图到 intent_history
    Test: 同一 wxid 调用两次，msg_count 加2
    """
    try:
        conn = sqlite3.connect(CRM_DB)
        row = conn.execute(
            "SELECT msg_count, intent_history FROM contacts WHERE wxid=?",
            (msg["talker"],),
        ).fetchone()

        now_iso = datetime.now().isoformat(timespec="seconds")
        if row:
            count = (row[0] or 0) + 1
            history: list = json.loads(row[1] or "[]")
            intent = msg.get("intent", "")
            if intent and intent != "ignore":
                history = (history + [intent])[-20:]  # 保留最近20条
            conn.execute(
                "UPDATE contacts SET last_msg_time=?, msg_count=?, intent_history=?, updated_at=? WHERE wxid=?",
                (
                    msg["create_time"],
                    count,
                    json.dumps(history, ensure_ascii=False),
                    now_iso,
                    msg["talker"],
                ),
            )
        else:
            intent = msg.get("intent", "")
            history = [intent] if intent and intent != "ignore" else []
            conn.execute(
                "INSERT INTO contacts (wxid, nickname, source, last_msg_time, msg_count, intent_history, last_contact, updated_at)"
                " VALUES (?,?,?,?,1,?,?,?)",
                (
                    msg["talker"],
                    msg.get("name", msg["talker"]),
                    msg["source"],
                    msg["create_time"],
                    json.dumps(history, ensure_ascii=False),
                    now_iso,
                    now_iso,
                ),
            )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        log.warning("CRM upsert 失败: %s", e)


# ─── AGI Brain 状态同步 ──────────────────────────────────────────────────────


def write_status(stats: dict[str, Any]) -> None:
    """写入 wechat-agent 状态供 AGI Brain sense 读取。"""
    try:
        STATUS_FILE.write_text(
            json.dumps({**stats, "ts": datetime.now().isoformat()}, ensure_ascii=False)
        )
        # 合并写入 agi-brain-status.json
        agi: dict = {}
        if AGI_STATUS.exists():
            try:
                agi = json.loads(AGI_STATUS.read_text())
            except Exception:
                pass
        agi["wechat"] = stats
        AGI_STATUS.write_text(json.dumps(agi, ensure_ascii=False, indent=2))
    except OSError:
        pass


# ─── 回复消费线程 ────────────────────────────────────────────────────────────


async def reply_worker() -> None:
    """后台协程：消费队列文件，执行实际发送。
    Why: 将 IO 密集的发送与生成逻辑解耦
    What: 读取 sent=false 条目 → xdotool 发送 → 标记 sent=true
    Test: 向队列写入一条记录，worker 应在30s内处理并更新 sent=true
    """
    while True:
        await asyncio.sleep(10)
        if not QUEUE_FILE.exists():
            continue
        lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()
        updated: list[str] = []
        changed = False
        for line in lines:
            if not line.strip():
                continue
            try:
                rec: dict = json.loads(line)
            except json.JSONDecodeError:
                updated.append(line)
                continue

            if rec.get("sent"):
                updated.append(line)
                continue

            wxid = rec.get("wxid") or rec.get("talker", "")
            if not wxid:
                updated.append(line)
                continue
            reply = rec["reply"]
            source = rec.get("source", "uos")

            ok_flag, reason = counter.allow(wxid)
            if not ok_flag:
                log.debug("跳过发送 %s: %s", wxid, reason)
                updated.append(line)
                continue

            success = send_reply_xdotool(wxid, reply, source)
            if success:
                counter.record(wxid)
                log.info("已发送 → %s [%s]: %s", wxid, source, reply[:40])
            rec["sent"] = success
            rec["sent_at"] = datetime.now().isoformat(timespec="seconds")
            updated.append(json.dumps(rec, ensure_ascii=False))
            changed = True

        if changed:
            QUEUE_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")


# ─── 主轮询周期 ──────────────────────────────────────────────────────────────

# 用户自己的微信昵称（群聊 @检测用），可通过 contact DB 自动获取，此处预设
MY_NICKNAMES: list[str] = ["Charlie", "charlie", "管理员"]


async def poll_cycle(state: dict[str, Any]) -> dict[str, Any]:
    """单次轮询：读取新消息 → 分类 → 生成回复 → 入队。
    Why: 主循环的核心逻辑，保持幂等（基于 last_id）
    What: 拉取新消息列表，逐条处理，更新 last_ids
    Test: 两次连续调用，第二次不应重复处理已处理的消息
    """
    all_msgs: list[dict[str, Any]] = []

    # — UOS WeChat —
    uos_key = "uos_create_time"  # 修复: 与更新时使用同一个key
    uos_last = state["last_ids"].get(uos_key, 0)
    uos_msgs = read_uos_messages(uos_last)
    all_msgs.extend(uos_msgs)

    # — Wine WeChat —
    for db_path in WINE_ACCOUNTS:
        wine_key = f"wine_{db_path.parent.parent.name}"
        wine_last = state["last_ids"].get(wine_key, 0)
        wine_msgs = read_wine_messages(db_path, wine_last)
        all_msgs.extend(wine_msgs)

    if not all_msgs:
        log.debug("本轮无新消息")
        return state

    log.info("本轮新消息 %d 条", len(all_msgs))

    processed = replied = silenced = 0

    for msg in all_msgs:
        classified = classify_message(msg, MY_NICKNAMES)

        # 更新 last_id：UOS 用 create_time 作时间戳，Wine 用 local_id
        if msg["source"] == "uos":
            source_key = "uos_create_time"
            state["last_ids"][source_key] = max(
                state["last_ids"].get(source_key, 0), msg["create_time"]
            )
        else:
            source_key = f"wine_{Path(msg['db_path']).parent.parent.name}"
            state["last_ids"][source_key] = max(
                state["last_ids"].get(source_key, 0), msg["id"]
            )

        # CRM 始终更新
        upsert_contact(classified)
        processed += 1

        if not classified.get("should_reply"):
            silenced += 1
            continue

        # 安全检查（发送时再检查，此处提前过滤静默时段）
        h = datetime.now().hour
        if SILENT_HOUR_START <= h < SILENT_HOUR_END:
            silenced += 1
            log.debug("静默时段，跳过回复 %s", msg["talker"])
            continue

        # COMMAND_ONLY 模式：只响应 # 命令，跳过 AI 闲聊
        content_raw = classified.get("content", "")
        is_command = any(content_raw.startswith(p) for p in (
            "#文档", "#doc", "#crm", "#客户", "#消息", "#总结", "#摘要",
            "#op", "#task", "#任务", "#状态", "#status",
        ))
        if COMMAND_ONLY and not is_command:
            log.debug("[COMMAND_ONLY] 跳过非命令消息: %s", content_raw[:40])
            continue

        reply = await generate_reply(classified)
        if not reply:
            continue

        enqueue_reply(classified, reply)
        replied += 1
        log.info(
            "入队回复 → %s [%s]: %s", msg["talker"], classified["intent"], reply[:50]
        )

    write_status(
        {
            "processed": processed,
            "replied": replied,
            "silenced": silenced,
            "daily_sent": counter._data.get("count", 0),
        }
    )

    # 导出到 viewer DB（供 Windows HTTP server 读取）
    export_to_viewer_db(all_msgs)

    log.info("本轮完成：处理%d 回复%d 静默%d", processed, replied, silenced)
    return state


# ─── Viewer 数据库导出 ───────────────────────────────────────────────────────

VIEWER_DB_DIR = Path("/mnt/data/wechat-viewer")
VIEWER_DB = VIEWER_DB_DIR / "messages.db"


def _init_viewer_db(conn: sqlite3.Connection) -> None:
    """初始化 viewer DB schema（幂等）。
    Why: 确保每次导出前表结构存在，不依赖外部初始化
    What: CREATE TABLE IF NOT EXISTS 三张表
    Test: 多次调用不报错，sqlite3 .tables 列出三张表
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id          TEXT PRIMARY KEY,
            account     TEXT,
            talker      TEXT,
            talker_name TEXT,
            msg_type    INTEGER,
            content     TEXT,
            is_sender   INTEGER,
            create_time INTEGER,
            source      TEXT
        );
        CREATE TABLE IF NOT EXISTS contacts (
            wxid         TEXT PRIMARY KEY,
            nickname     TEXT,
            remark       TEXT,
            avatar_path  TEXT,
            last_updated INTEGER
        );
        CREATE TABLE IF NOT EXISTS export_meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()


def export_to_viewer_db(messages: list[dict[str, Any]]) -> None:
    """将本轮解密消息写入 viewer SQLite DB。
    Why: 让 Windows HTTP server 能读取最新消息，无需访问加密 DB
    What: upsert messages 表，更新 export_meta.last_export_time
    Test: 传入 2 条消息后，sqlite3 "SELECT count(*) FROM messages" 返回 ≥2
    """
    if not messages:
        return
    try:
        VIEWER_DB_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(VIEWER_DB, timeout=10)
        _init_viewer_db(conn)

        rows = [
            (
                # id: source_msgid 保证跨 DB 唯一
                f"{msg['source']}_{msg['id']}",
                # account: 从 db_path 解析 wxid 目录名
                Path(msg.get("db_path", "")).parent.parent.name or msg["source"],
                msg.get("talker", ""),
                msg.get("name", ""),  # talker_name（分类后可能有 name）
                msg.get("type", 1),
                msg.get("content", ""),
                0,  # is_sender=0（只导出收到的消息）
                msg.get("create_time", 0),
                msg.get("source", ""),
            )
            for msg in messages
        ]
        conn.executemany(
            """INSERT OR REPLACE INTO messages
               (id, account, talker, talker_name, msg_type, content,
                is_sender, create_time, source)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            rows,
        )

        now_iso = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "INSERT OR REPLACE INTO export_meta (key, value) VALUES (?, ?)",
            ("last_export_time", now_iso),
        )
        conn.commit()
        conn.close()
        log.debug("viewer DB 导出 %d 条消息 → %s", len(rows), VIEWER_DB)
    except sqlite3.Error as e:
        log.warning("viewer DB 导出失败: %s", e)
    except OSError as e:
        log.warning("viewer DB 目录创建失败: %s", e)


# ─── 日报生成 ────────────────────────────────────────────────────────────────


async def generate_daily_report() -> None:
    """生成每日微信活动报告，写入审计日志。
    Why: 让用户了解 AI 助理当天的工作成果
    What: 统计今日队列记录，汇总输出到审计 JSONL
    Test: 调用后 grep today audit-log 有一条 type=wechat_daily
    """
    if not QUEUE_FILE.exists():
        return
    today = date.today().isoformat()
    sent = skipped = 0
    intents: dict[str, int] = {}
    for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("ts", "")[:10] != today:
            continue
        if rec.get("sent"):
            sent += 1
        else:
            skipped += 1
        intent = rec.get("intent", "")
        if intent:
            intents[intent] = intents.get(intent, 0) + 1

    log_path = Path.home() / ".claude/projects/-home-charlie/memory/agi-audit-log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "wechat_daily",
                    "sent": sent,
                    "skipped": skipped,
                    "intents": intents,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    log.info("日报已写入：发送%d 跳过%d 意图分布%s", sent, skipped, intents)


# ─── 进程检测 ────────────────────────────────────────────────────────────────


def is_wechat_running() -> bool:
    """检查微信进程是否存在（UOS 或 Wine 任意一个）。
    Why: 避免在微信未启动时无效解密、占用 CPU
    What: 扫描 /proc 寻找 wechat 进程名
    Test: 启动微信后返回 True，退出后返回 False
    """
    for pid_str in os.listdir("/proc"):
        if not pid_str.isdigit():
            continue
        try:
            comm = Path(f"/proc/{pid_str}/comm").read_text().strip().lower()
            if "wechat" in comm:
                return True
        except OSError:
            continue
    return False


# ─── 主入口 ──────────────────────────────────────────────────────────────────


async def _http_api_server() -> None:
    """轻量 HTTP API 服务，监听 9801 端口。
    Why: 供 macg.py MCP 工具 (macg_wechat_reply/macg_wechat_status) 调用
    Endpoints:
      GET  /api/wechat/status   → 返回 STATUS_FILE 内容
      GET  /api/wechat/contacts → 返回最近联系人列表
      POST /api/wechat/reply    → 发送消息 {"talker": str, "content": str}
    """
    from aiohttp import web  # type: ignore

    async def handle_status(request: web.Request) -> web.Response:
        data: dict[str, Any] = {}
        if STATUS_FILE.exists():
            try:
                data = json.loads(STATUS_FILE.read_text())
            except Exception:
                pass
        data["running"] = True
        data["dry_run"] = DRY_RUN
        return web.json_response(data)

    async def handle_contacts(request: web.Request) -> web.Response:
        contacts: list[dict[str, Any]] = []
        if STATE_FILE.exists():
            try:
                state = json.loads(STATE_FILE.read_text())
                contacts = list(state.get("recent_contacts", []))[:10]
            except Exception:
                pass
        return web.json_response(contacts)

    async def handle_reply(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "invalid json"}, status=400)
        talker = body.get("talker", "").strip()
        content = body.get("content", "").strip()
        if not talker or not content:
            return web.json_response({"ok": False, "error": "talker and content required"}, status=400)
        # COMMAND_ONLY 模式：API 发送也必须是 # 命令或 force=true
        if COMMAND_ONLY and not body.get("force") and not content.startswith("#"):
            log.info("[COMMAND_ONLY] 拦截 API 发送请求: talker=%s content=%s", talker, content[:40])
            return web.json_response({"ok": False, "blocked": "COMMAND_ONLY mode, use force=true to override"}, status=403)
        # 非阻塞：在线程中执行，立即返回 202 Accepted
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, send_reply_xdotool, talker, content, "api")
        return web.json_response({"ok": True, "queued": True}, status=202)

    app = web.Application()
    app.router.add_get("/api/wechat/status", handle_status)
    app.router.add_get("/api/wechat/contacts", handle_contacts)
    app.router.add_post("/api/wechat/reply", handle_reply)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 9801)
    await site.start()
    log.info("HTTP API 已启动: http://0.0.0.0:9801")


async def main() -> None:
    """守护进程主循环。
    Why: 持续监控微信，每30秒一次轮询
    What: 初始化 → 启动 reply_worker + HTTP API → 循环 poll_cycle
    Test: 启动后观察日志，每30s应有 "本轮" 输出
    """
    log.info("wechat-agent 启动 (DRY_RUN=%s)", DRY_RUN)
    init_crm()

    state = load_state()
    asyncio.create_task(reply_worker())

    # 启动 HTTP API 服务 (port 9801)
    try:
        asyncio.create_task(_http_api_server())
    except Exception as e:
        log.warning("HTTP API 启动失败: %s", e)

    last_report_day: str = ""

    while True:
        try:
            if not is_wechat_running():
                log.debug("微信未运行，跳过本轮")
            else:
                state = await poll_cycle(state)
                save_state(state)

            # 每日22:00 生成日报
            now = datetime.now()
            today_str = date.today().isoformat()
            if now.hour == 22 and last_report_day != today_str:
                await generate_daily_report()
                last_report_day = today_str

        except Exception as e:
            log.exception("poll_cycle 异常: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
