#!/usr/bin/env python3
"""Strategy Hunter v2 fixed-rule research.

Corrected execution timing:
- signal is generated from close[t]
- order is executed at open[t+1]
- equity is marked at close[t] using positions actually held on t

This version tests the original four rules plus research-backed candidates.
No optimization is performed here.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("research/data/data")
OHLCV = DATA / "ohlcv"
SHARIAH = DATA / "shariah" / "shariah_snapshots.csv"
OUT = Path("research/results")
OUT.mkdir(parents=True, exist_ok=True)

STARTING_CASH = 1000.0
CAPITAL_PCT = 0.95
LOT = 1
MIN_PRICE = 0.50
MAX_PRICE = 1000.0
MIN_AVG_DOLLAR_VOL = 100_000.0
COST_MODEL = {
    "commission_rate": 0.0003,
    "platform_fee": 3.0,
    "clearing_rate": 0.0003,
    "stamp_per_1000": 1.0,
    "sst_rate": 0.08,
}

STRATEGIES = {
    "momentum": {"lookback": 60, "hold_days": 10},
    "trend": {"fast": 20, "slow": 50, "hold_days": 20},
    "breakout": {"breakout": 20, "exit": 10, "trend": 50, "hold_days": 30},
    "shock_reaction": {"shock": -0.05, "trend": 100, "max_hold": 10},
    "slow_momentum": {"lookback": 252, "skip": 21, "trend": 200, "hold_days": 40},
    "volume_momentum": {"lookback": 126, "vol_window": 63, "trend": 100, "hold_days": 30},
    "trend_pullback": {"trend": 100, "momentum": 60, "drop_min": -0.10, "drop_max": -0.03, "hold_days": 15},
    "active_reversal": {"drop": -0.06, "trend": 200, "min_dollar_vol": 500_000.0, "rebound": 0.05, "max_hold": 10},
    "breakout_volume": {"breakout": 20, "exit": 10, "trend": 50, "volume_mult": 1.5, "hold_days": 30},
    "high_volume_reversal": {"drop": -0.05, "trend": 200, "min_dollar_vol": 500_000.0, "max_hold": 5, "rebound": 0.03},
    "downturn_reversal": {"drop": -0.05, "trend": 200, "min_dollar_vol": 500_000.0, "max_hold": 5, "rebound": 0.03, "breadth_max": 0.45},
    "relative_contrarian": {"lookback": 5, "bottom_quantile": 0.20, "min_dollar_vol": 500_000.0, "max_hold": 5},
}


def fee(trade_value: float) -> float:
    if os.environ.get("SH_DISABLE_COSTS", "0") == "1":
        return 0.0
    commission = trade_value * COST_MODEL["commission_rate"]
    clearing = trade_value * COST_MODEL["clearing_rate"]
    stamp = math.ceil(trade_value / 1000.0) * COST_MODEL["stamp_per_1000"]
    subtotal = commission + COST_MODEL["platform_fee"] + clearing
    sst = subtotal * COST_MODEL["sst_rate"]
    return commission + COST_MODEL["platform_fee"] + clearing + stamp + sst


def load_wide():
    rows = []
    for path in sorted(OHLCV.glob("*.csv")):
        try:
            d = pd.read_csv(path, parse_dates=["date"])
            required = {
                "date", "open", "high", "low", "close", "volume",
                "split_adj_open", "split_adj_high", "split_adj_low",
                "split_adj_close", "split_adj_volume",
            }
            if not required <= set(d.columns):
                continue
            sym = path.stem.replace("_", ".", 1)
            d = d.sort_values("date").drop_duplicates("date").set_index("date")
            rows.append((sym, d))
        except Exception:
            continue

    if not rows:
        raise SystemExit("No valid split-adjusted OHLCV data")

    index = pd.DatetimeIndex(sorted(set().union(*[set(d.index) for _, d in rows])))
    frames = {k: pd.DataFrame(index=index) for k in ("open", "high", "low", "close", "volume")}
    for sym, d in rows:
        frames["open"][sym] = d["split_adj_open"].reindex(index)
        frames["high"][sym] = d["split_adj_high"].reindex(index)
        frames["low"][sym] = d["split_adj_low"].reindex(index)
        frames["close"][sym] = d["split_adj_close"].reindex(index)
        frames["volume"][sym] = d["split_adj_volume"].reindex(index)
    return frames["open"], frames["high"], frames["low"], frames["close"], frames["volume"]


def universe_mask(index: pd.DatetimeIndex, columns: pd.Index) -> pd.DataFrame:
    u = pd.read_csv(SHARIAH, dtype={"raw_code": str})
    u["effective_date"] = pd.to_datetime(u["effective_date"])
    dates = sorted(u["effective_date"].dropna().unique())
    mask = pd.DataFrame(False, index=index, columns=columns)
    for i, dt in enumerate(dates):
        end = dates[i + 1] if i + 1 < len(dates) else index.max() + pd.Timedelta(days=1)
        members = set(u.loc[u["effective_date"].eq(dt), "yahoo_symbol"].astype(str))
        period = (index >= dt) & (index < end)
        cols = [c for c in columns if c in members]
        if cols and period.any():
            mask.loc[period, cols] = True
    return mask


def indicators(close: pd.DataFrame, volume: pd.DataFrame):
    dollar = close * volume
    return {
        "avg_dollar": dollar.rolling(20, min_periods=20).mean(),
        "avg_dollar_500k": dollar.rolling(20, min_periods=20).mean(),
        "mom5": close / close.shift(5) - 1.0,
        "mom60": close / close.shift(60) - 1.0,
        "mom126": close / close.shift(126) - 1.0,
        "mom252_skip21": close.shift(21) / close.shift(252 + 21) - 1.0,
        "ma20": close.rolling(20, min_periods=20).mean(),
        "ma50": close.rolling(50, min_periods=50).mean(),
        "ma100": close.rolling(100, min_periods=100).mean(),
        "ma200": close.rolling(200, min_periods=200).mean(),
        "vol63": close.pct_change().rolling(63, min_periods=63).std(),
        "prev20_high": close.shift(1).rolling(20, min_periods=20).max(),
        "prev10_low": close.shift(1).rolling(10, min_periods=10).min(),
        "volume_ratio20": volume / volume.rolling(20, min_periods=20).mean(),
        "one_day": close.pct_change(),
        "mom_week": close / close.shift(5) - 1.0,
    }


def select_candidate(date, close, universe, ind, strategy):
    eligible = universe.loc[date].copy()
    px = close.loc[date]
    liquid = (
        (ind["avg_dollar"].loc[date] >= MIN_AVG_DOLLAR_VOL)
        & (px >= MIN_PRICE)
        & (px <= MAX_PRICE)
        & px.notna()
    )
    eligible &= liquid.fillna(False)

    if strategy == "momentum":
        score = ind["mom60"].loc[date]
        signal = eligible & score.notna()
    elif strategy == "trend":
        score = ind["mom60"].loc[date]
        signal = eligible & (ind["ma20"].loc[date] > ind["ma50"].loc[date]) & score.notna()
    elif strategy == "breakout":
        score = ind["mom60"].loc[date]
        signal = (
            eligible
            & (px > ind["prev20_high"].loc[date])
            & (px > ind["ma50"].loc[date])
            & score.notna()
        )
    elif strategy == "shock_reaction":
        score = ind["mom5"].loc[date]
        signal = (
            eligible
            & (score <= STRATEGIES[strategy]["shock"])
            & (px > ind["ma100"].loc[date])
            & ind["ma100"].loc[date].notna()
        )
    elif strategy == "slow_momentum":
        score = ind["mom252_skip21"].loc[date]
        signal = eligible & (px > ind["ma200"].loc[date]) & score.notna()
    elif strategy == "volume_momentum":
        vol = ind["vol63"].loc[date]
        score = ind["mom126"].loc[date] / vol.replace(0, np.nan)
        signal = (
            eligible
            & (px > ind["ma100"].loc[date])
            & (ind["avg_dollar"].loc[date] >= MIN_AVG_DOLLAR_VOL)
            & score.notna()
        )
    elif strategy == "trend_pullback":
        score = ind["mom60"].loc[date]
        drop = ind["mom5"].loc[date]
        p = STRATEGIES[strategy]
        signal = (
            eligible
            & (px > ind["ma100"].loc[date])
            & (score > 0)
            & (drop >= p["drop_min"])
            & (drop <= p["drop_max"])
            & score.notna()
        )
    elif strategy == "active_reversal":
        score = ind["mom5"].loc[date]
        p = STRATEGIES[strategy]
        signal = (
            eligible
            & (score <= p["drop"])
            & (px > ind["ma200"].loc[date])
            & (ind["avg_dollar_500k"].loc[date] >= p["min_dollar_vol"])
            & ind["ma200"].loc[date].notna()
        )
    elif strategy == "breakout_volume":
        score = ind["mom60"].loc[date]
        p = STRATEGIES[strategy]
        signal = (
            eligible
            & (px > ind["prev20_high"].loc[date])
            & (px > ind["ma50"].loc[date])
            & (ind["volume_ratio20"].loc[date] >= p["volume_mult"])
            & score.notna()
        )
    elif strategy in {"high_volume_reversal", "downturn_reversal"}:
        score = ind["mom5"].loc[date]
        p = STRATEGIES[strategy]
        breadth = (px > ind["ma200"].loc[date]).where(eligible).mean()
        signal = (
            eligible
            & (score <= p["drop"])
            & (px > ind["ma200"].loc[date])
            & (ind["avg_dollar"].loc[date] >= p["min_dollar_vol"])
            & ind["ma200"].loc[date].notna()
        )
        if strategy == "downturn_reversal":
            signal &= breadth <= p["breadth_max"]
    elif strategy == "relative_contrarian":
        score = ind["mom_week"].loc[date]
        p = STRATEGIES[strategy]
        eligible_scores = score.where(eligible).dropna()
        if len(eligible_scores) >= 10:
            cutoff = eligible_scores.quantile(p["bottom_quantile"])
            signal = (
                eligible
                & (score <= cutoff)
                & (ind["avg_dollar"].loc[date] >= p["min_dollar_vol"])
                & score.notna()
            )
        else:
            signal = pd.Series(False, index=score.index)
    else:
        return None

    ranked = score.where(signal).dropna().sort_values(ascending=False)
    if strategy in {"shock_reaction", "active_reversal", "trend_pullback"}:
        ranked = score.where(signal).dropna().sort_values(ascending=True if strategy in {"active_reversal", "high_volume_reversal", "downturn_reversal"} else False)
    return ranked.index[0] if not ranked.empty else None


def should_exit(i, pos_sym, entry_i, entry_price, close, ind, strategy):
    px = close.iloc[i][pos_sym]
    if pd.isna(px):
        return False
    held = i - entry_i

    if strategy == "momentum":
        return held >= STRATEGIES[strategy]["hold_days"]
    if strategy == "trend":
        return (ind["ma20"].iloc[i][pos_sym] < ind["ma50"].iloc[i][pos_sym]) or held >= STRATEGIES[strategy]["hold_days"]
    if strategy == "breakout":
        return (px < ind["prev10_low"].iloc[i][pos_sym]) or held >= STRATEGIES[strategy]["hold_days"]
    if strategy == "shock_reaction":
        return held >= STRATEGIES[strategy]["max_hold"] or px >= entry_price * 1.05
    if strategy == "slow_momentum":
        return held >= STRATEGIES[strategy]["hold_days"]
    if strategy == "volume_momentum":
        return (px < ind["ma100"].iloc[i][pos_sym]) or held >= STRATEGIES[strategy]["hold_days"]
    if strategy == "trend_pullback":
        return (px > ind["ma20"].iloc[i][pos_sym]) or (px < ind["ma50"].iloc[i][pos_sym]) or held >= STRATEGIES[strategy]["hold_days"]
    if strategy == "active_reversal":
        return px >= entry_price * (1 + STRATEGIES[strategy]["rebound"]) or held >= STRATEGIES[strategy]["max_hold"]
    if strategy == "breakout_volume":
        return (px < ind["prev10_low"].iloc[i][pos_sym]) or held >= STRATEGIES[strategy]["hold_days"]
    if strategy in {"high_volume_reversal", "downturn_reversal"}:
        p = STRATEGIES[strategy]
        return px >= entry_price * (1 + p["rebound"]) or held >= p["max_hold"]
    if strategy == "relative_contrarian":
        return held >= STRATEGIES[strategy]["max_hold"]
    return False


def backtest(strategy, open_df, close_df, universe, ind):
    cash = STARTING_CASH
    pos_sym = None
    shares = 0
    entry_i = None
    entry_date = None
    entry_price = None
    pending_exit = False
    pending_entry = None
    equity_rows = []
    trades = []

    for i in range(1, len(close_df)):
        date = close_df.index[i]

        if pending_exit and pos_sym is not None:
            px = open_df.iloc[i][pos_sym]
            if pd.notna(px) and px > 0 and shares > 0:
                value = shares * float(px)
                costs = fee(value)
                cash += value - costs
                trades.append({
                    "strategy": strategy,
                    "entry_date": str(entry_date.date()),
                    "exit_date": str(date.date()),
                    "symbol": pos_sym,
                    "entry_price": float(entry_price),
                    "exit_price": float(px),
                    "shares": int(shares),
                    "gross_pnl": float((px - entry_price) * shares),
                    "exit_fee": float(costs),
                })
                pos_sym = None
                shares = 0
                entry_i = entry_date = entry_price = None
            pending_exit = False

        if pending_entry is not None and pos_sym is None:
            sym = pending_entry
            px = open_df.iloc[i][sym]
            if pd.notna(px) and px > 0:
                max_shares = int((cash * CAPITAL_PCT / float(px)) // LOT) * LOT
                if max_shares > 0:
                    value = max_shares * float(px)
                    costs = fee(value)
                    if value + costs <= cash:
                        cash -= value + costs
                        pos_sym = sym
                        shares = max_shares
                        entry_i = i
                        entry_date = date
                        entry_price = float(px)
            pending_entry = None

        # Equity at this date uses the position actually held on this date.
        eq = cash
        if pos_sym is not None:
            cp = close_df.iloc[i][pos_sym]
            if pd.notna(cp):
                eq += shares * float(cp)
        equity_rows.append((date, eq))

        # Signal at today's close, executed next trading day's open.
        if pos_sym is not None:
            if should_exit(i, pos_sym, entry_i, entry_price, close_df, ind, strategy):
                pending_exit = True
                pending_entry = None
        else:
            pending_entry = select_candidate(date, close_df, universe, ind, strategy)

    eq = pd.Series(dict(equity_rows)).sort_index()
    if eq.empty:
        return None

    # Liquidate at final close for a conservative final account value.
    if pos_sym is not None:
        final_date = close_df.index[-1]
        px = close_df.iloc[-1][pos_sym]
        if pd.notna(px) and shares > 0:
            value = shares * float(px)
            costs = fee(value)
            cash += value - costs
            trades.append({
                "strategy": strategy,
                "entry_date": str(entry_date.date()),
                "exit_date": str(final_date.date()),
                "symbol": pos_sym,
                "entry_price": float(entry_price),
                "exit_price": float(px),
                "shares": int(shares),
                "gross_pnl": float((px - entry_price) * shares),
                "exit_fee": float(costs),
            })
            eq.iloc[-1] = cash

    total_return = eq.iloc[-1] / STARTING_CASH - 1.0
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1 / 365.25)
    cagr = (eq.iloc[-1] / STARTING_CASH) ** (1 / years) - 1.0 if eq.iloc[-1] > 0 else np.nan
    drawdown = eq / eq.cummax() - 1.0
    tdf = pd.DataFrame(trades)

    if tdf.empty:
        win_rate = 0.0
        profit_factor = 0.0
    else:
        net_trade = tdf["gross_pnl"] - tdf["exit_fee"]
        win_rate = float((net_trade > 0).mean())
        gp = float(net_trade[net_trade > 0].sum())
        gl = float(-net_trade[net_trade < 0].sum())
        profit_factor = gp / gl if gl > 0 else float("inf")

    return {
        "strategy": strategy,
        "start": eq.index[0].date().isoformat(),
        "end": eq.index[-1].date().isoformat(),
        "final_equity": float(eq.iloc[-1]),
        "total_return": float(total_return),
        "cagr": float(cagr) if pd.notna(cagr) else np.nan,
        "max_drawdown": float(drawdown.min()),
        "trade_count": int(len(tdf)),
        "trades_per_month": float(len(tdf) / max(years * 12, 1)),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "equity_volatility": float(eq.pct_change(fill_method=None).std() * np.sqrt(252)),
        "trade_rows": trades,
    }


def main():
    open_df, _, _, close_df, vol_df = load_wide()
    universe = universe_mask(close_df.index, close_df.columns)
    ind = indicators(close_df, vol_df)

    results = []
    for strategy in STRATEGIES:
        result = backtest(strategy, open_df, close_df, universe, ind)
        if result:
            results.append(result)

    summary = pd.DataFrame([{k: v for k, v in r.items() if k != "trade_rows"} for r in results])
    summary.to_csv(OUT / "baseline_results.csv", index=False)

    with open(OUT / "baseline_trade_log.json", "w", encoding="utf-8") as f:
        json.dump({r["strategy"]: r["trade_rows"] for r in results}, f, indent=2)

    spec = pd.DataFrame(
        {
            "strategy": list(STRATEGIES),
            "parameters_json": [json.dumps(STRATEGIES[s], sort_keys=True) for s in STRATEGIES],
            "cost_model_json": [json.dumps(COST_MODEL, sort_keys=True)] * len(STRATEGIES),
            "starting_cash": [STARTING_CASH] * len(STRATEGIES),
            "capital_pct": [CAPITAL_PCT] * len(STRATEGIES),
            "lot_size": [LOT] * len(STRATEGIES),
        }
    )
    spec.to_csv(OUT / "baseline_spec.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
