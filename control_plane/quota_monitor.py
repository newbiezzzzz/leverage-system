"""Quota Monitor worker for Leverage.

Collects provider observations through pluggable adapters. No provider is assumed
unlimited. Unknown provider quotas are explicitly reported as safe-mode unknown.
The core itself uses only the Python standard library.
"""
from __future__ import annotations
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from control_plane.leverage_core import ResourceManager, ResourceState

OUT = Path("dashboard/resource_limits.json")


def now():
    return datetime.now(timezone.utc).isoformat()


def github_rate_limit():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return ResourceState("GitHub", "REST API requests", quota_verified=False, source="quota_monitor")
    req = urllib.request.Request("https://api.github.com/rate_limit", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "Leverage-Quota-Monitor"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
        core = data.get("resources", {}).get("core", {})
        return ResourceState("GitHub", "REST API requests", used=core.get("used"), limit=core.get("limit"), remaining=core.get("remaining"), reset_at=datetime.fromtimestamp(core.get("reset", 0), timezone.utc).isoformat() if core.get("reset") else None, quota_verified=True, source="github:/rate_limit", checked_at=now())
    except Exception as exc:
        return ResourceState("GitHub", "REST API requests", quota_verified=False, source=f"error:{type(exc).__name__}", checked_at=now())


def unknown(provider, metric):
    return ResourceState(provider, metric, quota_verified=False, source="provider_quota_not_exposed", checked_at=now())


def main():
    manager = ResourceManager()
    states = [github_rate_limit(), unknown("Gemini", "API quota"), unknown("GitHub Actions", "workflow minutes"), unknown("GitHub Pages", "deployment availability")]
    for state in states:
        manager.register(state)
    snapshot = manager.snapshot()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
