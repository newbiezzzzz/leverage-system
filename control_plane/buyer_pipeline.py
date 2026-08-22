"""Evidence-based buyer-response state machine with explicit send/revenue gates."""
from __future__ import annotations

from dataclasses import dataclass

STAGES = ("candidate", "validated", "offer_draft", "approved", "contacted", "replied", "interested", "sample_or_trial", "purchased", "verified_revenue", "closed")
TRANSITIONS = {stage: STAGES[i + 1] for i, stage in enumerate(STAGES[:-1])}
GATED = {"approved", "contacted", "purchased", "verified_revenue"}

@dataclass(frozen=True)
class Transition:
    ok: bool
    stage: str
    reason: str


def can_advance(pipeline: dict, target: str, approvals: set[str] | None = None, evidence: set[str] | None = None) -> Transition:
    approvals = approvals or set()
    evidence = evidence or set()
    current = pipeline.get("stage")
    if current not in STAGES:
        return Transition(False, current or "unknown", "invalid current stage")
    expected = TRANSITIONS.get(current)
    if target != expected:
        return Transition(False, current, f"invalid transition: {current} -> {target}")
    if target in GATED and target not in approvals:
        return Transition(False, current, f"approval required for stage: {target}")
    required = {"validated": "validation_evidence", "replied": "response_evidence", "purchased": "purchase_evidence", "verified_revenue": "authoritative_revenue_evidence"}.get(target)
    if required and required not in evidence:
        return Transition(False, current, f"evidence required: {required}")
    return Transition(True, target, "approved transition")


def new_pipeline(prospect_id: str) -> dict:
    return {"version": 1, "prospect_id": prospect_id, "stage": "candidate", "history": [], "approvals": [], "evidence": [], "send_status": "not_sent", "customer_status": "not_customer", "verified_revenue_usd": 0}


def advance(pipeline: dict, target: str, approvals: set[str] | None = None, evidence: set[str] | None = None) -> dict:
    result = can_advance(pipeline, target, approvals, evidence)
    if not result.ok:
        raise ValueError(result.reason)
    updated = dict(pipeline)
    updated["history"] = list(pipeline.get("history", [])) + [pipeline["stage"]]
    updated["stage"] = target
    return updated


def owner_summary(pipeline: dict) -> dict:
    return {
        "prospect_id": pipeline.get("prospect_id"),
        "stage": pipeline.get("stage"),
        "send_status": pipeline.get("send_status"),
        "customer_status": pipeline.get("customer_status"),
        "verified_revenue_usd": pipeline.get("verified_revenue_usd", 0),
        "owner_approval_required": [stage for stage in GATED if stage not in pipeline.get("approvals", [])],
    }


if __name__ == "__main__":
    print({"worker": "buyer-pipeline", "status": "healthy", "stages": STAGES, "automatic_sending": False})
