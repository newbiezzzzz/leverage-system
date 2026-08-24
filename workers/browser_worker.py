"""Leverage Browser Worker v1.

Goal-driven local browser automation using the installed Playwright CLI.
The worker discovers controls from the current page rather than relying on
stored element IDs. It is intentionally constrained to presentation edits.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
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
    proc = subprocess.run(["playwright-cli", *args], capture_output=True, text=True, timeout=timeout)
    output = (proc.stdout + "\n" + proc.stderr).strip()
    if proc.returncode != 0:
        raise RuntimeError(output)
    return output


def _snapshot() -> str:
    return _run_cli("snapshot", timeout=60)


def _find_ref(label: str) -> str:
    output = _run_cli("find", label, timeout=30)
    match = re.search(r"\[ref=([A-Za-z0-9]+)\]", output)
    if not match:
        raise RuntimeError(f"Could not discover UI target: {label}\n{output}")
    return match.group(1)


def authorize_goal(goal: str) -> BrowserResult:
    lowered = goal.lower()
    hits = sorted(term for term in FORBIDDEN_TERMS if term in lowered)
    if hits:
        return BrowserResult(False, "authorize", "Blocked goal contains protected action terms.", {"blocked_terms": hits})
    return BrowserResult(True, "authorize", "Goal is within presentation-editing boundary.", {})


def open_gumroad(profile: str) -> BrowserResult:
    _run_cli("open", "https://gumroad.com/products", "--browser=chromium", "--headed", "--persistent", f"--profile={profile}", timeout=90)
    return BrowserResult(True, "open_gumroad", "Browser opened.", {"snapshot": _snapshot()})


def find_product(product_id: str, title_hint: str) -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products", timeout=60)
    snap = _snapshot()
    found = product_id in snap and title_hint.lower() in snap.lower()
    return BrowserResult(found, "find_product", "Existing product located." if found else "Target product not found.", {"product_id": product_id, "snapshot": snap})


def _set_description(description_html: str) -> None:
    payload = json.dumps(description_html, ensure_ascii=False)
    js = (
        "(html) => { const editors=[...document.querySelectorAll('[contenteditable=true]')]; "
        "const el=editors.find(e=>e.innerText.includes('Fabrication Shop Profit & Quote System')) || editors[0]; "
        "if(!el) throw new Error('Description editor not found'); el.innerHTML=html; "
        "el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText'})); return el.innerText; }"
    )
    # Pass the JS function and JSON payload as one CLI argument so CMD does not split the content.
    _run_cli("eval", f"{js[:-1]}, {payload})", timeout=30)


def edit_p001_listing(summary: str, description_html: str) -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products/neiqwz/edit", timeout=60)
    summary_ref = _find_ref("Summary")
    _run_cli("fill", summary_ref, summary, timeout=30)
    _set_description(description_html)
    save_ref = _find_ref("Save changes")
    _run_cli("click", save_ref, timeout=30)
    _run_cli("reload", timeout=30)
    snap = _snapshot()
    amount_match = re.search(r'textbox \"Amount\"[^\n]*?:?\s*\"19\"', snap)
    price_ok = bool(amount_match) or ('Amount' in snap and '"19"' in snap)
    published_ok = 'button "Unpublish"' in snap
    summary_ok = summary.lower() in snap.lower()
    ok = price_ok and published_ok and summary_ok
    return BrowserResult(ok, "edit_p001_listing", "Listing edited and safety checks passed." if ok else "Verification failed; no further action taken.", {"price_guard": price_ok, "published_guard": published_ok, "summary_guard": summary_ok, "snapshot": snap})


def execute(goal: str, profile: str, product_id: str = "neiqwz") -> BrowserResult:
    auth = authorize_goal(goal)
    if not auth.ok:
        return auth
    open_gumroad(profile)
    product = find_product(product_id, "Fabrication Shop Profit & Quote System")
    if not product.ok:
        return product
    lowered = goal.lower()
    if not ("optimize" in lowered or "update" in lowered):
        return BrowserResult(True, "plan_only", "Goal validated and product found; no edit requested.", product.data)

    summary = "Know the cost and margin before you quote."
    description_html = (
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
    return edit_p001_listing(summary, description_html)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leverage Browser Worker v1")
    parser.add_argument("goal", help='Goal, e.g. "Optimize P-001 Gumroad listing"')
    parser.add_argument("--profile", default=os.environ.get("LEVERAGE_BROWSER_PROFILE", r"D:\Leverage\browser-profile"))
    args = parser.parse_args()
    result = execute(args.goal, args.profile)
    print(json.dumps({"ok": result.ok, "action": result.action, "detail": result.detail, **result.data}, indent=2, ensure_ascii=False))
