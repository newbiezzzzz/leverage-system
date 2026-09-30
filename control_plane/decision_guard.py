#!/usr/bin/env python3
"""Fail closed when mission direction drifts without a recorded decision."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSION = ROOT / "control_plane" / "leverage_mission.json"
DECISION = ROOT / "control_plane" / "decision_state.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    mission = read(MISSION)
    decision = read(DECISION)

    approved = decision.get("current_approved_approach", {})
    rules = decision.get("decision_rules", {})
    errors: list[str] = []

    if decision.get("status") not in {"LOCKED", "ACTIVE"}:
        errors.append("decision_state.status must be LOCKED or ACTIVE")

    if not approved.get("track"):
        errors.append("current_approved_approach.track is missing")

    if not approved.get("objective"):
        errors.append("current_approved_approach.objective is missing")

    if mission.get("active_track") != approved.get("track"):
        errors.append(
            f"active_track drift: mission={mission.get('active_track')!r} "
            f"approved={approved.get('track')!r}"
        )

    if mission.get("objective") != approved.get("objective"):
        errors.append("objective drift between leverage_mission.json and decision_state.json")

    if rules.get("new_idea_is_automatically_adopted") is not False:
        errors.append("new ideas must not be automatically adopted")

    if rules.get("replacement_requires_evidence") is not True:
        errors.append("replacement_requires_evidence must be true")

    if rules.get("activity_equals_success") is not False:
        errors.append("activity must not be treated as success")

    print("Leverage decision governance check")
    print(f"decision_id: {decision.get('decision_id')}")
    print(f"status: {decision.get('status')}")
    print(f"approved_track: {approved.get('track')}")
    print(f"mission_track: {mission.get('active_track')}")

    if errors:
        print("DRIFT DETECTED — FAIL CLOSED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS — mission direction matches the persistent decision record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
