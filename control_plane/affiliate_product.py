"""B4 Product & Affiliate Engine.

Turns ranked B3 demand opportunities into product/offer research candidates.
B4 preserves previously verified marketplace candidates and never invents
listings, prices, commissions, availability, or affiliate eligibility.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "affiliate_opportunity_queue.json"
CONFIG = ROOT / "affiliate_product_config.json"
OUTPUT = ROOT / "affiliate_product_queue.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional(path: Path) -> dict:
    try:
        return load(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def candidate_categories(problem: str) -> list[str]:
    p = problem.lower()
    rules = [
        (("tyre", "tayar", "tire"), ["tyres", "tyre accessories", "tyre tools"]),
        (("battery", "bateri"), ["car battery accessories", "battery testers", "jump starters"]),
        (("dashcam", "dash cam"), ["dashcams", "dashcam accessories"]),
        (("maintenance", "servis", "service", "repair"), ["car maintenance tools", "diagnostic tools", "car care products"]),
        (("oil", "minyak"), ["engine oil", "oil tools", "oil maintenance accessories"]),
        (("first car", "buying", "beli", "recommend", "sedan"), ["car buying accessories", "car safety accessories", "vehicle inspection tools"]),
        (("spare parts", "parts", "alat ganti"), ["car spare parts", "replacement parts", "automotive tools"]),
    ]
    categories: list[str] = []
    for needles, values in rules:
        if any(n in p for n in needles):
            categories.extend(values)
    return list(dict.fromkeys(categories)) or ["automotive accessories", "car care products", "automotive tools"]


def existing_verified_products() -> list[dict]:
    current = load_optional(OUTPUT)
    return [
        product for product in current.get("products", [])
        if str(product.get("status", "")).startswith("verified_")
    ]


def build() -> dict:
    cfg = load(CONFIG)
    source = load(INPUT)
    networks = cfg["networks"]
    opportunities = source.get("opportunities", [])

    verified = existing_verified_products()
    rows: list[dict] = list(verified)
    verified_ids = {p.get("id") for p in verified}

    for opp in opportunities[: int(cfg["output"]["max_opportunities"] )]:
        cats = candidate_categories(opp.get("problem", ""))
        for category in cats:
            for network in networks:
                key = f"{opp['id']}|{category}|{network['name']}"
                candidate_id = "pc-" + hashlib.sha256(key.encode()).hexdigest()[:16]
                if candidate_id in verified_ids:
                    continue
                rows.append({
                    "id": candidate_id,
                    "product_name": None,
                    "category": category,
                    "problem_solved": opp.get("problem"),
                    "affiliate_network": network["name"],
                    "network_role": network["role"],
                    "network_url": network["url"],
                    "offer_url": None,
                    "price_myr": None,
                    "commission_rate": None,
                    "estimated_commission_myr": None,
                    "availability": "unknown",
                    "affiliate_eligibility": "unknown",
                    "evidence": [
                        {"type": "opportunity", "url": e.get("url"), "excerpt": e.get("excerpt", "")}
                        for e in opp.get("evidence", [])
                    ] + [{"type": "affiliate_program", "url": network["url"], "excerpt": network["evidence"]}],
                    "opportunity_score": opp.get("opportunity_score", 0),
                    "status": "research_candidate",
                    "verification_required": ["specific_product_listing", "current_price", "current_commission", "availability", "affiliate_eligibility"],
                    "source_opportunity_id": opp.get("id"),
                    "generated_at": now(),
                })

    verified_count = len(verified)
    research_count = len(rows) - verified_count
    payload = {
        "version": 2,
        "project": "affiliate-project",
        "generated_at": now(),
        "input_generated_at": source.get("generated_at"),
        "opportunity_count": len(opportunities),
        "candidate_count": len(rows),
        "verified_product_count": verified_count,
        "research_candidate_count": research_count,
        "status": "research_completed_offer_verification_pending" if verified_count else "awaiting_product_evidence",
        "products": rows,
        "verification_policy": {
            "required_before_publish_as_verified_offer": [
                "specific_product_listing", "current_price", "availability", "affiliate_item_eligibility", "current_commission"
            ],
            "unknown_policy": "Never infer or invent missing commercial facts. A public listing is a product candidate, not proof that the exact item is commissionable for the connected creator account."
        },
        "boundary": "B4 researches product and affiliate candidates. Verified marketplace candidates persist across automated runs; commission and item-level affiliate eligibility remain unknown until authoritative account-level evidence exists.",
        "next_stage": "B5 Content Intelligence",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = build()
    print(json.dumps({"status": "ok", "opportunities": result["opportunity_count"], "verified_products": result["verified_product_count"], "research_candidates": result["research_candidate_count"], "output": str(OUTPUT)}))
