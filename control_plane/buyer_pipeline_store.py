"""Persistent buyer-pipeline registry with guarded stage transitions."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .buyer_pipeline import advance, new_pipeline, owner_summary, STAGES

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "buyer_pipeline.json"
PROSPECTS_PATH = ROOT / "prospects.json"


def _load(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def _save(data: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _sync_candidates(data: dict) -> bool:
    changed = False
    pipelines = data.setdefault("pipelines", {})
    prospects = _load(PROSPECTS_PATH, {"prospects": []}).get("prospects", [])
    for prospect in prospects:
        prospect_id = str(prospect.get("id", "")).strip()
        if not prospect_id or not prospect.get("public_contact_available"):
            continue
        if prospect_id in pipelines:
            continue
        pipelines[prospect_id] = new_pipeline(prospect_id)
        pipelines[prospect_id]["fit_score"] = prospect.get("fit", 0)
        pipelines[prospect_id]["prospect_name"] = prospect.get("name", prospect_id)
        pipelines[prospect_id]["validation_status"] = prospect.get("validation_status", "unvalidated")
        pipelines[prospect_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        changed = True
    return changed


def ensure_prospect(prospect_id: str) -> dict:
    data = _load(REGISTRY_PATH, {"version": 1, "pipelines": {}})
    pipelines = data.setdefault("pipelines", {})
    changed = _sync_candidates(data)
    if prospect_id not in pipelines:
        pipelines[prospect_id] = new_pipeline(prospect_id)
        pipelines[prospect_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        changed = True
    if changed:
        data["version"] = 1
        data["stages"] = list(STAGES)
        _save(data)
    return pipelines[prospect_id]


def list_pipelines() -> list[dict]:
    data = _load(REGISTRY_PATH, {"version": 1, "pipelines": {}})
    if _sync_candidates(data):
        data["version"] = 1
        data["stages"] = list(STAGES)
        _save(data)
    return [
        owner_summary(p) | {
            "history": p.get("history", []),
            "evidence": p.get("evidence", []),
            "approvals": p.get("approvals", []),
            "fit_score": p.get("fit_score", 0),
            "prospect_name": p.get("prospect_name", p.get("prospect_id", "")),
            "validation_status": p.get("validation_status", "unvalidated"),
        }
        for p in data.get("pipelines", {}).values()
    ]


def get_pipeline(prospect_id: str) -> dict:
    pipeline = ensure_prospect(prospect_id)
    return owner_summary(pipeline) | {
        "history": pipeline.get("history", []),
        "evidence": pipeline.get("evidence", []),
        "approvals": pipeline.get("approvals", []),
        "fit_score": pipeline.get("fit_score", 0),
        "prospect_name": pipeline.get("prospect_name", prospect_id),
        "validation_status": pipeline.get("validation_status", "unvalidated"),
    }


def transition_pipeline(prospect_id: str, target: str, approvals: list[str] | None = None, evidence: list[str] | None = None) -> dict:
    data = _load(REGISTRY_PATH, {"version": 1, "pipelines": {}})
    pipelines = data.setdefault("pipelines", {})
    _sync_candidates(data)
    pipeline = pipelines.get(prospect_id) or new_pipeline(prospect_id)
    approval_set = set(approvals or [])
    evidence_set = set(evidence or [])
    updated = advance(pipeline, target, approval_set, evidence_set)
    updated["approvals"] = sorted(set(pipeline.get("approvals", [])) | approval_set)
    updated["evidence"] = sorted(set(pipeline.get("evidence", [])) | evidence_set)
    updated["fit_score"] = pipeline.get("fit_score", 0)
    updated["prospect_name"] = pipeline.get("prospect_name", prospect_id)
    updated["validation_status"] = pipeline.get("validation_status", "unvalidated")
    if target == "contacted":
        updated["send_status"] = "sent"
    if target == "purchased":
        updated["customer_status"] = "customer"
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    pipelines[prospect_id] = updated
    data["version"] = 1
    data["stages"] = list(STAGES)
    _save(data)
    return get_pipeline(prospect_id)
