"""Draft evidence-based offers for qualified prospects without sending them."""
from __future__ import annotations

from datetime import datetime, timezone

PRODUCT = "Fabrication Shop Profit & Quote System"
PRODUCT_URL = "https://newbiezz.gumroad.com/l/neiqwq"


def draft_offer(prospect: dict) -> dict:
    workflow = str(prospect.get("candidate_workflow", "")).strip()
    name = str(prospect.get("name", "Prospect")).strip() or "Prospect"
    fit = float(prospect.get("fit", 0) or 0)
    evidence = [str(x).strip() for x in prospect.get("evidence", []) if str(x).strip()]
    why_fit = str(prospect.get("why_fit", "")).strip()
    public_contact = prospect.get("public_contact", {}) or {}
    return {
        "status": "draft",
        "prospect_id": prospect.get("id"),
        "prospect": name,
        "fit_score": fit,
        "offer": f"A practical quote and job-costing workbook to help {name} structure {workflow or 'fabrication quoting and job costing'}.",
        "value_proposition": "Track labour, material and consumable costs in one quote workflow so quoted margin is visible before the job is accepted.",
        "call_to_action": f"Would you like to review a sample workflow? {PRODUCT_URL}",
        "personalization_basis": workflow,
        "why_fit": why_fit,
        "evidence": evidence,
        "public_contact": public_contact,
        "price_usd": 19,
        "channel": "email_or_whatsapp",
        "send_status": "not_sent",
        "owner_approval_required": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safety": ["no_claim_of_customer_status", "no_fake_results", "no_mass_spam", "no_binding_commitment"],
    }


def self_test() -> dict:
    sample = draft_offer({
        "id": "sample",
        "name": "Sample Fabricator",
        "fit": 90,
        "candidate_workflow": "quote preparation and job costing",
        "why_fit": "fabrication quoting workflow",
        "evidence": ["public company profile"],
        "public_contact": {"email": "example@example.com"},
    })
    return {"worker": "offer-engine", "status": "healthy", "sample_status": sample["status"], "send_status": sample["send_status"]}


if __name__ == "__main__":
    import json
    print(json.dumps(self_test(), indent=2))
