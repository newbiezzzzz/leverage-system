"""Leverage Acquisition Worker.

Finds, qualifies and prepares compliant customer-acquisition work for any
company project. It does not spam, impersonate, sign contracts, send binding
offers, move money, bypass platform rules, or publish externally without
approval.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

ROLE = "customer acquisition and prospect qualification"


def qualify_prospect(name: str, fit_score: float, evidence: list[str] | None = None) -> dict:
    score = max(0.0, min(100.0, float(fit_score)))
    return {
        "prospect": name.strip(),
        "fit_score": score,
        "evidence": [item.strip() for item in (evidence or []) if item.strip()],
        "status": "qualified" if score >= 70 else "research_required",
        "next_action": "prepare_personalized_value_offer" if score >= 70 else "research_prospect",
        "approval_required": ["outreach", "customer_commitment"],
    }


def prepare_outreach(prospect: dict, value_offer: str, channel: str) -> dict:
    return {
        "prospect": prospect.get("prospect", ""),
        "channel": channel.strip(),
        "value_offer": value_offer.strip(),
        "status": "draft",
        "requires_owner_or_policy_approval": True,
        "safety_checks": [
            "no_mass_spam",
            "no_impersonation",
            "respect_channel_rules",
            "no_binding_commitment",
        ],
    }


def build_tracking_url(destination: str, source: str, medium: str, campaign: str) -> str:
    """Create a measurable destination URL without performing external publishing."""
    parsed = urlparse(destination)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.update({"utm_source": source, "utm_medium": medium, "utm_campaign": campaign})
    return urlunparse(parsed._replace(query=urlencode(params)))


def plan_campaign(project_id: str, destination: str, channel: str, campaign: str, medium: str = "organic") -> dict:
    """Prepare a traceable acquisition campaign for owner review."""
    return {
        "project_id": project_id,
        "channel": channel.strip(),
        "medium": medium.strip(),
        "campaign": campaign.strip(),
        "tracking_url": build_tracking_url(destination, channel.strip(), medium.strip(), campaign.strip()),
        "status": "draft",
        "owner_approval_required": True,
        "external_publishing": False,
        "measurement": ["clicks", "product_views", "sales"],
        "safety_checks": [
            "no_mass_spam",
            "no_impersonation",
            "respect_channel_rules",
            "no_paid_acquisition_under_rm0_constraint",
        ],
    }


def self_test() -> dict:
    sample = qualify_prospect("Example Prospect", 85, ["public business profile"])
    campaign = plan_campaign(
        "engineering-quote-toolkit",
        "https://newbiezz.gumroad.com/l/neiqwz",
        "community",
        "community-01",
    )
    return {
        "worker": "acquisition-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": [
            "prospect-discovery",
            "prospect-qualification",
            "offer-drafting",
            "campaign-planning",
            "tracking-link-generation",
            "outreach-planning",
            "response-tracking",
            "acquisition-reporting",
        ],
        "restricted_actions": [
            "mass_spam",
            "impersonate",
            "sign_contract",
            "publish_binding_offer",
            "publish_external_content_without_approval",
            "move_money",
            "bypass_platform_rules",
        ],
        "sample": sample,
        "campaign_sample": campaign,
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
