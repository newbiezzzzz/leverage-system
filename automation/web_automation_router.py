"""Leverage API-first web automation router.

Low-risk Gumroad tasks use the Gumroad API first. Browserbase/Stagehand is the
unattended fallback for UI-only actions. Credentials are environment-only.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from automation.gumroad_api import FREE_TOOL, P001_ID, run as gumroad_run, verify as gumroad_verify

ROOT = Path(__file__).resolve().parent

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


def _run_browserbase(action: str) -> dict[str, Any]:
    runner = ROOT / "run_browserbase_worker.cmd"
    if not runner.exists():
        raise FileNotFoundError(f"Browserbase runner missing: {runner}")
    env = os.environ.copy()
    env["LEVERAGE_WEB_ACTION"] = action
    env.setdefault("LEVERAGE_WEB_TARGET_URL", FREE_TOOL)
    proc = subprocess.run(
        [str(runner)],
        cwd=str(ROOT.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        shell=False,
        env=env,
    )
    output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode:
        raise RuntimeError(output or f"Browserbase worker exited {proc.returncode}")
    try:
        return json.loads(output.splitlines()[-1])
    except Exception:
        return {"ok": True, "raw": output, "action": action}


def _run_local_bridge(action: str) -> dict[str, Any]:
    """Legacy local bridge fallback when Browserbase isn't configured."""
    bridge = os.environ.get("LEVERAGE_BROWSER_BRIDGE", "http://127.0.0.1:8787/run")
    import urllib.request

    payload = json.dumps({
        "goal": "Update Gumroad Product 1 so buyers can reach the public Leverage free fabrication quote calculator",
        "action": action,
        "product_id": P001_ID,
        "target_url": FREE_TOOL,
    }).encode("utf-8")
    req = urllib.request.Request(bridge, method="POST", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _browser_fallback(action: str) -> dict[str, Any]:
    if _browserbase_enabled():
        return _run_browserbase(action)
    return _run_local_bridge(action)


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
                fallback = _browser_fallback(spec["browser_fallback"])
                return {
                    "ok": bool(fallback.get("ok", fallback.get("success", False))),
                    "route": "browserbase_stagehand" if _browserbase_enabled() else "local_browser_bridge",
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
            fallback = _browser_fallback(spec["browser_fallback"])
            return {
                "ok": bool(fallback.get("ok", fallback.get("success", False))),
                "route": "browserbase_stagehand" if _browserbase_enabled() else "local_browser_bridge",
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
