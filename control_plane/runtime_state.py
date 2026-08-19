"""Runtime state paths for Leverage Company OS.

Mutable company state lives under control_plane/runtime and is deliberately
excluded from source control. Legacy JSON files are migrated on first run.
"""
from __future__ import annotations
from pathlib import Path
import json
import shutil

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime"
RUNTIME.mkdir(exist_ok=True)

LEGACY_FILES={
 "projects.json":{"version":1,"projects":[]},
 "tasks.json":{"version":3,"tasks":[]},
 "approvals.json":{"version":1,"approvals":[]},
 "audit_log.json":{"version":1,"events":[]},
 "financial_ledger.json":{"version":1,"entries":[],"payout_queue":[],"policy":{"live_money_movement":False}},
 "gates.json":{"version":1,"decisions":[]},
 "resource_state.json":{"version":1,"resources":[]},
 "customer_orders.json":{"version":1,"orders":[]},
 "opportunities.json":{"version":1,"opportunities":[]},
 "prospects.json":{"version":1,"prospects":[]},
 "business_pipelines.json":{"version":1,"pipelines":[]},
}

def state_path(name:str)->Path: return RUNTIME/name

def ensure_runtime_state()->None:
    for name,default in LEGACY_FILES.items():
        target=state_path(name)
        if target.exists(): continue
        legacy=ROOT/name
        if legacy.exists(): shutil.copy2(legacy,target)
        else: target.write_text(json.dumps(default,indent=2)+"\n",encoding="utf-8")

ensure_runtime_state()
