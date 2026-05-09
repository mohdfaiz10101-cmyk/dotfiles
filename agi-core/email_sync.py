#!/usr/bin/env python3
"""Email IMAP sync — fetch emails, match entities, attach events to Context Graph.

Flow: IMAP server → fetch recent → extract sender/subject/body → entity_match → event_attach
"""

import argparse, json, os, sys
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parseaddr
from pathlib import Path

try:
    import aioimaplib
    import asyncio
except ImportError:
    print("[FAIL] 需要 aioimaplib: pip install aioimaplib", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from context_graph import entity_match, event_attach, entity_search

CHROMA_URL = os.environ.get("CHROMA_URL", "http://localhost:8000")
LITELLM_URL = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-charlie-2026")
SYNC_STATE = Path.home() / "agi" / "email_sync_state.json"

DEFAULT_CONFIG = {
    "host": os.environ.get("IMAP_HOST", ""),
    "port": int(os.environ.get("IMAP_PORT", "993")),
    "user": os.environ.get("IMAP_USER", ""),
    "password": os.environ.get("IMAP_PASS", ""),
    "folders": ["INBOX"],
    "max_per_sync": 50,
}


def _decode_str(s):
    if not s:
        return ""
    decoded = decode_header(s)
    parts = []
    for data, charset in decoded:
        if isinstance(data, bytes):
            parts.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(data)
    return "".join(parts)


def _load_state() -> dict:
    if SYNC_STATE.exists():
        return json.loads(SYNC_STATE.read_text())
    return {"last_uid": {}, "synced_ids": []}


def _save_state(state: dict):
    SYNC_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


async def fetch_emails(
    config: dict, folder: str = "INBOX", limit: int = 50
) -> list[dict]:
    if not config.get("host") or not config.get("user"):
        return []
    client = aioimaplib.IMAP4_SSL(host=config["host"], port=config.get("port", 993))
    await client.wait_hello_from_server()
    await client.login(config["user"], config["password"])
    await client.select(folder)

    state = _load_state()
    last_uid = state.get("last_uid", {}).get(folder, "0")

    _, data = await client.uid(
        "fetch",
        f"{last_uid}:*",
        "(UID ENVELOPE BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE)])",
    )
    emails = []
    current_uid = None

    for item in data:
        if isinstance(item, bytes) and item.strip():
            line = item.decode("utf-8", errors="replace").strip()
            if line.startswith("* "):
                continue
            if "UID" in line:
                try:
                    uid_start = line.split("UID")[1].strip().split()[0]
                    current_uid = uid_start.rstrip(")")
                except (IndexError, ValueError):
                    pass
            elif current_uid and (
                "From:" in line or "Subject:" in line or "Date:" in line
            ):
                header_dict = {}
                for hline in line.split("\r\n"):
                    if hline.lower().startswith("from:"):
                        name, addr = parseaddr(hline[5:].strip())
                        header_dict["from_name"] = _decode_str(name)
                        header_dict["from_email"] = addr
                    elif hline.lower().startswith("subject:"):
                        header_dict["subject"] = _decode_str(hline[8:].strip())
                    elif hline.lower().startswith("date:"):
                        header_dict["date"] = hline[5:].strip()
                if header_dict.get("from_email"):
                    header_dict["uid"] = current_uid
                    header_dict["folder"] = folder
                    emails.append(header_dict)

    await client.logout()
    if emails and current_uid:
        state.setdefault("last_uid", {})[folder] = current_uid
        _save_state(state)
    return emails[:limit]


def match_and_attach(emails: list[dict], dry_run: bool = False) -> list[dict]:
    results = []
    for em in emails:
        sender = em.get("from_name") or em.get("from_email", "")
        email_addr = em.get("from_email", "")
        subject = em.get("subject", "")

        match = entity_match(sender) or entity_match(email_addr)
        result = {
            "from": sender,
            "email": email_addr,
            "subject": subject,
            "matched_entity": match,
        }

        if match and not dry_run:
            entity_type = match["type"]
            entity_id = match["id"]
            eid = event_attach(
                source="email_sync",
                event_type="email_received",
                content=f"From: {sender} <{email_addr}> | Subject: {subject}",
                entity_type=entity_type,
                entity_id=entity_id,
                properties={
                    "email_subject": subject,
                    "sender_email": email_addr,
                    "sender_name": sender,
                },
            )
            result["event_id"] = eid

        results.append(result)
    return results


def run_sync(config: dict = None, dry_run: bool = False) -> dict:
    config = config or DEFAULT_CONFIG
    if not config.get("host"):
        return {
            "error": "IMAP未配置，请设置 IMAP_HOST/IMAP_USER/IMAP_PASS 环境变量或传入config"
        }

    all_emails = []
    all_results = []

    async def _sync():
        nonlocal all_emails
        for folder in config.get("folders", ["INBOX"]):
            emails = await fetch_emails(config, folder, config.get("max_per_sync", 50))
            all_emails.extend(emails)

    try:
        asyncio.run(_sync())
    except Exception as e:
        return {"error": f"IMAP连接失败: {e}"}

    if all_emails:
        all_results = match_and_attach(all_emails, dry_run)

    return {
        "synced": len(all_emails),
        "matched": sum(1 for r in all_results if r.get("matched_entity")),
        "attached": sum(1 for r in all_results if r.get("event_id")),
        "details": all_results[:20],
    }


def main():
    p = argparse.ArgumentParser(description="Email IMAP → Context Graph sync")
    sub = p.add_subparsers(dest="cmd")

    sync_cmd = sub.add_parser("sync", help="Sync recent emails")
    sync_cmd.add_argument("--dry-run", action="store_true")
    sync_cmd.add_argument("--host")
    sync_cmd.add_argument("--user")
    sync_cmd.add_argument("--password")

    cfg_cmd = sub.add_parser("config", help="Show/check IMAP config")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)

    if args.cmd == "sync":
        config = {**DEFAULT_CONFIG}
        if args.host:
            config["host"] = args.host
        if args.user:
            config["user"] = args.user
        if args.password:
            config["password"] = args.password
        result = run_sync(config, args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == "config":
        has = bool(DEFAULT_CONFIG["host"])
        print(
            json.dumps(
                {
                    "configured": has,
                    "host": DEFAULT_CONFIG["host"] or "(未设置)",
                    "user": DEFAULT_CONFIG["user"] or "(未设置)",
                    "hint": "export IMAP_HOST=xxx IMAP_USER=xxx IMAP_PASS=xxx"
                    if not has
                    else "OK",
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
