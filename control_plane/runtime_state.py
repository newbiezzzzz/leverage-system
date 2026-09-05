"""Runtime state paths for Leverage Company OS.

Mutable company state lives under control_plane/runtime and is deliberately
excluded from source control. Runtime state is bootstrapped from the tracked
company state when a runtime file is missing or empty, and tracked definitions
are reconciled into an existing runtime registry without overwriting mutable
runtime state.
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

# These registries contain definitions authored in source control. Runtime
# state may add execution fields, so reconciliation only adds missing IDs.
TRACKED_COLLECTIONS = {
    "projects.json": "projects",
    "tasks.json": "tasks",
}


def state_path(name: str) -> Path:
    return RUNTIME / name


def _write_default(target: Path, default: dict) -> None:
    target.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _item_key(item: dict) -> str | None:
    for key in ("id", "task_id", "project_id"):
        value = item.get(key)
        if value is not None:
            return str(value)
    return None


def _reconcile_tracked_collection(target: Path, tracked: Path, collection: str) -> None:
    """Add newly tracked definitions while preserving existing runtime records."""
    runtime_data = _read_json(target)
    tracked_data = _read_json(tracked)
    if runtime_data is None or tracked_data is None:
        return

    runtime_items = runtime_data.get(collection)
    tracked_items = tracked_data.get(collection)
    if not isinstance(runtime_items, list) or not isinstance(tracked_items, list):
        return

    existing = {_item_key(item) for item in runtime_items if isinstance(item, dict)}
    additions = [
        item for item in tracked_items
        if isinstance(item, dict) and _item_key(item) not in existing
    ]
    if not additions:
        return

    runtime_items.extend(additions)
    runtime_data["version"] = max(
        int(runtime_data.get("version", 1) or 1),
        int(tracked_data.get("version", 1) or 1),
    )
    target.write_text(json.dumps(runtime_data, indent=2) + "\n", encoding="utf-8")


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

        # Recover an empty registry from tracked state.
        if name in TRACKED_COLLECTIONS:
            collection = TRACKED_COLLECTIONS[name]
            data = _read_json(target)
            if data is None:
                if legacy.exists():
                    shutil.copy2(legacy, target)
                continue
            if not data.get(collection) and legacy.exists():
                tracked = _read_json(legacy)
                if tracked and tracked.get(collection):
                    shutil.copy2(legacy, target)
                    continue

            # Important: an existing runtime registry is not replaced wholesale.
            # This lets GitHub add P-002/B1-B10 while preserving live local state.
            if legacy.exists():
                _reconcile_tracked_collection(target, legacy, collection)


ensure_runtime_state()
