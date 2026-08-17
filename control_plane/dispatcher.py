"""Leverage Control Plane task dispatcher."""
from __future__ import annotations
import json
from pathlib import Path
from .runtime_state import state_path

ROOT = Path(__file__).resolve().parent
WORKERS_FILE = ROOT / "workers.json"
TASKS_FILE = state_path("tasks.json")
PROJECTS_FILE = state_path("projects.json")
POLICIES_FILE = ROOT / "policies.json"
APPROVALS_FILE = state_path("approvals.json")
ALLOWED_STATUSES = {"queued", "running", "blocked", "completed", "failed", "cancelled"}
SAFE_ACTIONS = {"research","analyze","recommend","collect","validate","transform","cache","build","test","lint","package","plan","schedule","route","report","monitor","verify","alert","recover_safe","intake","support","collect_feedback","reconcile","prepare_payout"}
RESTRICTED_ACTIONS = {"move_money","approve_money","open_financial_account","change_bank_details","publish_irreversible_contract","delete_production_data","deploy_unreviewed_external_change","execute_payout"}

def load_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def save_json(path: Path, value) -> None: path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
def worker_index(): return {worker["id"]: worker for worker in load_json(WORKERS_FILE)["workers"]}
def project_index(): return {project["id"]: project for project in load_json(PROJECTS_FILE).get("projects", [])}
def task_index(): return {task["id"]: task for task in load_json(TASKS_FILE).get("tasks", [])}
def has_owner_approval(action: str, target: str) -> bool: return any(item.get("action")==action and item.get("target")==target and item.get("status")=="approved" for item in load_json(APPROVALS_FILE).get("approvals", []))
def dependency_errors(task: dict, tasks: dict) -> list[str]:
    errors=[]
    for dependency_id in task.get("depends_on", []):
        dependency=tasks.get(dependency_id)
        if dependency is None: errors.append(f"unknown dependency: {dependency_id}")
        elif dependency.get("status") != "completed": errors.append(f"dependency incomplete: {dependency_id}")
    return errors

def validate_task(task: dict, workers: dict, projects: dict, tasks: dict | None = None) -> list[str]:
    errors=[]; required={"id","project","worker","description","status"}; missing=required-task.keys()
    if missing: return [f"missing fields: {sorted(missing)}"]
    if task["status"] not in ALLOWED_STATUSES: errors.append(f"invalid status: {task['status']}")
    project=projects.get(task["project"])
    if project is None: errors.append(f"unknown project: {task['project']}")
    elif project.get("status") in {"paused","retired"} and task.get("action") not in {"report","verify"}: errors.append(f"project is {project.get('status')}: {task['project']}")
    worker=workers.get(task["worker"])
    if worker is None: errors.append(f"unknown worker: {task['worker']}"); return errors
    if worker["status"] != "online": errors.append(f"worker is not online: {task['worker']}")
    authorized_projects=worker.get("projects", [])
    if "*" not in authorized_projects and task["project"] not in authorized_projects: errors.append(f"worker not authorized for project: {task['project']}")
    action=task.get("action","report"); capabilities=set(worker.get("capabilities",[]))
    if action in RESTRICTED_ACTIONS:
        target=task.get("target") or task["project"]
        if not has_owner_approval(action,target): errors.append(f"owner approval required for restricted action: {action}")
        if action in {"move_money","execute_payout"}: errors.append("live money movement is disabled in Leverage v1")
    elif action not in SAFE_ACTIONS: errors.append(f"unknown action: {action}")
    elif capabilities and action not in capabilities and action not in {"report","plan","route"}: errors.append(f"worker lacks capability: {action}")
    if tasks is not None: errors.extend(dependency_errors(task,tasks))
    return errors

def dispatch() -> int:
    workers=worker_index(); projects=project_index(); task_store=load_json(TASKS_FILE); tasks=task_store.get("tasks",[]); indexed_tasks={task.get("id"):task for task in tasks}; print("LEVERAGE CONTROL PLANE"); print("="*60); print(f"Workers registered: {len(workers)}"); print(f"Projects registered: {len(projects)}"); print(f"Tasks queued: {sum(task.get('status') == 'queued' for task in tasks)}"); failures=0
    for task in tasks:
        if task.get("status") != "queued": continue
        errors=validate_task(task,workers,projects,indexed_tasks)
        if errors:
            task["validation_errors"]=errors
            if all(error.startswith("dependency incomplete:") for error in errors): print(f"WAIT    {task.get('id','<unknown>')}: {'; '.join(errors)}"); continue
            task["status"]="blocked"; failures+=1; print(f"BLOCKED {task.get('id','<unknown>')}: {'; '.join(errors)}"); continue
        task["routing"]={"worker":task["worker"],"action":task.get("action","report"),"validated":True,"execution":"worker-controlled","dependencies_satisfied":True}; print(f"READY   {task['id']} -> {task['worker']} ({task.get('action','report')})")
    save_json(TASKS_FILE,task_store); print(f"Dispatcher completed with {failures} blocked task(s)."); return 1 if failures else 0

if __name__ == "__main__": raise SystemExit(dispatch())
