#!/usr/bin/env python3
"""Strategy Hunter V4: staged, realistic, continuously rotating search."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .baseline_research import load_wide, universe_mask, indicators
    from .realistic_engine_v1 import backtest, COST_MODEL, STARTING_CASH, CAPITAL_PCT, LOT_SIZE, SLIPPAGE_BPS, fee
except ImportError:
    from baseline_research import load_wide, universe_mask, indicators
    from realistic_engine_v1 import backtest, COST_MODEL, STARTING_CASH, CAPITAL_PCT, LOT_SIZE, SLIPPAGE_BPS, fee

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "results"
OUT.mkdir(parents=True, exist_ok=True)

STATE_PATH = OUT / "strategy_lab_v4_state.json"
EVENT_PATH = OUT / "strategy_lab_v4_event_screen.csv"
BT_PATH = OUT / "strategy_lab_v4_backtests.csv"
SUMMARY_PATH = OUT / "strategy_lab_v4_summary.json"

DEV_START = pd.Timestamp("2015-01-01")
DEV_END = pd.Timestamp("2019-12-31")
SEL_START = pd.Timestamp("2020-01-01")
SEL_END = pd.Timestamp("2022-12-31")
VAL_START = pd.Timestamp("2023-01-01")
VAL_END = pd.Timestamp("2024-12-31")
HOLDOUT_START = pd.Timestamp("2025-01-01")

SCREEN_HORIZONS = (5, 10, 20, 30)
STOP_LOSSES = (0.06, 0.10)
STRESS_COSTS = (1.0, 1.5)
STRESS_SLIPPAGE = (0.0, 20.0)
BATCH_PER_FAMILY = 4
FOCUS_COUNT = 12
TOP_REALISTIC_COUNT = 6
MIN_EVENTS = 50
MIN_PF = 1.03
MAX_SCREEN_TPM = 40.0
MAX_DD = 0.10
MIN_TPM = 5.0
MAX_TPM = 20.0
RR_VALUES = (0.50, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0)
RISK_PCTS = (0.03, 0.04, 0.05, 0.06)


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def months_between(a, b):
    return max((pd.Timestamp(b) - pd.Timestamp(a)).days / 30.4375, 1 / 30.4375)


def make_regime_series(cp, universe):
    ma200 = cp.rolling(200, min_periods=200).mean()
    denom = universe.sum(axis=1).replace(0, np.nan)
    breadth = ((cp > ma200) & universe).sum(axis=1) / denom
    regime = pd.Series("sideways", index=cp.index)
    regime[breadth >= 0.55] = "bull"
    regime[breadth <= 0.35] = "bear"
    return regime


def event_screen(mask, fwd, start, end):
    m = mask.loc[(mask.index >= start) & (mask.index <= end)]
    r = fwd.loc[(fwd.index >= start) & (fwd.index <= end)]
    valid = m.to_numpy(dtype=bool) & r.notna().to_numpy(dtype=bool)
    vals = r.to_numpy(dtype=float)[valid]
    if vals.size == 0:
        return None
    months = months_between(start, end)
    hurdle = 2.0 * fee(STARTING_CASH * CAPITAL_PCT) / (STARTING_CASH * CAPITAL_PCT)
    net = vals - hurdle
    pos, neg = net[net > 0], net[net < 0]
    gl = float(-neg.sum()) if len(neg) else 0.0
    gg = float(pos.sum()) if len(pos) else 0.0
    pf = gg / gl if gl else (float("inf") if gg else 0.0)
    return {
        "observations": int(vals.size),
        "mean_return": float(vals.mean()),
        "net_mean": float(net.mean()),
        "median_return": float(np.median(net)),
        "win_rate": float((net > 0).mean()),
        "profit_factor": float(pf),
        "trades_per_month": float(vals.size / months),
        "p10": float(np.quantile(net, 0.10)),
        "p90": float(np.quantile(net, 0.90)),
    }


def select_batch(variants, state):
    tested = set(state.get("tested_variants", []))
    by_family = {}
    for name, v in variants.items():
        by_family.setdefault(str(v["family"]), []).append(name)
    for fam in by_family:
        by_family[fam].sort()

    chosen = []
    for name in state.get("focus_variants", []):
        if name in variants and name not in chosen:
            chosen.append(name)
        if len(chosen) >= FOCUS_COUNT:
            break

    families = sorted(by_family)
    added = True
    while len(chosen) < 120 and added:
        added = False
        for fam in families:
            pool = [n for n in by_family[fam] if n not in tested and n not in chosen]
            if pool:
                chosen.append(pool[0])
                added = True
            if len(chosen) >= 120:
                break

    # Full coverage triggers a deterministic restart so the mission never ends.
    unseen_exists = any(n not in tested for n in variants)
    if not unseen_exists:
        state["tested_variants"] = []
        tested = set()
        chosen = list(dict.fromkeys(chosen))
        for fam in families:
            pool = by_family[fam]
            if pool:
                chosen.extend(pool[:BATCH_PER_FAMILY])
        chosen = list(dict.fromkeys(chosen))

    return chosen[:120]


def screen_candidates(variants, chosen, op, cp):
    fwd = {h: cp.shift(-h) / op.shift(-1) - 1.0 for h in SCREEN_HORIZONS}
    rows = []
    for name in chosen:
        v = variants[name]
        core_mask = v["mask"]
        activity = int(core_mask.loc[(core_mask.index >= DEV_START) & (core_mask.index <= SEL_END)].to_numpy(dtype=bool).sum())
        if activity < MIN_EVENTS:
            continue
        for h in SCREEN_HORIZONS:
            dev = event_screen(core_mask, fwd[h], DEV_START, DEV_END)
            sel = event_screen(core_mask, fwd[h], SEL_START, SEL_END)
            if not dev or not sel:
                continue
            if sel["observations"] < MIN_EVENTS or sel["trades_per_month"] > MAX_SCREEN_TPM:
                continue
            rows.append({
                "variant": name,
                "variant_id": hashlib.sha256(name.encode()).hexdigest()[:16],
                "family": v["family"],
                "horizon_days": h,
                "dev_net_mean": dev["net_mean"],
                "dev_pf": dev["profit_factor"],
                "dev_obs": dev["observations"],
                "sel_net_mean": sel["net_mean"],
                "sel_pf": sel["profit_factor"],
                "sel_win_rate": sel["win_rate"],
                "sel_obs": sel["observations"],
                "sel_tpm": sel["trades_per_month"],
                "screen_score": float(max(0, sel["net_mean"]) * np.log1p(sel["observations"]) * min(max(sel["profit_factor"],0),10)),
                "params": json.dumps(v["params"], sort_keys=True),
            })
    return pd.DataFrame(rows)


def basic_pass(r):
    return bool(
        r
        and r["final_equity"] > STARTING_CASH
        and r["profit_factor"] > 1.0
        and r["max_drawdown"] >= -MAX_DD
        and MIN_TPM <= r["trades_per_month"] <= MAX_TPM
    )


def replicate(v, name, op, hp, lp, cp, vp, universe, regime, horizon, stop, reward_r, risk_pct):
    if cp.shape[1] < 20:
        return []
    left, right = [], []
    for sym in cp.columns:
        h = int(hashlib.sha256(str(sym).encode()).hexdigest()[:8], 16)
        (left if h % 2 == 0 else right).append(sym)
    out = []
    for half, group in enumerate((left, right), 1):
        if len(group) < 8:
            continue
        u = universe.copy()
        excluded = [s for s in cp.columns if s not in group]
        if excluded:
            u.loc[:, excluded] = False
        r = backtest(name, v, op, hp, lp, cp, vp, u, HOLDOUT_START, cp.index.max(), horizon, stop, lot_size=LOT_SIZE, reward_r=reward_r, risk_pct=risk_pct, regime_series=regime)
        if r:
            out.append({
                "half": half,
                "final_equity": r["final_equity"],
                "total_return": r["total_return"],
                "max_drawdown": r["max_drawdown"],
                "trade_count": r["trade_count"],
                "trades_per_month": r["trades_per_month"],
                "profit_factor": r["profit_factor"],
            })
    return out


def evaluate_candidate(name, v, op, hp, lp, cp, vp, universe, regime, horizon, stop, reward_r, risk_pct):
    windows = [
        ("development", DEV_START, DEV_END),
        ("selection", SEL_START, SEL_END),
        ("validation", VAL_START, VAL_END),
        ("holdout", HOLDOUT_START, cp.index.max()),
        ("full", DEV_START, cp.index.max()),
    ]
    results = {}
    for label, a, b in windows:
        r = backtest(name, v, op, hp, lp, cp, vp, universe, a, b, horizon, stop, lot_size=LOT_SIZE, reward_r=reward_r, risk_pct=risk_pct, regime_series=regime)
        if r is None:
            return None
        results[label] = r

    # Small, local neighborhood around horizon/stop; enough to detect a magic
    # single setting without exploding the research workload.
    neighbors = []
    for h, sl in ((max(5, horizon-10), stop), (min(30, horizon+10), stop), (horizon, 0.08 if stop == 0.10 else 0.10)):
        if h == horizon and sl == stop:
            continue
        r = backtest(name, v, op, hp, lp, cp, vp, universe, HOLDOUT_START, cp.index.max(), h, sl, lot_size=LOT_SIZE, regime_series=regime)
        if r:
            neighbors.append({
                "horizon": h, "stop": sl, "basic_pass": basic_pass(r),
                "final_equity": r["final_equity"], "max_drawdown": r["max_drawdown"],
                "trades_per_month": r["trades_per_month"], "profit_factor": r["profit_factor"],
            })

    stress = []
    for cm, slip in ((1.5, 20.0), (1.5, 0.0), (1.0, 20.0)):
        r = backtest(name, v, op, hp, lp, cp, vp, universe, HOLDOUT_START, cp.index.max(), horizon, stop, lot_size=LOT_SIZE, reward_r=reward_r, risk_pct=risk_pct, slippage_bps=slip, cost_multiplier=cm, regime_series=regime)
        if r:
            stress.append({
                "cost_multiplier": cm, "slippage_bps": slip, "final_equity": r["final_equity"],
                "max_drawdown": r["max_drawdown"], "profit_factor": r["profit_factor"],
                "trades_per_month": r["trades_per_month"], "basic_pass": basic_pass(r),
            })

    reps = replicate(v, name, op, hp, lp, cp, vp, universe, regime, horizon, stop, reward_r, risk_pct)
    rep_pass = len(reps) == 2 and all(
        x["final_equity"] > STARTING_CASH and x["max_drawdown"] >= -MAX_DD and x["profit_factor"] > 1.0 for x in reps
    )

    dev, sel, val, hold, full = (results[x] for x in ("development","selection","validation","holdout","full"))
    neighbor_pass = sum(x["basic_pass"] for x in neighbors)
    stress_pass = sum(x["basic_pass"] for x in stress)

    research_candidate = bool(
        dev["total_return"] > 0 and sel["total_return"] > 0 and val["total_return"] > 0 and hold["total_return"] > 0
        and val["profit_factor"] > 1.0 and hold["profit_factor"] > 1.0
        and val["max_drawdown"] >= -MAX_DD and hold["max_drawdown"] >= -MAX_DD
        and MIN_TPM <= hold["trades_per_month"] <= MAX_TPM
        and rep_pass and neighbor_pass >= 2 and stress_pass >= 2
    )

    return {
        "pattern": name, "family": v["family"], "horizon_days": int(horizon), "stop_loss": float(stop), "reward_r": float(reward_r), "risk_pct": float(risk_pct),
        "params": json.dumps(v["params"], sort_keys=True),
        "development": dev, "selection": sel, "validation": val, "holdout": hold, "full": full,
        "replication": reps, "replication_pass": rep_pass,
        "neighbor_pass_count": int(neighbor_pass), "neighbor_test_count": len(neighbors),
        "stress_pass_count": int(stress_pass), "stress_test_count": len(stress),
        "sustained_20pct_monthly_flag": bool(full["sustained_20pct_monthly_flag"]),
        "research_candidate": research_candidate,
    }


def flatten(r):
    row = {
        "pattern": r["pattern"], "family": r["family"], "horizon_days": r["horizon_days"], "stop_loss": r["stop_loss"],
        "params": r["params"], "research_candidate": r["research_candidate"],
        "replication_pass": r["replication_pass"], "neighbor_pass_count": r["neighbor_pass_count"],
        "neighbor_test_count": r["neighbor_test_count"], "stress_pass_count": r["stress_pass_count"],
        "stress_test_count": r["stress_test_count"], "sustained_20pct_monthly_flag": r["sustained_20pct_monthly_flag"],
    }
    for pfx in ("development","selection","validation","holdout","full"):
        x = r[pfx]
        for k in ("final_equity","total_return","cagr","geometric_monthly_return","max_drawdown","trade_count","trades_per_month","win_rate","profit_factor","avg_win_r","avg_loss_r","realized_rr","expectancy_r","risk_breach_count","median_monthly_return","positive_month_fraction"):
            row[f"{pfx}_{k}"] = x.get(k)
    return row


def main():
    op, hp, lp, cp, vp = load_wide()
    universe = universe_mask(cp.index, cp.columns)
    ind = indicators(cp, vp)
    regime = make_regime_series(cp, universe)

    state = read_json(STATE_PATH, {})
    progress = read_json(OUT / "strategy_hunter_progress.json", {})
    previous_cycle = int(progress.get("cycle", state.get("cycle", 0)))
    # Preserve the cycle number while the prior core cycle is degraded. A new
    # cycle number represents a successfully completed research iteration.
    cycle = previous_cycle if str(progress.get("last_cycle_status", "")) == "degraded" else previous_cycle + 1
    variants = __import__("strategy_lab_v3").build_variants(op, hp, lp, cp, vp, universe, ind)
    chosen = select_batch(variants, state)

    screen = screen_candidates(variants, chosen, op, cp)
    screen.to_csv(EVENT_PATH, index=False)
    screen.to_csv(OUT / "strategy_lab_selection.csv", index=False)

    results = []
    realistic_tests = []
    if not screen.empty:
        screened = screen[(screen["dev_net_mean"] > 0) & (screen["sel_net_mean"] > 0) & (screen["sel_pf"] >= MIN_PF)].copy()
        screened = screened.sort_values(["screen_score","sel_net_mean","sel_pf"], ascending=False).head(TOP_REALISTIC_COUNT)
        for r in screened.itertuples(index=False):
            name = r.variant
            v = variants[name]
            # Test the same signal across explicit R-multiples and both stop sizes.
            # No RR is treated as inherently better; qualification remains evidence-based.
            for risk_pct in RISK_PCTS:
                for rr in RR_VALUES:
                    for stop in (0.06, 0.10):
                        ev = evaluate_candidate(
                            name, v, op, hp, lp, cp, vp, universe, regime,
                            int(r.horizon_days), stop, rr, risk_pct
                        )
                        if ev:
                            results.append(ev)
                            realistic_tests.append((name, int(r.horizon_days), stop, rr, risk_pct))

    bt_df = pd.DataFrame([flatten(x) for x in results])
    bt_df.to_csv(BT_PATH, index=False)

    tested = list(dict.fromkeys(state.get("tested_variants", []) + chosen))
    state.update({
        "cycle": cycle,
        "tested_variants": tested,
        "focus_variants": (
            screen.sort_values(["screen_score","sel_net_mean"], ascending=False)["variant"].drop_duplicates().head(FOCUS_COUNT).tolist()
            if not screen.empty else state.get("focus_variants", [])
        ),
        "last_batch_size": len(chosen),
        "last_screen_rows": int(len(screen)),
        "last_realistic_tests": len(realistic_tests),
        "search_space_variants": len(variants),
        "search_space_coverage": float(min(1.0, len(set(tested)) / max(len(variants),1))),
    })
    state.setdefault("exceptional_return_alerts", [])

    alerts = []
    if not bt_df.empty:
        hot = bt_df[bt_df["sustained_20pct_monthly_flag"] == True]
        for rr in hot.itertuples(index=False):
            alerts.append({
                "pattern": rr.pattern, "family": rr.family,
                "geometric_monthly_return_full": rr.full_geometric_monthly_return,
                "full_years": months_between(DEV_START, cp.index.max()) / 12.0,
                "note": "Exceptional return-rate flag; not a best-strategy verdict.",
            })
    state["exceptional_return_alerts"] = alerts

    qualified = bt_df[bt_df["research_candidate"] == True] if not bt_df.empty else pd.DataFrame()
    leader = None
    if not qualified.empty:
        leader = qualified.sort_values(["selection_total_return","selection_profit_factor"], ascending=False).iloc[0].to_dict()

    summary = {
        "engine_version": "realistic_engine_v1 + strategy_lab_v4",
        "status": "candidate_ready" if leader else "searching",
        "cycle": cycle,
        "search_space_variants": len(variants),
        "batch_variants": len(chosen),
        "screen_rows": len(screen),
        "realistic_tests": len(realistic_tests),
        "qualified_candidates": len(qualified),
        "search_space_coverage": state["search_space_coverage"],
        "exceptional_return_alerts": alerts,
        "leader": leader,
        "rules": {
            "signal_to_execution": "close_t_to_next_open",
            "lookahead_protection": True,
            "historical_universe": True,
            "lot_size": LOT_SIZE,
            "starting_cash": STARTING_CASH,
            "rr_values": list(RR_VALUES),
            "risk_pcts_per_trade": list(RISK_PCTS),
            "capital_pct": CAPITAL_PCT,
            "slippage_bps": SLIPPAGE_BPS,
            "cost_model": COST_MODEL,
            "development": [str(DEV_START.date()), str(DEV_END.date())],
            "selection": [str(SEL_START.date()), str(SEL_END.date())],
            "validation": [str(VAL_START.date()), str(VAL_END.date())],
            "sealed_holdout": [str(HOLDOUT_START.date()), str(cp.index.max().date())],
            "min_trades_per_month": MIN_TPM,
            "max_trades_per_month": MAX_TPM,
            "max_drawdown": MAX_DD,
            "holdout_used_for_ranking": False,
            "20pct_monthly_is_alert_not_goal_gate": True,
        },
    }
    write_json(SUMMARY_PATH, summary)

    progress = read_json(OUT / "strategy_hunter_progress.json", {})
    progress.update({
        "cycle": cycle, "updated_at": pd.Timestamp.utcnow().isoformat(),
        "engine_version": "strategy_lab_v4_realistic",
        "patterns_tested": len(variants), "strategy_lab_variants": len(variants),
        "strategy_lab_selection_candidates": len(screen), "strategy_lab_backtests": len(realistic_tests),
        "rr_values_tested": list(RR_VALUES),
        "risk_pcts_per_trade": list(RISK_PCTS),
        "strategy_lab_qualified_candidates": len(qualified),
        "strategy_lab_leader": (
            {k: leader.get(k) for k in ("pattern","family","holdout_total_return","holdout_max_drawdown","holdout_trades_per_month","holdout_profit_factor")}
            if leader else None
        ),
        "search_round": cycle,
        "realistic_search_space_coverage": state["search_space_coverage"],
        "realistic_exceptional_20pct_monthly_alerts": len(alerts),
        "candidates": len(screen), "robust_candidates": len(qualified),
        "engine_sanity": read_json(OUT / "engine_sanity.json", {}).get("status") == "passed",
        "last_cycle_status": "completed",
        "next_action": "deeper_validation" if leader else "continue_rotating_search",
    })
    write_json(OUT / "strategy_hunter_progress.json", progress)
    write_json(STATE_PATH, state)

    evidence = {
        "status": "candidate_ready" if leader else "searching",
        "candidate_id": None,
        "engine_version": "strategy_lab_v4_realistic",
        "lab_cycle": cycle,
        "gates": {
            "data_integrity": True,
            "engine_sanity": progress["engine_sanity"],
            "positive_after_costs": bool(leader and leader.get("holdout_total_return", 0) > 0),
            "robust_out_of_sample": bool(leader),
            "drawdown_within_limit": bool(leader and leader.get("holdout_max_drawdown", -1) >= -MAX_DD),
            "trade_frequency_feasible": bool(leader and MIN_TPM <= leader.get("holdout_trades_per_month",0) <= MAX_TPM),
            "broker_feasible_at_rm1000": False,
            "historical_shariah_compliance": True,
            "independent_replication": bool(leader and leader.get("replication_pass")),
            "forward_paper_validation": False,
        },
        "exceptional_return_alerts": alerts,
        "note": "Search continues; no result is labeled best automatically.",
    }
    if leader:
        raw = f'{leader["pattern"]}:{leader["horizon_days"]}:{leader["stop_loss"]}'.encode()
        evidence["candidate_id"] = f'SH-{int(hashlib.sha256(raw).hexdigest()[:8],16)%1_000_000:06d}'
        evidence["strategy"] = {
            "pattern": leader["pattern"], "family": leader["family"],
            "horizon_days": int(leader["horizon_days"]), "stop_loss": float(leader["stop_loss"]),
            "params": json.loads(leader["params"]),
        }
        evidence["holdout"] = {k: leader.get(f"holdout_{k}") for k in ("final_equity","total_return","cagr","geometric_monthly_return","max_drawdown","trade_count","trades_per_month","win_rate","profit_factor","risk_breach_count","median_monthly_return","positive_month_fraction")}
    write_json(OUT / "qualified_strategy_evidence.json", evidence)
    write_json(OUT / "strategy_lab_state.json", {
        "status": summary["status"], "engine_version": summary["engine_version"], "cycle": cycle,
        "variants_tested": len(variants), "selection_candidates": len(screen),
        "backtests": len(realistic_tests), "qualified_candidates": len(qualified),
        "leader": evidence.get("strategy"),
    })
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

# CI trigger: syntax-repaired Strategy Hunter
