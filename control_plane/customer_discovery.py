"""Rank discovered prospects for the current business opportunity."""
from __future__ import annotations
import json
from pathlib import Path

REGISTRY = Path(__file__).with_name("prospects.json")


def load_prospects() -> list[dict]:
    return json.loads(REGISTRY.read_text(encoding="utf-8")).get("prospects", [])


def rank_prospects(prospects: list[dict]) -> list[dict]:
    return sorted(prospects, key=lambda item: (item.get("fit", 0), item.get("public_contact_available", False)), reverse=True)


def discovery_report() -> dict:
    prospects = load_prospects()
    ranked = rank_prospects(prospects)
    return {
        "count": len(ranked),
        "ranked": ranked,
        "next_stage": "validate",
        "rule": "A discovered prospect is not a customer until the prospect explicitly accepts an offer and a real transaction is recorded.",
        "outreach_status": "not_sent",
    }


if __name__ == "__main__":
    print(json.dumps(discovery_report(), indent=2))
