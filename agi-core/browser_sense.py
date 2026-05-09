#!/usr/bin/env python3
"""浏览器感知引擎 — 通过 CDP 学习用户浏览行为，智能提取有价值内容。

架构：
  Floorp/Chrome → CDP WebSocket → 事件监听 → 行为分析 → 内容提取 → Letta/ChromaDB

判断"什么值得记"的信号权重系统：
  - 停留时间 > 30s（认真在看）                    +3
  - 页面有滚动行为（阅读中）                      +2
  - 重复访问同域名 ≥3次/天（高频关注）             +3
  - 收藏/书签操作                                  +5
  - 特定高价值域名（GitHub/StackOverflow/文档站）   +2
  - 搜索引擎结果页（信息需求信号）                 +1
  - 标签页打开 >5min 未关闭（待处理）              +1
  权重 ≥5 → 提取内容 + 存入记忆

Test: python3 browser_sense.py --test 验证 CDP 连接
"""

import asyncio
import json
import time
import hashlib
import sqlite3
import os
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import websockets
except ImportError:
    print("需要 websockets: pip install websockets")
    raise

# ── 配置 ────────────────────────────────────────────────
CDP_HOST = os.environ.get("CDP_HOST", "127.0.0.1")
CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))
DB_PATH = Path.home() / "agi" / "browser_memory.db"
LITELLM_URL = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-charlie-2026")
SUMMARY_MODEL = os.environ.get("BROWSER_SUMMARY_MODEL", "cerebras-llama-8b")
POLL_INTERVAL = 5  # 秒，轮询标签页变化
SCORE_THRESHOLD = 5  # 达到此分数才提取内容
MAX_CONTENT_LENGTH = 3000  # 提取内容最大字符数

# 高价值域名（自动 +2 权重）
HIGH_VALUE_DOMAINS = {
    "github.com", "stackoverflow.com", "docs.python.org",
    "nixos.wiki", "wiki.nixos.org", "developer.mozilla.org",
    "arxiv.org", "news.ycombinator.com", "reddit.com",
    "claude.ai", "platform.openai.com", "console.groq.com",
    "docs.anthropic.com", "huggingface.co",
}

# 忽略的域名/路径（不记录）
IGNORE_PATTERNS = [
    r"^chrome://", r"^about:", r"^chrome-extension://",
    r"^moz-extension://", r"localhost", r"127\.0\.0\.1",
    r"google\.com/search",  # 搜索页单独处理
    r"mail\.google\.com", r"web\.whatsapp\.com",
    r"youtube\.com/watch",  # 视频单独处理
]

# 搜索引擎 pattern（提取搜索词）
SEARCH_PATTERNS = [
    (r"google\.com/search\?.*q=([^&]+)", "Google"),
    (r"bing\.com/search\?.*q=([^&]+)", "Bing"),
    (r"baidu\.com/s\?.*wd=([^&]+)", "Baidu"),
]


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _should_ignore(url: str) -> bool:
    for pat in IGNORE_PATTERNS:
        if re.search(pat, url, re.IGNORECASE):
            return True
    return False


def _extract_search_query(url: str) -> str | None:
    """从搜索引擎 URL 提取搜索词。"""
    from urllib.parse import unquote
    for pat, engine in SEARCH_PATTERNS:
        m = re.search(pat, url)
        if m:
            return unquote(m.group(1).replace("+", " "))
    return None


