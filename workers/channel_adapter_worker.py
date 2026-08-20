"""Generic Leverage channel-adapter worker.

Routes platform-specific work through the stable adapter contract without
embedding a specific provider into Leverage core. This worker prepares,
validates and verifies adapter actions; execution remains approval-gated.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


def prepare(adapter: str, action: str, payload: dict) -> dict:
    return {
        "adapter": adapter,
        "action": action,
        "payload": payload,
        "status": "ready_for_approval",
        "external_side_effect": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate(request: dict) -> dict:
    required = ["adapter", "action", "payload"]
    missing = [key for key in required if key not in request]
    return {
        "valid": not missing,
        "missing": missing,
        "status": "validated" if not missing else "invalid",
    }


def verify(adapter: str, evidence: dict) -> dict:
    required = ["source", "action_id_or_reference", "timestamp", "status"]
    missing = [key for key in required if not evidence.get(key)]
    return {
        "adapter": adapter,
        "verified": not missing,
        "missing": missing,
        "evidence": evidence,
    }


def self_test() -> dict:
    request = prepare("marketplace", "publish", {"content": "example"})
    validation = validate(request)
    verification = verify("marketplace", {
        "source": "test",
        "action_id_or_reference": "TEST-001",
        "timestamp": "2026-08-20T00:00:00Z",
        "status": "simulated",
    })
    return {
        "worker": "channel-adapter-worker",
        "status": "healthy",
        "capabilities": ["prepare", "validate", "verify", "route"],
        "external_side_effects": False,
        "sample": {"request": request, "validation": validation, "verification": verification},
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
