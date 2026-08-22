"""Provider-neutral, approval-gated outreach adapter.

Prepares outbound messages for a selected provider but never sends by itself.
"""
from __future__ import annotations

from dataclasses import dataclass

PROVIDERS = ("gmail", "outlook")


@dataclass(frozen=True)
class OutreachDraft:
    provider: str
    prospect_id: str
    to: str
    subject: str
    body: str
    status: str = "draft"
    send_status: str = "not_sent"
    owner_approval_required: bool = True


def prepare_outreach(offer: dict, provider: str, approved: bool = False) -> OutreachDraft:
    provider = provider.lower().strip()
    if provider not in PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")
    if not approved:
        raise ValueError("owner approval required before preparing provider-ready outreach")
    contact = offer.get("public_contact") or {}
    to = str(contact.get("email") or "").strip()
    if not to:
        raise ValueError("public email contact required")
    prospect = str(offer.get("prospect") or "Prospect").strip()
    return OutreachDraft(
        provider=provider,
        prospect_id=str(offer.get("prospect_id") or ""),
        to=to,
        subject=f"Quote and job-costing workflow for {prospect}",
        body=str(offer.get("value_proposition") or offer.get("offer") or ""),
    )


def self_test() -> dict:
    sample = {"prospect_id": "sample", "prospect": "Sample Workshop", "public_contact": {"email": "sample@example.com"}, "offer": "Sample offer"}
    try:
        prepare_outreach(sample, "gmail", approved=False)
    except ValueError as exc:
        guarded = "approval required" in str(exc)
    else:
        guarded = False
    return {"worker": "outreach-adapter", "status": "healthy", "providers": list(PROVIDERS), "external_send": "gated", "approval_guard": guarded}


if __name__ == "__main__":
    import json
    print(json.dumps(self_test(), indent=2))
