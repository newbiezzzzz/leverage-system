"""Runtime state paths for Leverage Company OS.

Mutable company state lives under control_plane/runtime and is deliberately
excluded from source control. Runtime state is bootstrapped from the tracked
company state when a runtime file is missing or empty.
"""
from __future__ import annotations
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)

LEGACY_FILES = {
    "projects.json": {"version": 1, "projects": []},
    "tasks.json": {"version": 3, "tasks": []},
    "approvals.json": {"version": 1, "approvals": []},
    "audit_log.json": {"version": 1, "events": []},
    "financial_ledger.json": {"version": 1, "entries": [], "payout_queue": [], "policy": {"live_money_movement": False}},
    "gates.json": {"version": 1, "decisions": []},
    "resource_state.json": {"version": 1, "resources": []},
    "customer_orders.json": {"version": 1, "orders": []},
    "opportunities.json": {"version": 1, "opportunities": []},
    "prospects.json": {"version": 1, "prospects": []},
    "business_pipelines.json": {"version": 1, "pipelines": []},
}


def state_path(name: str) -> Path:
    return RUNTIME / name


def _write_default(target: Path, default: dict) -> None:
    target.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")


def _is_empty_state(target: Path, name: str) -> bool:
    if name != "projects.json" or not target.exists():
        return False
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return not data.get("projects")


def ensure_runtime_state() -> None:
    for name, default in LEGACY_FILES.items():
        target = state_path(name)
        legacy = ROOT / name

        if not target.exists():
            if legacy.exists():
                shutil.copy2(legacy, target)
            else:
                _write_default(target, default)
            continue

        # Existing runtime state is normally authoritative, but a newly cloned
        # or reset installation can contain an empty projects registry. In that
        # case recover the tracked project definitions so the dashboard remains
        # usable without requiring manual project re-entry.
        if _is_empty_state(target, name) and legacy.exists():
            try:
                tracked = json.loads(legacy.read_text(encoding="utf-8"))
                if tracked.get("projects"):
                    shutil.copy2(legacy, target)
            except (OSError, json.JSONDecodeError):
                pass


ensure_runtime_state()
