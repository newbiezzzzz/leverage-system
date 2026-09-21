#!/usr/bin/env python3
"""Cheap Strategy Hunter preflight.

Checks syntax/imports and key pandas alignment operations before an expensive
full-data run starts. No market data download is required.
"""
from __future__ import annotations

import importlib
import py_compile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FILES=[
    ROOT/"research/strategy/baseline_research.py",
    ROOT/"research/strategy/pattern_discovery.py",
    ROOT/"research/strategy/adaptive_improvement.py",
    ROOT/"research/strategy/specialist_runner.py",
    ROOT/"research/strategy/pipeline_orchestrator.py",
]
for path in FILES:
    py_compile.compile(str(path),doraise=True)

import pandas as pd
from research.strategy import baseline_research as br

idx=pd.date_range("2024-01-01",periods=4)
cols=["AAA","BBB","CCC"]
frame=pd.DataFrame([[.1,.2,.3],[.2,.1,.4],[.0,.3,.2],[.1,.2,.1]],index=idx,columns=cols)
series=pd.Series([.5,.6,.4,.7],index=idx)

# These are the alignment operations that previously broke the adaptive stage.
_=(frame.ge(series,axis=0))
_=(frame.le(series,axis=0))
_=(frame.gt(series,axis=0))
_=(frame < frame.shift(1))
_=(frame > frame.rolling(2).mean())

for name in ("research.strategy.pattern_discovery","research.strategy.adaptive_improvement","research.strategy.specialist_runner","research.strategy.pipeline_orchestrator"):
    importlib.import_module(name)

assert br.COST_HURDLE > 0
print("PREFLIGHT PASS: syntax, imports, and pandas alignment checks passed.")
