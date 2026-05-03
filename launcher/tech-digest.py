#!/usr/bin/env python3
"""Tech Digest Pipeline — GitHub Trending / arXiv / Hacker News."""

import argparse
import concurrent.futures
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# ── Constants ──────────────────────────────────────────────────────

PROXY = os.environ.get(
    "HTTPS_PROXY", os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")
)
ROADMAP_PATH = os.path.expanduser(
    "~/.claude/projects/-home-charlie/memory/ideas-roadmap.md"
)

DEFAULT_KEYWORDS = {
    "github": ["nixos", "ai", "rust", "llm", "agent", "terminal", "wayland"],
    "arxiv": ["large language model", "reinforcement learning", "agent"],
    "hn": ["ai", "rust", "linux", "open source", "programming"],
}

GITHUB_API = "https://api.github.com/search/repositories"
ARXIV_API = "http://export.arxiv.org/api/query"
HN_API = "https://hacker-news.firebaseio.com/v0"

USER_AGENT = "tech-digest/1.0"
OLLAMA_URL = "http://localhost:11434/api/generate"
TRANSLATE_MODEL = os.environ.get("TRANSLATE_MODEL", "qwen3:8b-nothink")


# ── Translation ────────────────────────────────────────────────────


def translate_batch(texts, timeout=60):
    """Translate a list of texts to Chinese via Ollama in one call."""
    if not texts:
        return []
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts) if t)
    if not numbered:
        return texts
    prompt = (
        "Translate each line below to Chinese. "
        "Keep the number prefix. Output ONLY translations, nothing else.\n\n" + numbered
    )
    payload = json.dumps(
        {
            "model": TRANSLATE_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    direct_opener = build_opener(use_proxy=False)
    try:
        with direct_opener.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        raw = data.get("response", "").strip()
        results = {}
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = __import__("re").match(r"^(\d+)\.\s*(.+)", line)
            if m:
                results[int(m.group(1))] = m.group(2).strip()
        translated = []
        for i, orig in enumerate(texts):
            translated.append(results.get(i + 1, orig))
        return translated
    except Exception as e:
        print(f"[WARN] Translation failed: {e}", file=sys.stderr)
        return texts


def translate_items(items, fields=("summary",)):
    """Translate specified fields in a list of item dicts."""
    texts = []
    indices = []
    for idx, item in enumerate(items):
        for field in fields:
            val = item.get(field, "")
            if val and val != "—":
                texts.append(val)
                indices.append((idx, field))
    if not texts:
        return items
    translated = translate_batch(texts)
    for (idx, field), val in zip(indices, translated):
        items[idx][field] = val
    return items


# ── Network helpers ────────────────────────────────────────────────


def build_opener(use_proxy=True):
    """Build urllib opener with optional proxy."""
    handlers = [urllib.request.HTTPSHandler()]
    if use_proxy and PROXY:
        handlers.append(
            urllib.request.ProxyHandler(
                {
                    "http": PROXY,
                    "https": PROXY,
                }
            )
        )
    return urllib.request.build_opener(*handlers)


def fetch_json(url, opener, timeout=15):
    """Fetch URL and return parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_xml(url, opener, timeout=20):
    """Fetch URL and return parsed XML ElementTree."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=timeout) as resp:
        return ET.parse(resp)


# ── GitHub Trending ────────────────────────────────────────────────


def fetch_github(keywords, opener, days=7):
    """Fetch trending repos created in the last N days."""
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    # GitHub API limits query complexity — use top 3 keywords
    top_kw = keywords[:3]
    query = "+OR+".join(top_kw)
    q = f"pushed%3A%3E{since}+stars%3A%3E100+%28{query}%29"
    url = f"{GITHUB_API}?q={q}&sort=stars&order=desc&per_page=30"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    }
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    items = []
    for repo in data.get("items", []):
        items.append(
            {
                "title": repo["full_name"],
                "url": repo["html_url"],
                "summary": (repo.get("description") or "")[:120],
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language") or "—",
                "date": repo.get("created_at", "")[:10],
                "source": "github",
            }
        )
    translate_items(items, fields=("summary",))
    return items


# ── arXiv Papers ───────────────────────────────────────────────────


def fetch_arxiv(keywords, opener):
    """Fetch recent arXiv papers matching keywords."""
    # arXiv works better without proxy
    direct_opener = build_opener(use_proxy=False)

    query_parts = [f'all:"{kw}"' for kw in keywords]
    search_query = " OR ".join(query_parts)
    url = (
        f"{ARXIV_API}?search_query={urllib.request.quote(search_query)}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results=20"
    )

    time.sleep(3)  # polite pooling
    tree = fetch_xml(url, direct_opener, timeout=25)
    root = tree.getroot()

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    items = []
    for entry in root.findall("atom:entry", ns):
        title = " ".join(entry.find("atom:title", ns).text.split())
        summary = " ".join(entry.find("atom:summary", ns).text.split())[:150]

        # get PDF link
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
                break
        if not pdf_url:
            pdf_url = entry.find("atom:id", ns).text

        published = entry.find("atom:published", ns).text[:10]

        items.append(
            {
                "title": title,
                "url": pdf_url,
                "summary": summary,
                "date": published,
                "source": "arxiv",
            }
        )
    translate_items(items, fields=("title", "summary"))
    return items


# ── Hacker News ────────────────────────────────────────────────────


def fetch_hn(keywords, opener, top_n=50):
    """Fetch top HN stories and filter by keywords."""
    data = fetch_json(f"{HN_API}/topstories.json", opener)
    ids = data[:top_n]

    items = []
    for story_id in ids:
        try:
            story = fetch_json(f"{HN_API}/item/{story_id}.json", opener)
        except Exception:
            continue
        if not story or story.get("type") != "story" or not story.get("url"):
            continue

        items.append(
            {
                "title": story.get("title", ""),
                "url": story.get("url", ""),
                "summary": "",
                "score": story.get("score", 0),
                "comments": story.get("descendants", 0),
                "by": story.get("by", ""),
                "source": "hn",
            }
        )
    translate_items(items, fields=("title",))
    return items


# ── Scoring & formatting ──────────────────────────────────────────


def score_results(items, keywords):
    """Score items by keyword relevance and return top N."""
    kw_lower = [k.lower() for k in keywords]
    for item in items:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        item["relevance"] = sum(1 for kw in kw_lower if kw in text)
    items.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    return items


def truncate(text, max_len=60):
    """Truncate text with ellipsis."""
    text = text.replace("|", " ").replace("\n", " ").strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def format_markdown(results, date_str, limit=15):
    """Generate structured Markdown report from source results dict."""
    lines = [
        "",
        "---",
        "",
        f"## Tech Digest — {date_str}",
        "",
    ]

    source_config = {
        "github": {
            "title": "GitHub 热门项目",
            "header": "| # | 仓库 | 星标 | 语言 | 摘要 |",
            "separator": "|---|------|-------|------|---------|",
            "row": lambda i, it: (
                f"| {i} | [{truncate(it['title'], 40)}]({it['url']}) "
                f"| {it.get('stars', 0)} "
                f"| {it.get('language', '—')} "
                f"| {truncate(it.get('summary', ''))} |"
            ),
            "empty": "| — | (暂无数据) | | | |",
        },
        "arxiv": {
            "title": "arXiv 论文",
            "header": "| # | 标题 | 日期 | 摘要 |",
            "separator": "|---|-------|------|---------|",
            "row": lambda i, it: (
                f"| {i} | [{truncate(it['title'], 50)}]({it['url']}) "
                f"| {it.get('date', '—')} "
                f"| {truncate(it.get('summary', ''), 80)} |"
            ),
            "empty": "| — | (暂无数据) | | |",
        },
        "hn": {
            "title": "Hacker News",
            "header": "| # | 标题 | 得分 | 评论 |",
            "separator": "|---|-------|-------|----------|",
            "row": lambda i, it: (
                f"| {i} | [{truncate(it['title'], 55)}]({it['url']}) "
                f"| {it.get('score', 0)} "
                f"| {it.get('comments', 0)} |"
            ),
            "empty": "| — | (暂无数据) | | |",
        },
    }

    for src_name, cfg in source_config.items():
        items = results.get(src_name, [])
        if not items and src_name not in results:
            continue  # skip sources not requested
        lines.append(f"### {cfg['title']}")
        lines.append("")
        lines.append(cfg["header"])
        lines.append(cfg["separator"])
        for i, item in enumerate(items[:limit], 1):
            lines.append(cfg["row"](i, item))
        if not items:
            lines.append(cfg["empty"])
        lines.append("")

    return "\n".join(lines)


def append_report(markdown, path):
    """Append report to roadmap file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(markdown)
    print(f"[OK] Report appended → {path}")


# ── CLI ────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(description="Tech Digest Pipeline")
    parser.add_argument(
        "--source",
        choices=["github", "arxiv", "hn", "all"],
        default="all",
        help="Data source(s) to fetch (default: all)",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="Comma-separated keywords (overrides defaults for all sources)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=15,
        help="Max items per source (default: 15)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=ROADMAP_PATH,
        help="Output file path",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Merge keywords
    if args.keywords:
        kw_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
        keywords = {src: kw_list for src in ("github", "arxiv", "hn")}
    else:
        keywords = DEFAULT_KEYWORDS

    sources_to_run = (
        ["github", "arxiv", "hn"] if args.source == "all" else [args.source]
    )

    opener = build_opener(use_proxy=True)
    results = {}

    fetchers = {
        "github": fetch_github,
        "arxiv": fetch_arxiv,
        "hn": fetch_hn,
    }

    for name in sources_to_run:
        print(f"[RUNNING] Fetching {name}...", file=sys.stderr)
        try:
            raw = fetchers[name](keywords[name], opener)
            results[name] = score_results(raw, keywords[name])
            print(f"[OK] {name}: {len(results[name])} items", file=sys.stderr)
        except Exception as e:
            print(f"[FAILED] {name}: {e}", file=sys.stderr)
            results[name] = []

    report = format_markdown(
        results,
        datetime.date.today().isoformat(),
        limit=args.limit,
    )
    append_report(report, args.output)

    # Write JSON output for 3000 dashboard
    import pathlib

    json_out = pathlib.Path.home() / "Desktop" / "巡检报告" / "tech-digest-latest.json"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_items = []
    for src, items in results.items():
        for item in items[:10]:
            json_items.append(
                {
                    "title": item.get("title", ""),
                    "summary": item.get("title", "")[:100],
                    "source": src,
                    "ts": datetime.date.today().isoformat(),
                }
            )
    json_out.write_text(
        json.dumps(
            {"title": "Tech Digest", "items": json_items[:30]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
