#!/usr/bin/env python3
"""Failure-analysis research loop for Strategy Hunter.

Turns failed/near-miss V4 tests into evidence:
failure signature -> common conditions -> research hypothesis -> next-cycle
improvement family. This never relaxes qualification gates.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "results"
BT_PATH = OUT / "strategy_lab_v4_backtests.csv"
HYP_PATH = OUT / "failure_research_hypotheses.json"
SIG_PATH = OUT / "failure_signatures.csv"
REPORT_PATH = OUT / "failure_analysis.json"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _number(r, key):
    """Read finite numeric evidence; missing/NaN values fail closed."""
    import math
    try:
        value = float(r.get(key))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def classify(r):
    """Classify failure from selection data only; the holdout is sealed."""
    tpm = _number(r, "selection_trades_per_month")
    dd = _number(r, "selection_max_drawdown")
    pf = _number(r, "selection_profit_factor")
    ret = _number(r, "selection_total_return")
    if any(v is None for v in (tpm, dd, pf, ret)):
        return "insufficient_selection_evidence"
    if tpm < 5:
        return "too_few_trades"
    if tpm > 20:
        return "too_many_trades"
    if dd < -0.10:
        return "drawdown_failure"
    if ret <= 0 and pf <= 1:
        return "negative_expectancy"
    if pf <= 1:
        return "profit_factor_failure"
    if ret <= 0:
        return "selection_failure"
    return "robustness_failure"


def main():
    if not BT_PATH.exists():
        report = {"status": "no_backtests", "cycle": None, "hypotheses": []}
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        HYP_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return

    df = pd.read_csv(BT_PATH)
    if df.empty:
        report = {"status": "no_backtests", "cycle": None, "hypotheses": []}
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        HYP_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return

    df["failure_signature"] = df.apply(classify, axis=1)
    failed = df[df.failure_signature != "qualified"].copy()

    # Prefer near-misses for diagnosis, while retaining aggregate evidence
    # from every failed test.
    # Missing selection metrics are unknown, not zero performance. Do not
    # substitute holdout metrics to fill gaps.
    for col in ("selection_total_return", "selection_profit_factor",
                "selection_max_drawdown", "selection_trades_per_month"):
        if col not in failed:
            failed[col] = np.nan
    # Rank near-misses exclusively on development/selection evidence.
    # Holdout results must not influence which hypotheses are tested next.
    failed["near_miss_score"] = (
        failed["selection_total_return"].clip(lower=-1, upper=1)
        + 0.25 * failed["selection_profit_factor"].clip(lower=0, upper=3)
    )

    sig_rows = []
    for sig, g in failed.groupby("failure_signature"):
        sig_rows.append({
            "failure_signature": sig,
            "count": int(len(g)),
            "families": int(g["family"].nunique()) if "family" in g else 0,
            "mean_selection_return": float(g["selection_total_return"].mean()),
            "median_selection_return": float(g["selection_total_return"].median()),
            "mean_selection_pf": float(g["selection_profit_factor"].replace([np.inf, -np.inf], np.nan).mean()),
            "mean_selection_dd": float(g["selection_max_drawdown"].mean()),
            "mean_selection_tpm": float(g["selection_trades_per_month"].mean()),
        })
    sig_df = pd.DataFrame(sig_rows).sort_values("count", ascending=False)
    sig_df.to_csv(SIG_PATH, index=False)

    hypotheses = []
    templates = {
        "too_few_trades": {
            "question": "Does the signal contain a real edge but trigger too rarely for the RM1,000 operating target?",
            "improvement": ["broaden entry confirmation", "test adjacent horizons", "test ranking/relative-strength selection", "combine with a second independent trigger"],
        },
        "too_many_trades": {
            "question": "Does reducing low-quality signals improve expectancy without collapsing opportunity frequency?",
            "improvement": ["add trend/regime filter", "add volatility/volume confirmation", "rank signals instead of taking every signal"],
        },
        "drawdown_failure": {
            "question": "Is the edge regime-dependent or is the entry/exit risk structure causing clustered losses?",
            "improvement": ["regime filter", "volatility-state filter", "ATR/structure-aware stop", "different reward-risk profile", "drawdown-aware exposure rule"],
        },
        "negative_expectancy": {
            "question": "Which market conditions separate profitable from losing occurrences of this family?",
            "improvement": ["condition on trend strength", "condition on volatility contraction/expansion", "relative-strength confirmation", "entry timing improvement"],
        },
        "profit_factor_failure": {
            "question": "Are losses too frequent/large, or are winners being exited too early?",
            "improvement": ["exit/reward-risk sweep", "trend persistence filter", "winner-hold extension", "loss containment"],
        },
        "replication_failure": {
            "question": "Is the apparent edge concentrated in a small set of symbols?",
            "improvement": ["cross-sectional diversification", "sector/regime robustness", "symbol-independent parameters"],
        },
        "holdout_failure": {
            "question": "Did the development/selection edge survive a genuinely unseen market period?",
            "improvement": ["regime-aware formulation", "less parameter-specific entry", "walk-forward revalidation"],
        },
        "frequency_failure": {
            "question": "Can the strategy meet the required opportunity rate without sacrificing quality?",
            "improvement": ["multi-timeframe confirmation", "signal ranking", "adjacent entry conditions"],
        },
        "robustness_failure": {
            "question": "Which gate is fragile around the chosen parameter setting?",
            "improvement": ["parameter neighborhood sweep", "cost/slippage stress", "walk-forward validation"],
        },
    }

    # Detect family/signature combinations that fail repeatedly. These are more
    # actionable than individual bad parameter sets.
    for (sig, fam), g in failed.groupby(["failure_signature", "family"]):
        if len(g) < 2:
            continue
        base = templates.get(sig, templates["robustness_failure"])
        rid = hashlib.sha256(f"{sig}:{fam}".encode()).hexdigest()[:12]
        hypotheses.append({
            "hypothesis_id": f"FH-{rid}",
            "failure_signature": sig,
            "family": fam,
            "evidence_tests": int(len(g)),
            "evidence_rate": float(len(g) / max(len(failed), 1)),
            "question": base["question"],
            "proposed_improvements": base["improvement"],
            "priority": "high" if len(g) >= 5 else "medium",
            "status": "queued_for_next_cycle",
        })

    # Also preserve the strongest near-misses as individual research leads.
    top = failed.sort_values("near_miss_score", ascending=False).head(20)
    for _, r in top.iterrows():
        sig = str(r["failure_signature"])
        base = templates.get(sig, templates["robustness_failure"])
        rid = hashlib.sha256(f"near:{r.get('pattern')}:{r.get('horizon_days')}:{r.get('stop_loss')}:{r.get('reward_r')}:{r.get('risk_pct')}".encode()).hexdigest()[:12]
        hypotheses.append({
            "hypothesis_id": f"NM-{rid}",
            "failure_signature": sig,
            "family": str(r.get("family")),
            "pattern": str(r.get("pattern")),
            "horizon_days": int(r.get("horizon_days", 0)),
            "stop_loss": float(r.get("stop_loss", 0)),
            "reward_r": None if pd.isna(r.get("reward_r")) else float(r.get("reward_r")),
            "risk_pct": None if pd.isna(r.get("risk_pct")) else float(r.get("risk_pct")),
            "question": base["question"],
            "proposed_improvements": base["improvement"],
            "selection_return": float(r.get("selection_total_return", 0)),
            "selection_pf": float(r.get("selection_profit_factor", 0)),
            "selection_dd": float(r.get("selection_max_drawdown", 0)),
            "selection_tpm": float(r.get("selection_trades_per_month", 0)),
            "holdout_access": "sealed_not_used_for_hypothesis_selection",
            "status": "queued_for_next_cycle",
        })

    # Deduplicate and cap the queue so the next cycle explores hypotheses,
    # rather than exploding into thousands of tweaks.
    unique = {}
    for h in hypotheses:
        unique[h["hypothesis_id"]] = h
    hypotheses = list(unique.values())[:100]

    cycle = int(load(OUT / "strategy_hunter_progress.json", {}).get("cycle", 0))
    report = {
        "status": "analyzed",
        "cycle": cycle,
        "tests_analyzed": int(len(df)),
        "failed_tests": int(len(failed)),
        "failure_signatures": sig_rows,
        "hypotheses": hypotheses,
        "next_cycle_policy": "test failure hypotheses based only on development/selection data; never use sealed holdout metrics for search",
        "holdout_policy": "sealed; not used to classify failures, rank near-misses, or generate next-cycle hypotheses",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    HYP_PATH.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "analyzed",
        "cycle": cycle,
        "tests_analyzed": len(df),
        "failed_tests": len(failed),
        "signature_count": len(sig_rows),
        "hypotheses_queued": len(hypotheses),
    }, indent=2))


if __name__ == "__main__":
    main()
