"""Operational company workflow for Leverage OS v1."""
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
from .company_core import Project, create_project, change_stage, load_json, save_json
from .finance_core import prepare_owner_payout, reconcile_entry
from .runtime_state import state_path
from .dispatcher import queue_summary

ROOT = Path(__file__).resolve().parent
TASKS_FILE = state_path("tasks.json")
PROJECTS_FILE = state_path("projects.json")
APPROVALS_FILE = state_path("approvals.json")
AUDIT_FILE = state_path("audit_log.json")
LEDGER_FILE = state_path("financial_ledger.json")
DEFAULT_PROJECT_WORKFLOW = [("project-manager", "plan", "Create project execution plan", []),("research-worker", "research", "Research demand, risks and opportunity", [0]),("data-worker", "validate", "Collect and validate the core project data", [0]),("code-worker", "build", "Build or configure the project deliverable", [1, 2]),("code-worker", "test", "Test, lint and quality-check the project deliverable", [3]),("operations-worker", "verify", "Verify readiness and operational health", [4]),("customer-worker", "intake", "Prepare customer intake, onboarding and feedback workflow", [0]),("finance-worker", "reconcile", "Prepare financial reporting and reconciliation workflow", [5, 6])]
def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _id(prefix: str) -> str: return f"{prefix}-{uuid.uuid4().hex[:10]}"
def audit(event_type: str, project_id: str | None, actor: str, details: dict | None = None) -> dict:
    data = load_json(AUDIT_FILE); event = {"id": _id("evt"), "timestamp": _now(), "event_type": event_type, "project_id": project_id, "actor": actor, "details": details or {}}; data.setdefault("events", []).append(event); data["last_event_at"] = event["timestamp"]; save_json(AUDIT_FILE, data); return event
def _load_tasks() -> dict: return load_json(TASKS_FILE)
def _save_tasks(data: dict) -> None: data["last_modified_at"] = _now(); save_json(TASKS_FILE, data)
def intake_project(project: Project) -> Project:
    created = create_project(project); audit("project_created", created.id, "project-manager", {"name": created.name, "type": created.type}); return created
def create_project_plan(project_id: str, workflow: list[tuple] | None = None) -> list[dict]:
    workflow = workflow or DEFAULT_PROJECT_WORKFLOW; projects = load_json(PROJECTS_FILE).get("projects", []); project = next((p for p in projects if p["id"] == project_id), None)
    if project is None: raise KeyError(f"project not found: {project_id}")
    tasks = _load_tasks(); existing_tasks = [t for t in tasks.get("tasks", []) if t.get("project") == project_id]
    if existing_tasks: audit("project_plan_reused", project_id, "project-manager", {"task_count": len(existing_tasks), "idempotent": True}); return existing_tasks
    created=[]; existing={t["id"] for t in tasks.get("tasks", [])}; task_ids=[]
    for worker, action, description, dependency_indexes in workflow:
        task_id=_id("task")
        while task_id in existing: task_id=_id("task")
        task={"id":task_id,"project":project_id,"worker":worker,"description":description,"action":action,"status":"queued","priority":"normal","depends_on":[task_ids[i] for i in dependency_indexes],"created_at":_now()}; tasks.setdefault("tasks",[]).append(task); created.append(task); existing.add(task_id); task_ids.append(task_id)
    _save_tasks(tasks)
    if project.get("lifecycle_stage")=="intake": change_stage(project_id,"validation","Complete research and data validation before build")
    audit("project_plan_created",project_id,"project-manager",{"task_count":len(created),"dependency_aware":True}); return created
def _dependency_state(data: dict, task: dict) -> tuple[bool,list[str]]:
    by_id={item.get("id"):item for item in data.get("tasks",[])}; missing=[]
    for dep_id in task.get("depends_on",[]):
        dep=by_id.get(dep_id)
        if dep is None or dep.get("status")!="completed": missing.append(dep_id)
    return not missing,missing
def _sync_project_stage(project_id: str, tasks: list[dict]) -> None:
    project=next((p for p in load_json(PROJECTS_FILE).get("projects",[]) if p.get("id")==project_id),None)
    if project is None or project.get("status") in {"paused","retired","revenue","payout-ready"}: return
    completed={t.get("action") for t in tasks if t.get("project")==project_id and t.get("status")=="completed"}; stage=project.get("lifecycle_stage"); target=None; reason=None
    if "research" in completed and "validate" in completed and stage=="validation": target,reason="build","Research and data validation gates completed; build is authorized"
    elif "build" in completed and "test" in completed and stage=="build": target,reason="launch","Build and quality gates completed; launch verification is authorized"
    elif "verify" in completed and "intake" in completed and stage=="launch": target,reason="operate","Operational and customer-readiness gates completed; project may operate"
    if target and target!=stage: change_stage(project_id,target,reason); audit("project_stage_advanced",project_id,"project-manager",{"from":stage,"to":target,"reason":reason})
def claim_task(task_id: str, worker_id: str) -> dict:
    data=_load_tasks()
    for task in data.get("tasks",[]):
        if task["id"]==task_id:
            if task["status"] not in {"queued","ready"}: raise ValueError(f"task is not claimable: {task_id}")
            if task["worker"]!=worker_id: raise ValueError("worker not assigned to task")
            ready,missing=_dependency_state(data,task)
            if not ready: raise ValueError(f"dependencies incomplete: {', '.join(missing)}")
            task["status"]="running"; task["started_at"]=_now(); task["claimed_by"]=worker_id; _save_tasks(data); audit("task_claimed",task["project"],worker_id,{"task_id":task_id,"dependencies":task.get("depends_on",[])}); return task
    raise KeyError(f"task not found: {task_id}")
