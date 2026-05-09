#!/usr/bin/env python3
"""Sensor: Read chronos task data from /tmp/chronos/*.json."""

import json, glob
from pathlib import Path


def collect() -> dict:
    chronos = {}
    for f in sorted(glob.glob("/tmp/chronos/*.json")):
        try:
            data = json.loads(Path(f).read_text())
            chronos[Path(f).stem] = data
        except Exception:
            pass
    return {"chronos": chronos}


if __name__ == "__main__":
    print(json.dumps(collect()))
