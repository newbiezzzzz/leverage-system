#!/usr/bin/env python3
"""Deterministic sanity checks for the realistic execution engine."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "strategy"))

from realistic_engine_v1 import backtest  # noqa: E402


def run():
    dates = pd.bdate_range("2024-01-01", periods=80)
    cols = ["TEST"]
    close = pd.DataFrame(10.0, index=dates, columns=cols)
    open_ = pd.DataFrame(10.0, index=dates, columns=cols)
    high = pd.DataFrame(10.1, index=dates, columns=cols)
    low = pd.DataFrame(9.9, index=dates, columns=cols)
    volume = pd.DataFrame(1_000_000.0, index=dates, columns=cols)

    # Only close[t=40] creates the entry signal. The engine MUST enter at t=41 open.
    close.iloc[40, 0] = 20.0
    open_.iloc[41, 0] = 30.0
    close.iloc[41, 0] = 30.0
    high.iloc[41, 0] = 31.0
    low.iloc[41, 0] = 29.0

    variant = {
        "score": close.copy(),
        "mask": close.ge(20.0),
        "family": "momentum",
        "params": {},
    }
    universe = pd.DataFrame(True, index=dates, columns=cols)

    result = backtest(
        "sanity", variant, open_, high, low, close, volume, universe,
        dates[35], dates[60], horizon_days=20, stop_loss=0.10,
        lot_size=1, slippage_bps=0.0,
    )
    assert result and result["trades"], "sanity trade missing"
    trade = result["trades"][0]
    assert trade["signal_date"] == dates[40].date().isoformat(), trade
    assert trade["entry_date"] == dates[41].date().isoformat(), trade
    assert trade["entry_price"] == 30.0, trade
    assert trade["signal_before_execution"] is True, trade

    # Verify gap-through stop is recorded as a real execution event.
    open2 = open_.copy()
    low2 = low.copy()
    close2 = close.copy()
    open2.iloc[42,0] = 20.0
    low2.iloc[42,0] = 19.0
    close2.iloc[42,0] = 20.0
    result2 = backtest(
        "sanity_gap", variant, open2, high, low2, close2, volume, universe,
        dates[35], dates[60], horizon_days=20, stop_loss=0.10,
        lot_size=1, slippage_bps=0.0,
    )
    assert result2 and any(t["exit_reason"] == "stop_gap_open" for t in result2["trades"]), result2
    assert all(
        pd.Timestamp(t["entry_date"]) > pd.Timestamp(t["signal_date"])
        for t in result2["trades"] if t.get("signal_date")
    )
    print("REALISTIC ENGINE SANITY PASS")


if __name__ == "__main__":
    run()
