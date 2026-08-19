"""Opportunity scoring and business-pipeline planning for Leverage."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

WEIGHTS = {"first_revenue_speed":20,"zero_cost_feasibility":15,"demand_evidence":15,"automation_potential":15,"profit_margin":10,"competition":10,"scalability":10,"owner_capability_fit":5}
REQUIRED_EVIDENCE = {"problem","customer","offer","evidence"}

@dataclass(frozen=True)
class OpportunityScore:
    opportunity_id: str
    score: float
    dimensions: dict[str,float]
    missing_evidence: list[str]
    decision: str

def _clamp(value: Any) -> float:
    try: return max(0.0,min(100.0,float(value)))
    except (TypeError,ValueError): return 0.0

def score_opportunity(opportunity: dict[str,Any]) -> OpportunityScore:
    dimensions={key:_clamp(opportunity.get(key,0)) for key in WEIGHTS}
    weighted=sum(dimensions[key]*weight for key,weight in WEIGHTS.items())/100.0
    missing=sorted(field for field in REQUIRED_EVIDENCE if not opportunity.get(field))
    decision="needs-evidence" if missing else ("candidate" if weighted>=75 else "watch" if weighted>=55 else "reject")
    return OpportunityScore(opportunity.get("id","unknown"),round(weighted,2),dimensions,missing,decision)

def rank_opportunities(opportunities: list[dict[str,Any]]) -> list[dict[str,Any]]:
    ranked=[]
    for opportunity in opportunities:
        result=score_opportunity(opportunity)
        ranked.append({**opportunity,"score":result.score,"score_breakdown":result.dimensions,"missing_evidence":result.missing_evidence,"decision":result.decision})
    return sorted(ranked,key=lambda item:item["score"],reverse=True)

def build_business_pipeline(opportunity: dict[str,Any]) -> dict[str,Any]:
    """Create a safe, human-gated execution plan; no external side effects."""
    score=score_opportunity(opportunity)
    return {"pipeline_version":1,"opportunity_id":opportunity.get("id"),"created_at":datetime.now(timezone.utc).isoformat(),"status":"awaiting_owner_approval" if score.decision=="candidate" else "not_eligible","stages":[
        {"id":"validate","owner":"research-worker","status":"ready"},
        {"id":"customer_discovery","owner":"acquisition-worker","status":"gated"},
        {"id":"offer","owner":"customer-worker","status":"gated"},
        {"id":"build","owner":"code-worker","status":"gated"},
        {"id":"deliver","owner":"operations-worker","status":"gated"},
        {"id":"support","owner":"customer-worker","status":"gated"},
        {"id":"measure","owner":"finance-worker","status":"gated"},
        {"id":"optimize","owner":"project-manager","status":"gated"}],
        "safety":{"no_unsolicited_spam":True,"no_impersonation":True,"no_contract_commitment":True,"no_live_money_movement":True,"owner_approval_required_for_launch":True}}

def summary(opportunities: list[dict[str,Any]]) -> dict[str,Any]:
    ranked=rank_opportunities(opportunities)
    return {"count":len(ranked),"candidates":sum(x["decision"]=="candidate" for x in ranked),"watch":sum(x["decision"]=="watch" for x in ranked),"needs_evidence":sum(x["decision"]=="needs-evidence" for x in ranked),"top":ranked[0] if ranked else None}
