#!/usr/bin/env python3
"""Strict Leverage achievement gate.

The mission is achieved only when independently generated evidence says every
required gate passed. Missing evidence always means continue researching.
"""
from __future__ import annotations

import json
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
MISSION = ROOT / "control_plane" / "leverage_mission.json"
SANITY = ROOT / "research/results/engine_sanity.json"
QUAL = ROOT / "research/results/strategy_hunter_candidate_qualification.json"
GOAL = ROOT / "research/results/strategy_hunter_goal.json"


def read(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


mission = read(MISSION, {})
sanity = read(SANITY, {})
qual = read(QUAL, {})

required = list(mission.get("achievement_gates", []))
gates = qual.get("gates", {}) if isinstance(qual, dict) else {}

passed = bool(sanity.get("status") == "passed")
missing = []

if "engine_sanity" in required and not passed:
    missing.append("engine_sanity")

for gate in required:
    if gate == "engine_sanity":
        continue
    if gates.get(gate) is not True:
        missing.append(gate)

achieved = bool(
    qual.get("status") == "achieved"
    and qual.get("all_gates_passed") is True
    and not missing
)

state = {
    "checked_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    "status": "achieved" if achieved else "searching",
    "all_gates_passed": achieved,
    "missing_gates": missing,
    "required_gates": required
}
GOAL.parent.mkdir(parents=True, exist_ok=True)
GOAL.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

out=os.environ.get("GITHUB_OUTPUT")
print(f"achieved={'true' if achieved else 'false'}")
if out:
    with open(out,"a",encoding="utf-8") as f:
        f.write(f"achieved={'true' if achieved else 'false'}\n")
