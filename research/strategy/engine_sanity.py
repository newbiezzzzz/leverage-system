#!/usr/bin/env python3
"""Deterministic sanity checks for the Strategy Hunter backtest engine.

These tests intentionally use synthetic data so engine correctness is checked
without depending on live market downloads or third-party data quality.
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "strategy"))

import baseline_research as br  # noqa: E402


def make_series(kind: str, n: int = 180) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=n)
    if kind == "up":
        close = 10.0 * (1.01 ** np.arange(n))
    elif kind == "down":
        close = 50.0 * (0.99 ** np.arange(n))
    elif kind == "flat":
        close = np.full(n, 20.0)
    else:
        raise ValueError(kind)
    open_ = close.copy()
    high = close * 1.01
    low = close * 0.99
    volume = np.full(n, 100_000.0)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=dates)


def run_case(kind: str) -> dict:
    df = make_series(kind)
    cols = pd.Index(["TEST"])
    close = pd.DataFrame({"TEST": df["close"]}, index=df.index)
    open_ = pd.DataFrame({"TEST": df["open"]}, index=df.index)
    volume = pd.DataFrame({"TEST": df["volume"]}, index=df.index)
    universe = pd.DataFrame(True, index=df.index, columns=cols)
    ind = br.indicators(close, volume)
    result = br.backtest("momentum", open_, close, universe, ind)
    if result is None:
        raise AssertionError(f"{kind}: no result returned")

    assert result["final_equity"] >= 0.0, f"{kind}: negative account value"
    assert result["max_drawdown"] <= 0.0, f"{kind}: positive drawdown"
    assert result["max_drawdown"] >= -1.0, f"{kind}: drawdown below -100%"
    for trade in result["trade_rows"]:
        lhs = trade["net_pnl"]
        rhs = trade["gross_pnl"] - trade["entry_fee"] - trade["exit_fee"]
        assert abs(lhs - rhs) < 1e-8, f"{kind}: trade P&L identity broken"
        assert trade["entry_price"] > 0 and trade["exit_price"] > 0
        assert trade["shares"] > 0

    return {
        "case": kind,
        "final_equity": result["final_equity"],
        "max_drawdown": result["max_drawdown"],
        "trade_count": result["trade_count"],
    }


def main() -> None:
    assert br.fee(0) >= 0
    assert br.fee(950) >= 0
    results = [run_case(k) for k in ("up", "down", "flat")]
    out = ROOT / "research" / "results" / "engine_sanity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "passed",
        "tests": results,
        "invariants": [
            "final_equity_nonnegative",
            "drawdown_between_minus_100_and_zero",
            "trade_pnl_identity",
            "positive_execution_prices",
            "positive_share_count"
        ]
    }
    out.write_text(__import__("json").dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(__import__("json").dumps(payload, indent=2))


if __name__ == "__main__":
    main()
