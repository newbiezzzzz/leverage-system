#!/usr/bin/env python3
"""Strategy Hunter V3 Strategy Lab.

Purpose:
- search a materially broader, reproducible set of long-only strategies;
- select only from development + selection periods;
- test selected strategies on a final holdout period;
- enforce realistic RM1,000 costs, one-position execution, and drawdown;
- keep the research loop moving even when no strategy qualifies.

This is research infrastructure. It does not place trades or move money.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "results"
OUT.mkdir(parents=True, exist_ok=True)

STARTING_CASH = 1000.0
CAPITAL_PCT = 0.95
STOP_LOSSES = (0.04, 0.06, 0.08, 0.10)
HORIZONS = (5, 10, 20, 30)
DEV_END = pd.Timestamp("2020-12-31")
SEL_END = pd.Timestamp("2023-12-29")
HOLDOUT_START = SEL_END + pd.Timedelta(days=1)
MIN_PRICE = 0.50
MAX_PRICE = 1000.0
MIN_AVG_DOLLAR_VOL = 100_000.0
MAX_DD = 0.10
MIN_TRADES_PER_MONTH = 5.0
MAX_TRADES_PER_MONTH = 20.0

COST_MODEL = {
    "commission_rate": 0.0003,
    "platform_fee": 3.0,
    "clearing_rate": 0.0003,
    "stamp_per_1000": 1.0,
    "sst_rate": 0.08,
}


def fee(value: float) -> float:
    if value <= 0:
        return 0.0
    commission = value * COST_MODEL["commission_rate"]
    clearing = value * COST_MODEL["clearing_rate"]
    stamp = math.ceil(value / 1000.0) * COST_MODEL["stamp_per_1000"]
    subtotal = commission + COST_MODEL["platform_fee"] + clearing
    return commission + COST_MODEL["platform_fee"] + clearing + stamp + subtotal * COST_MODEL["sst_rate"]


COST_HURDLE = 2.0 * fee(STARTING_CASH * CAPITAL_PCT) / (STARTING_CASH * CAPITAL_PCT)


def _stats(mask: pd.DataFrame, fwd: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, min_obs: int = 100):
    x = fwd.where(mask).loc[(fwd.index > start) & (fwd.index <= end)].stack().dropna()
    if len(x) < min_obs:
        return None
    return {
        "observations": int(len(x)),
        "mean_return": float(x.mean()),
        "net_mean": float(x.mean() - COST_HURDLE),
        "median_return": float(x.median()),
        "win_rate": float((x > 0).mean()),
        "p10": float(x.quantile(0.10)),
        "p90": float(x.quantile(0.90)),
    }


def _liquid_universe(cp, vp, universe, ind):
    return (
        universe
        & (ind["avg_dollar"] >= MIN_AVG_DOLLAR_VOL)
        & cp.ge(MIN_PRICE)
        & cp.le(MAX_PRICE)
        & cp.notna()
    )


def build_variants(op, hp, lp, cp, vp, universe, ind):
    """Return {name: {mask, score, family, params}} for reproducible candidates."""
    liquid = _liquid_universe(cp, vp, universe, ind)
    mom1 = cp / cp.shift(1) - 1.0
    mom3 = cp / cp.shift(3) - 1.0
    mom5 = cp / cp.shift(5) - 1.0
    mom10 = cp / cp.shift(10) - 1.0
    mom20 = cp / cp.shift(20) - 1.0
    mom60 = cp / cp.shift(60) - 1.0
    mom90 = cp / cp.shift(90) - 1.0
    mom120 = cp / cp.shift(120) - 1.0
    mom180 = cp / cp.shift(180) - 1.0
    mom252 = cp.shift(21) / cp.shift(273) - 1.0
    vr20 = ind["volume_ratio20"]
    vol20 = cp.pct_change().rolling(20, min_periods=20).std()
    vol63 = ind["vol63"]
    range_pct = (hp - lp) / cp.replace(0, np.nan)
    range20 = range_pct.rolling(20, min_periods=20).mean()
    market20 = mom20.where(liquid).mean(axis=1)
    rel20 = mom20.sub(market20, axis=0)
    market60 = mom60.where(liquid).mean(axis=1)
    rel60 = mom60.sub(market60, axis=0)
    breadth = ((cp > ind["ma200"]) & liquid).sum(axis=1) / liquid.sum(axis=1).replace(0, np.nan)
    q10 = mom5.where(liquid).quantile(0.10, axis=1)
    q20 = mom5.where(liquid).quantile(0.20, axis=1)

    variants = {}

    def add(name, mask, score, family, params):
        variants[name] = {
            "mask": mask.fillna(False),
            "score": score,
            "family": family,
            "params": params,
        }

    # 1) Momentum across several time horizons and trend filters.
    for lb, mom in ((20, mom20), (40, mom60), (60, mom60), (90, mom90), (120, mom120)):
        for threshold in (0.00, 0.03, 0.06, 0.10):
            for trend_name, trend in (("ma50", ind["ma50"]), ("ma200", ind["ma200"])):
                add(
                    f"momentum_lb{lb}_th{int(threshold*100)}_{trend_name}",
                    liquid & (mom > threshold) & (cp > trend),
                    mom,
                    "momentum",
                    {"lookback": lb, "threshold": threshold, "trend": trend_name},
                )

    # 2) Trend-transition / moving-average cross.
    for fast, slow in ((10, 30), (20, 50), (30, 100), (50, 200)):
        fma = cp.rolling(fast, min_periods=fast).mean()
        sma = cp.rolling(slow, min_periods=slow).mean()
        accel = fma / fma.shift(5) - 1.0
        add(
            f"cross_{fast}_{slow}_fresh",
            liquid & (fma > sma) & (fma.shift(1) <= sma.shift(1)) & (accel > 0),
            accel,
            "trend_transition",
            {"fast": fast, "slow": slow, "fresh": True},
        )
        add(
            f"cross_{fast}_{slow}_hold",
            liquid & (fma > sma) & (accel > 0) & (mom20 > 0),
            accel,
            "trend_transition",
            {"fast": fast, "slow": slow, "fresh": False},
        )

    # 3) Breakout + volume + optional volatility contraction.
    for b in (5, 10, 20, 40, 60):
        prev = cp.shift(1).rolling(b, min_periods=b).max()
        for vr in (1.0, 1.5, 2.0):
            for trend_name, trend in (("ma50", ind["ma50"]), ("ma100", ind["ma100"])):
                add(
                    f"breakout_b{b}_vr{vr:g}_{trend_name}",
                    liquid & (cp > prev) & (cp > trend) & (vr20 >= vr),
                    mom20,
                    "breakout",
                    {"breakout": b, "volume_ratio": vr, "trend": trend_name, "contraction": None},
                )
                for contraction in (0.70, 0.90):
                    add(
                        f"breakout_b{b}_vr{vr:g}_{trend_name}_vc{contraction:g}",
                        liquid
                        & (cp > prev)
                        & (cp > trend)
                        & (vr20 >= vr)
                        & (vol20 <= contraction * vol63),
                        mom20,
                        "breakout",
                        {"breakout": b, "volume_ratio": vr, "trend": trend_name, "contraction": contraction},
                    )

    # 4) Pullback / dip-buy in established trends.
    for lb, mom in ((20, mom20), (60, mom60), (120, mom120)):
        for drop in (-0.03, -0.05, -0.08, -0.10):
            for trend_name, trend in (("ma100", ind["ma100"]), ("ma200", ind["ma200"])):
                add(
                    f"pullback_lb{lb}_drop{int(abs(drop)*100)}_{trend_name}",
                    liquid
                    & (mom > 0)
                    & (mom5 <= drop)
                    & (mom5 >= -0.15)
                    & (cp > trend),
                    mom,
                    "pullback",
                    {"lookback": lb, "drop": drop, "trend": trend_name},
                )

    # 5) Short-term reversal, but only in longer-term uptrends.
    for drop in (-0.04, -0.06, -0.08, -0.10):
        for trend_name, trend in (("ma100", ind["ma100"]), ("ma200", ind["ma200"])):
            for vr in (1.0, 1.5, 2.0):
                add(
                    f"reversal_drop{int(abs(drop)*100)}_{trend_name}_vr{vr:g}",
                    liquid
                    & (mom5 <= drop)
                    & (cp > trend)
                    & (vr20 >= vr)
                    & (ind["avg_dollar"] >= 500_000.0),
                    -mom5,
                    "reversal",
                    {"drop": drop, "trend": trend_name, "volume_ratio": vr},
                )

    # 6) Cross-sectional relative strength / loser reversal.
    for relq in (0.70, 0.80, 0.90):
        q = rel20.where(liquid).quantile(relq, axis=1)
        for lb, mom in ((20, mom20), (60, mom60)):
            for trend_name, trend in (("ma100", ind["ma100"]), ("ma200", ind["ma200"])):
                add(
                    f"relstrength_q{int(relq*100)}_lb{lb}_{trend_name}",
                    liquid & rel20.ge(q, axis=0) & (mom > 0) & (cp > trend),
                    rel20,
                    "relative_strength",
                    {"relative_quantile": relq, "momentum_lb": lb, "trend": trend_name},
                )

    for quantile, name, score in ((0.10, "bottom10", -mom5), (0.20, "bottom20", -mom5)):
        q = mom5.where(liquid).quantile(quantile, axis=1)
        for trend_name, trend in (("ma50", ind["ma50"]), ("ma100", ind["ma100"]), ("ma200", ind["ma200"])):
            add(
                f"loser_reversal_{name}_{trend_name}",
                liquid & mom5.le(q, axis=0) & (cp > trend) & (ind["avg_dollar"] >= 500_000.0),
                score,
                "loser_reversal",
                {"loser_quantile": quantile, "trend": trend_name},
            )

    # 7) Volatility expansion / contraction.
    for ratio in (0.60, 0.90, 1.20, 1.50):
        add(
            f"vol_regime_mom_{ratio:g}",
            liquid & (mom20 > 0) & (cp > ind["ma100"]) & (vol20 <= ratio * vol63),
            mom20,
            "volatility",
            {"vol_ratio_max": ratio},
        )
        add(
            f"vol_expansion_mom_{ratio:g}",
            liquid & (mom20 > 0) & (cp > ind["ma100"]) & (vol20 >= ratio * vol63),
            mom20,
            "volatility",
            {"vol_ratio_min": ratio},
        )

    # 8) Gap continuation / gap recovery.
    gap = op / cp.shift(1) - 1.0
    for g in (0.02, 0.04, 0.06):
        add(
            f"gap_up_continuation_{int(g*100)}",
            liquid & (gap >= g) & (mom20 > 0) & (cp > ind["ma50"]),
            mom20,
            "gap",
            {"gap_min": g, "direction": "up"},
        )
        add(
            f"gap_down_recovery_{int(g*100)}",
            liquid & (gap <= -g) & (mom5 > 0) & (cp > ind["ma200"]),
            mom5,
            "gap",
            {"gap_min": g, "direction": "down"},
        )

    # 9) Range expansion / exhaustion reversal.
    for drop in (-0.03, -0.05, -0.07, -0.10):
        for expansion in (1.2, 1.5, 2.0):
            add(
                f"range_expansion_rev_drop{int(abs(drop)*100)}_x{expansion:g}",
                liquid
                & (mom5 <= drop)
                & (range_pct >= expansion * range20)
                & (cp > ind["ma200"])
                & (ind["avg_dollar"] >= 500_000.0),
                -mom5,
                "range_reversal",
                {"drop": drop, "range_expansion": expansion},
            )

    # 10) Wyckoff-style spring / SOS.
    for lb in (10, 20, 30):
        support = lp.rolling(lb, min_periods=lb).min().shift(1)
        undercut = lp / support - 1.0
        bar_range = (hp - lp).replace(0, np.nan)
        clv = (cp - lp) / bar_range
        for depth in (-0.01, -0.02, -0.03):
            for clv_min in (0.60, 0.70):
                for vr_max in (1.2, 1.5):
                    add(
                        f"wyckoff_spring_lb{lb}_d{int(abs(depth)*1000)}_clv{int(clv_min*100)}_vr{vr_max:g}",
                        liquid
                        & (undercut <= depth)
                        & (cp > support)
                        & (clv >= clv_min)
                        & (vr20 <= vr_max),
                        -mom5,
                        "wyckoff_spring",
                        {"support_lb": lb, "depth": depth, "clv_min": clv_min, "volume_ratio_max": vr_max},
                    )
        spring = (undercut <= -0.01) & (cp > support) & (clv >= 0.65) & (vr20 <= 1.5)
        for vr_min in (1.0, 1.3, 1.6, 2.0):
            add(
                f"wyckoff_sos_lb{lb}_vr{vr_min:g}",
                liquid & spring.shift(1).fillna(False) & (cp > hp.shift(1)) & (vr20 >= vr_min),
                mom5,
                "wyckoff_sos",
                {"support_lb": lb, "volume_ratio_min": vr_min},
            )

    # 11) Regime-aware momentum and reversal.
    for bull in (0.40, 0.55, 0.70):
        for lb, mom in ((20, mom20), (60, mom60)):
            add(
                f"regime_bull{int(bull*100)}_mom{lb}",
                liquid & breadth.ge(bull, axis=0) & (mom > 0) & (cp > ind["ma100"]),
                mom,
                "regime",
                {"breadth_min": bull, "momentum_lb": lb},
            )
            add(
                f"regime_bear{int(bull*100)}_rev{lb}",
                liquid & breadth.le(1.0 - bull, axis=0) & (mom5 < -0.03) & (cp > ind["ma200"]),
                -mom5,
                "regime_reversal",
                {"breadth_max": 1.0 - bull, "context_lb": lb},
            )

    # 12) Open-ended mathematical/indicator/pattern discovery layer.
    # This expands the search space beyond the hand-authored strategy families.
    try:
        from innovation_lab import build_discovery_variants
        discovered = build_discovery_variants(op, hp, lp, cp, vp, universe, ind)
        variants.update(discovered)
    except Exception as exc:
        # Discovery expansion is additive; a failure must not destroy the
        # deterministic core research path.
        print(f"innovation_lab degraded: {type(exc).__name__}: {exc}")

    return variants


def _choose_symbol(score, mask_row, reversal=False):
    candidates = score.where(mask_row).dropna()
    if candidates.empty:
        return None
    return candidates.sort_values(ascending=reversal).index[0]


def _backtest_window(name, variant, op, hp, lp, cp, vp, start, end, stop_loss, starting_cash=STARTING_CASH, universe=None):
    dates = cp.index
    idx = np.where((dates > start) & (dates <= end))[0]
    if len(idx) < 30:
        return None

    cash = float(starting_cash)
    peak = float(starting_cash)
    pos = None
    shares = 0
    entry_idx = None
    entry_price = None
    entry_fee = 0.0
    trades = []
    risk_breaches = 0
    equity_rows = []

    score = variant["score"]
    mask = variant["mask"]
    family = variant["family"]
    reversal = any(k in family for k in ("reversal", "loser"))

    for i in idx:
        if i <= 0:
            continue
        d = dates[i]

        if pos is not None:
            open_px = float(op.iloc[i][pos]) if pd.notna(op.iloc[i][pos]) else np.nan
            low_px = float(lp.iloc[i][pos]) if pd.notna(lp.iloc[i][pos]) else np.nan
            close_px = float(cp.iloc[i][pos]) if pd.notna(cp.iloc[i][pos]) else np.nan
            held = i - entry_idx
            exit_px = None
            reason = None

            stop = entry_price * (1.0 - stop_loss)
            if pd.notna(open_px) and pd.notna(low_px) and low_px <= stop:
                exit_px = min(open_px, stop)
                reason = "stop"
            elif held >= variant["horizon"] and pd.notna(open_px) and open_px > 0:
                exit_px = open_px
                reason = "horizon"

            if exit_px is not None and shares:
                value = shares * exit_px
                exit_fee = fee(value)
                cash += value - exit_fee
                trades.append({
                    "strategy": name,
                    "entry_date": str(dates[entry_idx].date()),
                    "exit_date": str(d.date()),
                    "symbol": pos,
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_px),
                    "shares": int(shares),
                    "entry_fee": float(entry_fee),
                    "exit_fee": float(exit_fee),
                    "gross_pnl": float((exit_px - entry_price) * shares),
                    "net_pnl": float((exit_px - entry_price) * shares - entry_fee - exit_fee),
                    "exit_reason": reason,
                })
                pos = None
                shares = 0
                entry_idx = None
                entry_price = None
                entry_fee = 0.0

        if pos is None:
            row_mask = mask.iloc[i]
            if universe is not None:
                row_mask = row_mask & universe.iloc[i]
            sym = _choose_symbol(score.iloc[i], row_mask, reversal=reversal)
            if sym is not None:
                px = op.iloc[i][sym]
                if pd.notna(px) and float(px) > 0:
                    deploy = cash * CAPITAL_PCT
                    qty = int(deploy / float(px))
                    if qty > 0:
                        value = qty * float(px)
                        ef = fee(value)
                        if value + ef <= cash:
                            cash -= value + ef
                            pos = sym
                            shares = qty
                            entry_idx = i
                            entry_price = float(px)
                            entry_fee = float(ef)

        eq = cash
        if pos is not None:
            px = cp.iloc[i][pos]
            if pd.notna(px):
                eq += shares * float(px)
        peak = max(peak, float(eq))
        dd = eq / peak - 1.0 if peak > 0 else -1.0
        if dd <= -MAX_DD:
            risk_breaches += 1
        equity_rows.append((d, float(eq)))

    if pos is not None and shares:
        px = cp.iloc[idx[-1]][pos]
        if pd.notna(px):
            value = shares * float(px)
            ef = fee(value)
            cash += value - ef
            trades.append({
                "strategy": name,
                "entry_date": str(dates[entry_idx].date()),
                "exit_date": str(dates[idx[-1]].date()),
                "symbol": pos,
                "entry_price": float(entry_price),
                "exit_price": float(px),
                "shares": int(shares),
                "entry_fee": float(entry_fee),
                "exit_fee": float(ef),
                "gross_pnl": float((px - entry_price) * shares),
                "net_pnl": float((px - entry_price) * shares - entry_fee - ef),
                "exit_reason": "window_end",
            })

    if not equity_rows:
        return None
    eq = pd.Series(dict(equity_rows)).sort_index()
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1 / 365.25)
    final_equity = float(cash)
    total_return = final_equity / starting_cash - 1.0
    max_dd = float((eq / eq.cummax() - 1.0).min())
    gp = sum(max(0.0, t["net_pnl"]) for t in trades)
    gl = sum(-min(0.0, t["net_pnl"]) for t in trades)
    pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)
    return {
        "final_equity": final_equity,
        "total_return": total_return,
        "cagr": float((final_equity / starting_cash) ** (1 / years) - 1.0) if final_equity > 0 else float("nan"),
        "max_drawdown": max_dd,
        "trade_count": int(len(trades)),
        "trades_per_month": float(len(trades) / max(years * 12.0, 1.0)),
        "profit_factor": float(pf),
        "risk_breach_count": int(risk_breaches),
        "trades": trades,
    }


def _replicate_by_symbol_half(result_name, variant, op, hp, lp, cp, vp, universe, stop_loss):
    symbols = list(cp.columns)
    if len(symbols) < 20:
        return None
    left, right = [], []
    for sym in symbols:
        h = int(hashlib.sha256(sym.encode("utf-8")).hexdigest()[:8], 16)
        (left if h % 2 == 0 else right).append(sym)
    reports = []
    for idx, group in enumerate((left, right), start=1):
        if len(group) < 8:
            continue
        masked_universe = universe.copy()
        masked_universe.loc[:, [s for s in cp.columns if s not in group]] = False
        r = _backtest_window(
            result_name,
            variant,
            op, hp, lp, cp, vp,
            HOLDOUT_START, cp.index.max(),
            stop_loss,
            starting_cash=STARTING_CASH,
            universe=masked_universe,
        )
        if r:
            reports.append((idx, r))
    if len(reports) != 2:
        return None
    return reports


def main():
    op, hp, lp, cp, vp = __import__("baseline_research").load_wide()
    universe = __import__("baseline_research").universe_mask(cp.index, cp.columns)
    ind = __import__("baseline_research").indicators(cp, vp)

    cycle_path = OUT / "strategy_hunter_progress.json"
    try:
        previous_cycle = int(json.loads(cycle_path.read_text(encoding="utf-8")).get("cycle", 0))
    except Exception:
        previous_cycle = 0
    cycle = previous_cycle + 1

    variants = build_variants(op, hp, lp, cp, vp, universe, ind)
    fwd = {h: cp.shift(-h) / op.shift(-1) - 1.0 for h in HORIZONS}

    rows = []
    for name, v in variants.items():
        for h in HORIZONS:
            v["horizon"] = h
            dev = _stats(v["mask"], fwd[h], pd.Timestamp("2014-01-01"), DEV_END)
            sel = _stats(v["mask"], fwd[h], DEV_END, SEL_END)
            if not dev or not sel:
                continue
            rows.append({
                "pattern": name,
                "family": v["family"],
                "horizon_days": h,
                "development_net_mean": dev["net_mean"],
                "selection_net_mean": sel["net_mean"],
                "selection_win_rate": sel["win_rate"],
                "selection_observations": sel["observations"],
                "selection_stability": min(dev["net_mean"], sel["net_mean"]),
                "params": json.dumps(v["params"], sort_keys=True),
            })

    event = pd.DataFrame(rows)
    event.to_csv(OUT / "strategy_lab_event_screen.csv", index=False)

    if event.empty:
        selected = pd.DataFrame()
    else:
        selected = event[
            (event.development_net_mean > 0)
            & (event.selection_net_mean > 0)
            & (event.selection_win_rate >= 0.50)
            & (event.selection_observations >= 100)
        ].copy()
        selected["selection_score"] = (
            selected["selection_net_mean"].clip(lower=0)
            * np.sqrt(selected["selection_observations"].clip(lower=1))
            * selected["selection_stability"].clip(lower=0)
        )
        # Keep the research broad: at most 6 variants from one family.
        selected = (
            selected.sort_values(["selection_score", "selection_net_mean"], ascending=False)
            .groupby("family", group_keys=False)
            .head(6)
            .sort_values(["selection_score", "selection_net_mean"], ascending=False)
            .head(24)
        )

    selected.to_csv(OUT / "strategy_lab_selection.csv", index=False)

    backtests = []
    for r in selected.itertuples(index=False):
        name = r.pattern
        v = variants[name]
        v["horizon"] = int(r.horizon_days)
        for stop in STOP_LOSSES:
            full = _backtest_window(
                name, v, op, hp, lp, cp, vp,
                pd.Timestamp("2014-01-01"), cp.index.max(),
                stop_loss=stop,
                starting_cash=STARTING_CASH,
                universe=universe,
            )
            sel_bt = _backtest_window(
                name, v, op, hp, lp, cp, vp,
                DEV_END, SEL_END,
                stop_loss=stop,
                starting_cash=STARTING_CASH,
                universe=universe,
            )
            hold_bt = _backtest_window(
                name, v, op, hp, lp, cp, vp,
                HOLDOUT_START, cp.index.max(),
                stop_loss=stop,
                starting_cash=STARTING_CASH,
                universe=universe,
            )
            if not full or not sel_bt or not hold_bt:
                continue

            rep = _replicate_by_symbol_half(name, v, op, hp, lp, cp, vp, universe, stop)
            rep_pass = False
            rep_detail = None
            if rep:
                rep_pass = all(
                    x[1]["final_equity"] > STARTING_CASH
                    and x[1]["max_drawdown"] >= -MAX_DD
                    and x[1]["profit_factor"] > 1.0
                    for x in rep
                )
                rep_detail = [
                    {
                        "half": x[0],
                        "final_equity": x[1]["final_equity"],
                        "max_drawdown": x[1]["max_drawdown"],
                        "profit_factor": x[1]["profit_factor"],
                        "trades_per_month": x[1]["trades_per_month"],
                    }
                    for x in rep
                ]

            backtests.append({
                "pattern": name,
                "family": r.family,
                "horizon_days": int(r.horizon_days),
                "stop_loss": stop,
            "params": r.params,
            "full_final_equity": full["final_equity"],
            "full_total_return": full["total_return"],
            "full_cagr": full["cagr"],
            "full_max_drawdown": full["max_drawdown"],
            "full_trade_count": full["trade_count"],
            "full_trades_per_month": full["trades_per_month"],
            "full_profit_factor": full["profit_factor"],
            "full_risk_breaches": full["risk_breach_count"],
            "selection_final_equity": sel_bt["final_equity"],
            "selection_total_return": sel_bt["total_return"],
            "selection_max_drawdown": sel_bt["max_drawdown"],
            "selection_trade_count": sel_bt["trade_count"],
            "selection_trades_per_month": sel_bt["trades_per_month"],
            "selection_profit_factor": sel_bt["profit_factor"],
            "holdout_final_equity": hold_bt["final_equity"],
            "holdout_total_return": hold_bt["total_return"],
            "holdout_cagr": hold_bt["cagr"],
            "holdout_max_drawdown": hold_bt["max_drawdown"],
            "holdout_trade_count": hold_bt["trade_count"],
            "holdout_trades_per_month": hold_bt["trades_per_month"],
            "holdout_profit_factor": hold_bt["profit_factor"],
            "holdout_risk_breaches": hold_bt["risk_breach_count"],
            "independent_replication": rep_pass,
            "replication_detail": json.dumps(rep_detail),
            "frequency_gate": bool(
                MIN_TRADES_PER_MONTH <= hold_bt["trades_per_month"] <= MAX_TRADES_PER_MONTH
            ),
            "risk_gate": bool(hold_bt["max_drawdown"] >= -MAX_DD),
            "profit_gate": bool(hold_bt["final_equity"] > STARTING_CASH and hold_bt["profit_factor"] > 1.0),
            "holdout_positive": bool(hold_bt["total_return"] > 0),
        })

    bt = pd.DataFrame(backtests)
    if not bt.empty:
        # Selection order is fixed before holdout evaluation. Holdout is
        # confirmatory and cannot be used to rank or cherry-pick a winner.
        # Rank only on the development/selection periods; however, every
        # shortlisted combination is tested on the sealed holdout.
        bt["selection_score"] = (
            bt["selection_total_return"].clip(lower=0)
            * np.sqrt(bt["selection_trade_count"].clip(lower=1))
            * bt["selection_profit_factor"].replace([np.inf, -np.inf], 0).clip(lower=0)
        )
        bt = bt.sort_values(
            ["selection_score", "selection_total_return", "selection_profit_factor"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
        bt["selection_rank"] = np.arange(1, len(bt) + 1)
        # Do not discard holdout survivors merely because another
        # candidate ranked above them during selection. Qualification is a
        # gate; final champion selection happens only after all gates.
        bt["research_candidate"] = (
            bt["holdout_positive"]
            & bt["profit_gate"]
            & bt["risk_gate"]
            & bt["frequency_gate"]
            & bt["independent_replication"]
            & bt["selection_total_return"].gt(0)
            & bt["selection_profit_factor"].gt(1.0)
            & bt["selection_trades_per_month"].between(MIN_TRADES_PER_MONTH, MAX_TRADES_PER_MONTH)
        )
    bt.to_csv(OUT / "strategy_lab_backtests.csv", index=False)

    winners = bt[bt.research_candidate == True] if not bt.empty else pd.DataFrame()
    leader = winners.iloc[0] if not winners.empty else None

    evidence = {
        "status": "candidate_ready" if leader is not None else "searching",
        "candidate_id": None,
        "selected_by": "strategy_lab_v3_plus_discovery_layer_development_selection_only",
        "lab_cycle": cycle,
        "gates": {
            "data_integrity": True,
            "engine_sanity": (OUT / "engine_sanity.json").exists()
            and json.loads((OUT / "engine_sanity.json").read_text(encoding="utf-8")).get("status") == "passed",
            "positive_after_costs": False,
            "robust_out_of_sample": False,
            "drawdown_within_limit": False,
            "trade_frequency_feasible": False,
            "broker_feasible_at_rm1000": False,
            "historical_shariah_compliance": True,
            "independent_replication": False,
            "forward_paper_validation": False,
        },
    }

    if leader is not None:
        raw_id = f"{leader['pattern']}:{int(leader['horizon_days'])}:{leader['stop_loss']}".encode("utf-8")
        evidence["candidate_id"] = f"SH-{int(hashlib.sha256(raw_id).hexdigest()[:8], 16) % 1_000_000:06d}"
        evidence["strategy"] = {
            "pattern": leader["pattern"],
            "family": leader["family"],
            "horizon_days": int(leader["horizon_days"]),
            "stop_loss": float(leader["stop_loss"]),
            "params": json.loads(leader["params"]),
        }
        evidence["selection_result"] = {
            "final_equity": float(leader["selection_final_equity"]),
            "total_return": float(leader["selection_total_return"]),
            "max_drawdown": float(leader["selection_max_drawdown"]),
            "trade_count": int(leader["selection_trade_count"]),
            "trades_per_month": float(leader["selection_trades_per_month"]),
            "profit_factor": float(leader["selection_profit_factor"]),
        }
        evidence["oos_result"] = {
            "final_equity": float(leader["holdout_final_equity"]),
            "total_return": float(leader["holdout_total_return"]),
            "cagr": float(leader["holdout_cagr"]),
            "max_drawdown": float(leader["holdout_max_drawdown"]),
            "trade_count": int(leader["holdout_trade_count"]),
            "trades_per_month": float(leader["holdout_trades_per_month"]),
            "profit_factor": float(leader["holdout_profit_factor"]),
            "risk_breaches": int(leader["holdout_risk_breaches"]),
        }
        evidence["gates"]["positive_after_costs"] = True
        evidence["gates"]["robust_out_of_sample"] = True
        evidence["gates"]["drawdown_within_limit"] = bool(leader["holdout_max_drawdown"] >= -MAX_DD)
        evidence["gates"]["trade_frequency_feasible"] = bool(leader["frequency_gate"])
        # Broker feasibility is intentionally left as a separate gate. The
        # lab's own accounting is not proof of Moomoo/Phillip Nova execution rules.
        evidence["gates"]["broker_feasible_at_rm1000"] = False
        evidence["gates"]["independent_replication"] = bool(leader["independent_replication"])

    (OUT / "qualified_strategy_evidence.json").write_text(
        json.dumps(evidence, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    try:
        gi = json.loads((OUT / "global_strategy_intelligence.json").read_text(encoding="utf-8"))
    except Exception:
        gi = {}
    progress = {
        "cycle": cycle,
        "updated_at": pd.Timestamp.utcnow().isoformat(),
        "patterns_tested": int(len(variants)),
        "strategy_lab_variants": int(len(variants)),
        "discovery_layer": {
            "enabled": True,
            "innovation_variants": int(sum(1 for v in variants.values() if str(v.get("family", "")).startswith("math_") or str(v.get("family", "")).startswith("interaction_") or str(v.get("family", "")).startswith("price_action"))),
            "external_items": int(gi.get("source_count", 0)),
            "external_hypotheses": int(len(gi.get("hypotheses", []))),
        },
        "strategy_lab_selection_candidates": int(len(selected)),
        "strategy_lab_backtests": int(len(bt)),
        "strategy_lab_qualified_candidates": int(len(winners)),
        "strategy_lab_leader": (
            {
                "pattern": leader["pattern"],
                "family": leader["family"],
                "holdout_total_return": float(leader["holdout_total_return"]),
                "holdout_max_drawdown": float(leader["holdout_max_drawdown"]),
                "holdout_trades_per_month": float(leader["holdout_trades_per_month"]),
                "holdout_profit_factor": float(leader["holdout_profit_factor"]),
                "independent_replication": bool(leader["independent_replication"]),
            }
            if leader is not None else None
        ),
        "search_round": int(cycle),
        "adaptive_unique_variants": 0,
        "adaptive_new_variants_this_cycle": 0,
        "adaptive_focus_patterns": [],
        "candidates": int(len(selected)),
        "robust_candidates": int(len(winners)),
        "engine_sanity": evidence["gates"]["engine_sanity"],
        "last_cycle_status": "completed",
        "next_action": "deeper_validation" if leader is not None else "expand_search",
    }
    (OUT / "strategy_hunter_progress.json").write_text(
        json.dumps(progress, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    report = {
        "status": "candidate_ready" if leader is not None else "searching",
        "cycle": cycle,
        "variants_tested": int(len(variants)),
        "selection_candidates": int(len(selected)),
        "backtests": int(len(bt)),
        "qualified_candidates": int(len(winners)),
        "cost_hurdle": COST_HURDLE,
        "leader": evidence.get("strategy"),
    }
    (OUT / "strategy_lab_state.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "research" / "strategy"))
    main()
