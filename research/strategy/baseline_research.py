#!/usr/bin/env python3
"""Strategy Hunter fixed-rule baseline backtest.

This worker runs quantitative research outside ChatGPT. Rules are fixed before
optimization. It enforces one active position, Bursa 100-share lots, a
RM1,000 starting account, and next-day-open execution after close signals.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("research/data/data")
OHLCV = DATA / "ohlcv"
SHARIAH = DATA / "shariah" / "shariah_snapshots.csv"
OUT = Path("research/results")
OUT.mkdir(parents=True, exist_ok=True)

STARTING_CASH = 1000.0
LOT = 100
MAX_PRICE = 9.00
MIN_AVG_DOLLAR_VOL = 500_000.0
COST_MODEL = {
    "commission_rate": 0.0003,
    "commission_min": 3.0,
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
}


def fee(trade_value: float) -> float:
    commission = max(COST_MODEL["commission_min"], trade_value * COST_MODEL["commission_rate"])
    clearing = trade_value * COST_MODEL["clearing_rate"]
    stamp = math.ceil(trade_value / 1000.0) * COST_MODEL["stamp_per_1000"]
    subtotal = commission + COST_MODEL["platform_fee"] + clearing
    sst = subtotal * COST_MODEL["sst_rate"]
    return commission + COST_MODEL["platform_fee"] + clearing + stamp + sst


def load_wide():
    rows = []
    symbols = []
    for path in sorted(OHLCV.glob("*.csv")):
        try:
            d = pd.read_csv(path, parse_dates=["date"])
            required = {"date", "open", "high", "low", "close", "volume"}
            if not required <= set(d.columns):
                continue
            sym = path.stem.replace("_", ".", 1)
            d = d.sort_values("date").drop_duplicates("date")
            d = d.set_index("date")
            rows.append((sym, d))
            symbols.append(sym)
        except Exception:
            continue

    if not rows:
        raise SystemExit("No OHLCV data")

    idx = sorted(set().union(*[set(d.index) for _, d in rows]))
    index = pd.DatetimeIndex(idx)
    open_df = pd.DataFrame(index=index)
    high_df = pd.DataFrame(index=index)
    low_df = pd.DataFrame(index=index)
    close_df = pd.DataFrame(index=index)
    vol_df = pd.DataFrame(index=index)

    for sym, d in rows:
        open_df[sym] = d["open"].reindex(index)
        high_df[sym] = d["high"].reindex(index)
        low_df[sym] = d["low"].reindex(index)
        close_df[sym] = d["close"].reindex(index)
        vol_df[sym] = d["volume"].reindex(index)

    return open_df, high_df, low_df, close_df, vol_df


def universe_mask(index: pd.DatetimeIndex, columns: pd.Index) -> pd.DataFrame:
    u = pd.read_csv(SHARIAH, dtype={"raw_code": str})
    u["effective_date"] = pd.to_datetime(u["effective_date"])
    u = u.sort_values(["effective_date", "yahoo_symbol"])

    # Forward-fill each symbol's membership state across SC effective snapshots.
    dates = sorted(u["effective_date"].unique())
    mask = pd.DataFrame(False, index=index, columns=columns)

    for i, dt in enumerate(dates):
        end = dates[i + 1] if i + 1 < len(dates) else index.max() + pd.Timedelta(days=1)
        members = set(u.loc[u["effective_date"].eq(dt), "yahoo_symbol"].astype(str))
        period = (index >= dt) & (index < end)
        if period.any():
            cols = [c for c in columns if c in members]
            if cols:
                mask.loc[period, cols] = True
    return mask


def indicators(close, volume):
    avg_dollar = (close * volume).rolling(20, min_periods=20).mean()
    mom60 = close / close.shift(60) - 1.0
    ma20 = close.rolling(20, min_periods=20).mean()
    ma50 = close.rolling(50, min_periods=50).mean()
    ma100 = close.rolling(100, min_periods=100).mean()
    prev20_close_high = close.shift(1).rolling(20, min_periods=20).max()
    prev10_close_low = close.shift(1).rolling(10, min_periods=10).min()
    one_day = close.pct_change()
    return {
        "avg_dollar": avg_dollar,
        "mom60": mom60,
        "ma20": ma20,
        "ma50": ma50,
        "ma100": ma100,
        "prev20_high": prev20_close_high,
        "prev10_low": prev10_close_low,
        "one_day": one_day,
    }


def select_candidate(date, current_close, universe, ind, strategy, current_pos):
    eligible = universe.loc[date].copy()
    px = current_close.loc[date]
    liquid = (ind["avg_dollar"].loc[date] >= MIN_AVG_DOLLAR_VOL) & (px <= MAX_PRICE) & (px > 0)
    eligible &= liquid.fillna(False)

    if strategy == "momentum":
        signal = eligible & ind["mom60"].loc[date].notna()
        ranked = ind["mom60"].loc[date].where(signal).sort_values(ascending=False)
        return ranked.index[0] if len(ranked.dropna()) else None

    if strategy == "trend":
        signal = eligible & (ind["ma20"].loc[date] > ind["ma50"].loc[date]) & ind["ma50"].loc[date].notna()
        ranked = ind["mom60"].loc[date].where(signal).sort_values(ascending=False)
        return ranked.index[0] if len(ranked.dropna()) else None

    if strategy == "breakout":
        signal = (
            eligible
            & (current_close.loc[date] > ind["prev20_high"].loc[date])
            & (current_close.loc[date] > ind["ma50"].loc[date])
            & ind["ma50"].loc[date].notna()
        )
        ranked = ind["mom60"].loc[date].where(signal).sort_values(ascending=False)
        return ranked.index[0] if len(ranked.dropna()) else None

    if strategy == "shock_reaction":
        signal = (
            eligible
            & (ind["one_day"].loc[date] <= STRATEGIES["shock_reaction"]["shock"])
            & (current_close.loc[date] > ind["ma100"].loc[date])
            & ind["ma100"].loc[date].notna()
        )
        ranked = ind["mom60"].loc[date].where(signal).sort_values(ascending=False)
        return ranked.index[0] if len(ranked.dropna()) else None

    return None


def should_exit(date, pos_sym, entry_date, close, ind, strategy):
    px = close.loc[date, pos_sym]
    if pd.isna(px):
        return False
    if strategy == "momentum":
        return (date - entry_date).days >= STRATEGIES["momentum"]["hold_days"]
    if strategy == "trend":
        return (ind["ma20"].loc[date, pos_sym] < ind["ma50"].loc[date, pos_sym]) or (
            (date - entry_date).days >= STRATEGIES["trend"]["hold_days"]
        )
    if strategy == "breakout":
        return (close.loc[date, pos_sym] < ind["prev10_low"].loc[date, pos_sym]) or (
            (date - entry_date).days >= STRATEGIES["breakout"]["hold_days"]
        )
    if strategy == "shock_reaction":
        return (
            (date - entry_date).days >= STRATEGIES["shock_reaction"]["max_hold"]
            or (px >= 1.05 * close.shift(1).loc[date, pos_sym] if not pd.isna(close.shift(1).loc[date, pos_sym]) else False)
        )
    return False


def backtest(strategy: str, open_df, close_df, universe, ind):
    cash = STARTING_CASH
    pos_sym = None
    shares = 0
    entry_date = None
    entry_price = None
    equity = []
    trades = []

    dates = close_df.index
    pending_exit = False
    pending_entry = None

    for i, date in enumerate(dates[:-1]):
        next_date = dates[i + 1]

        # Execute decisions generated from the prior close at next open.
        if pending_exit and pos_sym is not None:
            px = open_df.loc[next_date, pos_sym]
            if pd.notna(px) and shares > 0:
                value = shares * px
                costs = fee(value)
                cash += value - costs
                trades.append({
                    "strategy": strategy,
                    "entry_date": entry_date,
                    "exit_date": next_date,
                    "symbol": pos_sym,
                    "entry_price": entry_price,
                    "exit_price": float(px),
                    "shares": int(shares),
                    "gross_pnl": float((px - entry_price) * shares),
                    "exit_fee": float(costs),
                })
                pos_sym = None
                shares = 0
                entry_date = None
                entry_price = None
            pending_exit = False

        if pending_entry is not None and pos_sym is None:
            sym = pending_entry
            px = open_df.loc[next_date, sym]
            if pd.notna(px) and px > 0:
                max_shares = int((cash / px) // LOT) * LOT
                if max_shares >= LOT:
                    value = max_shares * px
                    costs = fee(value)
                    if value + costs <= cash:
                        cash -= value + costs
                        pos_sym = sym
                        shares = max_shares
                        entry_date = next_date
                        entry_price = float(px)
            pending_entry = None

        # Mark-to-market at today's close after execution.
        eq = cash
        if pos_sym is not None:
            cp = close_df.loc[date, pos_sym]
            if pd.notna(cp):
                eq += shares * cp
        equity.append((date, eq))

        # Generate next-close decisions.
        if pos_sym is not None:
            if should_exit(date, pos_sym, entry_date, close_df, ind, strategy):
                pending_exit = True
                pending_entry = None
        else:
            pending_entry = select_candidate(date, close_df, universe, ind, strategy, current_pos=None)

    eq = pd.Series(dict(equity)).sort_index()
    if eq.empty:
        return None

    # Close any remaining position at final close for analysis.
    if pos_sym is not None:
        final = dates[-1]
        px = close_df.loc[final, pos_sym]
        if pd.notna(px):
            value = shares * px
            costs = fee(value)
            cash += value - costs
            trades.append({
                "strategy": strategy,
                "entry_date": entry_date,
                "exit_date": final,
                "symbol": pos_sym,
                "entry_price": entry_price,
                "exit_price": float(px),
                "shares": int(shares),
                "gross_pnl": float((px - entry_price) * shares),
                "exit_fee": float(costs),
            })
            eq.iloc[-1] = cash

    ret = eq.iloc[-1] / STARTING_CASH - 1.0
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1 / 365.25)
    cagr = (eq.iloc[-1] / STARTING_CASH) ** (1 / years) - 1.0
    peak = eq.cummax()
    dd = eq / peak - 1.0
    trade_df = pd.DataFrame(trades)

    wins = (trade_df["gross_pnl"] - trade_df["exit_fee"] > 0).sum() if not trade_df.empty else 0
    win_rate = wins / len(trade_df) if len(trade_df) else 0.0
    gross_profit = (trade_df.loc[trade_df["gross_pnl"] - trade_df["exit_fee"] > 0, "gross_pnl"] - trade_df.loc[trade_df["gross_pnl"] - trade_df["exit_fee"] > 0, "exit_fee"]).sum() if not trade_df.empty else 0.0
    gross_loss = -(trade_df.loc[trade_df["gross_pnl"] - trade_df["exit_fee"] < 0, "gross_pnl"] - trade_df.loc[trade_df["gross_pnl"] - trade_df["exit_fee"] < 0, "exit_fee"]).sum() if not trade_df.empty else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    return {
        "strategy": strategy,
        "start": eq.index[0].date().isoformat(),
        "end": eq.index[-1].date().isoformat(),
        "final_equity": float(eq.iloc[-1]),
        "total_return": float(ret),
        "cagr": float(cagr),
        "max_drawdown": float(dd.min()),
        "trade_count": int(len(trade_df)),
        "trades_per_month": float(len(trade_df) / max(years * 12, 1)),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "equity_volatility": float(eq.pct_change().std() * np.sqrt(252)),
        "trade_rows": trades,
    }


def main():
    open_df, high_df, low_df, close_df, vol_df = load_wide()
    universe = universe_mask(close_df.index, close_df.columns)
    ind = indicators(close_df, vol_df)

    results = []
    for strategy in STRATEGIES:
        result = backtest(strategy, open_df, close_df, universe, ind)
        if result:
            results.append(result)

    out = []
    for r in results:
        x = {k: v for k, v in r.items() if k != "trade_rows"}
        out.append(x)
    pd.DataFrame(out).to_csv(OUT / "baseline_results.csv", index=False)

    with open(OUT / "baseline_trade_log.json", "w", encoding="utf-8") as f:
        json.dump({r["strategy"]: r["trade_rows"] for r in results}, f, indent=2, default=str)

    pd.DataFrame(
        {
            "strategy": list(STRATEGIES),
            "parameters_json": [json.dumps(STRATEGIES[s], sort_keys=True) for s in STRATEGIES],
            "cost_model_json": [json.dumps(COST_MODEL, sort_keys=True)] * len(STRATEGIES),
            "starting_cash": [STARTING_CASH] * len(STRATEGIES),
            "lot_size": [LOT] * len(STRATEGIES),
        }
    ).to_csv(OUT / "baseline_spec.csv", index=False)

    print(pd.DataFrame(out).to_string(index=False))


if __name__ == "__main__":
    main()