class BrowserMemoryDB:
    """浏览器记忆数据库 — 记录访问历史、行为信号、内容摘要。"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                url_hash TEXT NOT NULL,
                domain TEXT NOT NULL,
                title TEXT,
                timestamp TEXT NOT NULL,
                dwell_time_sec REAL DEFAULT 0,
                scrolled INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS domain_stats (
                domain TEXT PRIMARY KEY,
                visit_count INTEGER DEFAULT 0,
                last_visit TEXT,
                avg_dwell_sec REAL DEFAULT 0,
                is_favorite INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS content_cache (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                extracted_at TEXT,
                sent_to_letta INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                engine TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_interests (
                topic TEXT PRIMARY KEY,
                weight REAL DEFAULT 1.0,
                last_seen TEXT,
                example_urls TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_visits_domain ON visits(domain);
            CREATE INDEX IF NOT EXISTS idx_visits_time ON visits(timestamp);
            CREATE INDEX IF NOT EXISTS idx_visits_hash ON visits(url_hash);
        """)
        self.db.commit()

    def record_visit(self, url: str, title: str, dwell_sec: float = 0,
                     scrolled: bool = False, selection_bonus: int = 0) -> int:
        """记录一次访问，返回计算的兴趣分数。"""
        domain = _domain(url)
        url_hash = _url_hash(url)
        now = datetime.now().isoformat()

        score = self._calculate_score(url, domain, dwell_sec, scrolled, selection_bonus)

        self.db.execute(
            "INSERT INTO visits (url, url_hash, domain, title, timestamp, "
            "dwell_time_sec, scrolled, score) VALUES (?,?,?,?,?,?,?,?)",
            (url, url_hash, domain, title, now, dwell_sec, int(scrolled), score)
        )

        # 更新域名统计
        self.db.execute("""
            INSERT INTO domain_stats (domain, visit_count, last_visit, avg_dwell_sec)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                visit_count = visit_count + 1,
                last_visit = excluded.last_visit,
                avg_dwell_sec = (avg_dwell_sec * visit_count + excluded.avg_dwell_sec)
                              / (visit_count + 1)
        """, (domain, now, dwell_sec))

        # 搜索词提取
        query = _extract_search_query(url)
        if query:
            self.db.execute(
                "INSERT INTO search_queries (query, engine, timestamp) VALUES (?,?,?)",
                (query, "search", now)
            )

        self.db.commit()
        return score

    def _calculate_score(self, url: str, domain: str,
                         dwell_sec: float, scrolled: bool,
                         selection_bonus: int = 0) -> int:
        """计算兴趣权重分数。"""
        score = 0

        # 停留时间
        if dwell_sec > 30:
            score += 3
        elif dwell_sec > 10:
            score += 1
        elif dwell_sec > 3:
            score += 0  # 短暂停留不加也不减

        # 滚动行为
        if scrolled:
            score += 2

        # 文本选中（说明在读某段，即使没复制）
        if selection_bonus > 0:
            score += min(selection_bonus, 3)  # 最多+3

        # 高价值域名
        if any(hv in domain for hv in HIGH_VALUE_DOMAINS):
            score += 2

        # 重复访问（今日同域名 ≥3次）
        today = datetime.now().strftime("%Y-%m-%d")
        row = self.db.execute(
            "SELECT COUNT(*) FROM visits WHERE domain=? AND timestamp LIKE ?",
            (domain, f"{today}%")
        ).fetchone()
        if row and row[0] >= 3:
            score += 3

        # 搜索引擎结果页
        if _extract_search_query(url):
            score += 1

        return score

    def is_already_cached(self, url: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM content_cache WHERE url_hash=?", (_url_hash(url),)
        ).fetchone()
        return row is not None

    def save_content(self, url: str, title: str, summary: str):
        self.db.execute("""
            INSERT OR REPLACE INTO content_cache (url_hash, url, title, summary, extracted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (_url_hash(url), url, title, summary, datetime.now().isoformat()))
        self.db.commit()

    def mark_sent_to_letta(self, url: str):
        self.db.execute(
            "UPDATE content_cache SET sent_to_letta=1 WHERE url_hash=?",
            (_url_hash(url),)
        )
        self.db.commit()

    def get_today_stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        total = self.db.execute(
            "SELECT COUNT(*) FROM visits WHERE timestamp LIKE ?", (f"{today}%",)
        ).fetchone()[0]
        extracted = self.db.execute(
            "SELECT COUNT(*) FROM content_cache WHERE extracted_at LIKE ?",
            (f"{today}%",)
        ).fetchone()[0]
        top_domains = self.db.execute(
            "SELECT domain, COUNT(*) as c FROM visits WHERE timestamp LIKE ? "
            "GROUP BY domain ORDER BY c DESC LIMIT 5", (f"{today}%",)
        ).fetchall()
        searches = self.db.execute(
            "SELECT query FROM search_queries WHERE timestamp LIKE ? "
            "ORDER BY timestamp DESC LIMIT 10", (f"{today}%",)
        ).fetchall()
        return {
            "total_visits": total,
            "content_extracted": extracted,
            "top_domains": [(d, c) for d, c in top_domains],
            "recent_searches": [q[0] for q in searches],
        }

    def get_browsing_profile(self) -> dict:
        """生成用户浏览偏好画像。"""
        # 最常访问的域名（所有时间）
        top_all = self.db.execute(
            "SELECT domain, visit_count, avg_dwell_sec FROM domain_stats "
            "ORDER BY visit_count DESC LIMIT 20"
        ).fetchall()

        # 高停留时间页面（认真阅读的内容）
        deep_reads = self.db.execute(
            "SELECT url, title, dwell_time_sec FROM visits "
            "WHERE dwell_time_sec > 60 ORDER BY dwell_time_sec DESC LIMIT 10"
        ).fetchall()

        # 搜索词频率
        search_freq = self.db.execute(
            "SELECT query, COUNT(*) as c FROM search_queries "
            "GROUP BY query ORDER BY c DESC LIMIT 15"
        ).fetchall()

        return {
            "top_domains": [(d, vc, ds) for d, vc, ds in top_all],
            "deep_reads": [(u, t, d) for u, t, d in deep_reads],
            "search_interests": [(q, c) for q, c in search_freq],
        }


class BrowserSenseEngine:
    """浏览器感知引擎 — CDP 连接 + 行为监听 + 智能提取。"""

    def __init__(self):
        self.db = BrowserMemoryDB()
        self.active_tabs: dict[str, dict] = {}  # tab_id → {url, title, opened_at, scrolled}
        self.ws = None

    async def connect_cdp(self):
        """连接浏览器 CDP 端点。"""
        # 获取可用的调试 targets
        url = f"http://{CDP_HOST}:{CDP_PORT}/json"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                targets = json.loads(resp.read().decode())
        except Exception as e:
            print(f"[浏览器感知] 无法连接 CDP {url}: {e}")
            print(f"[浏览器感知] 请确保浏览器以 --remote-debugging-port={CDP_PORT} 启动")
            return False

        pages = [t for t in targets if t.get("type") == "page"]
        print(f"[浏览器感知] 发现 {len(pages)} 个标签页")

        # 初始化所有标签页
        for page in pages:
            tab_id = page.get("id", "")
            self.active_tabs[tab_id] = {
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "opened_at": time.time(),
                "scrolled": False,
                "ws_url": page.get("webSocketDebuggerUrl", ""),
            }
        return True

    async def poll_tabs(self):
        """轮询标签页变化 — 检测导航、关闭、新开。"""
        url = f"http://{CDP_HOST}:{CDP_PORT}/json"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                targets = json.loads(resp.read().decode())
        except Exception:
            return

        current_ids = set()
        for t in targets:
            if t.get("type") != "page":
                continue
            tab_id = t["id"]
            current_ids.add(tab_id)
            tab_url = t.get("url", "")
            tab_title = t.get("title", "")

            if tab_id in self.active_tabs:
                old = self.active_tabs[tab_id]
                # URL 变了 = 导航发生 → 记录旧页面的停留时间
                if old["url"] != tab_url and not _should_ignore(old["url"]):
                    dwell = time.time() - old["opened_at"]
                    await self._on_page_leave(old["url"], old["title"],
                                              dwell, old.get("scrolled", False), old)
                    # 更新为新页面
                    old["url"] = tab_url
                    old["title"] = tab_title
                    old["opened_at"] = time.time()
                    old["scrolled"] = False
                else:
                    # 更新标题（可能异步加载）
                    old["title"] = tab_title
            else:
                # 新标签页
                self.active_tabs[tab_id] = {
                    "url": tab_url,
                    "title": tab_title,
                    "opened_at": time.time(),
                    "scrolled": False,
                    "ws_url": t.get("webSocketDebuggerUrl", ""),
                }

        # 检测关闭的标签页
        closed = set(self.active_tabs.keys()) - current_ids
        for tab_id in closed:
            old = self.active_tabs.pop(tab_id)
            if not _should_ignore(old["url"]):
                dwell = time.time() - old["opened_at"]
                await self._on_page_leave(old["url"], old["title"],
                                          dwell, old.get("scrolled", False), old)

    async def check_scroll_state(self):
        """通过 CDP 检查每个标签页的滚动行为 + copy 事件 + 选中文本。"""
        for tab_id, tab in self.active_tabs.items():
            if not tab.get("ws_url"):
                continue
            try:
                async with websockets.connect(tab["ws_url"],
                                              close_timeout=2) as ws:

                    # ① 注入 copy 监听器（只注入一次）
                    if not tab.get("copy_listener_injected"):
                        inject_js = """
(function(){
  if(window.__browserSenseInit) return;
  window.__browserSenseInit = true;
  window.__copiedTexts = [];
  window.__selectedTexts = [];
  document.addEventListener('copy', function(e){
    var t = window.getSelection ? window.getSelection().toString() : '';
    if(t && t.length > 5) window.__copiedTexts.push(t.substring(0,2000));
  });
  document.addEventListener('mouseup', function(){
    var t = window.getSelection ? window.getSelection().toString() : '';
    if(t && t.length > 50) window.__selectedTexts.push(t.substring(0,500));
  });
})();
true
"""
                        await ws.send(json.dumps({
                            "id": 10,
                            "method": "Runtime.evaluate",
                            "params": {"expression": inject_js}
                        }))
                        await asyncio.wait_for(ws.recv(), timeout=2)
                        tab["copy_listener_injected"] = True

                    # ② 读取已复制的文本
                    await ws.send(json.dumps({
                        "id": 11,
                        "method": "Runtime.evaluate",
                        "params": {"expression":
                            "JSON.stringify({copied: window.__copiedTexts||[], "
                            "selected: window.__selectedTexts||[], "
                            "scrollY: window.scrollY})"}
                    }))
                    resp = await asyncio.wait_for(ws.recv(), timeout=3)
                    data = json.loads(resp)
                    raw = data.get("result", {}).get("result", {}).get("value", "{}")
                    signals = json.loads(raw) if raw else {}

                    copied = signals.get("copied", [])
                    selected = signals.get("selected", [])
                    scroll_y = signals.get("scrollY", 0)

                    if scroll_y and scroll_y > 100:
                        tab["scrolled"] = True

                    # ③ 有复制行为 → 立即触发存入 Letta（最强意图信号）
                    if copied and not _should_ignore(tab.get("url", "")):
                        if not tab.get("copy_stored"):
                            tab["copy_stored"] = True
                            combined = "\n---\n".join(copied)
                            print(f"[浏览器感知] 检测到复制行为 → 立即存入 Letta: {tab.get('title','')[:40]}")
                            asyncio.create_task(
                                self._store_copied_text(
                                    tab.get("url", ""), tab.get("title", ""), combined
                                )
                            )
                        # 清空已处理的复制记录
                        await ws.send(json.dumps({
                            "id": 12,
                            "method": "Runtime.evaluate",
                            "params": {"expression": "window.__copiedTexts=[];true"}
                        }))
                        await asyncio.wait_for(ws.recv(), timeout=2)
                        tab["copy_stored"] = False  # 允许下次继续检测

                    # ④ 大量选中文本 → 记录为中等信号（不强制存，提高后续分数）
                    if selected and not tab.get("has_selection"):
                        tab["has_selection"] = True
                        tab["selection_bonus"] = len(selected)  # 在_on_page_leave时加分

            except Exception:
                pass  # 连接失败不影响主流程

    async def _store_copied_text(self, url: str, title: str, copied_text: str):
        """直接将复制的文本存入 Letta（不等页面离开）。"""
        if len(copied_text) < 5:
            return
        summary = f"[用户复制] {title or url}\n\n{copied_text[:1500]}"
        await self._store_to_letta(url, title, summary, trigger="copy")

    async def _on_page_leave(self, url: str, title: str,
                             dwell_sec: float, scrolled: bool,
                             tab_meta: dict = None):
        """页面离开时的处理逻辑。"""
        if _should_ignore(url) or dwell_sec < 1:  # 降低到1s（快速复制场景）
            return

        selection_bonus = (tab_meta or {}).get("selection_bonus", 0)
        score = self.db.record_visit(url, title, dwell_sec, scrolled,
                                     selection_bonus=selection_bonus)

        # 分数达标 + 未缓存 → 提取内容
        if score >= SCORE_THRESHOLD and not self.db.is_already_cached(url):
            print(f"[浏览器感知] 高价值页面（分数{score}）: {title[:50]} → 提取内容")
            await self._extract_and_store(url, title)
        elif score >= 3:
            print(f"[浏览器感知] 中等兴趣（分数{score}）: {title[:50]}")

    async def _extract_and_store(self, url: str, title: str):
        """提取页面内容并存入记忆。"""
        # 通过 CDP 获取页面文本
        text = await self._get_page_text(url)
        if not text or len(text) < 50:
            return

        # 用 Cerebras 极速生成摘要
        summary = await self._summarize(title, text)
        if not summary:
            return

        self.db.save_content(url, title, summary)

        # 写入 Letta 记忆
        await self._send_to_letta(url, title, summary)
        print(f"[浏览器感知] 已存入记忆: {title[:40]}")

    async def _get_page_text(self, url: str) -> str | None:
        """通过任意可用标签页的 CDP 获取页面文本内容。"""
        # 找到匹配 URL 的标签页
        for tab_id, tab in self.active_tabs.items():
            if tab["url"] == url and tab.get("ws_url"):
                try:
                    async with websockets.connect(tab["ws_url"],
                                                  close_timeout=3) as ws:
                        await ws.send(json.dumps({
                            "id": 1,
                            "method": "Runtime.evaluate",
                            "params": {
                                "expression": """
                                    (function() {
                                        // 移除脚本、样式、导航等无用元素
                                        const removes = document.querySelectorAll(
                                            'script,style,nav,header,footer,aside,.sidebar,.ad,.advertisement'
                                        );
                                        const clone = document.body.cloneNode(true);
                                        clone.querySelectorAll(
                                            'script,style,nav,header,footer,aside'
                                        ).forEach(el => el.remove());
                                        return clone.innerText.substring(0, 5000);
                                    })()
                                """
                            }
                        }))
                        resp = await asyncio.wait_for(ws.recv(), timeout=5)
                        data = json.loads(resp)
                        text = data.get("result", {}).get("result", {}).get("value", "")
                        return text[:MAX_CONTENT_LENGTH] if text else None
                except Exception:
                    pass
        return None

    async def _summarize(self, title: str, text: str) -> str | None:
        """用 Cerebras 极速生成内容摘要。"""
        prompt = f"""请用中文简洁总结以下网页内容（≤100字），提取核心信息和关键要点。

标题：{title}
内容：
{text[:2000]}"""

        payload = json.dumps({
            "model": SUMMARY_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.1,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{LITELLM_URL}/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {LITELLM_KEY}",
                    "Content-Type": "application/json",
                },
            )
            # 绕过代理直连本地
            handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(handler)
            with opener.open(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[浏览器感知] 摘要生成失败: {e}")
            return None

    async def _send_to_letta(self, url: str, title: str, summary: str):
        """将内容摘要存入 Letta 归档记忆。"""
        text = (
            f"[{datetime.now().strftime('%Y-%m-%d')}] [浏览器感知] "
            f"用户浏览: {title}\n"
            f"URL: {url}\n"
            f"摘要: {summary}"
        )
        payload = json.dumps({
            "text": text,
            "tags": ["browser-sense", _domain(url)],
        }).encode()

        try:
            # 通过 Letta MCP 存储
            req = urllib.request.Request(
                "http://localhost:8283/v1/agents/agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea/archival",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(handler)
            with opener.open(req, timeout=10):
                self.db.mark_sent_to_letta(url)
        except Exception as e:
            print(f"[浏览器感知] Letta 写入失败: {e}")

    async def run(self):
        """主运行循环。"""
        if not await self.connect_cdp():
            return

        print(f"[浏览器感知] 启动监听（轮询间隔 {POLL_INTERVAL}s，"
              f"提取阈值 ≥{SCORE_THRESHOLD} 分）")

        while True:
            try:
                await self.poll_tabs()
                await self.check_scroll_state()
                await asyncio.sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[浏览器感知] 错误: {e}")
                await asyncio.sleep(10)

        # 退出时记录所有活跃标签
        for tab_id, tab in self.active_tabs.items():
            if not _should_ignore(tab["url"]):
                dwell = time.time() - tab["opened_at"]
                await self._on_page_leave(
                    tab["url"], tab["title"], dwell, tab.get("scrolled", False)
                )

    def report(self) -> str:
        """输出今日浏览报告。"""
        stats = self.db.get_today_stats()
        profile = self.db.get_browsing_profile()
        lines = [
            f"今日浏览 {stats['total_visits']} 页，提取 {stats['content_extracted']} 条",
            "常访域名: " + ", ".join(f"{d}({c})" for d, c in stats["top_domains"][:5]),
        ]
        if stats["recent_searches"]:
            lines.append("搜索: " + " | ".join(stats["recent_searches"][:5]))
        return "\n".join(lines)


# ── 给 brain.py 调用的接口 ──────────────────────────────
def get_browser_context() -> dict:
    """供 AGI Brain sense() 调用，返回浏览器上下文。"""
    try:
        db = BrowserMemoryDB()
        stats = db.get_today_stats()
        return {
            "browser_visits_today": stats["total_visits"],
            "content_extracted": stats["content_extracted"],
            "top_domains": stats["top_domains"][:3],
            "recent_searches": stats["recent_searches"][:3],
        }
    except Exception:
        return {"browser": "unavailable"}


async def test_connection():
    """测试 CDP 连接。"""
    engine = BrowserSenseEngine()
    ok = await engine.connect_cdp()
    if ok:
        print(f"[OK] CDP 连接成功，{len(engine.active_tabs)} 个标签页")
        for tid, tab in list(engine.active_tabs.items())[:5]:
            print(f"  • {tab['title'][:60]} — {tab['url'][:80]}")
    else:
        print("[FAIL] CDP 连接失败")
        print(f"  提示: 需要以调试模式启动浏览器:")
        print(f"  floorp --remote-debugging-port={CDP_PORT}")
        print(f"  或 google-chrome-stable --remote-debugging-port={CDP_PORT}")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        asyncio.run(test_connection())
    elif "--report" in sys.argv:
        db = BrowserMemoryDB()
        print(db.get_today_stats())
    elif "--profile" in sys.argv:
        db = BrowserMemoryDB()
        profile = db.get_browsing_profile()
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        asyncio.run(BrowserSenseEngine().run())
