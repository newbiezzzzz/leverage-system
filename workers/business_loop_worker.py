"""Leverage Business Loop Worker.

Coordinates the canonical Discover -> Decide loop without bypassing
worker safety boundaries. It produces an observable execution plan; it does
not perform restricted external side effects.
"""
from __future__ import annotations
import json

STAGES = [
    "discover", "validate", "build", "publish", "acquire",
    "convert", "deliver", "support", "measure", "decide"
]


def build_plan(project_id: str, stage_status: dict[str, str] | None = None) -> dict:
    status = stage_status or {}
    stages = []
    for stage in STAGES:
        current = status.get(stage, "not_started")
        stages.append({
            "id": stage,
            "status": current,
            "ready": current in {"complete", "ready"},
        })
    return {
        "project_id": project_id,
        "stages": stages,
        "next_stage": next((s["id"] for s in stages if not s["ready"]), "complete"),
        "restricted_external_execution": True,
        "owner_approval_required_for": ["external_outreach", "binding_commitment", "spend", "money_movement"],
    }


def evaluate_gate(metrics: dict) -> dict:
    views = metrics.get("product_page_views")
    sales = metrics.get("verified_sales", 0)
    revenue = metrics.get("verified_revenue_usd", 0)
    traffic_connected = metrics.get("traffic_status") == "connected"
    return {
        "traffic_connected": traffic_connected,
        "sales_verified": sales > 0,
        "revenue_verified": revenue > 0,
        "conversion_measurable": traffic_connected and views not in (None, 0),
        "status": "validated" if traffic_connected and sales > 0 and revenue > 0 else "evidence_pending",
    }


def self_test() -> dict:
    plan = build_plan(
        "example-project",
        {"discover": "complete", "validate": "complete", "build": "complete"},
    )
    gate = evaluate_gate({"traffic_status": "not_connected", "verified_sales": 0, "verified_revenue_usd": 0})
    return {
        "worker": "business-loop-worker",
        "status": "healthy",
        "stages": STAGES,
        "sample_plan": plan,
        "sample_gate": gate,
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
