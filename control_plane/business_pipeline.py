"""Safe business pipeline state machine with explicit Owner gates."""
from __future__ import annotations
from dataclasses import dataclass
STAGES=("validate","customer_discovery","offer","build","deliver","support","measure","optimize")
TRANSITIONS={stage:STAGES[i+1] for i,stage in enumerate(STAGES[:-1])}
GATED={"customer_discovery","offer","build","deliver"}
@dataclass(frozen=True)
class Transition:
    ok: bool
    stage: str
    reason: str

def can_advance(pipeline:dict,target:str,approvals:set[str]|None=None)->Transition:
    approvals=approvals or set(); current=pipeline.get("current_stage")
    if current not in STAGES: return Transition(False,current or "unknown","invalid current stage")
    expected=TRANSITIONS.get(current)
    if target!=expected: return Transition(False,current,f"invalid transition: {current} -> {target}")
    if target in GATED and target not in approvals: return Transition(False,current,f"approval required for stage: {target}")
    return Transition(True,target,"approved transition")

def new_pipeline(opportunity_id:str)->dict:
    return {"version":1,"opportunity_id":opportunity_id,"status":"active","current_stage":"validate","completed_stages":[],"approvals":[],"metrics":{"leads":0,"customers":0,"revenue":0,"expenses":0,"profit":0}}

def advance(pipeline:dict,target:str,approvals:set[str]|None=None)->dict:
    result=can_advance(pipeline,target,approvals)
    if not result.ok: raise ValueError(result.reason)
    updated=dict(pipeline); updated["completed_stages"]=list(pipeline.get("completed_stages",[]))+[pipeline["current_stage"]]; updated["current_stage"]=target
    return updated

def owner_summary(pipeline:dict)->dict:
    metrics=pipeline.get("metrics",{})
    return {"stage":pipeline.get("current_stage"),"status":pipeline.get("status"),"customers":metrics.get("customers",0),"revenue":metrics.get("revenue",0),"expenses":metrics.get("expenses",0),"profit":metrics.get("profit",0),"owner_approvals_pending":[stage for stage in GATED if stage not in pipeline.get("approvals",[])]}
