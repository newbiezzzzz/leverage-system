"""Leverage Browser Worker v1."""
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
    for c in ("playwright-cli.cmd", "playwright-cli"):
        p = shutil.which(c)
        if p:
            return p
    p = os.path.join(
        os.environ.get("LEVERAGE_NPM_GLOBAL", r"D:\development\node.js\npm-global"),
        "playwright-cli.cmd",
    )
    if os.path.exists(p):
        return p
    raise FileNotFoundError("playwright-cli was not found")


def _run_cli(*args: str, timeout: int = 60, allow_fail: bool = False) -> str:
    proc = subprocess.run(
        [_playwright_executable(), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    out = out.strip()
    if proc.returncode and not allow_fail:
        raise RuntimeError(out or f"playwright-cli exited {proc.returncode}")
    return out


def authorize_goal(goal: str) -> BrowserResult:
    hits = sorted(t for t in FORBIDDEN_TERMS if t in goal.lower())
    return BrowserResult(
        not hits,
        "authorize",
        "Goal is allowed." if not hits else "Blocked protected action.",
        {"blocked_terms": hits},
    )


def snapshot() -> str:
    return _run_cli("snapshot", timeout=60)


def attach_or_open(profile: str) -> BrowserResult:
    attached = _run_cli("attach", "default", timeout=30, allow_fail=True)
    if "attached" in attached.lower():
        return BrowserResult(True, "attach", "Attached to existing browser.", {"snapshot": snapshot()})
    _run_cli(
        "open",
        "https://gumroad.com/products",
        "--browser=chromium",
        "--headed",
        "--persistent",
        f"--profile={profile}",
        timeout=90,
    )
    return BrowserResult(True, "open", "Opened browser.", {"snapshot": snapshot()})


def _extract_ref(snap: str, label: str) -> str | None:
    m = re.search(rf'(?:textbox|button|combobox) "{re.escape(label)}" \[ref=([^\]]+)\]', snap)
    return m.group(1) if m else None


def _extract_generic_ref(snap: str, label: str) -> str | None:
    m = re.search(rf'generic "{re.escape(label)}" \[ref=([^\]]+)\]', snap)
    return m.group(1) if m else None


def find_product(product_id: str) -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products", timeout=60)
    snap = snapshot()
    ok = product_id in snap and "Fabrication Shop Profit & Quote System".lower() in snap.lower()
    return BrowserResult(
        ok,
        "find_product",
        "Existing product located." if ok else "Product not found.",
        {"snapshot": snap},
    )


def edit_p001_listing() -> BrowserResult:
    summary = "Know the cost and margin before you quote."
    description = (
        "Know the cost and margin before you quote.\n\n"
        "A macro-free Excel toolkit for small fabrication, welding, machine and job shops.\n\n"
        "WHAT YOU GET\n"
        "• Shop Rate Calculator\n"
        "• Quote Builder\n"
        "• Material & Consumables Costing\n"
        "• Target-Margin Profit Check\n"
        "• Job Log — Quoted vs Actual\n"
        "• Change Order Register\n"
        "• Sample Job Data\n"
        "• Quick-Start Guide\n\n"
        "WHY IT IS DIFFERENT\n"
        "• Macro-free — no VBA required\n"
        "• No subscription for the workbook\n"
        "• Uses your own rates and assumptions\n"
        "• Built around fabrication and job-shop quoting\n"
        "• Includes the post-job actual-vs-estimate learning loop\n\n"
        "WHO IT IS FOR\n"
        "Fabrication shops, welding businesses, machine/job shops, engineering workshops and small contractors pricing custom work.\n\n"
        "IMPORTANT\n"
        "This is a quoting and job-costing tool, not accounting, tax, legal or engineering certification software. Replace example assumptions with your own verified business inputs.\n\n"
        "DIGITAL PRODUCT\n"
        "You receive downloadable digital files after purchase."
    )

    _run_cli("goto", "https://gumroad.com/products/neiqwz/edit", timeout=60)
    snap = snapshot()
    summary_ref = _extract_ref(snap, "Summary")
    save_ref = _extract_ref(snap, "Save changes")
    description_ref = _extract_generic_ref(snap, "Description")

    if not summary_ref or not save_ref or not description_ref:
        return BrowserResult(
            False,
            "edit_p001_listing",
            "Required Gumroad controls were not rediscovered.",
            {"snapshot": snap, "summary_ref": summary_ref, "description_ref": description_ref, "save_ref": save_ref},
        )

    _run_cli("fill", summary_ref, summary, timeout=30)
    _run_cli("click", description_ref, timeout=30)
    _run_cli("press", "Control+A", timeout=30)
    _run_cli("type", description, timeout=60)
    _run_cli("click", save_ref, timeout=30)

    verify = snapshot()
    price_ok = bool(re.search(r'textbox "Amount"[^\n]*"19"', verify))
    published_ok = 'button "Unpublish"' in verify
    summary_ok = summary.lower() in verify.lower()
    ok = price_ok and published_ok and summary_ok

    return BrowserResult(
        ok,
        "edit_p001_listing",
        "Listing saved and protected fields verified." if ok else "Verification failed.",
        {
            "price_guard": price_ok,
            "published_guard": published_ok,
            "summary_guard": summary_ok,
            "snapshot": verify,
        },
    )


def execute(goal: str, profile: str) -> BrowserResult:
    auth = authorize_goal(goal)
    if not auth.ok:
        return auth
    browser = attach_or_open(profile)
    if not browser.ok:
        return browser
    product = find_product("neiqwz")
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
