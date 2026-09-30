#!/usr/bin/env python3
"""Single source of truth for Leverage mission progress.

This controller never declares success from activity alone. Achievement comes
only from the explicit evidence gate.

Decision governance is read from control_plane/decision_state.json so a new
idea cannot silently become the active direction without an explicit decision.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MISSION = ROOT / "control_plane" / "leverage_mission.json"
DECISION = ROOT / "control_plane" / "decision_state.json"
RESULTS = ROOT / "research" / "results"
STATE = ROOT / "control_plane" / "mission_state.json"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    mission = read_json(MISSION, {})
    decision = read_json(DECISION, {})
    goal = read_json(RESULTS / "strategy_hunter_goal.json", {})
    progress = read_json(RESULTS / "strategy_hunter_progress.json", {})
    cycle = read_json(RESULTS / "research_cycle_state.json", {})
    sanity = read_json(RESULTS / "engine_sanity.json", {})

    approved = decision.get("current_approved_approach", {})
    approved_track = approved.get("track")
    approved_objective = approved.get("objective")

    current_track = mission.get("active_track", "strategy_hunter")
    current_objective = mission.get("objective")

    # Detect silent mission drift. This is a warning/state signal, not a new
    # strategy decision; directional changes must still be made through the
    # persistent decision record.
    decision_drift = bool(
        approved_track
        and current_track != approved_track
        or approved_objective
        and current_objective != approved_objective
    )

    achieved = bool(
        goal.get("status") == "achieved"
        and goal.get("all_gates_passed") is True
    )

    state = {
        "mission": mission.get("mission", "Leverage"),
        "active_track": current_track,
        "objective": current_objective,
        "state": "ACHIEVED" if achieved else "RUNNING",
        "goal_achieved": achieved,
        "engine_sanity": sanity.get("status") == "passed",
        "cycle": progress.get("cycle", cycle.get("cycle", 0)),
        "progress": progress,
        "last_cycle": cycle,
        "next_action": "stop" if achieved else "continue_research",
        "owner_action_required": False,
        "decision_governance": {
            "decision_id": decision.get("decision_id"),
            "status": decision.get("status"),
            "default_new_issue_action": decision.get("decision_rules", {}).get(
                "default_action_on_new_issue", "KEEP_OR_IMPROVE"
            ),
            "replacement_requires_evidence": decision.get("decision_rules", {}).get(
                "replacement_requires_evidence", True
            ),
            "decision_drift": decision_drift
        }
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
