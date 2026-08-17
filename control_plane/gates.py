"""Project decision gates for Leverage Company OS.

Gates turn project evidence into explicit recommendations. They never spend
money, publish external changes, or silently advance a project.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
PROJECTS_FILE = ROOT / "projects.json"
TASKS_FILE = ROOT / "tasks.json"
LEDGER_FILE = ROOT / "financial_ledger.json"
GATES_FILE = ROOT / "gates.json"

GATE_ORDER = ["intake", "validation", "build", "launch", "operate", "revenue", "payout-ready"]

GATE_RULES = {
    "intake": {"label": "Project intake", "requires": "A clear project goal and initial workflow plan."},
    "validation": {"label": "Validation", "requires": "Research and data validation are completed."},
    "build": {"label": "Build readiness", "requires": "The validated idea is ready for implementation."},
    "launch": {"label": "Launch readiness", "requires": "Build and test evidence are complete."},
    "operate": {"label": "Operations readiness", "requires": "Operational verification and customer workflow are complete."},
    "revenue": {"label": "Revenue evidence", "requires": "Verified income has been recorded."},
    "payout-ready": {"label": "Payout readiness", "requires": "Revenue is recorded and a payout has been prepared."},
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tasks(project_id: str) -> list[dict]:
    return [t for t in _load(TASKS_FILE).get("tasks", []) if t.get("project") == project_id]


def _revenue(project_id: str) -> list[dict]:
    return [
        e for e in _load(LEDGER_FILE).get("entries", [])
        if e.get("project_id") == project_id and e.get("direction") == "income" and e.get("verified")
    ]


def _payouts(project_id: str) -> list[dict]:
    return [p for p in _load(LEDGER_FILE).get("payout_queue", []) if p.get("project_id") == project_id]


def evaluate_gate(project_id: str, stage: str) -> dict:
    if stage not in GATE_RULES:
        raise ValueError(f"unknown gate: {stage}")
    project = next((p for p in _load(PROJECTS_FILE).get("projects", []) if p.get("id") == project_id), None)
    if project is None:
        raise KeyError(f"project not found: {project_id}")

    tasks = _tasks(project_id)
    completed = {t.get("action") for t in tasks if t.get("status") == "completed"}
    reasons: list[str] = []
    evidence: list[str] = []

    if stage == "intake":
        ready = bool(project.get("name", "").strip() and project.get("description", "").strip() and tasks)
        if ready:
            evidence.append("project brief and starter workflow exist")
        else:
            reasons.append("project brief or starter workflow is incomplete")
    elif stage == "validation":
        ready = {"research", "validate"}.issubset(completed)
        for action in ("research", "validate"):
            if action in completed:
                evidence.append(f"{action} evidence completed")
            else:
                reasons.append(f"{action} task is not completed")
    elif stage == "build":
        ready = "validate" in completed and "research" in completed
        if ready:
            evidence.append("research and data validation completed")
        else:
            reasons.append("validation evidence is incomplete")
    elif stage == "launch":
        ready = {"build", "test"}.issubset(completed)
        for action in ("build", "test"):
            if action in completed:
                evidence.append(f"{action} evidence completed")
            else:
                reasons.append(f"{action} task is not completed")
    elif stage == "operate":
        ready = {"verify", "intake"}.issubset(completed)
        for action in ("verify", "intake"):
            if action in completed:
                evidence.append(f"{action} evidence completed")
            else:
                reasons.append(f"{action} task is not completed")
    elif stage == "revenue":
        revenue = _revenue(project_id)
        ready = bool(revenue)
        if ready:
            evidence.append(f"{len(revenue)} verified revenue entr{'y' if len(revenue) == 1 else 'ies'} recorded")
        else:
            reasons.append("no verified revenue recorded")
    else:  # payout-ready
        revenue = _revenue(project_id)
        payouts = _payouts(project_id)
        ready = bool(revenue and payouts)
        if revenue:
            evidence.append("verified revenue exists")
        else:
            reasons.append("verified revenue is missing")
        if payouts:
            evidence.append("payout request is prepared")
        else:
            reasons.append("payout request is not prepared")

    return {
        "project_id": project_id,
        "stage": stage,
        "label": GATE_RULES[stage]["label"],
        "status": "ready" if ready else "waiting",
        "requires": GATE_RULES[stage]["requires"],
        "evidence": evidence,
        "reasons": reasons,
        "evaluated_at": _now(),
        "owner_decision_required": stage in {"launch", "operate", "revenue", "payout-ready"} and ready,
    }


def project_gate_report(project_id: str) -> dict:
    results = [evaluate_gate(project_id, stage) for stage in GATE_ORDER]
    current = next((r for r in results if r["stage"] == next_stage(project_id)), results[0])
    return {
        "project_id": project_id,
        "current_stage": current["stage"],
        "current_gate": current,
        "gates": results,
        "generated_at": _now(),
    }


def next_stage(project_id: str) -> str:
    project = next((p for p in _load(PROJECTS_FILE).get("projects", []) if p.get("id") == project_id), None)
    if project is None:
        raise KeyError(f"project not found: {project_id}")
    stage = project.get("lifecycle_stage", "intake")
    return stage if stage in GATE_RULES else "intake"


def save_gate_decision(project_id: str, stage: str, decision: str, note: str, decided_by: str = "Boss") -> dict:
    if stage not in GATE_RULES:
        raise ValueError(f"unknown gate: {stage}")
    if decision not in {"pass", "hold", "stop"}:
        raise ValueError("decision must be pass, hold or stop")
    if not note.strip():
        raise ValueError("decision note is required")
    path = GATES_FILE
    data = _load(path)
    decision_record = {
        "project_id": project_id,
        "stage": stage,
        "decision": decision,
        "note": note.strip(),
        "decided_by": decided_by,
        "decided_at": _now(),
    }
    data.setdefault("decisions", []).append(decision_record)
    data["last_modified_at"] = decision_record["decided_at"]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return decision_record
