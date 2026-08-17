"""Leverage Finance Worker.

Reconciles verified financial records and prepares owner payout requests.
It intentionally cannot approve or execute money movement.
"""
from __future__ import annotations
import json
from control_plane.finance_core import prepare_owner_payout, can_execute_payout

ROLE = "finance reconciliation and payout preparation"


def self_test() -> dict:
    return {
        "worker": "finance-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["reconciliation", "revenue-reporting", "payout-preparation"],
        "restricted_actions": ["approve_money", "move_money", "change_bank_details"],
        "cost": {"amount": 0, "currency": "RM"},
    }


def prepare(amount: float, destination: str, purpose: str) -> dict:
    return {"request": prepare_owner_payout(amount, destination, purpose).__dict__}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
