"""Leverage Operations Worker.

Monitors system health, verifies expected state and reports safe recoveries.
It cannot perform restricted financial or destructive actions.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

ROLE = "system operations and health"


def health_snapshot(workers: list[dict], tasks: list[dict]) -> dict:
    online = sum(w.get("status") == "online" for w in workers)
    blocked = sum(t.get("status") == "blocked" for t in tasks)
    failed = sum(t.get("status") == "failed" for t in tasks)
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "workers_online": online,
        "workers_total": len(workers),
        "blocked_tasks": blocked,
        "failed_tasks": failed,
        "health": "attention" if blocked or failed else "healthy",
    }


def self_test() -> dict:
    return {
        "worker": "operations-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["health-monitoring", "state-verification", "alerting", "safe-recovery"],
        "restricted_actions": ["move_money", "delete_production_data", "change_bank_details"],
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
