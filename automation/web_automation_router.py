"""Leverage API-first web automation router.

Route low-risk Gumroad actions through the Gumroad API first. Browserbase is
reserved for UI-only actions. No credentials are stored in this repository.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from automation.gumroad_api import FREE_TOOL, P001_ID, run as gumroad_run, verify as gumroad_verify


SAFE_ACTIONS = {
    "update_gumroad_public_web_cta": {
        "provider": "gumroad",
        "api": "update_description",
        "browser_fallback": "edit_description",
    },
    "verify_gumroad_public_web_cta": {
        "provider": "gumroad",
        "api": "verify",
        "browser_fallback": "verify_public_listing",
    },
}


def _browserbase_enabled() -> bool:
    return bool(os.environ.get("BROWSERBASE_API_KEY"))


def _run_browser_fallback(action: str) -> dict[str, Any]:
    """Invoke the local guarded browser bridge when API is insufficient.

    Browserbase can replace the local bridge later without changing the workflow
    contract; this fallback keeps the current zero-cost local path operational.
    """
    bridge = os.environ.get("LEVERAGE_BROWSER_BRIDGE", "http://127.0.0.1:8787/run")
    # Do not send secrets. The bridge is responsible for its own authenticated
    # browser session or Browserbase-backed execution.
    import urllib.request

    payload = json.dumps({
        "goal": "Update Gumroad Product 1 description so the buyer can reach the public Leverage free fabrication quote calculator",
        "action": action,
        "product_id": P001_ID,
        "target_url": FREE_TOOL,
    }).encode("utf-8")
    req = urllib.request.Request(
        bridge,
        method="POST",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def execute(action: str) -> dict[str, Any]:
    if action not in SAFE_ACTIONS:
        return {"ok": False, "error": "unsupported_or_protected_action", "action": action}

    spec = SAFE_ACTIONS[action]
    if action == "update_gumroad_public_web_cta":
        try:
            result = gumroad_run()
            return {
                "ok": bool(result.get("ok")),
                "route": "gumroad_api",
                "browserbase_configured": _browserbase_enabled(),
                "result": result,
            }
        except Exception as api_error:
            try:
                fallback = _run_browser_fallback(spec["browser_fallback"])
                return {
                    "ok": bool(fallback.get("ok", fallback.get("success", False))),
                    "route": "browser_fallback",
                    "browserbase_configured": _browserbase_enabled(),
                    "api_error": str(api_error),
                    "result": fallback,
                }
            except Exception as browser_error:
                return {
                    "ok": False,
                    "route": "none",
                    "browserbase_configured": _browserbase_enabled(),
                    "api_error": str(api_error),
                    "browser_error": str(browser_error),
                }

    try:
        return {
            "ok": True,
            "route": "gumroad_api",
            "browserbase_configured": _browserbase_enabled(),
            "result": gumroad_verify(),
        }
    except Exception as api_error:
        try:
            fallback = _run_browser_fallback(spec["browser_fallback"])
            return {
                "ok": bool(fallback.get("ok", fallback.get("success", False))),
                "route": "browser_fallback",
                "browserbase_configured": _browserbase_enabled(),
                "api_error": str(api_error),
                "result": fallback,
            }
        except Exception as browser_error:
            return {
                "ok": False,
                "route": "none",
                "browserbase_configured": _browserbase_enabled(),
                "api_error": str(api_error),
                "browser_error": str(browser_error),
            }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=sorted(SAFE_ACTIONS))
    args = parser.parse_args()
    print(json.dumps(execute(args.action), indent=2, ensure_ascii=False))
