"""Persistent buyer-pipeline registry with guarded stage transitions."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .buyer_pipeline import advance, new_pipeline, owner_summary, STAGES

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "buyer_pipeline.json"


def _load() -> dict:
    if not REGISTRY_PATH.exists():
        return {"version": 1, "pipelines": {}}
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"version": 1, "pipelines": {}}
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "pipelines": {}}


def _save(data: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_prospect(prospect_id: str) -> dict:
    data = _load()
    pipelines = data.setdefault("pipelines", {})
    if prospect_id not in pipelines:
        pipelines[prospect_id] = new_pipeline(prospect_id)
        pipelines[prospect_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save(data)
    return pipelines[prospect_id]


def list_pipelines() -> list[dict]:
    data = _load()
    return [owner_summary(p) | {"history": p.get("history", []), "evidence": p.get("evidence", []), "approvals": p.get("approvals", [])} for p in data.get("pipelines", {}).values()]


def get_pipeline(prospect_id: str) -> dict:
    pipeline = ensure_prospect(prospect_id)
    return owner_summary(pipeline) | {"history": pipeline.get("history", []), "evidence": pipeline.get("evidence", []), "approvals": pipeline.get("approvals", [])}


def transition_pipeline(prospect_id: str, target: str, approvals: list[str] | None = None, evidence: list[str] | None = None) -> dict:
    data = _load()
    pipelines = data.setdefault("pipelines", {})
    pipeline = pipelines.get(prospect_id) or new_pipeline(prospect_id)
    approval_set = set(approvals or [])
    evidence_set = set(evidence or [])
    updated = advance(pipeline, target, approval_set, evidence_set)
    updated["approvals"] = sorted(set(pipeline.get("approvals", [])) | approval_set)
    updated["evidence"] = sorted(set(pipeline.get("evidence", [])) | evidence_set)
    if target == "contacted":
        updated["send_status"] = "sent"
    if target == "purchased":
        updated["customer_status"] = "customer"
    if target == "verified_revenue":
        updated["verified_revenue_usd"] = max(float(pipeline.get("verified_revenue_usd", 0)), 0.0)
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    pipelines[prospect_id] = updated
    data["version"] = 1
    data["stages"] = list(STAGES)
    _save(data)
    return get_pipeline(prospect_id)
