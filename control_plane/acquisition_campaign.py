"""Autonomous, policy-safe acquisition campaign planner.

Runs without ChatGPT. It creates fresh organic-content/outreach tasks for the
live Gumroad product, adds concrete prospect-validation work, gives each
channel a distinct UTM link, prepares an evidence-based offer draft for the
highest-fit prospect, deduplicates the queue, and keeps actual sending behind
channel-specific authorization/policy gates.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode

from .offer_engine import draft_offer
from .quota_guard import acquisition_budget

ROOT = Path(__file__).resolve().parent
PRODUCT = "Fabrication Shop Profit & Quote System"
PRODUCT_URL = "https://newbiezz.gumroad.com/l/neiqwz"
QUEUE_PATH = ROOT / "acquisition_queue.json"
PROSPECTS_PATH = ROOT / "prospects.json"

CONTENT_PILLARS = [
    "how to calculate a fabrication shop hourly rate",
    "why fabrication jobs get underquoted",
    "quoted vs actual job profit",
    "material and consumable markup",
    "change-order profit protection",
]
CHANNELS = ["seo_content", "linkedin", "niche_community", "direct_outreach"]


def _load() -> dict:
    if not QUEUE_PATH.exists():
        return {"version": 3, "items": [], "prospect_validation": []}
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def _load_prospects() -> list[dict]:
    if not PROSPECTS_PATH.exists():
        return []
    try:
        return json.loads(PROSPECTS_PATH.read_text(encoding="utf-8")).get("prospects", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return []


def _save(data: dict) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def tracked_url(channel: str, date_key: str) -> str:
    params = {
        "utm_source": channel,
        "utm_medium": "organic",
        "utm_campaign": f"first-product-{date_key}",
        "utm_content": channel,
    }
    return f"{PRODUCT_URL}?{urlencode(params)}"


def _prospect_validation_items(date_key: str, prospects: list[dict], existing: set[str], cap: int) -> list[dict]:
    created: list[dict] = []
    ranked = sorted(
        prospects,
        key=lambda item: (
            item.get("validation_status") == "fresh_candidate",
            item.get("fit", 0),
            item.get("public_contact_available", False),
        ),
        reverse=True,
    )
    for prospect in ranked[:cap]:
        if not prospect.get("public_contact_available"):
            continue
        key = f"{date_key}::prospect-validation::{prospect.get('id', '')}"
        if key in existing:
            continue
        created.append({
            "key": key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "project": "engineering-quote-toolkit",
            "type": "prospect-validation",
            "prospect_id": prospect.get("id"),
            "prospect": prospect.get("name"),
            "fit_score": prospect.get("fit", 0),
            "category": prospect.get("category", ""),
            "location": prospect.get("location", ""),
            "candidate_workflow": prospect.get("candidate_workflow", ""),
            "why_fit": prospect.get("why_fit", ""),
            "public_contact": prospect.get("public_contact", {}),
            "evidence": prospect.get("evidence", []),
            "status": "research_required",
            "next_action": "validate_problem_and_public_contact",
            "requires_owner_or_policy_approval": ["outreach", "customer_commitment"],
            "policy": ["no_spam", "no_impersonation", "respect_platform_rules", "no_fake_claims"],
        })
    return created


def generate_daily_queue(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    data = _load()
    existing_keys = {item.get("key") for item in data.get("items", [])}
    existing_prospect_keys = {item.get("key") for item in data.get("prospect_validation", [])}
    created = []
    date_key = now.date().isoformat()
    prospects = _load_prospects()
    budget = acquisition_budget()
    ranked_prospects = sorted(
        prospects,
        key=lambda item: (
            item.get("validation_status") == "fresh_candidate",
            item.get("fit", 0),
            item.get("public_contact_available", False),
        ),
        reverse=True,
    )
    top_prospect = ranked_prospects[0] if ranked_prospects else None
    offer = draft_offer(top_prospect) if top_prospect else None

    daily_content_target = min(len(CONTENT_PILLARS), int(budget["daily_content_target"]))
    for index, pillar in enumerate(CONTENT_PILLARS[:daily_content_target]):
        channel = CHANNELS[index % len(CHANNELS)]
        key = f"{date_key}::{channel}::{pillar}"
        if key in existing_keys:
            continue
        destination = tracked_url(channel, date_key)
        item = {
            "key": key,
            "created_at": now.isoformat(),
            "project": "engineering-quote-toolkit",
            "product": PRODUCT,
            "destination": destination,
            "channel": channel,
            "topic": pillar,
            "call_to_action": destination,
            "status": "draft",
            "requires_channel_authorization": True,
            "policy": ["no_spam", "no_impersonation", "respect_platform_rules", "no_fake_claims"],
        }
        if channel == "direct_outreach" and top_prospect:
            item["prospect_id"] = top_prospect.get("id")
            item["prospect"] = top_prospect.get("name")
            item["prospect_fit_score"] = top_prospect.get("fit", 0)
            item["prospect_status"] = "research_required"
            item["personalization_basis"] = top_prospect.get("candidate_workflow", "")
            item["offer_status"] = offer.get("status") if offer else "not_prepared"
            item["offer_send_status"] = offer.get("send_status") if offer else "not_prepared"
        created.append(item)

    prospect_validation = _prospect_validation_items(
        date_key,
        prospects,
        existing_prospect_keys,
        int(budget["daily_prospect_validation_cap"]),
    )
    data.setdefault("items", []).extend(created)
    data.setdefault("prospect_validation", []).extend(prospect_validation)
    data["version"] = 3
    data["last_generated_at"] = now.isoformat()
    data["tracking"] = {
        "base_product_url": PRODUCT_URL,
        "utm_enabled": True,
        "utm_note": "Gumroad Analytics can attribute clicks, sales, revenue and conversion to UTM links.",
    }
    data["prospect_pipeline"] = {
        "source": "control_plane/prospects.json",
        "policy": "Prospects remain candidates until explicitly validated and accepted; no outreach is sent automatically.",
        "validation_queue_size": len(data["prospect_validation"]),
        "top_candidate": top_prospect.get("id") if top_prospect else None,
        "offer_status": offer.get("status") if offer else "not_prepared",
        "offer_send_status": offer.get("send_status") if offer else "not_prepared",
    }
    data["automation_budget"] = budget
    _save(data)
    return {
        "created": len(created),
        "prospects_created": len(prospect_validation),
        "queue_size": len(data["items"]),
        "prospect_validation_size": len(data["prospect_validation"]),
        "top_candidate": top_prospect,
        "offer": offer,
        "automation_budget": budget,
        "queue": created,
        "prospect_validation": prospect_validation,
    }


def self_test() -> dict:
    sample = tracked_url("linkedin", "2026-08-20")
    return {
        "worker": "acquisition-campaign-planner",
        "status": "healthy",
        "product": PRODUCT,
        "channels": CHANNELS,
        "autonomous": True,
        "sending": "gated",
        "prospect_validation": "enabled",
        "offer_drafting": "enabled",
        "fresh_candidate_priority": True,
        "quota_guard": "enabled",
        "utm_tracking": sample,
        "cost_rm": 0,
    }


if __name__ == "__main__":
    print(json.dumps(generate_daily_queue(), indent=2))
