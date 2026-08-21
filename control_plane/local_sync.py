"""Publish a sanitized local Company OS snapshot to GitHub."""
from __future__ import annotations
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from .company_core import list_projects
from .company_ops import system_snapshot
from .health import company_health
from .readiness import company_os_readiness
from .dispatcher import queue_summary
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"dashboard"/"local_state.json"
def _run(*args: str)->subprocess.CompletedProcess[str]: return subprocess.run(args,cwd=ROOT,text=True,capture_output=True,check=False)
def build_snapshot()->dict:
    readiness=company_os_readiness(); health=company_health(); snapshot=system_snapshot(); projects=list_projects()
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"source":"local-leverage-runtime","privacy":"sanitized-no-finance-no-audit","readiness":{"ready":readiness["ready"],"status":readiness["status"],"release_gate":readiness["release_gate"],"checks":[{"name":c["name"],"status":c["status"]} for c in readiness["checks"]]},"health":{"status":health.get("status"),"alert_count":health.get("summary",{}).get("total",0)},"company":{"projects":snapshot.get("projects",0),"active_projects":snapshot.get("active_projects",0),"tasks":snapshot.get("tasks",{}),"verified_revenue":snapshot.get("verified_revenue",0),"verified_expenses":snapshot.get("verified_expenses",0),"verified_profit":snapshot.get("verified_profit",0),"money_movement_protected":not snapshot.get("live_money_movement",False)},"workers":queue_summary(),"projects":[{"id":p.id,"name":p.name,"type":p.type,"status":p.status,"lifecycle_stage":p.lifecycle_stage,"revenue_status":p.revenue_status,"capital_deployed":p.capital_deployed,"currency":p.currency,"next_gate":p.next_gate} for p in projects]}
def sync(push: bool=True)->int:
    if push:
        status=_run("git","status","--porcelain")
        if status.returncode!=0: print(status.stderr.strip() or "git status failed"); return 2
        allowed={"dashboard/local_state.json"}; changed={line[3:].strip() for line in status.stdout.splitlines() if len(line)>=4}; unexpected=changed-allowed
        if unexpected:
            print("SYNC BLOCKED: unexpected local changes detected:"); [print(f"  {path}") for path in sorted(unexpected)]; return 2
        pull=_run("git","pull","--ff-only")
        if pull.returncode!=0: print("SYNC BLOCKED: git pull failed; local changes were not overwritten."); print(pull.stderr.strip()); return 2
    OUTPUT.parent.mkdir(parents=True,exist_ok=True); OUTPUT.write_text(json.dumps(build_snapshot(),indent=2)+"\n",encoding="utf-8")
    if not push: print(f"Local state written: {OUTPUT}"); return 0
    add=_run("git","add","dashboard/local_state.json")
    if add.returncode!=0: print(add.stderr.strip() or "git add failed"); return 2
    diff=_run("git","diff","--cached","--quiet")
    if diff.returncode==0: print("LEVERAGE LOCAL SYNC: no state change"); return 0
    commit=_run("git","commit","-m","chore: sync sanitized local company state")
    if commit.returncode!=0: print(commit.stderr.strip() or "git commit failed"); return 2
    push_result=_run("git","push")
    if push_result.returncode!=0: print("SYNC BLOCKED: git push failed. Local commit is preserved for inspection."); print(push_result.stderr.strip()); return 2
    print("LEVERAGE LOCAL SYNC: published sanitized local state"); return 0
