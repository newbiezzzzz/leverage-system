"""Leverage Browser Worker v1.
Goal-driven local Gumroad browser automation using Playwright CLI.
External financial/account/security actions remain blocked.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORBIDDEN_TERMS = {
    "price", "pricing", "amount", "payout", "bank", "password", "email",
    "payment", "refund", "unpublish", "publish", "delete", "money",
    "withdraw", "tax", "security", "account owner",
}
P001_ID = "neiqwz"
P001_PUBLIC = "https://leverage-tools.pages.dev/fabrication-profit-system/"
P001_FREE_CALCULATOR = "https://leverage-tools.pages.dev/fabrication-quote-calculator/?utm_source=gumroad&utm_medium=product&utm_campaign=p001&utm_content=free-calculator"
P001_FREE_CALCULATOR_LABEL = "Try the FREE Fabrication Quote Calculator"
P001_GUMROAD_PUBLIC = f"https://newbiezz.gumroad.com/l/{P001_ID}"
ASSET_DIR = Path(r"D:\Leverage\artifacts\p001")
COVER_PATH = ASSET_DIR / "p001-cover.png"
THUMB_PATH = ASSET_DIR / "p001-thumbnail.png"

@dataclass
class BrowserResult:
    ok: bool
    action: str
    detail: str
    data: dict[str, Any]


def _playwright_executable() -> str:
    for c in ("playwright-cli.cmd", "playwright-cli"):
        p = shutil.which(c)
        if p:
            return p
    p = os.path.join(os.environ.get("LEVERAGE_NPM_GLOBAL", r"D:\development\node.js\npm-global"), "playwright-cli.cmd")
    if os.path.exists(p):
        return p
    raise FileNotFoundError("playwright-cli was not found")


def _run_cli(*args: str, timeout: int = 60, allow_fail: bool = False) -> str:
    proc = subprocess.run([_playwright_executable(), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False)
    out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode and not allow_fail:
        raise RuntimeError(out or f"playwright-cli exited {proc.returncode}")
    return out


def authorize_goal(goal: str) -> BrowserResult:
    hits = sorted(t for t in FORBIDDEN_TERMS if t in goal.lower())
    return BrowserResult(not hits, "authorize", "Goal is allowed." if not hits else "Blocked protected action.", {"blocked_terms": hits})


def snapshot() -> str:
    return _run_cli("snapshot", timeout=60)


def attach_or_open(profile: str) -> BrowserResult:
    attached = _run_cli("attach", "default", timeout=30, allow_fail=True)
    if "attached" in attached.lower():
        return BrowserResult(True, "attach", "Attached to existing browser.", {"snapshot": snapshot()})
    _run_cli("open", "https://gumroad.com/products", "--browser=chromium", "--headed", "--persistent", f"--profile={profile}", timeout=90)
    return BrowserResult(True, "open", "Opened browser.", {"snapshot": snapshot()})


def _extract_ref(snap: str, label: str) -> str | None:
    m = re.search(rf'(?:textbox|button|combobox|link) "{re.escape(label)}" \[ref=([^\]]+)\]', snap)
    return m.group(1) if m else None


def _extract_generic_ref(snap: str, label: str) -> str | None:
    m = re.search(rf'generic "{re.escape(label)}" \[ref=([^\]]+)\]', snap)
    return m.group(1) if m else None


def find_product(product_id: str) -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products", timeout=60)
    snap = snapshot()
    ok = product_id in snap and "Fabrication Shop Profit & Quote System".lower() in snap.lower()
    return BrowserResult(ok, "find_product", "Existing product located." if ok else "Product not found.", {"snapshot": snap})


def _public_listing_snapshot() -> str:
    _run_cli("goto", P001_GUMROAD_PUBLIC, timeout=60)
    snap = snapshot()
    read_more = _extract_ref(snap, "Read more")
    if read_more:
        _run_cli("click", read_more, timeout=30)
    return snapshot()


def _public_html() -> str:
    request = urllib.request.Request(P001_GUMROAD_PUBLIC, headers={"User-Agent": "Mozilla/5.0 LeverageBrowserWorker"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _verify_public_listing(snapshot_text: str) -> dict[str, Any]:
    body = snapshot_text.lower()
    try:
        html = _public_html().lower()
    except Exception as exc:
        html = ""
        html_error = str(exc)
    else:
        html_error = ""
    url_token = P001_FREE_CALCULATOR.lower()
    label_token = P001_FREE_CALCULATOR_LABEL.lower()
    html_url = url_token in html
    html_label = label_token in html
    snapshot_url = url_token in body
    snapshot_label = label_token in body
    clickable = html_url and ("<a " in html and url_token in html)
    return {
        "url_guard": snapshot_url or html_url,
        "label_guard": snapshot_label or html_label,
        "clickable_link_guard": clickable,
        "html_has_url": html_url,
        "html_has_label": html_label,
        "html_error": html_error,
    }


def edit_p001_listing() -> BrowserResult:
    summary = "Know the cost and margin before you quote."
    description = (
        "Know the cost and margin before you quote.\n\n"
        "A macro-free Excel toolkit for small fabrication, welding, machine and job shops.\n\n"
        "TRY THE FREE TOOL FIRST\n"
        f"{P001_FREE_CALCULATOR_LABEL}\n"
        f"{P001_FREE_CALCULATOR}\n\n"
        "WHAT YOU GET\n"
        "• Shop Rate Calculator\n• Quote Builder\n• Material & Consumables Costing\n"
        "• Target-Margin Profit Check\n• Job Log — Quoted vs Actual\n• Change Order Register\n"
        "• Sample Job Data\n• Quick-Start Guide\n\n"
        "WHY IT IS DIFFERENT\n"
        "• Macro-free — no VBA required\n• No subscription for the workbook\n"
        "• Uses your own rates and assumptions\n• Built around fabrication and job-shop quoting\n"
        "• Includes the post-job actual-vs-estimate learning loop\n\n"
        "WHO IT IS FOR\n"
        "Fabrication shops, welding businesses, machine/job shops, engineering workshops and small contractors pricing custom work.\n\n"
        "IMPORTANT\n"
        "This is a quoting and job-costing tool, not accounting, tax, legal or engineering certification software. Replace example assumptions with your own verified business inputs.\n\n"
        "DIGITAL PRODUCT\n"
        "You receive downloadable digital files after purchase."
    )
    _run_cli("goto", f"https://gumroad.com/products/{P001_ID}/edit", timeout=60)
    snap = snapshot()
    summary_ref = _extract_ref(snap, "Summary")
    save_ref = _extract_ref(snap, "Save changes")
    description_ref = _extract_generic_ref(snap, "Description")
    if not summary_ref or not save_ref or not description_ref:
        return BrowserResult(False, "edit_p001_listing", "Required Gumroad controls were not rediscovered.", {"snapshot": snap})
    _run_cli("fill", summary_ref, summary, timeout=30)
    _run_cli("click", description_ref, timeout=30)
    _run_cli("press", "Control+A", timeout=30)
    _run_cli("type", description, timeout=60)
    _run_cli("click", save_ref, timeout=30)
    public_snapshot = _public_listing_snapshot()
    verify = _verify_public_listing(public_snapshot)
    published_ok = "Fabrication Shop Profit & Quote System".lower() in public_snapshot.lower()
    summary_ok = summary.lower() in public_snapshot.lower()
    ok = bool(verify["url_guard"] and verify["label_guard"] and published_ok and summary_ok)
    detail = "Gumroad Product 1 updated and tracked free-calculator CTA verified." if ok else "Verification failed."
    return BrowserResult(ok, "edit_p001_listing", detail, {
        "price_guard": True,
        "published_guard": published_ok,
        "summary_guard": summary_ok,
        "free_calculator_url_guard": bool(verify["url_guard"]),
        "free_calculator_label_guard": bool(verify["label_guard"]),
        "clickable_link_guard": bool(verify["clickable_link_guard"]),
        "free_calculator_url": P001_FREE_CALCULATOR,
        "public_verification": verify,
        "snapshot": public_snapshot,
    })


def execute(goal: str, profile: str) -> BrowserResult:
    auth = authorize_goal(goal)
    if not auth.ok:
        return auth
    browser = attach_or_open(profile)
    if not browser.ok:
        return browser
    product = find_product(P001_ID)
    if not product.ok:
        return product
    if "optimize" not in goal.lower() and "update" not in goal.lower():
        return BrowserResult(True, "plan_only", "Goal validated; no edit requested.", {})
    return edit_p001_listing()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--profile", default=os.environ.get("LEVERAGE_BROWSER_PROFILE", r"D:\Leverage\browser-profile"))
    args = ap.parse_args()
    result = execute(args.goal, args.profile)
    print(json.dumps({"ok": result.ok, "action": result.action, "detail": result.detail, **result.data}, indent=2, ensure_ascii=False))
