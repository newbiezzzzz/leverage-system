#!/usr/bin/env python3
"""Strategy Hunter pattern discovery: test interpretable price/volume/regime patterns.

This is an event-study stage, not a final trading strategy. Signals use only
information known at close[t]. Forward returns begin at open[t+1] to avoid
look-ahead. The sample is split into fixed discovery and validation periods.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from baseline_research import load_wide, universe_mask, indicators, MIN_PRICE, MAX_PRICE, fee, CAPITAL_PCT, STARTING_CASH

OUT = Path("research/results")
OUT.mkdir(parents=True, exist_ok=True)

DISCOVERY_END = pd.Timestamp("2023-12-29")
HORIZONS = (5, 10, 20, 40)


def main():
    open_df, high_df, low_df, close_df, volume_df = load_wide()
    universe = universe_mask(close_df.index, close_df.columns)
    ind = indicators(close_df, volume_df)

    liquid = (
        universe
        & (ind["avg_dollar"] >= 100_000.0)
        & close_df.ge(MIN_PRICE)
        & close_df.le(MAX_PRICE)
        & close_df.notna()
    )

    dollar = close_df * volume_df
    range_pct = (high_df - low_df) / close_df.replace(0, np.nan)
    range20 = range_pct.rolling(20, min_periods=20).mean()
    vol20 = close_df.pct_change().rolling(20, min_periods=20).std()
    vol63 = close_df.pct_change().rolling(63, min_periods=63).std()

    mom1 = close_df / close_df.shift(1) - 1.0
    mom3 = close_df / close_df.shift(3) - 1.0
    mom5 = close_df / close_df.shift(5) - 1.0
    mom20 = close_df / close_df.shift(20) - 1.0
    mom60 = close_df / close_df.shift(60) - 1.0
    mom126 = close_df / close_df.shift(126) - 1.0
    mom252_skip21 = close_df.shift(21) / close_df.shift(273) - 1.0

    market_ret5 = mom5.where(liquid).mean(axis=1)
    market_ret20 = mom20.where(liquid).mean(axis=1)
    rel5 = mom5.sub(market_ret5, axis=0)
    rel20 = mom20.sub(market_ret20, axis=0)

    breadth200 = ((close_df > ind["ma200"]) & liquid).sum(axis=1) / liquid.sum(axis=1).replace(0, np.nan)
    q10_mom5 = mom5.where(liquid).quantile(0.10, axis=1)
    q20_mom5 = mom5.where(liquid).quantile(0.20, axis=1)
    q80_rel20 = rel20.where(liquid).quantile(0.80, axis=1)

    breakout20 = close_df > ind["prev20_high"]
    volume_ratio = ind["volume_ratio20"]

    patterns = {
        "momentum_60_uptrend": liquid & (mom60 > 0.05) & (close_df > ind["ma100"]),
        "slow_momentum_12_1": liquid & (mom252_skip21 > 0) & (close_df > ind["ma200"]),
        "pullback_in_uptrend": liquid & (mom60 > 0) & (close_df > ind["ma100"]) & mom5.between(-0.10, -0.03),
        "reversal_bottom10": liquid & (mom5.le(q10_mom5, axis=0)) & (close_df > ind["ma200"]) & (ind["avg_dollar"] >= 500_000.0),
        "panic_reversal_volume": liquid & (mom1 <= -0.05) & (volume_ratio >= 1.5) & (close_df > ind["ma200"]) & (ind["avg_dollar"] >= 500_000.0),
        "relative_reversal_bottom20": liquid & (mom5.le(q20_mom5, axis=0)) & (close_df > ind["ma50"]) & (ind["avg_dollar"] >= 500_000.0),
        "breakout_plus_volume": liquid & breakout20 & (close_df > ind["ma50"]) & (volume_ratio >= 1.5),
        "volatility_contraction_breakout": liquid & breakout20 & (close_df > ind["ma50"]) & (volume_ratio >= 1.5) & (vol20 <= 0.80 * vol63),
        "relative_strength_20": liquid & (rel20.ge(q80_rel20, axis=0)) & (close_df > ind["ma100"]),
        "low_vol_momentum_regime": liquid & (breadth200 >= 0.55) & (mom60 > 0) & (close_df > ind["ma100"]),
        "high_vol_reversal_regime": liquid & (breadth200 <= 0.45) & mom5.le(q10_mom5, axis=0) & (close_df > ind["ma200"]) & (ind["avg_dollar"] >= 500_000.0),
        "range_expansion_reversal": liquid & (mom5 <= -0.05) & (range_pct >= 1.5 * range20) & (close_df > ind["ma200"]) & (ind["avg_dollar"] >= 500_000.0),
    }

    rows = []
    for horizon in HORIZONS:
        fwd = (close_df.shift(-horizon) / open_df.shift(-1)) - 1.0
        for name, mask in patterns.items():
            x = fwd.where(mask)
            flat = x.stack().dropna()
            for period_name, period_mask in (
                ("discovery", fwd.index <= DISCOVERY_END),
                ("validation", fwd.index > DISCOVERY_END),
            ):
                pflat = x.loc[period_mask].stack().dropna()
                if pflat.empty:
                    continue
                rows.append({
                    "pattern": name,
                    "horizon_days": horizon,
                    "period": period_name,
                    "observations": int(len(pflat)),
                    "mean_return": float(pflat.mean()),
                    "median_return": float(pflat.median()),
                    "win_rate": float((pflat > 0).mean()),
                    "p10": float(pflat.quantile(0.10)),
                    "p90": float(pflat.quantile(0.90)),
                "net_mean_vs_hurdle": float(pflat.mean() - COST_HURDLE),
                })

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "pattern_discovery.csv", index=False)

    # Produce a compact validation-focused table. Patterns are not ranked by
    # full-sample results; selection requires positive discovery and validation.
    piv = df.pivot_table(index=["pattern", "horizon_days"], columns="period", values=["mean_return", "win_rate", "observations"])
    candidates = []
    for name in patterns:
        ok = []
        for h in HORIZONS:
            try:
                di = float(piv.loc[(name, h), ("mean_return", "discovery")])
                va = float(piv.loc[(name, h), ("mean_return", "validation")])
                vw = float(piv.loc[(name, h), ("win_rate", "validation")])
                vn = int(piv.loc[(name, h), ("observations", "validation")])
                if di > COST_HURDLE and va > COST_HURDLE and vw >= 0.50 and vn >= 100:
                    ok.append((h, va, vw, vn))
            except Exception:
                pass
        if ok:
            best_h, best_mean, best_win, best_n = max(ok, key=lambda z: z[1])
            candidates.append({
                "pattern": name,
                "robust_horizons": len(ok),
                "best_validation_horizon": best_h,
                "validation_mean": best_mean,
                "validation_win_rate": best_win,
                "validation_observations": best_n,
            })

    cand = pd.DataFrame(candidates).sort_values(
        ["robust_horizons", "validation_mean"], ascending=False
    ) if candidates else pd.DataFrame(columns=[
        "pattern", "robust_horizons", "best_validation_horizon",
        "validation_mean", "validation_win_rate", "validation_observations"
    ])
    cand.to_csv(OUT / "pattern_candidates.csv", index=False)

    lines = [
        "# Strategy Hunter — Pattern Discovery",
        "",
        f"Discovery period: through {DISCOVERY_END.date()} | Validation period: after {DISCOVERY_END.date()}",
        "",
        "Signals use close[t]; forward return starts from open[t+1].",
        "",
        "## Patterns surviving both periods",
        "",
        f"| Approx. round-trip cost hurdle on RM1,000 | | | {COST_HURDLE*100:.2f}% | | |",
        "",
        "| Pattern | Cost-positive horizons | Best validation horizon | Validation mean | Win rate | Observations |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    if cand.empty:
        lines.append("| None yet | 0 | — | — | — | — |")
    else:
        for _, r in cand.head(12).iterrows():
            lines.append(
                f"| {r['pattern']} | {int(r['robust_horizons'])} | "
                f"{int(r['best_validation_horizon'])}d | {r['validation_mean']*100:.2f}% | "
                f"{r['validation_win_rate']*100:.1f}% | {int(r['validation_observations'])} |"
            )
    lines += [
        "",
        "This is pattern evidence, not a live-trading recommendation.",
        "A pattern must beat the approximate round-trip cost hurdle in both discovery and validation before becoming a strategy candidate.",
        "Next gate: convert surviving patterns into low-turnover RM1,000 backtests with realistic costs and walk-forward testing.",
    ]
    (OUT / "pattern_discovery.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(cand.to_string(index=False) if not cand.empty else "No robust candidates yet.")


if __name__ == "__main__":
    main()
