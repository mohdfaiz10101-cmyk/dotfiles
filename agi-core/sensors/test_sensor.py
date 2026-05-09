#!/usr/bin/env python3
"""Test sensor — validates auto-loading mechanism."""

import json, datetime


def collect() -> dict:
    return {"test": "ok", "loaded_at": datetime.datetime.now().isoformat()}


if __name__ == "__main__":
    print(json.dumps(collect()))
