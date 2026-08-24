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
import shutil
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


def _playwright_executable() -> str:
    candidates = ["playwright-cli.cmd", "playwright-cli"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found

    npm_global = os.environ.get("LEVERAGE_NPM_GLOBAL", r"D:\development\node.js\npm-global")
    candidate = os.path.join(npm_global, "playwright-cli.cmd")
    if os.path.exists(candidate):
        return candidate

    raise FileNotFoundError(
        "playwright-cli was not found. Add the npm global bin directory to PATH "
        "or set LEVERAGE_NPM_GLOBAL to the directory containing playwright-cli.cmd."
    )


def _run_cli(*args: str, timeout: int = 60, allow_fail: bool = False) -> str:
    cmd = [_playwright_executable(), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=False)
    output = (proc.stdout + "\n" + proc.stderr).strip()
    if proc.returncode != 0 and not allow_fail:
        raise RuntimeError(output)
    return output


def authorize_goal(goal: str) -> BrowserResult:
    lowered = goal.lower()
    hits = sorted(term for term in FORBIDDEN_TERMS if term in lowered)
    if hits:
        return BrowserResult(False, "authorize", "Blocked goal contains protected action terms.", {"blocked_terms": hits})
    return BrowserResult(True, "authorize", "Goal is within presentation-editing boundary.", {})


def attach_or_open(profile: str, url: str = "https://gumroad.com/products") -> BrowserResult:
    attached = _run_cli("attach", "default", timeout=30, allow_fail=True)
    if "attached" in attached.lower() or "browser" in attached.lower() and "error" not in attached.lower():
        snap = _run_cli("snapshot", timeout=60)
        return BrowserResult(True, "attach_browser", "Attached to existing Playwright browser session.", {"snapshot": snap})

    _run_cli("open", url, "--browser=chromium", "--headed", "--persistent", f"--profile={profile}", timeout=90)
    snap = _run_cli("snapshot", timeout=60)
    return BrowserResult(True, "open_browser", "Browser opened and snapshot captured.", {"snapshot": snap})


def find_product(product_id: str, title_hint: str = "Fabrication Shop Profit & Quote System") -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products", timeout=60)
    snap = _run_cli("snapshot", timeout=60)
    found = product_id in snap and title_hint.lower() in snap.lower()
    return BrowserResult(found, "find_product", "Existing product located." if found else "Target product not found.", {"product_id": product_id, "snapshot": snap})


def _extract_ref(snapshot: str, label: str) -> str | None:
    pattern = rf'(?:textbox|button|combobox) "{re.escape(label)}" \[ref=([^\]]+)\]'
    match = re.search(pattern, snapshot)
    return match.group(1) if match else None


def edit_p001_listing(summary: str, description_html: str) -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products/neiqwz/edit", timeout=60)
    snap = _run_cli("snapshot", timeout=60)

    summary_ref = _extract_ref(snap, "Summary")
    save_ref = _extract_ref(snap, "Save changes")
    if not summary_ref or not save_ref:
        return BrowserResult(False, "edit_p001_listing", "Could not rediscover required Gumroad controls.", {"snapshot": snap})

    _run_cli("fill", summary_ref, summary, timeout=30)
    js = (
        "() => { const el=document.querySelector('[contenteditable=true]'); "
        "if(!el) throw new Error('Description editor not found'); "
        "el.innerHTML='" + description_html.replace("\\", "\\\\").replace("'", "\\'") + "'; "
        "el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText'})); return el.innerText; }"
    )
    _run_cli("eval", js, timeout=30)
    _run_cli("click", save_ref, timeout=30)

    verify = _run_cli("snapshot", timeout=60)
    price_ok = bool(re.search(r'textbox \"Amount\"[^\n]*\"19\"', verify))
    published_ok = "button \"Unpublish\"" in verify
    summary_ok = summary.lower() in verify.lower()
    ok = price_ok and published_ok and summary_ok

    return BrowserResult(
        ok,
        "edit_p001_listing",
        "Listing saved and protected fields verified." if ok else "Save attempted but verification failed.",
        {
            "price_guard": price_ok,
            "published_guard": published_ok,
            "summary_guard": summary_ok,
            "snapshot": verify,
        },
    )


def execute(goal: str, profile: str, product_id: str = "neiqwz") -> BrowserResult:
    auth = authorize_goal(goal)
    if not auth.ok:
        return auth

    browser = attach_or_open(profile)
    if not browser.ok:
        return browser

    product = find_product(product_id)
    if not product.ok:
        return product

    if "optimize" not in goal.lower() and "update" not in goal.lower():
        return BrowserResult(True, "plan_only", "Goal validated and product found; no edit keyword requested.", product.data)

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
    import argparse
    parser = argparse.ArgumentParser(description="Leverage Browser Worker v1")
    parser.add_argument("goal", help='Goal, e.g. "Optimize P-001 Gumroad listing"')
    parser.add_argument("--profile", default=os.environ.get("LEVERAGE_BROWSER_PROFILE", r"D:\Leverage\browser-profile"))
    args = parser.parse_args()
    result = execute(args.goal, args.profile)
    print(json.dumps({"ok": result.ok, "action": result.action, "detail": result.detail, **result.data}, indent=2, ensure_ascii=False))
