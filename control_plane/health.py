"""Read-only company health checks for Leverage OS.

Health checks surface conditions that need attention. They never mutate
company state, advance projects, spend money, or execute payouts.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from .company_core import list_projects
from .runtime_state import state_path, ensure_runtime_state
from .gates import project_gate_report
import json


def _load(name: str) -> dict:
    ensure_runtime_state()
    return json.loads(state_path(name).read_text(encoding="utf-8"))


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def company_health() -> dict:
    projects = list_projects()
    tasks = _load("tasks.json").get("tasks", [])
    approvals = _load("approvals.json").get("approvals", [])
    ledger = _load("financial_ledger.json")
    now = datetime.now(timezone.utc)
    alerts: list[dict] = []

    for task in tasks:
        if task.get("status") == "failed":
            alerts.append({"severity": "red", "type": "failed_task", "project_id": task.get("project"), "message": f"Task failed: {task.get('description', task.get('id', 'unknown task'))}", "action": "Review the worker result and decide whether to retry or stop."})
        elif task.get("status") == "blocked":
            alerts.append({"severity": "red", "type": "blocked_task", "project_id": task.get("project"), "message": f"Task blocked: {task.get('description', task.get('id', 'unknown task'))}", "action": "Resolve the safety or scope block before continuing."})
        elif task.get("status") == "running":
            started = _parse_time(task.get("started_at"))
            if started and now - started > timedelta(hours=24):
                alerts.append({"severity": "yellow", "type": "stale_task", "project_id": task.get("project"), "message": f"Task running for more than 24 hours: {task.get('description', task.get('id', 'unknown task'))}", "action": "Check whether the worker is stuck or the task needs re-scoping."})

    for project in projects:
        if project.status in {"paused", "retired"}:
            continue
        try:
            report = project_gate_report(project.id)
            gate = report["current_gate"]
            if gate["status"] == "waiting":
                alerts.append({"severity": "yellow", "type": "gate_waiting", "project_id": project.id, "message": f"Project waiting at {gate['label']}: {gate['reasons'][0] if gate['reasons'] else 'evidence incomplete'}", "action": "Review the gate evidence and decide whether work should continue."})
            elif gate.get("owner_decision_required"):
                alerts.append({"severity": "yellow", "type": "owner_decision", "project_id": project.id, "message": f"Boss decision required at {gate['label']}", "action": "Review the recommendation and record Pass, Hold, or Stop."})
        except (KeyError, ValueError):
            alerts.append({"severity": "red", "type": "health_check_error", "project_id": project.id, "message": "Project health report could not be evaluated.", "action": "Inspect the project state before allowing further execution."})

    pending_approvals = [a for a in approvals if a.get("status") == "pending"]
    if pending_approvals:
        alerts.append({"severity": "yellow", "type": "pending_approval", "project_id": None, "message": f"{len(pending_approvals)} owner approval(s) are pending.", "action": "Review the approval queue before consequential actions."})

    prepared_payouts = [p for p in ledger.get("payout_queue", []) if p.get("status") == "prepared"]
    if prepared_payouts:
        alerts.append({"severity": "yellow", "type": "payout_waiting", "project_id": prepared_payouts[0].get("project_id"), "message": f"{len(prepared_payouts)} payout request(s) are prepared and awaiting owner approval/provider execution.", "action": "Review payout details. Live money movement remains protected."})

    severity_rank = {"red": 3, "yellow": 2, "green": 1}
    highest = max((severity_rank[a["severity"]] for a in alerts), default=1)
    overall = {3: "red", 2: "yellow", 1: "green"}[highest]
    return {
        "status": overall,
        "summary": {"red": sum(a["severity"] == "red" for a in alerts), "yellow": sum(a["severity"] == "yellow" for a in alerts), "total": len(alerts)},
        "alerts": alerts,
        "evaluated_at": now.isoformat(),
    }