def complete_task(task_id: str, result: str, worker_id: str, success: bool = True) -> dict:
    data=_load_tasks()
    for task in data.get("tasks",[]):
        if task["id"]==task_id:
            if task["status"] not in {"running","queued","ready"}: raise ValueError(f"task cannot be completed from status {task['status']}")
            if task.get("worker")!=worker_id: raise ValueError("worker not assigned to task")
            if task["status"]!="running":
                ready,missing=_dependency_state(data,task)
                if not ready: raise ValueError(f"dependencies incomplete: {', '.join(missing)}")
            task["status"]="completed" if success else "failed"; task["result"]=result; task["completed_at"]=_now(); _save_tasks(data); audit("task_completed" if success else "task_failed",task["project"],worker_id,{"task_id":task_id,"result":result})
            if success: _sync_project_stage(task["project"],data.get("tasks",[]))
            return task
    raise KeyError(f"task not found: {task_id}")
def project_task_summary(project_id: str) -> dict:
    tasks=[t for t in _load_tasks().get("tasks",[]) if t.get("project")==project_id]; counts={s:sum(1 for t in tasks if t.get("status")==s) for s in ["queued","ready","running","blocked","completed","failed","cancelled"]}; by_id={t.get("id"):t for t in tasks}; counts["waiting_on_dependencies"]=sum(1 for t in tasks if t.get("status") in {"queued","ready"} and any(by_id.get(d,{}).get("status")!="completed" for d in t.get("depends_on",[]))); counts["ready_to_claim"]=sum(1 for t in tasks if t.get("status") in {"queued","ready"} and all(by_id.get(d,{}).get("status")=="completed" for d in t.get("depends_on",[]))); counts["total"]=len(tasks); counts["progress"]=round((counts["completed"]/counts["total"])*100,1) if counts["total"] else 0; return counts
def record_revenue(project_id: str, amount: float, description: str, external_reference: str) -> dict:
    if amount<=0: raise ValueError("revenue amount must be positive")
    if not any(p.get("id")==project_id for p in load_json(PROJECTS_FILE).get("projects",[])): raise KeyError(f"project not found: {project_id}")
    entry=reconcile_entry(f"{project_id}: {description}",amount,"income",external_reference); ledger=load_json(LEDGER_FILE)
    for item in ledger.get("entries",[]):
        if item.get("id")==entry["id"]: item["project_id"]=project_id; break
    ledger["last_modified_at"]=_now(); save_json(LEDGER_FILE,ledger); change_stage(project_id,"revenue","Revenue recorded; reconcile and verify before payout"); audit("revenue_recorded",project_id,"finance-worker",{"entry_id":entry["id"],"amount":amount,"external_reference":external_reference}); return entry
def prepare_payout(project_id: str, amount: float, destination: str, purpose: str) -> dict:
    if not any(p.get("id")==project_id for p in load_json(PROJECTS_FILE).get("projects",[])): raise KeyError(f"project not found: {project_id}")
    request=prepare_owner_payout(amount,destination,f"{project_id}: {purpose}"); ledger=load_json(LEDGER_FILE)
    for item in ledger.get("payout_queue",[]):
        if item.get("id")==request.id: item["project_id"]=project_id; break
    ledger["last_modified_at"]=_now(); save_json(LEDGER_FILE,ledger); change_stage(project_id,"payout-ready","Owner approval required before any payout execution"); audit("payout_prepared",project_id,"finance-worker",{"payout_id":request.id,"amount":request.amount}); return asdict(request)
def approve_payout(payout_id: str, owner: str = "Boss") -> dict:
    ledger=load_json(LEDGER_FILE); request=next((r for r in ledger.get("payout_queue",[]) if r.get("id")==payout_id),None)
    if request is None: raise KeyError(f"payout request not found: {payout_id}")
    approvals=load_json(APPROVALS_FILE); approval={"id":_id("approval"),"type":"owner_payout","action":"approve_money","target":payout_id,"status":"approved","approved_by":owner,"approved_at":_now()}; approvals.setdefault("approvals",[]).append(approval); approvals["last_modified_at"]=_now(); save_json(APPROVALS_FILE,approvals); request["status"]="approved"; request["owner_approval_id"]=approval["id"]; ledger["last_modified_at"]=_now(); save_json(LEDGER_FILE,ledger); audit("owner_payout_approved",request.get("project_id"),owner,{"payout_id":payout_id,"approval_id":approval["id"]}); return approval
def system_snapshot() -> dict:
    projects=load_json(PROJECTS_FILE).get("projects",[]); tasks=load_json(TASKS_FILE).get("tasks",[]); ledger=load_json(LEDGER_FILE); entries=ledger.get("entries",[]); income=sum(float(e.get("amount",0)) for e in entries if e.get("direction")=="income" and e.get("verified")); expenses=sum(float(e.get("amount",0)) for e in entries if e.get("direction")=="expense" and e.get("verified"));
    return {"generated_at":_now(),"projects":len(projects),"active_projects":sum(1 for p in projects if p.get("status") not in {"paused","retired"}),"tasks":{s:sum(1 for t in tasks if t.get("status")==s) for s in ["queued","ready","running","completed","failed","blocked"]},"revenue_entries":len([e for e in entries if e.get("direction")=="income"]),"verified_revenue":round(income,2),"verified_expenses":round(expenses,2),"verified_profit":round(income-expenses,2),"payouts_prepared":len(ledger.get("payout_queue",[])),"live_money_movement":bool(ledger.get("policy",{}).get("live_money_movement",False)),"worker_queues":queue_summary()}
