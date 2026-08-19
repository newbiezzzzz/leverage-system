"""Prepare, validate, and track customer outreach without sending it.

Leverage v1 treats outbound communication as an explicit approval boundary.
This module creates a reviewable outreach package from a qualified prospect;
it does not send messages, impersonate people, or create customers.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROSPECTS = ROOT / "prospects.json"
OUTREACH = ROOT / "outreach_queue.json"

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

def build_message(prospect: dict, offer: str) -> str:
    name = prospect.get("business_name", "your business")
    problem = prospect.get("observed_problem", "a repetitive workflow")
    return (f"Subject: Small workflow improvement for {name}\n\n"
            f"Hi {prospect.get('contact_name', 'there')},\n\n"
            f"I noticed {problem}. I’m testing a narrowly scoped automation service "
            f"for businesses like {name}. The idea is to improve one measurable workflow "
            f"without replacing your existing systems.\n\n"
            f"Offer: {offer}\n\n"
            "If this is relevant, I can share a short workflow audit and proposed next step.\n\n"
            "Regards,\nLeverage")

def prepare_outreach(prospect_id: str, offer: str) -> dict:
    prospects = load(PROSPECTS).get("prospects", [])
    prospect = next((p for p in prospects if p.get("id") == prospect_id), None)
    if prospect is None:
        raise KeyError(f"unknown prospect: {prospect_id}")
    if not prospect.get("public_contact_available"):
        raise ValueError("no public contact method recorded")
    item = {
        "id": f"outreach-{prospect_id}",
        "prospect_id": prospect_id,
        "channel": prospect.get("preferred_public_channel", "manual_review"),
        "message": build_message(prospect, offer),
        "status": "draft",
        "approval_required": True,
        "sent_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data = load(OUTREACH)
    queue = [x for x in data.get("outreach", []) if x.get("id") != item["id"]]
    queue.append(item)
    save(OUTREACH, {"version": 1, "outreach": queue})
    return item

if __name__ == "__main__":
    print(json.dumps({"status": "ready", "rule": "draft only; human approval required before sending"}, indent=2))
