#!/usr/bin/env python3
"""Strategy Hunter final goal gate.

The loop continues until the pipeline publishes an explicit achieved marker.
No marker means research must continue.
"""
from pathlib import Path
import json
import os

path = Path("research/results/strategy_hunter_goal.json")
achieved = False

if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        achieved = data.get("status") == "achieved" and data.get("all_gates_passed") is True
    except Exception:
        achieved = False

print(f"achieved={achieved}")
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"achieved={'true' if achieved else 'false'}\n")

if achieved:
    print("GOAL ACHIEVED")
else:
    print("GOAL NOT ACHIEVED — continue autonomous research")
