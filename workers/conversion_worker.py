"""Leverage Conversion Worker.

Analyzes and prepares conversion experiments. It does not alter live offers,
pricing, or publish binding changes without approval.
"""
from __future__ import annotations
import json

ROLE = "conversion optimization and experiment planning"


def build_experiment(project_id: str, hypothesis: str, change: str, metric: str = "purchase_conversion") -> dict:
    return {
        "project_id": project_id.strip(),
        "hypothesis": hypothesis.strip(),
        "proposed_change": change.strip(),
        "primary_metric": metric.strip(),
        "status": "draft",
        "requires_owner_approval": True,
        "reversible": True,
        "success_rule": "Use verified traffic and sales evidence; do not infer conversion from unknown traffic.",
    }


def evaluate(metrics: dict) -> dict:
    views = metrics.get("product_page_views")
    sales = metrics.get("verified_sales")
    if views is None or sales is None:
        return {"status": "insufficient_evidence", "conversion_rate": None, "reason": "traffic or sales evidence unavailable"}
    views = float(views)
    sales = float(sales)
    rate = None if views <= 0 else sales / views
    return {"status": "measurable", "conversion_rate": rate, "verified_sales": sales, "product_page_views": views}


def self_test() -> dict:
    return {
        "worker": "conversion-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["experiment-design", "funnel-analysis", "conversion-evaluation", "reporting"],
        "restricted_actions": ["change_price", "publish_offer", "bind_customer", "move_money"],
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
