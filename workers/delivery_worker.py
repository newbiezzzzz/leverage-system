"""Leverage Delivery Worker.

Prepares and verifies customer fulfillment without taking payment, changing
accounts, or making unauthorized external commitments.
"""
from __future__ import annotations
import json

ROLE = "customer delivery and fulfillment orchestration"


def create_delivery(project_id: str, customer_ref: str, product_ref: str, fulfillment_method: str) -> dict:
    return {
        "project_id": project_id.strip(),
        "customer_ref": customer_ref.strip(),
        "product_ref": product_ref.strip(),
        "fulfillment_method": fulfillment_method.strip(),
        "status": "prepared",
        "external_execution_required": True,
        "owner_approval_required": False,
        "verification_required": True,
        "notes": "For automated marketplaces, use authoritative platform confirmation as the delivery evidence.",
    }


def verify_delivery(record: dict, evidence: str | None = None) -> dict:
    verified = bool(evidence and evidence.strip())
    return {
        "delivery_status": "verified" if verified else "awaiting_evidence",
        "evidence": evidence.strip() if evidence else None,
        "verified": verified,
    }


def self_test() -> dict:
    return {
        "worker": "delivery-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["fulfillment-preparation", "delivery-verification", "status-reporting"],
        "restricted_actions": ["move_money", "change_customer_entitlement_without_evidence", "issue_refund"],
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
