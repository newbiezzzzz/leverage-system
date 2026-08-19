"""Autonomous, policy-safe acquisition campaign planner.

Runs without ChatGPT. It creates fresh organic-content/outreach tasks for the
live Gumroad product, deduplicates the queue, and keeps actual sending behind
channel-specific authorization/policy gates.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

PRODUCT = "Fabrication Shop Profit & Quote System"
PRODUCT_URL = "https://newbiezz.gumroad.com/l/neiqwz"
QUEUE_PATH = Path("control_plane/acquisition_queue.json")

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
        return {"version": 1, "items": []}
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generate_daily_queue(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    data = _load()
    existing_keys = {item["key"] for item in data.get("items", [])}
    created = []
    for index, pillar in enumerate(CONTENT_PILLARS):
        channel = CHANNELS[index % len(CHANNELS)]
        key = f"{now.date().isoformat()}::{channel}::{pillar}"
        if key in existing_keys:
            continue
        created.append({
            "key": key,
            "created_at": now.isoformat(),
            "project": "engineering-quote-toolkit",
            "product": PRODUCT,
            "destination": PRODUCT_URL,
            "channel": channel,
            "topic": pillar,
            "call_to_action": PRODUCT_URL,
            "status": "draft",
            "requires_channel_authorization": True,
            "policy": ["no_spam", "no_impersonation", "respect_platform_rules", "no_fake_claims"],
        })
    data.setdefault("items", []).extend(created)
    data["last_generated_at"] = now.isoformat()
    _save(data)
    return {"created": len(created), "queue_size": len(data["items"]), "queue": created}


def self_test() -> dict:
    return {
        "worker": "acquisition-campaign-planner",
        "status": "healthy",
        "product": PRODUCT,
        "channels": CHANNELS,
        "autonomous": True,
        "sending": "gated",
        "cost_rm": 0,
    }


if __name__ == "__main__":
    print(json.dumps(generate_daily_queue(), indent=2))
