#!/usr/bin/env python3
"""Realistic single-position trading execution engine for Leverage.

Hard invariants:
- signal timestamp = close[t]
- execution timestamp = open[t+1] or later
- whole-share/board-lot sizing
- exact configured transaction costs
- adverse slippage
- liquidity participation cap
- gap-aware stop losses
- explicit data-end liquidation
- execution audit rejects look-ahead
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


STARTING_CASH = 1000.0
CAPITAL_PCT = 0.95
LOT_SIZE = 100
MIN_PRICE = 0.50
MAX_PRICE = 1000.0
MIN_AVG_DOLLAR_VOL = 100_000.0
MAX_PARTICIPATION = 0.10
SLIPPAGE_BPS = 10.0

# Verified broker reference used for the RM1,000 feasibility gate.
# Moomoo MY's current Bursa equity schedule uses 0.03% commission,
# RM3/order platform fee, 0.03% clearing, RM1 per RM1,000 stamp duty, and
# 8% SST on commission/platform/clearing. Bursa equity trades use 100-share
# board lots on the supported path.
BROKER_NAME = "Moomoo MY - Bursa Malaysia equities"
BROKER_LOT_SIZE = 100
BROKER_FEE_SOURCE = "https://www.moomoo.com/my/support/topic9_137"

COST_MODEL = {
    "commission_rate": 0.0003,
    "platform_fee": 3.0,
    "clearing_rate": 0.0003,
    "stamp_per_1000": 1.0,
    "sst_rate": 0.08,
}


def fee(trade_value: float) -> float:
    if trade_value <= 0:
        return 0.0
    commission = trade_value * COST_MODEL["commission_rate"]
    clearing = trade_value * COST_MODEL["clearing_rate"]
    stamp = math.ceil(trade_value / 1000.0) * COST_MODEL["stamp_per_1000"]
    subtotal = commission + COST_MODEL["platform_fee"] + clearing
    sst = subtotal * COST_MODEL["sst_rate"]
    return float(commission + COST_MODEL["platform_fee"] + clearing + stamp + sst)


def _choose_idx(scores: np.ndarray, eligible: np.ndarray, reverse: bool) -> int | None:
    if not eligible.any():
        return None
    if reverse:
        vals = np.where(eligible & np.isfinite(scores), scores, np.inf)
        j = int(np.argmin(vals))
        return j if np.isfinite(vals[j]) else None
    vals = np.where(eligible & np.isfinite(scores), scores, -np.inf)
    j = int(np.argmax(vals))
    return j if np.isfinite(vals[j]) else None


def backtest(
    name: str,
    variant: dict,
    op: pd.DataFrame,
    hp: pd.DataFrame,
    lp: pd.DataFrame,
    cp: pd.DataFrame,
    vp: pd.DataFrame,
    universe: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    horizon_days: int,
    stop_loss: float,
    starting_cash: float = STARTING_CASH,
    reward_r: float | None = None,
    risk_basis: str = "entry_stop",
    risk_pct: float | None = None,
    lot_size: int = LOT_SIZE,
    slippage_bps: float = SLIPPAGE_BPS,
    max_participation: float = MAX_PARTICIPATION,
    cost_multiplier: float = 1.0,
    regime_series: pd.Series | None = None,
) -> dict | None:
    dates = cp.index
    idx = np.where((dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end)))[0]
    if len(idx) < max(30, int(horizon_days) + 5):
        return None

    cols = list(cp.columns)
    n = len(cols)
    sym_to_idx = {str(s): i for i, s in enumerate(cols)}
    oa, ha, la, ca, va = (
        op.to_numpy(dtype=float),
        hp.to_numpy(dtype=float),
        lp.to_numpy(dtype=float),
        cp.to_numpy(dtype=float),
        vp.to_numpy(dtype=float),
    )
    mask = variant["mask"].reindex(index=dates, columns=cp.columns, fill_value=False).to_numpy(dtype=bool)
    score = variant["score"].reindex(index=dates, columns=cp.columns).to_numpy(dtype=float)
    ua = universe.reindex(index=dates, columns=cp.columns, fill_value=False).to_numpy(dtype=bool)

    avg_volume20 = vp.shift(1).rolling(20, min_periods=20).mean().to_numpy(dtype=float)
    avg_dollar20 = (cp * vp).shift(1).rolling(20, min_periods=20).mean().to_numpy(dtype=float)

    cash = float(starting_cash)
    position_j: int | None = None
    shares = 0
    entry_i: int | None = None
    entry_price: float | None = None
    entry_fee = 0.0
    signal_date: pd.Timestamp | None = None
    pending_entry: tuple[int, pd.Timestamp] | None = None
    pending_exit = False
    trades: list[dict] = []
    equity_rows: list[tuple[pd.Timestamp, float]] = []
    peak = float(starting_cash)
    risk_breaches = 0
    first_idx, last_idx = int(idx[0]), int(idx[-1])
    entry_order_values: list[float] = []
    broker_lot_violations = 0
    enforce_broker_lot = int(lot_size) == BROKER_LOT_SIZE
    slippage = float(slippage_bps) / 10_000.0
    reverse_rank = any(k in str(variant.get("family", "")) for k in ("reversal", "loser"))

    valid_end_by_col: dict[int, int] = {}
    for j in range(n):
        valid = np.flatnonzero(np.isfinite(ca[:, j]))
        if len(valid):
            valid_end_by_col[j] = int(valid[-1])

    def scaled_fee(value: float) -> float:
        return fee(value) * float(cost_multiplier)

    def close_position(exec_i: int, raw_exec_price: float, reason: str) -> None:
        nonlocal cash, position_j, shares, entry_i, entry_price, entry_fee, signal_date
        if position_j is None or shares <= 0 or entry_price is None or entry_i is None:
            return
        exec_price = float(raw_exec_price)
        sell_value = shares * exec_price
        exit_fee = scaled_fee(sell_value)
        cash += sell_value - exit_fee
        sig = signal_date
        trade = {
            "strategy": name,
            "signal_date": str(sig.date()) if sig is not None else None,
            "entry_date": str(dates[entry_i].date()),
            "exit_date": str(dates[exec_i].date()),
            "symbol": cols[position_j],
            "entry_price": float(entry_price),
            "exit_price": exec_price,
            "shares": int(shares),
            "entry_fee": float(entry_fee),
            "exit_fee": float(exit_fee),
            "gross_pnl": float((exec_price - entry_price) * shares),
            "net_pnl": float((exec_price - entry_price) * shares - entry_fee - exit_fee),
            "planned_risk_per_share": float(entry_price * float(stop_loss)),
            "planned_risk_value": float(shares * entry_price * float(stop_loss)),
            "r_multiple_gross": float((exec_price - entry_price) * shares / max(shares * entry_price * float(stop_loss), 1e-12)),
            "exit_reason": reason,
            "signal_before_execution": bool(sig is not None and dates[exec_i] > sig),
        }
        if sig is not None and dates[exec_i] <= sig:
            raise AssertionError("Execution timestamp must be strictly after signal timestamp")
        trades.append(trade)
        position_j = None
        shares = 0
        entry_i = None
        entry_price = None
        entry_fee = 0.0
        signal_date = None

    def open_position(exec_i: int, j: int, sig_date: pd.Timestamp) -> None:
        nonlocal cash, position_j, shares, entry_i, entry_price, entry_fee, signal_date
        px = oa[exec_i, j]
        if not np.isfinite(px) or px <= 0 or not ua[exec_i, j]:
            return
        av = avg_volume20[exec_i, j]
        if not np.isfinite(av) or av <= 0:
            return
        exec_px = px * (1.0 + slippage)
        max_value = min(cash * CAPITAL_PCT, av * float(max_participation) * exec_px)
        if risk_pct is not None and float(risk_pct) > 0:
            risk_budget = cash * float(risk_pct)
            stop_distance = exec_px * float(stop_loss)
            risk_qty = int(risk_budget / stop_distance) if stop_distance > 0 else 0
            max_value = min(max_value, risk_qty * exec_px)
        lot = max(1, int(lot_size))
        qty = int(max_value / exec_px)
        qty = (qty // lot) * lot
        if qty <= 0:
            return
        value = qty * exec_px
        buy_fee = scaled_fee(value)
        if value + buy_fee > cash:
            return
        if enforce_broker_lot and (
            qty < BROKER_LOT_SIZE or qty % BROKER_LOT_SIZE != 0
        ):
            nonlocal broker_lot_violations
            broker_lot_violations += 1
            return
        entry_order_values.append(float(value))
        cash -= value + buy_fee
        position_j = j
        shares = qty
        entry_i = exec_i
        entry_price = exec_px
        entry_fee = buy_fee
        signal_date = sig_date

    for i in idx:
        i = int(i)
        d = dates[i]

        if pending_exit and position_j is not None:
            px = oa[i, position_j]
            if np.isfinite(px) and px > 0:
                close_position(i, px * (1.0 - slippage), "signal_next_open")
            pending_exit = False

        if pending_entry is not None and position_j is None:
            j, sig_date = pending_entry
            open_position(i, j, sig_date)
            pending_entry = None

        if position_j is not None and entry_price is not None:
            opx = oa[i, position_j]
            low = la[i, position_j]
            stop_px = entry_price * (1.0 - float(stop_loss))
            target_px = None
            if reward_r is not None and float(reward_r) > 0:
                risk_per_share = entry_price - stop_px
                target_px = entry_price + float(reward_r) * risk_per_share
            if np.isfinite(opx) and opx > 0 and opx <= stop_px:
                close_position(i, opx * (1.0 - slippage), "stop_gap_open")
            elif reward_r is not None and target_px is not None and np.isfinite(opx) and opx >= target_px:
                close_position(i, opx * (1.0 - slippage), "target_gap_open")
            elif np.isfinite(low) and low <= stop_px:
                close_position(i, stop_px * (1.0 - slippage), "stop_intraday")
            elif reward_r is not None and target_px is not None and np.isfinite(ha[i, position_j]) and ha[i, position_j] >= target_px:
                close_position(i, target_px * (1.0 - slippage), "target_intraday")

        if position_j is not None and valid_end_by_col.get(position_j, i) < i:
            last = valid_end_by_col[position_j]
            if first_idx <= last <= last_idx and np.isfinite(ca[last, position_j]):
                close_position(last, ca[last, position_j] * (1.0 - slippage), "data_end")

        eq = cash
        if position_j is not None and np.isfinite(ca[i, position_j]):
            eq += shares * ca[i, position_j]
        peak = max(peak, float(eq))
        dd = eq / peak - 1.0 if peak > 0 else -1.0
        if dd <= -0.10:
            risk_breaches += 1
        equity_rows.append((d, float(eq)))

        # Signal logic is evaluated after today's close. Nothing from this
        # block can execute until the next trading day.
        if position_j is not None and entry_i is not None:
            if i - entry_i >= int(horizon_days):
                pending_exit = True
                pending_entry = None
        elif position_j is None and i < last_idx:
            eligible = (
                mask[i]
                & ua[i]
                & np.isfinite(ca[i])
                & (ca[i] >= MIN_PRICE)
                & (ca[i] <= MAX_PRICE)
                & np.isfinite(avg_dollar20[i])
                & (avg_dollar20[i] >= MIN_AVG_DOLLAR_VOL)
            )
            j = _choose_idx(score[i], eligible, reverse_rank)
            if j is not None:
                pending_entry = (j, d)

    if position_j is not None and last_idx >= int(entry_i or last_idx):
        px = ca[last_idx, position_j]
        if np.isfinite(px):
            close_position(last_idx, px * (1.0 - slippage), "final_close")

    if not equity_rows:
        return None
    eq = pd.Series(dict(equity_rows)).sort_index()
    broker_feasible_rm1000 = bool(
        enforce_broker_lot
        and len(trades) > 0
        and broker_lot_violations == 0
        and all(
            int(t.get("shares", 0)) >= BROKER_LOT_SIZE
            and int(t.get("shares", 0)) % BROKER_LOT_SIZE == 0
            for t in trades
        )
    )
    min_entry_order_value = float(min(entry_order_values)) if entry_order_values else None
    max_entry_order_value = float(max(entry_order_values)) if entry_order_values else None
    final_equity = float(cash)
    total_return = final_equity / starting_cash - 1.0
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1 / 365.25)
    cagr = (final_equity / starting_cash) ** (1.0 / years) - 1.0 if final_equity > 0 else float("nan")
    drawdown = eq / eq.cummax() - 1.0
    tdf = pd.DataFrame(trades)
    net = tdf["net_pnl"] if not tdf.empty else pd.Series(dtype=float)
    gp = float(net[net > 0].sum()) if not net.empty else 0.0
    gl = float(-net[net < 0].sum()) if not net.empty else 0.0
    pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)
    rvals = pd.to_numeric(tdf["r_multiple_gross"], errors="coerce") if not tdf.empty else pd.Series(dtype=float)
    winners_r = rvals[rvals > 0]
    losers_r = rvals[rvals < 0]
    avg_win_r = float(winners_r.mean()) if not winners_r.empty else 0.0
    avg_loss_r = float(-losers_r.mean()) if not losers_r.empty else 0.0
    realized_rr = float(avg_win_r / avg_loss_r) if avg_loss_r > 0 else (float("inf") if avg_win_r > 0 else 0.0)
    expectancy_r = float(rvals.mean()) if not rvals.empty else 0.0
    months = max((eq.index[-1] - eq.index[0]).days / 30.4375, 1 / 30.4375)
    geom_monthly = (final_equity / starting_cash) ** (1.0 / months) - 1.0 if final_equity > 0 else -1.0
    monthly = eq.resample("ME").last().pct_change(fill_method=None).dropna()
    first_close = eq.resample("ME").first()
    if not first_close.empty and monthly.empty is False:
        pass
    violations = [t for t in trades if not t.get("signal_before_execution", False) and t.get("signal_date")]
    if violations:
        raise AssertionError(f"Look-ahead execution violation(s): {len(violations)}")

    regime_stats = {}
    if regime_series is not None and not monthly.empty:
        labels = regime_series.reindex(monthly.index, method="ffill").fillna("sideways")
        for label in ("bull", "sideways", "bear"):
            vals = monthly[labels.eq(label)]
            if len(vals):
                regime_stats[label] = {
                    "months": int(len(vals)),
                    "mean_monthly_return": float(vals.mean()),
                    "median_monthly_return": float(vals.median()),
                    "positive_month_fraction": float((vals > 0).mean()),
                }

    return {
        "strategy": name,
        "start": eq.index[0].date().isoformat(),
        "end": eq.index[-1].date().isoformat(),
        "final_equity": final_equity,
        "total_return": float(total_return),
        "cagr": float(cagr) if np.isfinite(cagr) else float("nan"),
        "geometric_monthly_return": float(geom_monthly),
        "max_drawdown": float(drawdown.min()),
        "trade_count": int(len(trades)),
        "trades_per_month": float(len(trades) / max(months, 1.0)),
        "win_rate": float((net > 0).mean()) if not net.empty else 0.0,
        "profit_factor": float(pf),
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "realized_rr": realized_rr,
        "expectancy_r": expectancy_r,
        "risk_breach_count": int(risk_breaches),
        "broker_name": BROKER_NAME,
        "broker_lot_size": BROKER_LOT_SIZE,
        "broker_feasible_rm1000": broker_feasible_rm1000,
        "broker_lot_violations": int(broker_lot_violations),
        "min_entry_order_value": min_entry_order_value,
        "max_entry_order_value": max_entry_order_value,
        "median_monthly_return": float(monthly.median()) if not monthly.empty else float("nan"),
        "positive_month_fraction": float((monthly > 0).mean()) if not monthly.empty else 0.0,
        "sustained_20pct_monthly_flag": bool(geom_monthly >= 0.20 and months >= 36),
        "regime_stats": regime_stats,
        "trades": trades,
        "execution_model": {
            "signal": "close_t",
            "entry_execution": "open_t_plus_1",
            "exit_execution": "open_t_plus_1",
            "stop_model": "gap_open_or_intraday_stop",
            "reward_r": None if reward_r is None else float(reward_r),
            "risk_basis": risk_basis,
            "risk_pct": None if risk_pct is None else float(risk_pct),
            "rr_enabled": bool(reward_r is not None and float(reward_r) > 0),
            "lot_size": int(lot_size),
            "slippage_bps_per_side": float(slippage_bps),
            "max_participation": float(max_participation),
            "cost_multiplier": float(cost_multiplier),
        },
    }
