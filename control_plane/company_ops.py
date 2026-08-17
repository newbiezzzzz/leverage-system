"""Operational company workflow for Leverage OS v1.

This module turns the company model into a reusable project lifecycle:
intake -> plan -> execute/record work -> revenue -> payout-ready -> owner approval.
No external payment is performed here.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

from .company_core import Project, create_project, change_stage, load_json, save_json, utc_now
from .finance_core import prepare_owner_payout, reconcile_entry

ROOT = Path(__file__).resolve().parent
TASKS_FILE = ROOT / "tasks.json"
PROJECTS_FILE = ROOT / "projects.json"
APPROVALS_FILE = ROOT / "approvals.json"
AUDIT_FILE = ROOT / "audit_log.json"
LEDGER_FILE = ROOT / "financial_ledger.json"

DEFAULT_PROJECT_WORKFLOW = [
    ("project-manager", "plan", "Create project execution plan"),
    ("research-worker", "research", "Research demand, risks and opportunity"),
    ("code-worker", "build", "Build or configure the project deliverable"),
    ("operations-worker", "verify", "Verify readiness and operational health"),
    ("customer-worker", "intake", "Prepare customer intake and support workflow"),
    ("finance-worker", "reconcile", "Prepare revenue and financial reporting workflow"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def audit(event_type: str, project_id: str | None, actor: str, details: dict | None = None) -> dict:
    data = load_json(AUDIT_FILE)
    event = {
        "id": _id("evt"),
        "timestamp": _now(),
        "event_type": event_type,
        "project_id": project_id,
        "actor": actor,
        "details": details or {},
    }
    data.setdefault("events", []).append(event)
    data["last_event_at"] = event["timestamp"]
    save_json(AUDIT_FILE, data)
    return event


def _load_tasks() -> dict:
    return load_json(TASKS_FILE)


def _save_tasks(data: dict) -> None:
    data["last_modified_at"] = _now()
    save_json(TASKS_FILE, data)


def intake_project(project: Project) -> Project:
    created = create_project(project)
    audit("project_created", created.id, "project-manager", {"name": created.name, "type": created.type})
    return created


def create_project_plan(project_id: str, workflow: list[tuple[str, str, str]] | None = None) -> list[dict]:
    workflow = workflow or DEFAULT_PROJECT_WORKFLOW
    projects = load_json(PROJECTS_FILE).get("projects", [])
    project = next((p for p in projects if p["id"] == project_id), None)
    if project is None:
        raise KeyError(f"project not found: {project_id}")
    tasks = _load_tasks()
    created = []
    existing = {t["id"] for t in tasks.get("tasks", [])}
    for worker, action, description in workflow:
        task = {
            "id": _id("task"),
            "project": project_id,
            "worker": worker,
            "description": description,
            "action": action,
            "status": "queued",
            "priority": "normal",
            "created_at": _now(),
        }
        while task["id"] in existing:
            task["id"] = _id("task")
        tasks.setdefault("tasks", []).append(task)
        created.append(task)
        existing.add(task["id"])
    _save_tasks(tasks)
    if project.get("lifecycle_stage") == "intake":
        change_stage(project_id, "validation", "Complete initial project validation before build")
    audit("project_plan_created", project_id, "project-manager", {"task_count": len(created)})
    return created


def claim_task(task_id: str, worker_id: str) -> dict:
    data = _load_tasks()
    for task in data.get("tasks", []):
        if task["id"] != task_id:
            continue
        if task["status"] != "queued":
            raise ValueError(f"task is not queued: {task_id}")
        if task["worker"] != worker_id:
            raise ValueError("worker not assigned to task")
        task["status"] = "running"
        task["started_at"] = _now()
        task["claimed_by"] = worker_id
        _save_tasks(data)
        audit("task_claimed", task["project"], worker_id, {"task_id": task_id})
        return task
    raise KeyError(f"task not found: {task_id}")


def complete_task(task_id: str, result: str, worker_id: str, success: bool = True) -> dict:
    data = _load_tasks()
    for task in data.get("tasks", []):
        if task["id"] != task_id:
            continue
        if task["status"] not in {"running", "queued"}:
            raise ValueError(f"task cannot be completed from status {task['status']}")
        task["status"] = "completed" if success else "failed"
        task["result"] = result
        task["completed_at"] = _now()
        task["worker"] = worker_id
        _save_tasks(data)
        audit("task_completed" if success else "task_failed", task["project"], worker_id, {"task_id": task_id, "result": result})
        return task
    raise KeyError(f"task not found: {task_id}")


def project_task_summary(project_id: str) -> dict:
    tasks = [t for t in _load_tasks().get("tasks", []) if t.get("project") == project_id]
    counts = {s: sum(1 for t in tasks if t.get("status") == s) for s in ["queued", "running", "blocked", "completed", "failed", "cancelled"]}
    counts["total"] = len(tasks)
    counts["progress"] = round((counts["completed"] / counts["total"]) * 100, 1) if counts["total"] else 0
    return counts


def record_revenue(project_id: str, amount: float, description: str, external_reference: str) -> dict:
    if amount <= 0:
        raise ValueError("revenue amount must be positive")
    projects = load_json(PROJECTS_FILE).get("projects", [])
    project = next((p for p in projects if p["id"] == project_id), None)
    if project is None:
        raise KeyError(f"project not found: {project_id}")
    entry = reconcile_entry(f"{project_id}: {description}", amount, "income", external_reference)
    ledger = load_json(LEDGER_FILE)
    entry["project_id"] = project_id
    # reconcile_entry already persisted; append project attribution in-place.
    for item in ledger.get("entries", []):
        if item.get("id") == entry["id"]:
            item["project_id"] = project_id
            break
    ledger["last_modified_at"] = _now()
    save_json(LEDGER_FILE, ledger)
    change_stage(project_id, "revenue", "Revenue recorded; reconcile and verify before payout")
    audit("revenue_recorded", project_id, "finance-worker", {"entry_id": entry["id"], "amount": amount, "external_reference": external_reference})
    return entry


def prepare_payout(project_id: str, amount: float, destination: str, purpose: str) -> dict:
    request = prepare_owner_payout(amount, destination, f"{project_id}: {purpose}")
    ledger = load_json(LEDGER_FILE)
    for item in ledger.get("payout_queue", []):
        if item.get("id") == request.id:
            item["project_id"] = project_id
            break
    ledger["last_modified_at"] = _now()
    save_json(LEDGER_FILE, ledger)
    change_stage(project_id, "payout-ready", "Owner approval required before any payout execution")
    audit("payout_prepared", project_id, "finance-worker", {"payout_id": request.id, "amount": request.amount})
    return asdict(request)


def approve_payout(payout_id: str, owner: str = "Boss") -> dict:
    approvals = load_json(APPROVALS_FILE)
    approval = {
        "id": _id("approval"),
        "type": "owner_payout",
        "action": "approve_money",
        "target": payout_id,
        "status": "approved",
        "approved_by": owner,
        "approved_at": _now(),
    }
    approvals.setdefault("approvals", []).append(approval)
    approvals["last_modified_at"] = _now()
    save_json(APPROVALS_FILE, approvals)

    ledger = load_json(LEDGER_FILE)
    for request in ledger.get("payout_queue", []):
        if request.get("id") == payout_id:
            request["status"] = "approved"
            request["owner_approval_id"] = approval["id"]
            break
    else:
        raise KeyError(f"payout request not found: {payout_id}")
    ledger["last_modified_at"] = _now()
    save_json(LEDGER_FILE, ledger)
    audit("owner_payout_approved", None, owner, {"payout_id": payout_id, "approval_id": approval["id"]})
    return approval


def system_snapshot() -> dict:
    projects = load_json(PROJECTS_FILE).get("projects", [])
    tasks = load_json(TASKS_FILE).get("tasks", [])
    ledger = load_json(LEDGER_FILE)
    return {
        "generated_at": _now(),
        "projects": len(projects),
        "active_projects": sum(1 for p in projects if p.get("status") not in {"paused", "retired"}),
        "tasks": {s: sum(1 for t in tasks if t.get("status") == s) for s in ["queued", "running", "completed", "failed", "blocked"]},
        "revenue_entries": len([e for e in ledger.get("entries", []) if e.get("direction") == "income"]),
        "payouts_prepared": len(ledger.get("payout_queue", [])),
        "live_money_movement": bool(ledger.get("policy", {}).get("live_money_movement", False)),
    }
