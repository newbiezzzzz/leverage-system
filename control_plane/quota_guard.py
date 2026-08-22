"""Small, deterministic resource guard for Leverage automation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESOURCE_STATE = ROOT / "resource_state.json"
ACQUISITION_CONFIG = ROOT / "acquisition_config.json"


def load_json(path: Path, fallback: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def automation_policy() -> dict:
    state = load_json(RESOURCE_STATE, {})
    policy = state.get("policy", {}) if isinstance(state.get("policy"), dict) else {}
    resources = state.get("resources", []) if isinstance(state.get("resources"), list) else []
    unknown = [r.get("provider") for r in resources if r.get("status") == "unknown_quota_safe_mode"]
    return {
        "safe_mode": bool(unknown),
        "unknown_quota_providers": [x for x in unknown if x],
        "warning_threshold": float(policy.get("warning_threshold", 0.8)),
        "critical_threshold": float(policy.get("critical_threshold", 0.95)),
        "no_unbounded_retry": bool(policy.get("no_unbounded_retry", True)),
        "zero_cost_core": bool(policy.get("zero_cost_core", True)),
    }


def acquisition_daily_targets() -> dict[str, int]:
    config = load_json(ACQUISITION_CONFIG, {})
    channels = config.get("channels", [])
    result: dict[str, int] = {}
    if isinstance(channels, list):
        for channel in channels:
            if not isinstance(channel, dict):
                continue
            name = str(channel.get("name", "")).strip()
            try:
                target = max(0, int(channel.get("daily_target", 0)))
            except (TypeError, ValueError):
                target = 0
            if name:
                result[name] = target
    return result


def acquisition_budget() -> dict:
    targets = acquisition_daily_targets()
    # Draft planning is local and cheap; keep the queue bounded even when
    # provider quotas are unknown. Safe mode never increases work.
    total_target = sum(targets.values())
    policy = automation_policy()
    return {
        "safe_mode": policy["safe_mode"],
        "daily_content_target": min(total_target, 9),
        "daily_prospect_validation_cap": 5 if policy["safe_mode"] else 10,
        "no_unbounded_retry": policy["no_unbounded_retry"],
        "zero_cost_core": policy["zero_cost_core"],
    }
