#!/usr/bin/env python3
"""Single source of truth for Leverage mission progress.

This controller never declares success from activity alone. Achievement comes
only from the explicit evidence gate.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MISSION = ROOT / "control_plane" / "leverage_mission.json"
RESULTS = ROOT / "research" / "results"
STATE = ROOT / "control_plane" / "mission_state.json"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    mission = read_json(MISSION, {})
    goal = read_json(RESULTS / "strategy_hunter_goal.json", {})
    progress = read_json(RESULTS / "strategy_hunter_progress.json", {})
    cycle = read_json(RESULTS / "research_cycle_state.json", {})
    sanity = read_json(RESULTS / "engine_sanity.json", {})

    achieved = bool(
        goal.get("status") == "achieved"
        and goal.get("all_gates_passed") is True
    )

    state = {
        "mission": mission.get("mission", "Leverage"),
        "active_track": mission.get("active_track", "strategy_hunter"),
        "objective": mission.get("objective"),
        "state": "ACHIEVED" if achieved else "RUNNING",
        "goal_achieved": achieved,
        "engine_sanity": sanity.get("status") == "passed",
        "cycle": progress.get("cycle", cycle.get("cycle", 0)),
        "progress": progress,
        "last_cycle": cycle,
        "next_action": "stop" if achieved else "continue_research",
        "owner_action_required": False
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
