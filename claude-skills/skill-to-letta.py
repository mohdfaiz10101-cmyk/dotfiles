#!/usr/bin/env python3
"""
将 Skill 内容索引到 Letta MCP，支持语义检索
用途：将 SKILL.md 文件的内容写入 Letta 的归档记忆，使其支持语义搜索
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback

LETTA_API_URL = os.getenv("LETTA_API_URL", "http://localhost:8283")
LETTA_API_KEY = os.getenv("LETTA_API_KEY", "letta")
# code-assistant agent ID (from system context)
CODE_ASSISTANT_AGENT_ID = "agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea"
SKILLS_DIR = Path.home() / ".claude" / "skills"

def make_request(method, endpoint, data=None):
    """通过 urllib 进行 HTTP 请求（避免依赖 requests）"""
    try:
        from urllib.request import Request, urlopen
        from urllib.error import URLError
        import urllib.parse

        url = f"{LETTA_API_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {LETTA_API_KEY}",
            "Content-Type": "application/json",
        }

        if data:
            data = json.dumps(data).encode('utf-8')

        req = Request(url, data=data, headers=headers, method=method)
        with urlopen(req, timeout=15) as resp:
            response_data = resp.read().decode('utf-8')
            return json.loads(response_data) if response_data else {}
    except Exception as e:
        print(f"[ERROR] HTTP request failed: {e}", file=sys.stderr)
        return None

def letta_store(agent_id, text, tags):
    """将文本存储到 Letta 的归档记忆"""
    payload = {
        "text": text,
        "tags": tags
    }
    endpoint = f"/v1/agents/{agent_id}/archival-memory"
    result = make_request("POST", endpoint, payload)
    return result is not None

def letta_search(agent_id, query, limit=5):
    """从 Letta 的归档记忆中搜索（可选，用于验证）"""
    endpoint = f"/v1/agents/{agent_id}/archival-memory/search"
    payload = {"query": query, "limit": limit}
    result = make_request("POST", endpoint, payload)
    return result

def read_skill_metadata(skill_dir):
    """读取 skill.json 元数据"""
    skill_json = skill_dir / "skill.json"
    if skill_json.exists():
        try:
            with open(skill_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to read {skill_json}: {e}", file=sys.stderr)
            return {}
    return {}

def read_skill_content(skill_dir):
    """读取 SKILL.md 的前 2000 个字符作为摘要"""
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
                return content[:2000]  # 取前 2000 字符
        except Exception as e:
            print(f"[WARN] Failed to read {skill_md}: {e}", file=sys.stderr)
            return ""
    return ""

def index_skill(skill_dir, agent_id=CODE_ASSISTANT_AGENT_ID):
    """
    将单个 skill 索引到 Letta

    返回值：
        True: 索引成功
        False: 索引失败
        None: 跳过（无效的 skill）
    """
    skill_name = skill_dir.name

    # 跳过特殊目录
    if skill_name.startswith('.') or skill_name.startswith('_'):
        return None

    metadata = read_skill_metadata(skill_dir)
    content = read_skill_content(skill_dir)

    # 如果既没有 skill.json 也没有 SKILL.md，跳过
    if not metadata and not content:
        return None

    # 构建索引文本
    skill_name_display = metadata.get("name", skill_name)
    version = metadata.get("version", "unknown")
    description = metadata.get("description", "No description")

    # 摘要：[Skill:名称 v版本] 描述 + 前 500 字符
    summary = f"[Skill:{skill_name_display} v{version}] {description}\n\n{content[:500]}"

    # 构建标签：skill, skill_name, 以及 triggers（最多 7 个标签）
    triggers = metadata.get("triggers", [])
    tags = ["skill", skill_name_display]
    if isinstance(triggers, list):
        tags.extend(triggers[:5])  # 最多添加 5 个 trigger

    # 限制标签数量
    tags = tags[:7]

    # 存储到 Letta
    success = letta_store(agent_id, summary, tags)

    if success:
        print(f"[OK] Indexed skill: {skill_name_display} (v{version})")
        return True
    else:
        print(f"[FAILED] Failed to index skill: {skill_name_display}")
        return False

def main():
    """主程序：遍历所有 skills 并索引"""
    if not SKILLS_DIR.exists():
        print(f"[ERROR] Skills directory not found: {SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Indexing skills from: {SKILLS_DIR}")
    print(f"[INFO] Letta API: {LETTA_API_URL}")
    print(f"[INFO] Agent ID: {CODE_ASSISTANT_AGENT_ID}")
    print()

    indexed = 0
    failed = 0
    skipped = 0

    # 遍历所有 skill 目录
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue

        try:
            result = index_skill(skill_dir)
            if result is True:
                indexed += 1
            elif result is False:
                failed += 1
            else:  # None
                skipped += 1
        except Exception as e:
            print(f"[ERROR] Exception processing {skill_dir.name}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            failed += 1

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Letta Indexing Summary:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Indexed: {indexed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print()

    # 如果有失败，返回非零退出码
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
