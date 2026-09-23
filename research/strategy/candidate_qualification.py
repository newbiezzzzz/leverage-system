#!/usr/bin/env python3
"""Build the machine-readable final candidate gate from validated evidence.

This file deliberately remains false until an actual strategy evidence package
is produced by the research pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"research/results/qualified_strategy_evidence.json"
OUT=ROOT/"research/results/strategy_hunter_candidate_qualification.json"

REQUIRED=[
    "data_integrity",
    "engine_sanity",
    "positive_after_costs",
    "robust_out_of_sample",
    "drawdown_within_limit",
    "trade_frequency_feasible",
    "broker_feasible_at_rm1000",
    "historical_shariah_compliance",
    "independent_replication",
    "forward_paper_validation",
]

try:
    raw=json.loads(SRC.read_text(encoding="utf-8"))
except Exception:
    raw={}

gates=raw.get("gates",{}) if isinstance(raw,dict) else {}
all_passed=bool(
    raw.get("status")=="validated"
    and raw.get("candidate_id")
    and all(gates.get(k) is True for k in REQUIRED)
)

payload={
    "status":"achieved" if all_passed else "searching",
    "candidate_id":raw.get("candidate_id"),
    "all_gates_passed":all_passed,
    "gates":{k: bool(gates.get(k) is True) for k in REQUIRED},
    "evidence_source": str(SRC.relative_to(ROOT)),
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
print(json.dumps(payload,indent=2))
