"""Guarded marketplace action planner.

Prepares marketplace actions and chooses API vs browser mode. For browser-capable
marketplaces it emits a concrete local Browser Worker goal/command, while keeping
financial/account/security actions outside the worker's authority.
"""
from __future__ import annotations

FORBIDDEN = {
    "move_money", "approve_payout", "change_bank_details", "change_password",
    "change_account_email", "bypass_platform_rules", "mass_spam",
}

BROWSER_CAPABLE = {"gumroad", "itch", "cgtrader", "fab"}


def prepare_listing(marketplace: str, product: dict) -> dict:
    marketplace_key = marketplace.lower()
    browser_mode = marketplace_key in BROWSER_CAPABLE
    product_id = str(product.get("marketplace_product_id", product.get("product_id", ""))).strip()
    return {
        "marketplace": marketplace,
        "title": product.get("title", product.get("name", "Product")),
        "description": product.get("description", ""),
        "price": product.get("price"),
        "assets": product.get("assets", []),
        "execution": "browser_worker" if browser_mode else "api_or_browser_guarded",
        "browser_worker": {
            "enabled": browser_mode,
            "goal": f"Optimize {product.get('name', product.get('title', 'product'))} marketplace listing",
            "marketplace": marketplace_key,
            "product_id": product_id,
            "command": 'tools\\run-browser-worker.cmd "Optimize {0} marketplace listing"'.format(
                product.get('name', product.get('title', 'product'))
            ),
            "financial_actions_allowed": False,
        },
        "approval_required": False,
        "financial_action": False,
    }


def authorize_action(action: str) -> dict:
    if action in FORBIDDEN:
        return {"allowed": False, "reason": f"blocked by financial/security policy: {action}"}
    return {"allowed": True, "reason": "within marketplace publishing boundary"}
