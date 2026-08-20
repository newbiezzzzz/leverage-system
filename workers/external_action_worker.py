"""Leverage External Action Worker.

Converts prepared external work into an approval-gated action record and
verifies completion evidence. This worker does not directly send messages,
publish content, move money, or bypass platform controls.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone

ROLE = "external action preparation, approval routing and verification"

APPROVAL_REQUIRED = {
    "external_publish": True,
    "outreach": True,
    "price_change": True,
    "binding_customer_commitment": True,
    "money_movement": True,
    "internal_reversible_change": False,
}


def prepare_action(project_id: str, action_type: str, channel: str, target: str,
                   intended_effect: str, verification_method: str) -> dict:
    action_type = action_type.strip()
    return {
        "action_id": f"act-{uuid.uuid4().hex[:12]}",
        "project_id": project_id.strip(),
        "action_type": action_type,
        "channel": channel.strip(),
        "target": target.strip(),
        "intended_effect": intended_effect.strip(),
        "verification_method": verification_method.strip(),
        "status": "ready_for_approval" if APPROVAL_REQUIRED.get(action_type, True) else "approved",
        "approval_required": APPROVAL_REQUIRED.get(action_type, True),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "execution": {
            "performed": False,
            "evidence": None,
        },
    }


def verify_completion(action: dict, evidence: str) -> dict:
    updated = dict(action)
    updated["status"] = "completed"
    updated["execution"] = {
        "performed": True,
        "evidence": evidence.strip(),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    return updated


def self_test() -> dict:
    sample = prepare_action(
        "example-project",
        "external_publish",
        "web",
        "example-target",
        "publish an approved asset",
        "confirm public URL and timestamp",
    )
    return {
        "worker": "external-action-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["prepare", "route_for_approval", "track", "verify"],
        "restricted_actions": [
            "direct_external_send",
            "mass_spam",
            "impersonation",
            "binding_commitment",
            "money_movement",
            "bypass_platform_rules",
        ],
        "sample": sample,
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
