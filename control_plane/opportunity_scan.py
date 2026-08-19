"""Load, score and summarize the current Leverage opportunity registry."""
from __future__ import annotations
import json
from pathlib import Path
from .opportunity_engine import rank_opportunities, summary

REGISTRY = Path(__file__).with_name("opportunities.json")


def load_opportunities() -> list[dict]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return data.get("opportunities", [])


def scan() -> dict:
    opportunities = load_opportunities()
    ranked = rank_opportunities(opportunities)
    return {
        "registry_version": 1,
        "count": len(ranked),
        "summary": summary(opportunities),
        "ranked": ranked,
        "owner_gate": "No opportunity may launch without explicit Owner approval.",
    }


if __name__ == "__main__":
    print(json.dumps(scan(), indent=2))
