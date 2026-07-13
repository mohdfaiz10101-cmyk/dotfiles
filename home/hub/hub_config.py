"""Hub API 配置类 — 集中管理所有路径和数据库连接配置"""

from pathlib import Path
import json
import os


class HubConfig:
    """Hub API 全局配置，支持环境变量覆盖"""

    def __init__(self):
        self._ai_data = Path(os.environ.get("AI_DATA_DIR", "/mnt/ai/data"))
        self._ai_apps = Path(os.environ.get("AI_APPS_DIR", "/mnt/ai/apps"))

        # 三方对话室
        self.DIALOGUE_FEED = Path(Path.home() / ".local/state/dialogue-feed.jsonl")

        # 微信数据库路径
        self.WECHAT_DBS = [
            Path.home() / ".local/share/hyperchat/data/wechat_digests.db",
        ]
        self.WECHAT_CONTACT_DB = Path(
            os.environ.get(
                "WECHAT_CONTACT_DB",
                str(self._ai_data / "win-wechat-decrypted/contact/contact.db"),
            )
        )
        self.WECHAT_MSG_DBS = [
            Path(
                os.environ.get(
                    "WECHAT_MSG_DB_MERGED_OLD",
                    str(self._ai_data / "wechat-merged/messages.db"),
                )
            ),
            Path(
                os.environ.get(
                    "WECHAT_MSG_DB_WIN",
                    str(self._ai_data / "win-wechat-decrypted/message/message_0.db"),
                )
            ),
        ]
        self.WECHAT_MSG_DB_MERGED = Path(
            os.environ.get(
                "WECHAT_MSG_DB_MERGED",
                str(self._ai_data / "wechat-merged/message/message_0.db"),
            )
        )
        self.WECHAT_MSG_DB_WIN_FALLBACK = Path(
            os.environ.get(
                "WECHAT_MSG_DB_WIN",
                str(self._ai_data / "win-wechat-decrypted/message/message_0.db"),
            )
        )
        self.WECHAT_CRM_DB = Path(
            os.environ.get(
                "WECHAT_CRM_DB", str(self._ai_apps / "wechat-agent/data/crm.db")
            )
        )
        self.CRM_DB = Path(
            os.environ.get("CRM_DB", str(self._ai_apps / "crm/crm.db"))
        )
        self.WECHAT_TABLE_MAP = Path.home() / ".local/share/macg/wechat-table-map.json"

        # 回复队列
        self.REPLY_QUEUE = Path(Path.home() / ".local/state/wechat-reply-queue.jsonl")

    def load_table_map(self) -> dict:
        if self.WECHAT_TABLE_MAP.exists():
            return json.loads(self.WECHAT_TABLE_MAP.read_text())
        return {}


cfg = HubConfig()