"""Product Factory orchestration contract.

Creates deterministic plans and quality gates. External marketplace execution is
routed through the existing guarded Browser Worker on the Owner machine.
"""
from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "product_factory_config.json"

FACTORY_STAGES = (
    "research", "select", "build", "functional_qa", "creative_qa",
    "conversion_qa", "website_package", "marketplace_package", "marketing_package",
    "analytics_package", "safety_audit",
)


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def create_dry_run_plan(product_name: str = "FACTORY-DRY-RUN") -> dict:
    config = load_config()
    return {
        "mode": "dry-run",
        "product": product_name,
        "stages": [{"name": stage, "status": "queued"} for stage in FACTORY_STAGES],
        "publish_threshold": config["quality"]["minimum_publish_score"],
        "real_paid_publish": False,
        "money_movement": False,
        "marketplace_execution": {
            "mode": "guarded_browser_worker",
            "enabled": config["marketplaces"]["gumroad"]["browser_worker"]["enabled"],
            "owner_machine_required": True,
        },
        "owner_approval_boundaries": ["payout", "payment_credentials", "bank_details", "major_financial_action"],
    }


def browser_worker_goal(product_name: str, marketplace: str = "gumroad") -> str:
    return f"Optimize {product_name} {marketplace} marketplace listing"


def ready_for_product_one(stage_results: dict[str, bool]) -> dict:
    missing = [stage for stage in FACTORY_STAGES if not stage_results.get(stage, False)]
    return {
        "ready": not missing,
        "missing": missing,
        "next": "create_product_1" if not missing else "complete_dry_run",
    }


if __name__ == "__main__":
    print(json.dumps(create_dry_run_plan(), indent=2))
