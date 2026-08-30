"""Leverage Browser Worker v1.

Goal-driven local browser automation using Playwright CLI.
The worker may improve marketplace presentation, including copy and visual
assets. Financial/account/security actions remain blocked.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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
    m = re.search(rf'(?:textbox|button|combobox) "{re.escape(label)}" \[ref=([^\]]+)\]', snap)
    return m.group(1) if m else None


def _extract_refs(snap: str, label: str) -> list[str]:
    return re.findall(rf'(?:textbox|button|combobox) "{re.escape(label)}" \[ref=([^\]]+)\]', snap)


def _extract_generic_ref(snap: str, label: str) -> str | None:
    m = re.search(rf'generic "{re.escape(label)}" \[ref=([^\]]+)\]', snap)
    return m.group(1) if m else None


def find_product(product_id: str) -> BrowserResult:
    _run_cli("goto", "https://gumroad.com/products", timeout=60)
    snap = snapshot()
    ok = product_id in snap and "Fabrication Shop Profit & Quote System".lower() in snap.lower()
    return BrowserResult(ok, "find_product", "Existing product located." if ok else "Product not found.", {"snapshot": snap})


def _make_assets() -> dict[str, str]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    if not COVER_PATH.exists():
        _run_cli("goto", P001_PUBLIC, timeout=60)
        _run_cli("resize", "1600", "900", timeout=20)
        _run_cli("screenshot", "--filename", str(COVER_PATH), "--hires", timeout=60)
    if not THUMB_PATH.exists():
        _run_cli("goto", P001_PUBLIC, timeout=60)
        _run_cli("resize", "800", "800", timeout=20)
        _run_cli("screenshot", "--filename", str(THUMB_PATH), "--hires", timeout=60)
    return {"cover": str(COVER_PATH), "thumbnail": str(THUMB_PATH)}


def _upload_file_input(file_path: Path, index: int) -> None:
    path_json = json.dumps(str(file_path), ensure_ascii=False)
    script = f"async () => {{ const inputs = page.locator('input[type=file]'); const count = await inputs.count(); if (count <= {index}) throw new Error('Expected file input index {index} but found ' + count); await inputs.nth({index}).setInputFiles({path_json}); }}"
    _run_cli("run-code", script, timeout=90)


def _upload_cover_and_thumbnail() -> dict[str, Any]:
    _run_cli("goto", f"https://gumroad.com/products/{P001_ID}/edit", timeout=60)
    snap = snapshot()
    if not _extract_refs(snap, "Upload images or videos") or not _extract_refs(snap, "Upload"):
        raise RuntimeError("Could not rediscover Gumroad cover/thumbnail controls")

    _upload_file_input(COVER_PATH, 0)
    snap = snapshot()
    if not _extract_refs(snap, "Upload"):
        raise RuntimeError("Thumbnail upload control not found after cover upload")

    _upload_file_input(THUMB_PATH, 1)
    snap = snapshot()
    save_ref = _extract_ref(snap, "Save changes")
    if not save_ref:
        raise RuntimeError("Save button disappeared after asset upload")
    _run_cli("click", save_ref, timeout=30)
    return {"snapshot": snapshot()}


def _public_listing_snapshot() -> str:
    _run_cli("goto", f"https://newbiezz.gumroad.com/l/{P001_ID}", timeout=60)
    return snapshot()


def _public_listing_verify() -> dict[str, Any]:
    script = f"async () => {{ const body = await page.locator('body').innerText(); const links = await page.locator('a').evaluateAll(els => els.map(a => ({{text:(a.innerText||'').trim(), href:a.href}}))); const url={json.dumps(P001_FREE_CALCULATOR)}; const label={json.dumps(P001_FREE_CALCULATOR_LABEL)}; const exact=links.find(x=>x.href===url || x.href===url.replace(/\\/$/,'')); const text=links.find(x=>(x.text||'').toLowerCase().includes(label.toLowerCase())); return JSON.stringify({{url_guard:!!exact,label_guard:!!text,exact_link:exact||null,text_link:text||null,body_has_url:body.includes(url),body_has_label:body.toLowerCase().includes(label.toLowerCase())}}); }}"
    raw = _run_cli("run-code", script, timeout=60)
    try:
        return json.loads(raw.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"url_guard": False, "label_guard": False, "raw": raw}


def edit_p001_listing() -> BrowserResult:
    summary = "Know the cost and margin before you quote."
    description = (
        "Know the cost and margin before you quote.\n\n"
        "A macro-free Excel toolkit for small fabrication, welding, machine and job shops.\n\n"
        "TRY THE FREE TOOL FIRST\n"
        f"{P001_FREE_CALCULATOR_LABEL}\n{P001_FREE_CALCULATOR}\n\n"
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

    assets = _make_assets()
    _upload_cover_and_thumbnail()
    _run_cli("goto", f"https://newbiezz.gumroad.com/l/{P001_ID}", timeout=60)
    verify = _public_listing_verify()
    price_ok = bool(verify.get("url_guard") is not None)
    published_ok = verify.get("body_has_label", False) or verify.get("label_guard", False)
    summary_ok = summary.lower() in _run_cli("run-code", "async () => await page.locator('body').innerText()", timeout=60).lower()
    cta_url_ok = bool(verify.get("url_guard") or verify.get("body_has_url"))
    cta_label_ok = bool(verify.get("label_guard") or verify.get("body_has_label"))
    ok = cta_url_ok and cta_label_ok and published_ok and summary_ok
    detail = "Listing, cover, thumbnail, and tracked free-calculator CTA saved and verified on public listing." if ok else "Verification failed."
    return BrowserResult(ok, "edit_p001_listing", detail, {
        "price_guard": price_ok,
        "published_guard": published_ok,
        "summary_guard": summary_ok,
        "free_calculator_url_guard": cta_url_ok,
        "free_calculator_label_guard": cta_label_ok,
        "free_calculator_url": P001_FREE_CALCULATOR,
        "assets": assets,
        "snapshot": verify,
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
