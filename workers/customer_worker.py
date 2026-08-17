"""Leverage Customer Worker.

Handles structured project/customer intake, support summaries and feedback.
No customer-facing commitment or contract becomes active automatically.
"""
from __future__ import annotations
import json

ROLE = "customer intake and support"


def intake(name: str, problem: str, desired_outcome: str) -> dict:
    return {
        "customer_name": name.strip(),
        "problem": problem.strip(),
        "desired_outcome": desired_outcome.strip(),
        "next_action": "research_and_validation",
        "approval_required": ["project_acceptance", "customer_commitment"],
    }


def self_test() -> dict:
    return {
        "worker": "customer-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["customer-intake", "support-triage", "feedback-collection", "customer-reporting"],
        "restricted_actions": ["sign_contract", "issue_refund", "publish_binding_offer"],
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
