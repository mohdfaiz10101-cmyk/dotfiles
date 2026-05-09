#!/usr/bin/env python3
"""Skill creator for Claude Code — CLI and stdin input modes.

Why: Automates SKILL.md scaffolding with optional LLM enhancement,
     eliminating manual boilerplate and ensuring consistent structure.
What: Parses name/content/tags, optionally calls DeepSeek for richer content,
      generates a SKILL.md with YAML front-matter, and triggers skill-sync.sh.
Test: python3 create-skill.py --name "test-skill" --content "test" --no-llm
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


SKILLS_DIR = Path.home() / ".claude" / "skills"
SYNC_SCRIPT = SKILLS_DIR / "skill-sync.sh"
LITELLM_URL = "http://localhost:4000/v1/chat/completions"
LITELLM_KEY = "sk-litellm-charlie-2026"
LITELLM_MODEL = "silicon/deepseek-v3.2"
LLM_TIMEOUT = 30


def slugify(name: str) -> str:
    """Convert name to lowercase-hyphen slug.

    Why: Ensures consistent directory names across skills.
    What: Lowercases, replaces non-alnum with hyphens, collapses duplicates.
    Test: slugify("My Skill #1!") -> "my-skill-1"
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Why: Supports both direct CLI usage and piping from other scripts.
    What: Returns namespace with name, content, category, tags, no_llm, description.
    Test: parse_args() with --name "x" --content "y" returns namespace.name=="x".
    """
    parser = argparse.ArgumentParser(description="Create a Claude Code skill")
    parser.add_argument("--name", required=True, help="Skill name (will be slugified)")
    parser.add_argument("--content", required=True, help="Skill content summary")
    parser.add_argument("--category", default="general", help="Skill category")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM enhancement")
    parser.add_argument("--description", default=None, help="Manual description")
    return parser.parse_args()


def read_stdin() -> dict[str, Any] | None:
    """Read JSON from stdin if data is available.

    Why: Enables piping structured data from other tools.
    What: Returns parsed dict or None if stdin is empty/not JSON.
    Test: echo '{"name":"x"}' | read_stdin() -> {"name": "x"}
    """
    if sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, EOFError):
        return None


def call_llm(content: str) -> dict[str, str]:
    """Call DeepSeek via LiteLLM to enhance skill content.

    Why: Auto-generates richer scene/steps/notes from a brief summary.
    What: Returns dict with scene, steps, notes keys. Falls back on failure.
    Test: Mock LiteLLM response, assert parsed keys exist.
    """
    prompt = (
        "Based on the following skill summary, generate structured content "
        "for a skill document. Return JSON with keys: "
        '"scene" (scenario description), "steps" (step-by-step instructions), '
        '"notes" (important caveats). Keep each field concise.\n\n'
        f"Summary: {content}"
    )
    payload = json.dumps({
        "model": LITELLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800,
    }).encode()

    req = Request(
        LITELLM_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(req, timeout=LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"]["content"]
        # Extract JSON from potential markdown code fences
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return json.loads(text)
    except (HTTPError, URLError, json.JSONDecodeError, KeyError, TimeoutError) as exc:
        print(f"[WARN] LLM enhancement failed ({exc}), using raw content", file=sys.stderr)
        return {
            "scene": content,
            "steps": "See content summary.",
            "notes": "Auto-generated from brief summary.",
        }


def build_skill_md(
    slug_name: str,
    description: str,
    category: str,
    tags_list: list[str],
    scene: str,
    steps: str,
    notes: str,
    version: str,
) -> str:
    """Build the full SKILL.md content string.

    Why: Centralizes template rendering in one place for consistency.
    What: Returns complete markdown with YAML front-matter and body sections.
    Test: Assert output starts with '---' and contains slug_name.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = slug_name.replace("-", " ").title()
    tags_yaml = ", ".join(tags_list) if tags_list else ""

    return f"""---
name: {slug_name}
description: "{description}"
user-invocable: false
version: "{version}"
category: {category}
tags: [{tags_yaml}]
effort: medium
auto-generated: true
created: {date_str}
---

# {title}

## 场景
{scene}

## 步骤
{steps}

## 注意事项
{notes}
"""


def get_existing_version(skill_dir: Path) -> str:
    """Read existing skill version, return next version bump.

    Why: Prevents overwriting skills silently — bumps version instead.
    What: Parses existing SKILL.md version and increments patch number.
    Test: skill with version "1.2.3" returns "1.2.4".
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return "1.0.0"
    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r'version:\s*"(\d+)\.(\d+)\.(\d+)"', text)
    if not match:
        return "1.0.0"
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return f"{major}.{minor}.{patch + 1}"


def run_sync() -> None:
    """Run skill-sync.sh after creation, non-blocking.

    Why: Keeps skill index up-to-date automatically.
    What: Calls sync script, warns on failure but does not abort.
    Test: Skill creation succeeds even if sync script is missing.
    """
    if not SYNC_SCRIPT.exists():
        print("[SKIP] skill-sync.sh not found, skipping sync")
        return
    try:
        result = subprocess.run(
            ["bash", str(SYNC_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("[OK] Skill sync completed")
        else:
            print(f"[WARN] Sync exited with code {result.returncode}")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"[WARN] Sync failed ({exc}), skill creation unaffected")


def main() -> int:
    """Entry point — parse input, optionally enhance via LLM, write SKILL.md.

    Why: Orchestrates the full skill creation pipeline.
    What: Returns 0 on success, 1 on failure.
    Test: main() with --name "test" --content "x" --no-llm creates directory.
    """
    # Merge CLI args with potential stdin JSON
    args = parse_args()
    stdin_data = read_stdin()

    name = stdin_data.get("name", args.name) if stdin_data else args.name
    content = stdin_data.get("content", args.content) if stdin_data else args.content
    category = stdin_data.get("category", args.category) if stdin_data else args.category
    tags_raw = stdin_data.get("tags", args.tags) if stdin_data else args.tags
    no_llm = args.no_llm
    description = (
        stdin_data.get("description", args.description)
        if stdin_data
        else args.description
    )

    slug_name = slugify(name)
    if not slug_name:
        print("[FAIL] Invalid skill name — slugified to empty string")
        return 1

    tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

    if description is None:
        description = (content[:97] + "...") if len(content) > 100 else content

    # LLM enhancement or fallback to raw content
    if no_llm:
        scene = content
        steps = "See content summary for details."
        notes = "Manually created — review and expand as needed."
    else:
        enhanced = call_llm(content)
        scene = enhanced.get("scene", content)
        steps = enhanced.get("steps", "See content summary.")
        notes = enhanced.get("notes", "Review and verify before use.")

    # Create skill directory and determine version
    skill_dir = SKILLS_DIR / slug_name
    version = get_existing_version(skill_dir)

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[FAIL] Cannot create directory {skill_dir}: {exc}")
        return 1

    # Build and write SKILL.md
    skill_md_content = build_skill_md(
        slug_name=slug_name,
        description=description,
        category=category,
        tags_list=tags_list,
        scene=scene,
        steps=steps,
        notes=notes,
        version=version,
    )

    skill_md_path = skill_dir / "SKILL.md"
    try:
        skill_md_path.write_text(skill_md_content, encoding="utf-8")
    except OSError as exc:
        print(f"[FAIL] Cannot write {skill_md_path}: {exc}")
        return 1

    action = "updated" if version != "1.0.0" else "created"
    print(f"[OK] Skill '{slug_name}' {action} (v{version}) -> {skill_md_path}")

    # Trigger sync (best-effort)
    run_sync()

    return 0


if __name__ == "__main__":
    sys.exit(main())
