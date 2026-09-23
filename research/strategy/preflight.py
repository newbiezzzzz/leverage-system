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
):
    importlib.import_module(name)

assert br.COST_HURDLE > 0

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
