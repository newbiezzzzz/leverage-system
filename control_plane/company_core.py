"""Core company/project lifecycle helpers for Leverage.

This module is deliberately provider-independent. It owns state validation and
planning rules; it does not perform external financial transfers or destructive
external actions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from datetime import datetime, timezone
from pathlib import Path
import json
from .runtime_state import state_path

ROOT = Path(__file__).resolve().parent
COMPANY_FILE = ROOT / "company.json"
PROJECTS_FILE = state_path("projects.json")
APPROVALS_FILE = state_path("approvals.json")

LIFECYCLE = [
    "intake", "validation", "build", "launch", "operate",
    "revenue", "payout-ready", "paused", "retired"
]

ALLOWED_TRANSITIONS = {
    "intake": {"validation", "paused", "retired"},
    "validation": {"build", "paused", "retired"},
    "build": {"launch", "paused", "retired"},
    "launch": {"operate", "paused", "retired"},
    "operate": {"revenue", "paused", "retired"},
    "revenue": {"payout-ready", "operate", "paused", "retired"},
    "payout-ready": {"operate", "paused", "retired"},
    "paused": {"validation", "retired"},
    "retired": set(),
}

@dataclass
class Project:
    id: str
    name: str
    project_no: str = ""
    type: str = "general"
    status: str = "intake"
    lifecycle_stage: str = "intake"
    revenue_status: str = "none"
    capital_deployed: float = 0.0
    currency: str = "MYR"
    owner_approval_required_for_spend: bool = True
    description: str = ""
    next_gate: str = ""


PROJECT_FIELDS = {field.name for field in fields(Project)}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_from_record(item: dict) -> Project:
    """Build the stable Project model while tolerating extended project metadata."""
    payload = {key: item[key] for key in PROJECT_FIELDS if key in item}
    return Project(**payload)


def validate_project(project: Project) -> list[str]:
    errors: list[str] = []
    if not project.id.strip(): errors.append("project id is required")
    if not project.name.strip(): errors.append("project name is required")
    if project.lifecycle_stage not in LIFECYCLE: errors.append(f"invalid lifecycle stage: {project.lifecycle_stage}")
    if project.status not in LIFECYCLE: errors.append(f"invalid project status: {project.status}")
    if project.capital_deployed < 0: errors.append("capital_deployed cannot be negative")
    if project.currency != "MYR": errors.append("default company currency is MYR")
    if project.status != project.lifecycle_stage: errors.append("project status and lifecycle_stage must match")
    return errors


def list_projects() -> list[Project]:
    return [project_from_record(item) for item in load_json(PROJECTS_FILE).get("projects", [])]


def create_project(project: Project) -> Project:
    errors = validate_project(project)
    if errors: raise ValueError("; ".join(errors))
    data = load_json(PROJECTS_FILE)
    existing = {item["id"] for item in data.get("projects", [])}
    if project.id in existing: raise ValueError(f"project already exists: {project.id}")
    data.setdefault("projects", []).append(asdict(project)); data["last_modified_at"] = utc_now(); save_json(PROJECTS_FILE, data)
    return project


def can_change_stage(current_stage: str, next_stage: str) -> bool:
    return next_stage in ALLOWED_TRANSITIONS.get(current_stage, set())


def change_stage(project_id: str, stage: str, reason: str) -> Project:
    if stage not in LIFECYCLE: raise ValueError(f"invalid lifecycle stage: {stage}")
    data = load_json(PROJECTS_FILE)
    for item in data.get("projects", []):
        if item["id"] == project_id:
            current = item.get("lifecycle_stage", item.get("status", "intake"))
            if current != stage and not can_change_stage(current, stage):
                raise ValueError(f"invalid lifecycle transition: {current} -> {stage}")
            item["lifecycle_stage"] = stage; item["status"] = stage; item["next_gate"] = reason; data["last_modified_at"] = utc_now(); save_json(PROJECTS_FILE, data); return project_from_record(item)
    raise KeyError(f"project not found: {project_id}")


def approval_required(action: str) -> bool:
    return action in {"move_money", "approve_money", "open_financial_account", "change_bank_details", "publish_irreversible_contract", "delete_production_data", "deploy_unreviewed_external_change"}


def has_owner_approval(action: str, target: str) -> bool:
    return any(item.get("action") == action and item.get("target") == target and item.get("status") == "approved" for item in load_json(APPROVALS_FILE).get("approvals", []))


if __name__ == "__main__":
    company = load_json(COMPANY_FILE); projects = list_projects(); print(f"Leverage company: {company['company']['name']}"); print(f"Projects registered: {len(projects)}")
    for project in projects: print(f"- {project.project_no or project.id}: {project.lifecycle_stage}")
