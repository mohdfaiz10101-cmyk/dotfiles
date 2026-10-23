#!/usr/bin/env python3
"""github-cold-repo WebUI backend (Flask)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from flask import Flask, jsonify, request

DATA_DIR = Path("/var/home/charlie/.hermes/data/github-cold-repo")
SCRIPT = Path("/var/home/charlie/.hermes/scripts/github-cold-repo")
HTML_DIR = Path("/var/home/charlie/.hermes/webui/github-cold-repo")
HTML_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)


def list_scans() -> list[dict]:
    scans = []
    for p in sorted(DATA_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text())
            scans.append({
                "date": p.stem,
                "topic": data.get("topic", ""),
                "accepted": data.get("accepted", 0),
                "total": data.get("total_discovered", 0),
                "generated_at": data.get("generated_at", ""),
            })
        except Exception:
            continue
    return scans


def read_scan(date: str) -> dict | None:
    p = DATA_DIR / f"{date}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def aggregate_stats() -> dict:
    from collections import Counter
    audits: Counter = Counter()
    langs: Counter = Counter()
    total_repos = 0
    topics: Counter = Counter()
    for p in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        topics[data.get("topic", "unknown")] += 1
        for c in data.get("candidates", []):
            total_repos += 1
            audits[c.get("audit", "C")] += 1
            lang = c.get("language") or "unknown"
            langs[lang] += 1
    return {
        "total_scans": len(list(DATA_DIR.glob("*.json"))),
        "total_repos": total_repos,
        "audits": dict(audits),
        "top_languages": dict(langs.most_common(10)),
        "top_topics": dict(topics.most_common(10)),
    }


def trigger_scan(topic: str, stars_max: int, since: str, context7: bool) -> dict:
    cmd = [
        str(SCRIPT),
        topic,
        str(stars_max),
        since,
        "json",
        "true" if context7 else "false",
    ]
    env = os.environ.copy()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env, timeout=600)
        out = p.stdout.strip()
        return json.loads(out) if out else {}
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr or str(e)}
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def index():
    return (HTML_DIR / "index.html").read_text(encoding="utf-8")


@app.route("/api/scans")
def api_scans():
    return jsonify(list_scans())


@app.route("/api/scans/<date>")
def api_scan(date):
    data = read_scan(date)
    if data is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)


@app.route("/api/stats")
def api_stats():
    return jsonify(aggregate_stats())


@app.route("/api/scan", methods=["POST"])
def api_scan_post():
    body = request.get_json(force=True) or {}
    topic = (body.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400
    stars_max = int(body.get("stars_max", 2000))
    since = body.get("since", "2024-01-01")
    context7 = bool(body.get("context7", False))
    result = trigger_scan(topic, stars_max, since, context7)
    return jsonify(result)


@app.route("/api/scans/<date>", methods=["DELETE"])
def api_scan_delete(date):
    p = DATA_DIR / f"{date}.json"
    if not p.exists():
        return jsonify({"error": "not found"}), 404
    p.unlink()
    return jsonify({"ok": True})


def run():
    app.run(host="127.0.0.1", port=8789, debug=False)


if __name__ == "__main__":
    run()
