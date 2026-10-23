#!/usr/bin/env python3
"""
Restore/refresh local Hermes overrides after Hermes upgrades.
This script verifies file hashes before restoring to avoid unnecessary overwrites.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

HOME = Path.home()
HERMES = HOME / ".hermes"
WORKSPACE = Path("/var/home/charlie/workspace")
SOURCE_COMPRESS = WORKSPACE / "auto_compress_heavy_sessions.py"
SOURCE_EXTRACT = WORKSPACE / "extract_session_skills.py"
SOURCE_RENAME = WORKSPACE / "auto_rename_sessions.py"
DEST_COMPRESS = HERMES / "scripts" / "auto_compress_heavy_sessions.py"
DEST_EXTRACT = HERMES / "skills" / "hermes-session-compactor" / "scripts" / "extract_session_skills.py"
DEST_RENAME = HERMES / "skills" / "hermes-session-compactor" / "scripts" / "auto_rename_sessions.py"
SKILL_MD = HERMES / "skills" / "hermes-session-compactor" / "SKILL.md"
CRON_JOBS = HERMES / "cron" / "jobs.json"
COMPRESS_JOB_ID = "809292ce4226"
MANAGED_FILES = [
    DEST_COMPRESS,
    DEST_EXTRACT,
    DEST_RENAME,
]


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".bak.override")
    shutil.copy2(path, backup)
    return backup


def restore_if_needed(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)
        return True
    src_hash = file_sha256(src)
    dst_hash = file_sha256(dst)
    if src_hash and dst_hash and src_hash != dst_hash:
        backup_file(dst)
        shutil.copy2(src, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)
        return True
    return False


def ensure_cron_job() -> bool:
    if not CRON_JOBS.exists():
        return False
    try:
        jobs = json.loads(CRON_JOBS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        jobs = []
    if not isinstance(jobs, list):
        jobs = []
    target = next((j for j in jobs if isinstance(j, dict) and j.get("job_id") == COMPRESS_JOB_ID), None)
    expected = {
        "job_id": COMPRESS_JOB_ID,
        "name": "自动压缩重型 Hermes 会话",
        "skills": [],
        "prompt_preview": "",
        "model": None,
        "provider": None,
        "base_url": None,
        "schedule": "0 */6 * * *",
        "repeat": "forever",
        "deliver": "local",
        "enabled_toolsets": [],
        "no_agent": True,
        "script": "auto_compress_heavy_sessions.py --compress",
        "workdir": "/var/home/charlie/workspace",
    }
    if target == expected:
        return False
    backup_file(CRON_JOBS)
    if target:
        # Update existing job in-place.
        target.update(expected)
    else:
        jobs = [j for j in jobs if not (isinstance(j, dict) and j.get("job_id") == COMPRESS_JOB_ID)]
        jobs.append(expected)
    CRON_JOBS.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def ensure_extract_script() -> bool:
    if not DEST_EXTRACT.exists():
        return False
    text = DEST_EXTRACT.read_text(encoding="utf-8")
    orig = text
    if "HERMES_ALLOW_UNATTENDED_SESSION_EXTRACT=1" not in text:
        text = text.replace(
            "parser.add_argument('mode'",
            "os.environ.setdefault('HERMES_ALLOW_UNATTENDED_SESSION_EXTRACT','0')\n"
            "    if 'auto' in sys.argv[1:]:\n"
            "        if os.environ.get('HERMES_ALLOW_UNATTENDED_SESSION_EXTRACT') != '1':\n"
            "            print('[BLOCK] auto mode requires HERMES_ALLOW_UNATTENDED_SESSION_EXTRACT=1', file=sys.stderr)\n"
            "            sys.exit(2)\n"
            "    parser.add_argument('mode'",
        )
    if "# UNVERIFIED AUTO-EXTRACTION" not in text:
        text = text.replace(
            "# Auto policy",
            "# UNVERIFIED AUTO-EXTRACTION\n"
            "# Output was generated without human review.\n"
            "# Only items with evidence are included.\n"
            "# Review before writing to skills/memory/scripts.\n"
            "\n"
            "# Auto policy",
            1,
        )
    if text != orig:
        backup_file(DEST_EXTRACT)
        DEST_EXTRACT.write_text(text, encoding="utf-8")
        return True
    return False


def ensure_rename_script() -> bool:
    if not DEST_RENAME.exists():
        return False
    text = DEST_RENAME.read_text(encoding="utf-8")
    orig = text
    if "def has_recent_file_activity(sid, max_seconds=86400):" not in text:
        text = text.replace(
            "def has_new_activity(item):",
            "def has_recent_file_activity(sid, max_seconds=86400):\n"
            "    now = datetime.now(timezone.utc).timestamp()\n"
            "    for p in [\n"
            "        os.path.join(BASE, f'{sid}.json'),\n"
            "        os.path.join(BASE, '_archive_old', f'{sid}.json'),\n"
            "    ]:\n"
            "        if os.path.exists(p) and (now - os.path.getmtime(p)) < max_seconds:\n"
            "            return True\n"
            "    return False\n"
            "\n"
            "\n"
            "def has_new_activity(item):",
        )
    if '        if item.get("pinned"):\n            continue\n        title = item.get(\'title\')' in text:
        text = text.replace(
            '        if item.get("pinned"):\n            continue\n        title = item.get(\'title\')',
            '        if item.get("pinned"):\n            continue\n        if has_recent_file_activity(sid, max_seconds=86400):\n            continue\n        title = item.get(\'title\'',
        )
    if text != orig:
        backup_file(DEST_RENAME)
        DEST_RENAME.write_text(text, encoding="utf-8")
        return True
    return False


def ensure_skill_doc() -> bool:
    if not SKILL_MD.exists():
        return False
    text = SKILL_MD.read_text(encoding="utf-8")
    orig = text
    needle = "auto_rename_sessions.py 现在会跳过最近 24 小时内仍有文件活跃的会话"
    if needle not in text:
        text = text.replace(
            "- 自动模式不删除原会话，只改名 + 生成 seed\n- 若用户要求，再额外执行归档\n",
            "- 自动模式不删除原会话，只改名 + 生成 seed\n- 若用户要求，再额外执行归档\n"
            "- `auto_rename_sessions.py` 现在会跳过最近 24 小时内仍有文件活跃的会话，避免把正在使用的会话改名\n",
        )
    if text != orig:
        backup_file(SKILL_MD)
        SKILL_MD.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    changes = []
    changes.append(("auto_compress_heavy_sessions.py", restore_if_needed(SOURCE_COMPRESS, DEST_COMPRESS)))
    changes.append(("extract_session_skills.py", ensure_extract_script()))
    changes.append(("auto_rename_sessions.py", ensure_rename_script()))
    changes.append(("SKILL.md", ensure_skill_doc()))
    changes.append(("cron_job", ensure_cron_job()))
    for name, changed in changes:
        print(f"{name}: {'restored' if changed else 'noop/ok'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
