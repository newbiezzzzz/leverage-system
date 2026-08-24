"""Guarded marketplace action planner.

The worker prepares marketplace actions and chooses API vs browser mode. It does not
execute financial/account-security changes.
"""
from __future__ import annotations

FORBIDDEN = {
    "move_money", "approve_payout", "change_bank_details", "change_password",
    "change_account_email", "bypass_platform_rules", "mass_spam",
}


def prepare_listing(marketplace: str, product: dict) -> dict:
    return {
        "marketplace": marketplace,
        "title": product.get("title", product.get("name", "Product")),
        "description": product.get("description", ""),
        "price": product.get("price"),
        "assets": product.get("assets", []),
        "execution": "api_or_browser_guarded",
        "approval_required": False,
        "financial_action": False,
    }


def authorize_action(action: str) -> dict:
    if action in FORBIDDEN:
        return {"allowed": False, "reason": f"blocked by financial/security policy: {action}"}
    return {"allowed": True, "reason": "within marketplace publishing boundary"}
