"""API-first Gumroad automation for Leverage P-001.

Uses GUMROAD_ACCESS_TOKEN from the environment. Secrets are never stored in git.
The worker only performs low-risk product description/summary edits and public
product verification. Financial/account actions are intentionally out of scope.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.gumroad.com/v2"
P001_ID = "neiqwz"
PUBLIC_GUMROAD = f"https://newbiezz.gumroad.com/l/{P001_ID}"
FREE_TOOL = (
    "https://leverage-tools.pages.dev/fabrication-quote-calculator/"
    "?utm_source=gumroad&utm_medium=product&utm_campaign=p001&utm_content=free-calculator"
)
CTA_LABEL = "Try the FREE Fabrication Quote Calculator"
SUMMARY = "Know the cost and margin before you quote."

DESCRIPTION_HTML = f"""<p><strong>{SUMMARY}</strong></p>
<p>A macro-free Excel toolkit for small fabrication, welding, machine and job shops.</p>
<h2>TRY THE FREE TOOL FIRST</h2>
<p><a href=\"{FREE_TOOL}\">{CTA_LABEL}</a></p>
<h2>WHAT YOU GET</h2>
<ul>
<li>Shop Rate Calculator</li>
<li>Quote Builder</li>
<li>Material and Consumables Costing</li>
<li>Target-Margin Profit Check</li>
<li>Job Log — Quoted vs Actual</li>
<li>Change Order Register</li>
<li>Sample Job Data</li>
<li>Quick-Start Guide</li>
</ul>
<h2>WHY IT IS DIFFERENT</h2>
<ul>
<li>Macro-free — no VBA required</li>
<li>No subscription for the workbook</li>
<li>Uses your own rates and assumptions</li>
<li>Built around fabrication and job-shop quoting</li>
<li>Includes the post-job actual-vs-estimate learning loop</li>
</ul>
<h2>WHO IT IS FOR</h2>
<p>Fabrication shops, welding businesses, machine/job shops, engineering workshops and small contractors pricing custom work.</p>
<h2>IMPORTANT</h2>
<p>This is a quoting and job-costing tool, not accounting, tax, legal or engineering certification software. Replace example assumptions with your own verified business inputs.</p>
<p><strong>DIGITAL PRODUCT</strong><br>Downloadable digital files are delivered after purchase.</p>"""


class GumroadAPIError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("GUMROAD_ACCESS_TOKEN", "").strip()
    if not token:
        raise GumroadAPIError("GUMROAD_ACCESS_TOKEN is not configured")
    return token


def request(path: str, method: str = "GET", data: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _token()
    body = None
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "Leverage-Gumroad-Automation/1.0"}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(f"{API}{path}", method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GumroadAPIError(f"Gumroad HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GumroadAPIError(f"Gumroad network error: {exc}") from exc


def get_product() -> dict[str, Any]:
    return request(f"/products/{P001_ID}")


def update_description() -> dict[str, Any]:
    return request(
        f"/products/{P001_ID}",
        method="PUT",
        data={"description": DESCRIPTION_HTML},
    )


def update_summary() -> dict[str, Any]:
    return request(
        f"/products/{P001_ID}",
        method="PUT",
        data={"custom_summary": SUMMARY},
    )


def verify() -> dict[str, Any]:
    product = get_product().get("product", {})
    description = str(product.get("description", ""))
    summary = str(product.get("custom_summary", ""))
    checks = {
        "product_found": product.get("id") is not None,
        "summary_present": SUMMARY in summary or SUMMARY in description,
        "free_tool_url_present": FREE_TOOL in description,
        "cta_label_present": CTA_LABEL in description,
        "public_url": product.get("short_url") or PUBLIC_GUMROAD,
    }
    checks["ok"] = all(
        checks[key] for key in ("product_found", "summary_present", "free_tool_url_present", "cta_label_present")
    )
    return checks


def run() -> dict[str, Any]:
    before = get_product()
    updated = update_description()
    verified = verify()
    return {
        "ok": bool(verified.get("ok")),
        "provider": "gumroad",
        "product_id": P001_ID,
        "action": "update_description_with_public_web_cta",
        "before": before.get("product", {}),
        "updated": updated.get("product", {}),
        "verification": verified,
        "financial_action": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
