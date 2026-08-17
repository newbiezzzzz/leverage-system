"""Core company/project lifecycle helpers for Leverage.

This module is deliberately provider-independent. It owns state validation and
planning rules; it does not perform external financial transfers or destructive
external actions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
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

@dataclass
class Project:
    id: str
    name: str
    type: str = "general"
    status: str = "intake"
    lifecycle_stage: str = "intake"
    revenue_status: str = "none"
    capital_deployed: float = 0.0
    currency: str = "MYR"
    owner_approval_required_for_spend: bool = True
    description: str = ""
    next_gate: str = ""


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_project(project: Project) -> list[str]:
    errors: list[str] = []
    if not project.id.strip(): errors.append("project id is required")
    if not project.name.strip(): errors.append("project name is required")
    if project.lifecycle_stage not in LIFECYCLE: errors.append(f"invalid lifecycle stage: {project.lifecycle_stage}")
    if project.status not in LIFECYCLE: errors.append(f"invalid project status: {project.status}")
    if project.capital_deployed < 0: errors.append("capital_deployed cannot be negative")
    if project.currency != "MYR": errors.append("default company currency is MYR")
    return errors


def list_projects() -> list[Project]:
    return [Project(**item) for item in load_json(PROJECTS_FILE).get("projects", [])]


def create_project(project: Project) -> Project:
    errors = validate_project(project)
    if errors: raise ValueError("; ".join(errors))
    data = load_json(PROJECTS_FILE)
    existing = {item["id"] for item in data.get("projects", [])}
    if project.id in existing: raise ValueError(f"project already exists: {project.id}")
    data.setdefault("projects", []).append(asdict(project)); data["last_modified_at"] = utc_now(); save_json(PROJECTS_FILE, data)
    return project


def change_stage(project_id: str, stage: str, reason: str) -> Project:
    if stage not in LIFECYCLE: raise ValueError(f"invalid lifecycle stage: {stage}")
    data = load_json(PROJECTS_FILE)
    for item in data.get("projects", []):
        if item["id"] == project_id:
            item["lifecycle_stage"] = stage; item["status"] = stage; item["next_gate"] = reason; data["last_modified_at"] = utc_now(); save_json(PROJECTS_FILE, data); return Project(**item)
    raise KeyError(f"project not found: {project_id}")


def approval_required(action: str) -> bool:
    return action in {"move_money", "approve_money", "open_financial_account", "change_bank_details", "publish_irreversible_contract", "delete_production_data", "deploy_unreviewed_external_change"}


def has_owner_approval(action: str, target: str) -> bool:
    return any(item.get("action") == action and item.get("target") == target and item.get("status") == "approved" for item in load_json(APPROVALS_FILE).get("approvals", []))


if __name__ == "__main__":
    company = load_json(COMPANY_FILE); projects = list_projects(); print(f"Leverage company: {company['company']['name']}"); print(f"Projects registered: {len(projects)}")
    for project in projects: print(f"- {project.id}: {project.lifecycle_stage}")
