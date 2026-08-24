"""Leverage Browser Worker v1.

Goal-driven local browser automation using Playwright CLI.

This worker is intentionally constrained: it may edit marketplace presentation
fields, but it will refuse money movement, payout/security changes, price changes,
or publishing/unpublishing actions. The authenticated browser session remains on
 the Owner machine in the dedicated Playwright profile.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORBIDDEN_TERMS = {
    "price", "pricing", "amount", "payout", "bank", "password", "email",
    "payment", "refund", "unpublish", "publish", "delete", "money",
    "withdraw", "tax", "security", "account owner",
}

@dataclass
class BrowserResult:
    ok: bool
    action: str
    detail: str
    data: dict[str, Any]


def _run_cli(*args: str, timeout: int = 60) -> str:
    cmd = ["playwright-cli", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError((proc.stdout + "\n" + proc.stderr).strip())
    return proc.stdout.strip()


def authorize_goal(goal: str) -> BrowserResult:
    lowered = goal.lower()
    hits = sorted(term for term in FORBIDDEN_TERMS if term in lowered)
    if hits:
        return BrowserResult(False, "authorize", "Blocked goal contains protected action terms.", {"blocked_terms": hits})
    return BrowserResult(True, "authorize", "Goal is within presentation-editing boundary.", {})


def open_gumroad(profile: str, url: str = "https://gumroad.com/products") -> BrowserResult:
    _run_cli("open", url, "--browser=chromium", "--headed", "--persistent", f"--profile={profile}", timeout=90)
    snap = _run_cli("snapshot", timeout=60)
    return BrowserResult(True, "open_gumroad", "Browser opened and snapshot captured.", {"snapshot": snap})


def find_product(product_id: str, title_hint: str = "Fabrication Shop Profit & Quote System") -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products", timeout=60)
    snap = _run_cli("snapshot", timeout=60)
    found = product_id in snap and title_hint.lower() in snap.lower()
    return BrowserResult(found, "find_product", "Existing product located." if found else "Target product not found.", {"product_id": product_id, "snapshot": snap})


def edit_p001_listing(summary: str, description: str) -> BrowserResult:
    # Open the known editor after product discovery has passed.
    _run_cli("goto", "https://gumroad.com/products/neiqwz/edit", timeout=60)
    _run_cli("fill", "f4e237", summary, timeout=30)
    # Use page-evaluated DOM replacement in one line to avoid CMD multiline quoting.
    js = (
        "() => { const el=document.querySelector('[contenteditable=true]'); "
        "if(!el) throw new Error('Description editor not found'); "
        "el.innerHTML='" + description.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "<br>") + "'; "
        "el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText'})); return el.innerText; }"
    )
    _run_cli("eval", js, timeout=30)
    _run_cli("click", "f4e64", timeout=30)
    snap = _run_cli("snapshot", timeout=60)
    price_ok = bool(re.search(r'textbox \"Amount\"[^\n]*\"19\"', snap))
    return BrowserResult(
        price_ok,
        "edit_p001_listing",
        "Listing saved and price guard verified." if price_ok else "Save completed but price guard could not be verified.",
        {"price_guard": price_ok, "snapshot": snap},
    )


def execute(goal: str, profile: str, product_id: str = "neiqwz") -> BrowserResult:
    auth = authorize_goal(goal)
    if not auth.ok:
        return auth
    open_result = open_gumroad(profile)
    if not open_result.ok:
        return open_result
    product = find_product(product_id)
    if not product.ok:
        return product
    if "optimize" not in goal.lower() and "update" not in goal.lower():
        return BrowserResult(True, "plan_only", "Goal validated and product found; no edit keyword requested.", product.data)

    summary = "Know the cost and margin before you quote."
    description = (
        "<p><strong>Know the cost and margin before you quote.</strong></p>"
        "<p>A macro-free Excel toolkit for small fabrication, welding, machine and job shops.</p>"
        "<p><strong>WHAT YOU GET</strong></p>"
        "<p>• Shop Rate Calculator<br>• Quote Builder<br>• Material &amp; Consumables Costing<br>"
        "• Target-Margin Profit Check<br>• Job Log — Quoted vs Actual<br>• Change Order Register<br>"
        "• Sample Job Data<br>• Quick-Start Guide</p>"
        "<p><strong>WHY IT IS DIFFERENT</strong></p>"
        "<p>• Macro-free — no VBA required<br>• No subscription for the workbook<br>"
        "• Uses your own rates and assumptions<br>• Built around fabrication and job-shop quoting<br>"
        "• Includes the post-job actual-vs-estimate learning loop</p>"
        "<p><strong>WHO IT IS FOR</strong></p>"
        "<p>Fabrication shops, welding businesses, machine/job shops, engineering workshops and small contractors pricing custom work.</p>"
        "<p><strong>IMPORTANT</strong></p>"
        "<p>This is a quoting and job-costing tool, not accounting, tax, legal or engineering certification software. Replace example assumptions with your own verified business inputs.</p>"
        "<p><strong>DIGITAL PRODUCT</strong></p><p>You receive downloadable digital files after purchase.</p>"
    )
    return edit_p001_listing(summary, description)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Leverage Browser Worker v1")
    parser.add_argument("goal", help='Goal, e.g. "Optimize P-001 Gumroad listing"')
    parser.add_argument("--profile", default=os.environ.get("LEVERAGE_BROWSER_PROFILE", r"D:\Leverage\browser-profile"))
    args = parser.parse_args()
    result = execute(args.goal, args.profile)
    print(json.dumps({"ok": result.ok, "action": result.action, "detail": result.detail, **result.data}, indent=2, ensure_ascii=False))
