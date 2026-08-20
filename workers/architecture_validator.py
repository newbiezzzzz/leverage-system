"""Validate project-type/channel/delivery compatibility without launching anything."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_registry() -> dict:
    path = ROOT / "control_plane" / "project_types.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate(project_type: str, channel: str, delivery: str, revenue_event: str) -> dict:
    registry = load_registry()["types"]
    spec = registry.get(project_type)
    if not spec:
        return {"valid": False, "reason": f"unknown_project_type:{project_type}"}
    checks = {
        "channel": channel in spec["channels"],
        "delivery": delivery in spec["delivery"],
        "revenue_event": revenue_event in spec["revenue_events"],
    }
    return {
        "valid": all(checks.values()),
        "project_type": project_type,
        "channel": channel,
        "delivery": delivery,
        "revenue_event": revenue_event,
        "checks": checks,
        "build_capabilities": spec["build_capabilities"],
        "dry_run_only": True,
    }


def self_test() -> dict:
    samples = [
        validate("digital_product", "marketplace", "digital_download", "purchase"),
        validate("software", "web", "hosted_service", "subscription"),
        validate("automation_service", "direct", "service_execution", "invoice"),
        validate("data_product", "direct", "api_access", "subscription"),
        validate("content_media", "video", "content", "advertising"),
        validate("lead_generation", "search", "qualified_lead", "lead_sale"),
    ]
    return {
        "worker": "architecture-validator",
        "status": "healthy" if all(x["valid"] for x in samples) else "failed",
        "samples": samples,
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
