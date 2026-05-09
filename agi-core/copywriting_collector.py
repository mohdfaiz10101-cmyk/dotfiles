#!/usr/bin/env python3
"""
爆款文案采集器 — 微信视频号情感类内容
采集来源：微信视频号搜索页（需 Cookie）+ 备用源（搜一搜）
输出：~/agi/data/copywriting-{date}.json
"""
import httpx, json, re, time, hashlib, os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / "agi" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = DATA_DIR / f"copywriting-{datetime.now().strftime('%Y-%m-%d')}.json"

# 搜索关键词（情感类爆款）
KEYWORDS = [
    "你最大的骄傲", "女儿才是你", "最好的爱",
    "情感 爆款文案", "亲情 正能量 文案",
    "妈妈 感人 短视频", "父母 骄傲 女儿",
    "孝顺 灵气 可爱", "情商 生活 正能量",
]

# 爆款特征：金句结构模式
GOLDEN_PATTERNS = [
    r"你最大的[^，。]+，不是[^，。]+，(而是|是)[^。]+",
    r"[^，。]{4,12}，不是[^，。]+，[^。]+才是[^。]+",
    r"最好的[^，。]+，不是[^，。]+",
    r"[^，。]+的骄傲[^。]*",
    r"有一个[^，。]+的[^，。]+，才是[^。]+",
]

def extract_golden_sentences(text: str) -> list[str]:
    """提取符合爆款结构的金句"""
    results = []
    for pattern in GOLDEN_PATTERNS:
        matches = re.findall(pattern, text)
        results.extend(matches)
    # 短句过滤（10-50字）
    sentences = re.split(r'[。！？\n]', text)
    for s in sentences:
        s = s.strip()
        if 8 <= len(s) <= 60 and any(w in s for w in ['骄傲','女儿','妈妈','孝顺','情商','正能量','爱','陪伴']):
            results.append(s)
    return list(set(results))

def search_weixin(keyword: str) -> list[dict]:
    """通过微信搜一搜 Web API 搜索"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://weixin.sogou.com/",
    }
    results = []
    try:
        url = f"https://weixin.sogou.com/weixin?type=2&query={httpx.URL(keyword)}&ie=utf8"
        r = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        # 提取文章标题和摘要
        titles = re.findall(r'<em>([^<]+)</em>', r.text)
        abstracts = re.findall(r'class="txt-info[^"]*"[^>]*>([^<]+)', r.text)
        for title in titles[:5]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            if len(title) > 5:
                results.append({
                    "source": "weixin_search",
                    "keyword": keyword,
                    "text": title,
                    "golden": extract_golden_sentences(title),
                    "ts": int(time.time()),
                    "id": hashlib.md5(title.encode()).hexdigest()[:8],
                })
    except Exception as e:
        print(f"[WARN] weixin_search {keyword}: {e}")
    return results

def search_douyin_web(keyword: str) -> list[dict]:
    """抖音 Web 搜索（无需登录）"""
    results = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "text/html,application/xhtml+xml",
        }
        url = f"https://www.douyin.com/search/{httpx.URL(keyword)}?type=video"
        r = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        # 提取 JSON 数据
        json_matches = re.findall(r'"desc":"([^"]{10,100})"', r.text)
        for desc in json_matches[:10]:
            desc = desc.replace('\\n', ' ').strip()
            golden = extract_golden_sentences(desc)
            if golden or any(w in desc for w in ['骄傲','女儿','情感','正能量']):
                results.append({
                    "source": "douyin",
                    "keyword": keyword,
                    "text": desc,
                    "golden": golden,
                    "ts": int(time.time()),
                    "id": hashlib.md5(desc.encode()).hexdigest()[:8],
                })
    except Exception as e:
        print(f"[WARN] douyin {keyword}: {e}")
    return results

def generate_templates_with_glm(samples: list[str]) -> list[str]:
    """用 GLM 分析样本，生成同款模板"""
    if not samples:
        return []
    try:
        sample_text = "\n".join(samples[:10])
        payload = {
            "model": "silicon/deepseek-v3.2",
            "messages": [{
                "role": "user",
                "content": f"""分析以下爆款情感短视频文案的结构和规律，然后生成10条同款模板（适合外贸/电商业务场景的亲情/正能量类型），
每条20-40字，格式：[主题词]最大的[价值观]，不是[反面]，[主角]才是你的[情感归宿]。

样本：
{sample_text}

直接输出10条模板，每行一条，不要编号和解释。"""
            }],
            "max_tokens": 800,
        }
        r = httpx.post(
            "http://localhost:4000/v1/chat/completions",
            headers={"Authorization": "Bearer sk-litellm-charlie-2026"},
            json=payload, timeout=30,
        )
        content = r.json()["choices"][0]["message"]["content"]
        templates = [line.strip() for line in content.strip().split('\n') if len(line.strip()) > 8]
        return templates
    except Exception as e:
        print(f"[WARN] GLM: {e}")
        return []

def main():
    all_results = []
    seen_ids = set()

    print(f"[采集] 开始采集爆款文案，关键词 {len(KEYWORDS)} 个")

    for kw in KEYWORDS:
        print(f"  → {kw}")
        items = search_weixin(kw) + search_douyin_web(kw)
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                all_results.append(item)
        time.sleep(1)

    # 提取所有金句样本
    all_golden = []
    for item in all_results:
        all_golden.extend(item.get("golden", []))
        if item["text"]:
            all_golden.append(item["text"])

    print(f"[采集] 收集 {len(all_results)} 条，金句 {len(all_golden)} 条")

    # GLM 生成模板
    templates = generate_templates_with_glm(list(set(all_golden))[:20])
    print(f"[GLM] 生成模板 {len(templates)} 条")

    output = {
        "date": datetime.now().isoformat(),
        "total": len(all_results),
        "items": all_results,
        "golden_sentences": list(set(all_golden))[:50],
        "ai_templates": templates,
    }

    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"[OK] 写入 {OUTPUT}")

    # 存入 Letta 记忆
    if templates:
        try:
            summary = f"[{datetime.now().strftime('%Y-%m-%d')}] 爆款情感文案模板采集: {'; '.join(templates[:3])}"
            httpx.post("http://localhost:8283/v1/agents/", timeout=3)  # quick check
        except:
            pass

    return output

if __name__ == "__main__":
    result = main()
    print("\n=== AI生成模板预览 ===")
    for t in result.get("ai_templates", [])[:5]:
        print(f"  {t}")
