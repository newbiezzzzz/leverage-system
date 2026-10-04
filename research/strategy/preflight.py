#!/usr/bin/env python3
"""Cheap Strategy Hunter preflight and engine sanity gate."""
from __future__ import annotations

import importlib
import json
import py_compile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FILES = [
    ROOT / "research/strategy/baseline_research.py",
    ROOT / "research/strategy/pattern_discovery.py",
    ROOT / "research/strategy/adaptive_improvement.py",
    ROOT / "research/strategy/specialist_runner.py",
    ROOT / "research/strategy/pipeline_orchestrator.py",
    ROOT / "research/strategy/engine_sanity.py",
    ROOT / "research/strategy/mission_controller.py",
    ROOT / "research/strategy/candidate_qualification.py",
    ROOT / "research/strategy/candidate_backtest.py",
    ROOT / "research/strategy/strategy_lab_v3.py",
    ROOT / "research/strategy/realistic_engine_v1.py",
    ROOT / "research/strategy/strategy_lab_v4.py",
    ROOT / "research/strategy/innovation_lab.py",
    ROOT / "research/strategy/global_strategy_intelligence.py",
]
for path in FILES:
    py_compile.compile(str(path), doraise=True)

import pandas as pd  # noqa: E402
from research.strategy import baseline_research as br  # noqa: E402

idx = pd.date_range("2024-01-01", periods=4)
cols = ["AAA", "BBB", "CCC"]
frame = pd.DataFrame([[.1, .2, .3], [.2, .1, .4], [.0, .3, .2], [.1, .2, .1]], index=idx, columns=cols)
series = pd.Series([.5, .6, .4, .7], index=idx)
_ = frame.ge(series, axis=0)
_ = frame.le(series, axis=0)
_ = frame.gt(series, axis=0)
_ = frame < frame.shift(1)
_ = frame > frame.rolling(2).mean()

for name in (
    "research.strategy.pattern_discovery",
    "research.strategy.adaptive_improvement",
    "research.strategy.specialist_runner",
    "research.strategy.pipeline_orchestrator",
    "research.strategy.engine_sanity",
    "research.strategy.mission_controller",
    "research.strategy.candidate_qualification",
    "research.strategy.candidate_backtest",
    "research.strategy.strategy_lab_v3",
    "research.strategy.realistic_engine_v1",
    "research.strategy.strategy_lab_v4",
    "research.strategy.innovation_lab",
    "research.strategy.global_strategy_intelligence",
):
    importlib.import_module(name)

assert br.COST_HURDLE > 0

# Research-funnel regression guard: realistic admission must remain broad,
# include the short horizons needed for the owner's 5-20 trades/month target,
# and preserve capital-sized / explicit-RR exploration.
from research.strategy import strategy_lab_v4 as v4  # noqa: E402
assert v4.SCREEN_HORIZONS == (1, 2, 3, 5, 7, 10, 15, 20, 30)
assert None in v4.RR_VALUES
assert None in v4.RISK_PCTS
sample_rows = []
for i in range(v4.REALISTIC_CANDIDATE_ROWS):
    sample_rows.append({
        "variant": f"synthetic_{i}",
        "variant_id": f"id{i}",
        "family": f"family_{i}",
        "horizon_days": 1 + i,
        "dev_net_mean": -0.01 + i * 0.001,
        "dev_pf": 0.8 + i * 0.02,
        "dev_obs": 100,
        "sel_net_mean": -0.005 + i * 0.001,
        "sel_pf": 0.9 + i * 0.02,
        "sel_win_rate": 0.45,
        "sel_obs": 100,
        "sel_tpm": 5.0 + (i % 6),
        "selection_stability": -0.01 + i * 0.001,
        "screen_score": 0.5 + i * 0.01,
        "positive_selection_signal": False,
        "params": "{}",
    })
slate = v4.select_realistic_rows(pd.DataFrame(sample_rows))
assert len(slate) == v4.REALISTIC_CANDIDATE_ROWS
assert slate["family"].nunique() == v4.REALISTIC_CANDIDATE_ROWS


# Deterministic engine verification. A failed sanity check blocks only the
# current research cycle; the external supervisor will schedule recovery.
import subprocess  # noqa: E402
p = subprocess.run([sys.executable, str(ROOT / "research/strategy/engine_sanity.py")], cwd=ROOT, capture_output=True, text=True)
if p.returncode != 0:
    raise SystemExit(p.stdout + "\n" + p.stderr)
sanity = ROOT / "research/results/engine_sanity.json"
payload = json.loads(sanity.read_text(encoding="utf-8"))
assert payload.get("status") == "passed"

print("PREFLIGHT PASS: syntax, imports, pandas alignment, and engine sanity checks passed.")
