"""Pre-Product-#1 factory orchestration contract.

This module is intentionally provider-agnostic. It creates a deterministic plan and
quality gates; external execution is routed through existing guarded adapters.
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
        "owner_approval_boundaries": ["payout", "payment_credentials", "bank_details", "major_financial_action"],
    }


def ready_for_product_one(stage_results: dict[str, bool]) -> dict:
    missing = [stage for stage in FACTORY_STAGES if not stage_results.get(stage, False)]
    return {
        "ready": not missing,
        "missing": missing,
        "next": "create_product_1" if not missing else "complete_dry_run",
    }


if __name__ == "__main__":
    print(json.dumps(create_dry_run_plan(), indent=2))
