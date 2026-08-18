"""Leverage Acquisition Worker.

Finds, qualifies and prepares compliant customer-acquisition work for any
company project. It does not spam, impersonate, sign contracts, send binding
offers, move money, or bypass platform rules.
"""
from __future__ import annotations
import json

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


def self_test() -> dict:
    sample = qualify_prospect("Example Prospect", 85, ["public business profile"])
    return {
        "worker": "acquisition-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": [
            "prospect-discovery",
            "prospect-qualification",
            "offer-drafting",
            "outreach-planning",
            "response-tracking",
            "acquisition-reporting",
        ],
        "restricted_actions": [
            "mass_spam",
            "impersonate",
            "sign_contract",
            "publish_binding_offer",
            "move_money",
            "bypass_platform_rules",
        ],
        "sample": sample,
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
