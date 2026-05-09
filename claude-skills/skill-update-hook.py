#!/usr/bin/env python3
"""
Skill 更新 Hook — 检测 trigger pattern 并自动更新 Skill
用途：当用户遇到特定问题时，自动更新相关 skill 的 troubleshooting 部分
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess

SKILLS_DIR = Path.home() / ".claude" / "skills"

def detect_trigger(user_message, skill_triggers):
    """检查用户消息是否匹配 skill 的 trigger patterns"""
    message_lower = user_message.lower()
    for pattern in skill_triggers:
        try:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        except re.error:
            # 忽略不合法的正则表达式
            pass
    return False

def append_troubleshooting(skill_md, new_entry):
    """
    将新的 troubleshooting 条目追加到 SKILL.md

    返回值：
        True: 成功追加
        False: 未找到 Troubleshooting 部分或追加失败
    """
    try:
        content = skill_md.read_text(encoding='utf-8')

        # 查找 Troubleshooting 部分
        if "## Troubleshooting" not in content:
            # 如果不存在，在末尾添加
            if content.endswith('\n'):
                content += f"\n## Troubleshooting\n\n{new_entry}\n"
            else:
                content += f"\n\n## Troubleshooting\n\n{new_entry}\n"
            skill_md.write_text(content, encoding='utf-8')
            return True

        # 查找 Troubleshooting 部分的位置
        troubleshooting_idx = content.find("## Troubleshooting")
        after_troubleshooting = content[troubleshooting_idx:]

        # 查找下一个 ## 标题
        next_section = re.search(r'\n## ', after_troubleshooting[2:])  # 跳过第一个 ##

        if next_section:
            # 有其他部分，在 Troubleshooting 末尾插入
            insert_pos = troubleshooting_idx + next_section.start() + 2
        else:
            # 没有其他部分，追加到末尾
            insert_pos = len(content)

        # 插入新条目
        new_content = (
            content[:insert_pos] +
            f"\n\n{new_entry}\n" +
            content[insert_pos:]
        )

        skill_md.write_text(new_content, encoding='utf-8')
        return True
    except Exception as e:
        print(f"[ERROR] Failed to append troubleshooting: {e}", file=sys.stderr)
        return False

def find_matching_skill(user_message):
    """
    找到与用户消息匹配的 skill

    返回值：
        (skill_dir, metadata) 或 (None, None)
    """
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
            continue

        skill_json = skill_dir / "skill.json"
        if not skill_json.exists():
            continue

        try:
            with open(skill_json, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            triggers = metadata.get("triggers", [])
            if detect_trigger(user_message, triggers):
                return skill_dir, metadata
        except Exception:
            continue

    return None, None

def generate_troubleshooting_entry(skill_name, user_message, context=""):
    """
    生成 troubleshooting 条目

    注意：实际应用中，这里应该调用 LLM 生成更智能的条目
    当前实现是简单的模板生成
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"### Issue (Auto-detected @ {timestamp})\n\n"
    entry += f"**User Report:** {user_message[:100]}\n\n"
    entry += "**Symptoms:**\n"
    entry += f"- {user_message[:50]}\n"
    entry += "- Issue occurred during skill execution\n\n"
    entry += "**Resolution:**\n"
    entry += "- [TODO] Add specific resolution steps\n"
    entry += "- Check related logs and error messages\n"
    entry += f"- See related skills for context (if available)\n"

    if context:
        entry += f"\n**Additional Context:**\n{context}\n"

    return entry

def commit_to_git(skill_dir, skill_name):
    """将 skill 变更提交到 Git"""
    try:
        cwd = SKILLS_DIR
        # 只提交该 skill 目录的变更
        subprocess.run(
            ["git", "add", f"{skill_name}/"],
            cwd=cwd,
            capture_output=True,
            timeout=5
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"feat({skill_name}): auto-update troubleshooting @ {datetime.now().isoformat()}"],
            cwd=cwd,
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[WARN] Git commit failed: {e}", file=sys.stderr)
        return False

def main():
    """主程序：检测 trigger 并自动更新 skill"""
    if len(sys.argv) < 2:
        print("Usage: skill-update-hook.py <user_message> [context]", file=sys.stderr)
        sys.exit(1)

    user_message = " ".join(sys.argv[1:])
    context = ""

    # 查找匹配的 skill
    skill_dir, metadata = find_matching_skill(user_message)

    if not skill_dir:
        print(f"[INFO] No matching skill found for: {user_message[:50]}")
        sys.exit(0)

    skill_name = metadata.get("name", skill_dir.name)
    auto_update_config = metadata.get("auto_update", {})

    # 检查 auto_update 是否启用
    if not auto_update_config.get("enabled", False):
        print(f"[SKIP] Auto-update disabled for {skill_name}")
        sys.exit(0)

    # 检查是否应该追加 troubleshooting
    update_strategy = auto_update_config.get("update_strategy", "")
    if update_strategy != "append_troubleshooting":
        print(f"[SKIP] Update strategy '{update_strategy}' not supported")
        sys.exit(0)

    print(f"[INFO] Auto-updating skill: {skill_name}")
    print(f"[INFO] User message: {user_message[:100]}")

    # 生成 troubleshooting 条目
    entry = generate_troubleshooting_entry(skill_name, user_message, context)

    # 追加到 SKILL.md
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"[ERROR] SKILL.md not found: {skill_md}", file=sys.stderr)
        sys.exit(1)

    if append_troubleshooting(skill_md, entry):
        print(f"[OK] Appended troubleshooting entry to {skill_name}")

        # 提交到 Git
        if commit_to_git(skill_dir, skill_dir.name):
            print(f"[OK] Committed changes to Git")
        else:
            print(f"[WARN] Git commit failed (skill file updated but not committed)")
    else:
        print(f"[ERROR] Failed to append troubleshooting entry", file=sys.stderr)
        sys.exit(1)

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Skill Auto-Update Summary:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Skill: {skill_name}")
    print(f"File: {skill_md}")
    print(f"Entry: troubleshooting (auto-detected)")
    print()

if __name__ == "__main__":
    main()
