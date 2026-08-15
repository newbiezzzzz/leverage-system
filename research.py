import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

"""FCPO research worker.

Research-only: no live orders, no paid real-time feed, no external API calls.
Uses a cached local OHLCV dataset when available and performs deterministic
technical-strategy screening with conservative transaction-cost/slippage inputs.
"""

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "fcpo_ohlcv.csv"
DASH = ROOT / "dashboard"
DASH.mkdir(exist_ok=True)
TIMESTAMP = datetime.now(timezone.utc).isoformat()

CONFIG = {
    "instrument": "FCPO",
    "timeframes": ["5m", "15m", "1h", "4h", "1d"],
    "strategy_families": [
        "trend-following", "momentum", "breakout", "volatility",
        "price-action", "volume-confirmation", "multi-timeframe"
    ],
    "validation": [
        "realistic fees and slippage",
        "in-sample versus out-of-sample split",
        "walk-forward validation",
        "parameter-stability checks",
        "risk-adjusted ranking",
        "reject overfit candidates"
    ],
    "risk_gate": "REAL MONEY BLOCKED",
    "cost_policy": "RM0; cached data; no unnecessary API calls; no paid real-time dependency"
}


def sma(values, n):
    out = [math.nan] * len(values)
    if len(values) < n:
        return out
    s = sum(values[:n])
    out[n - 1] = s / n
    for i in range(n, len(values)):
        s += values[i] - values[i - n]
        out[i] = s / n
    return out


def load_ohlcv():
    if not DATA.exists():
        return []
    with DATA.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        try:
            out.append({
                "timestamp": r.get("timestamp", ""),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r.get("volume", 0) or 0),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return out


def simple_ma_cross(closes, fast, slow):
    sf, ss = sma(closes, fast), sma(closes, slow)
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    trades = 0
    pos = 0
    entry = None
    for i in range(len(closes)):
        if math.isnan(sf[i]) or math.isnan(ss[i]):
            continue
        signal = 1 if sf[i] > ss[i] else 0
        if signal != pos:
            if pos and entry is not None:
                equity *= max(0.0, 1.0 + (closes[i] / entry - 1.0) - 0.0008)
                trades += 1
            if signal:
                entry = closes[i]
            pos = signal
        peak = max(peak, equity)
        max_dd = max(max_dd, 1 - equity / peak)
    if pos and entry is not None:
        equity *= max(0.0, 1.0 + (closes[-1] / entry - 1.0) - 0.0008)
        trades += 1
    return {"return": equity - 1, "max_drawdown": max_dd, "trades": trades}


def main():
    rows = load_ohlcv()
    result = {
        "generated_at": TIMESTAMP,
        "worker": "research-worker",
        "project": "FCPO Trading Research",
        "instrument": "FCPO",
        "status": "research_in_progress",
        "mode": "research_only",
        "observations": len(rows),
        "strategy_candidates_tested": 0,
        "validated_strategies": 0,
        "strategy_results": [],
        "data_source": "cached local dataset (no live feed)",
        "data_policy": CONFIG["cost_policy"],
        "risk_gate": CONFIG["risk_gate"],
    }

    if not rows:
        result["latest_result"] = "FCPO dataset not yet available. Research worker is ready and waiting for cached OHLCV data."
    else:
        closes = [r["close"] for r in rows]
        candidates = [(10, 30), (20, 50), (20, 100), (50, 200)]
        scored = []
        for fast, slow in candidates:
            stats = simple_ma_cross(closes, fast, slow)
            scored.append({"family": "trend-following", "name": f"SMA {fast}/{slow}", **stats})
        result["strategy_candidates_tested"] = len(scored)
        result["strategy_results"] = scored
        result["latest_result"] = "Initial FCPO technical screen complete; candidates require out-of-sample and walk-forward validation."
        result["status"] = "research_complete_initial_screen"

    (DASH / "research.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = {
        "project": "FCPO Trading Research",
        "generated_at": TIMESTAMP,
        "instrument": "FCPO",
        "status": result["status"],
        "observations": result["observations"],
        "strategy_candidates_tested": result["strategy_candidates_tested"],
        "strategy_results": result["strategy_results"],
        "next_step": "Acquire/cache a permitted FCPO OHLCV dataset, then run technical strategy screening and walk-forward validation.",
        "risk_gate": CONFIG["risk_gate"],
        "cost_policy": CONFIG["cost_policy"]
    }
    (ROOT / "market_report.md").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
