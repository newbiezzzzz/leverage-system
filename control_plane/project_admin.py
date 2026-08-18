"""Administrative lifecycle actions for Leverage projects."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

from .runtime_state import state_path

PROJECTS_FILE = state_path("projects.json")
TASKS_FILE = state_path("tasks.json")
AUDIT_FILE = state_path("audit_log.json")
LEDGER_FILE = state_path("financial_ledger.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def remove_project(project_id: str, actor: str = "Boss") -> dict:
    """Remove a paused/retired zero-capital project from runtime state.

    Audit history is preserved. Projects with financial records or deployed
    capital are deliberately protected from removal.
    """
    projects = _load(PROJECTS_FILE)
    project = next((p for p in projects.get("projects", []) if p.get("id") == project_id), None)
    if project is None:
        raise KeyError(f"project not found: {project_id}")
    if project.get("status") not in {"paused", "retired"}:
        raise ValueError("only paused or retired projects can be removed")
    if float(project.get("capital_deployed", 0) or 0) != 0:
        raise ValueError("project with deployed capital cannot be removed")

    ledger = _load(LEDGER_FILE)
    if any(e.get("project_id") == project_id for e in ledger.get("entries", [])):
        raise ValueError("project with financial ledger entries cannot be removed")
    if any(p.get("project_id") == project_id for p in ledger.get("payout_queue", [])):
        raise ValueError("project with payout records cannot be removed")

    projects["projects"] = [p for p in projects.get("projects", []) if p.get("id") != project_id]
    projects["last_modified_at"] = _now()
    _save(PROJECTS_FILE, projects)

    tasks = _load(TASKS_FILE)
    removed_tasks = sum(1 for t in tasks.get("tasks", []) if t.get("project") == project_id)
    tasks["tasks"] = [t for t in tasks.get("tasks", []) if t.get("project") != project_id]
    tasks["last_modified_at"] = _now()
    _save(TASKS_FILE, tasks)

    audit = _load(AUDIT_FILE)
    event = {
        "id": _id("evt"),
        "timestamp": _now(),
        "event_type": "project_removed",
        "project_id": project_id,
        "actor": actor,
        "details": {"name": project.get("name"), "removed_tasks": removed_tasks},
    }
    audit.setdefault("events", []).append(event)
    audit["last_event_at"] = event["timestamp"]
    _save(AUDIT_FILE, audit)

    return {"project_id": project_id, "name": project.get("name"), "removed_tasks": removed_tasks}
