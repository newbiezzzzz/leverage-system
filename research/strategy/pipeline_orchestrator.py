#!/usr/bin/env python3
"""Strategy Hunter V2: mission-oriented, recoverable research cycle.

Design rule: a failed experiment is not a failed mission. Optional specialists
are advisory. The external supervisor owns continuation across workflow runs.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "results"
OUT.mkdir(parents=True, exist_ok=True)
LOGS = OUT / "pipeline_logs"
LOGS.mkdir(exist_ok=True)
STATUS = OUT / "strategy_hunter_pipeline.json"
CYCLE = OUT / "research_cycle_state.json"
REPAIR = OUT / "repair_queue.json"
PROGRESS = OUT / "strategy_hunter_progress.json"

MAX_ATTEMPTS = 3
STAGES = [
    ("baseline", "Baseline backtest", "core"),
    ("pattern_hunter", "Pattern Hunter", "core"),
    # Strategy Lab V4 is now the primary strategy-search and selection engine.
    # The former adaptive/candidate path remains in the repository for reference
    # but is no longer allowed to consume the main research cycle.
    ("strategy_lab", "Strategy Lab V4 (realistic execution)", "core"),
    ("failure_analysis", "Failure Analysis + Hypothesis Research", "core"),
    ("vectorbt", "VectorBT", "optional"),
    ("lightgbm", "LightGBM", "optional"),
    ("symbolic", "Symbolic Regression", "optional"),
    ("qlib", "Qlib", "optional"),
    ("optuna", "Optuna", "optional"),
    ("lean", "LEAN", "optional"),
    ("chronos2", "Chronos-2", "optional"),
]

KNOWN_FIXES = (
    ("truth value of a series is ambiguous", "baseline breadth alignment"),
    ("unsupported metric: mae", "gplearn metric name"),
    ("cost_hurdle", "cost hurdle import"),
)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def cycle_number() -> int:
    p = read_json(PROGRESS, {})
    previous = int(p.get("cycle", 0))
    # A degraded core cycle is still the same research cycle. Do not advance
    # the cycle number until the intended core testing work actually completes.
    if str(p.get("last_cycle_status", "")) == "degraded":
        return previous
    return previous + 1


def write_status(status: str, stage: str | None, attempt: int, details: dict, error: str | None = None) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "stage": stage,
        "attempt": attempt,
        "error": error,
        "stages": details,
    }
    write_json(STATUS, payload)


def patch_known_failure(log: str) -> bool:
    text = log.lower()
    changed = False
    baseline = ROOT / "research/strategy/baseline_research.py"
    pattern = ROOT / "research/strategy/pattern_discovery.py"
    specialist = ROOT / "research/strategy/specialist_runner.py"

    if "truth value of a series is ambiguous" in text and baseline.exists():
        body = baseline.read_text(encoding="utf-8")
        old = 'breadth = (px > ind["ma200"]).where(eligible).mean()'
        new = 'breadth = (px > ind["ma200"].loc[date]).where(eligible).mean()'
        if old in body:
            baseline.write_text(body.replace(old, new), encoding="utf-8")
            changed = True

    if "unsupported metric: mae" in text and specialist.exists():
        body = specialist.read_text(encoding="utf-8")
        old = 'metric="mae"'
        if old in body:
            specialist.write_text(body.replace(old, 'metric="mean absolute error"'), encoding="utf-8")
            changed = True

    if "cost_hurdle" in text and "not defined" in text and baseline.exists():
        body = baseline.read_text(encoding="utf-8")
        if "COST_HURDLE =" not in body and "def fee(" in body:
            needle = '    return commission + COST_MODEL["platform_fee"] + clearing + stamp + sst\n\n\n'
            addition = '# Transaction-cost hurdle used by event-study screening.\nCOST_HURDLE = 2.0 * fee(STARTING_CASH * CAPITAL_PCT) / (STARTING_CASH * CAPITAL_PCT)\n\n\n'
            if needle in body:
                baseline.write_text(body.replace(needle, needle + addition), encoding="utf-8")
                changed = True
        if pattern.exists():
            body = pattern.read_text(encoding="utf-8")
            if "COST_HURDLE" not in body:
                old = 'from baseline_research import load_wide, universe_mask, indicators, MIN_PRICE, MAX_PRICE, fee, CAPITAL_PCT, STARTING_CASH'
                if old in body:
                    pattern.write_text(body.replace(old, old + ", COST_HURDLE"), encoding="utf-8")
                    changed = True

    return changed


def run_cmd(command: str, stage: str):
    last = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        log_path = LOGS / f"{stage}_attempt_{attempt}.log"
        proc = subprocess.run(command, shell=True, cwd=ROOT, capture_output=True, text=True, env=os.environ.copy())
        last = (proc.stdout or "") + (proc.stderr or "")
        log_path.write_text(last, encoding="utf-8")
        if proc.returncode == 0:
            return True, attempt, last
        if patch_known_failure(last):
            continue
        time.sleep(min(10 * attempt, 30))
    return False, MAX_ATTEMPTS, last


def extract_progress(details: dict, cycle: int):
    patterns = 0
    candidates = 0
    robust = 0
    p = OUT / "pattern_discovery.csv"
    if p.exists():
        try:
            import pandas as pd
            df = pd.read_csv(p)
            patterns = int(df["pattern"].nunique()) if "pattern" in df.columns else 0
        except Exception:
            pass
    a = OUT / "adaptive_candidates.csv"
    if a.exists():
        try:
            import pandas as pd
            df = pd.read_csv(a)
            candidates = int(len(df))
            robust = int(df["robust_holdout"].sum()) if "robust_holdout" in df.columns else 0
        except Exception:
            pass
    adaptive_memory = read_json(OUT / "adaptive_search_memory.json", {})
    lab = read_json(OUT / "strategy_lab_state.json", {})
    lab_progress = read_json(OUT / "strategy_hunter_progress.json", {})
    gi = read_json(OUT / "global_strategy_intelligence.json", {})
    discovery = lab_progress.get("discovery_layer", {})
    if not isinstance(discovery, dict):
        discovery = {}
    discovery.setdefault("enabled", True)
    discovery.setdefault("external_items", int(gi.get("source_count", 0)))
    discovery.setdefault("external_hypotheses", int(len(gi.get("hypotheses", []))))
    payload = {
        "cycle": cycle,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "patterns_tested": int(lab_progress.get("strategy_lab_variants", patterns)),
        "strategy_lab_variants": int(lab.get("variants_tested", lab_progress.get("strategy_lab_variants", 0))),
        "strategy_lab_selection_candidates": int(lab.get("selection_candidates", lab_progress.get("strategy_lab_selection_candidates", 0))),
        "strategy_lab_backtests": int(lab.get("backtests", lab_progress.get("strategy_lab_backtests", 0))),
        "strategy_lab_qualified_candidates": int(lab.get("qualified_candidates", lab_progress.get("strategy_lab_qualified_candidates", 0))),
        "strategy_lab_leader": lab.get("leader", lab_progress.get("strategy_lab_leader")),
        "discovery_layer": discovery,
        "global_intelligence_items": int(discovery.get("external_items", gi.get("source_count", 0))),
        "global_intelligence_hypotheses": int(discovery.get("external_hypotheses", len(gi.get("hypotheses", [])))),
        # Legacy fields remain for dashboard compatibility but are no longer
        # presented as the authoritative source of research breadth.
        "adaptive_search_round": adaptive_memory.get("search_round"),
        "adaptive_unique_variants": int(adaptive_memory.get("unique_variants_tested", 0)),
        "adaptive_new_variants_this_cycle": int(adaptive_memory.get("new_variants_this_cycle", 0)),
        "adaptive_focus_patterns": adaptive_memory.get("focus_patterns", []),
        "candidates": int(lab_progress.get("candidates", candidates)),
        "robust_candidates": int(lab_progress.get("robust_candidates", robust)),
        "engine_sanity": read_json(OUT / "engine_sanity.json", {}).get("status") == "passed",
        "last_cycle_status": details.get("_cycle_status", "unknown"),
    }
    write_json(PROGRESS, payload)


def main():
    cycle = cycle_number()
    details = {}
    repair_items = []
    write_status("running", "baseline", 0, details)
    core_failed = False

    for key, label, tier in STAGES:
        # Core stages are independently recoverable. A failure in adaptive
        # discovery must not prevent the independent candidate backtest from
        # testing the patterns already produced by Pattern Hunter.

        # Optional research tools are activated only after the core engine has
        # produced a candidate. This keeps the loop focused and quota-efficient.
        if tier == "optional":
            candidate_count = 0
            candidate_file = OUT / "strategy_lab_selection.csv"
            if candidate_file.exists():
                try:
                    import pandas as pd
                    candidate_count = len(pd.read_csv(candidate_file))
                except Exception:
                    candidate_count = 0
            if candidate_count == 0:
                details[key] = {"status": "skipped", "reason": "no_strategy_lab_selection_pool"}
                continue

        write_status("running", key, 0, details)
        command = (
            "python research/strategy/pattern_discovery.py"
            if key == "pattern_hunter"
            else "python research/strategy/adaptive_improvement.py"
            if key == "adaptive"
            else "python research/strategy/candidate_backtest.py"
            if key == "candidate_backtest"
            else "python research/strategy/strategy_lab_v4.py"
            if key == "strategy_lab"
            else "python research/strategy/failure_analysis.py"
            if key == "failure_analysis"
            else "python research/strategy/specialist_runner.py " + key
            if key not in {"baseline"}
            else "python research/strategy/baseline_research.py"
        )

        if key == "baseline":
            ok, attempts, log = run_cmd(command, "baseline_costs")
            if ok:
                import shutil
                shutil.copy2(OUT / "baseline_results.csv", OUT / "baseline_with_costs.csv")
                ok2, attempts2, log2 = run_cmd(
                    "SH_DISABLE_COSTS=1 python research/strategy/baseline_research.py",
                    "baseline_nocosts",
                )
                if ok2:
                    shutil.copy2(OUT / "baseline_results.csv", OUT / "baseline_no_costs.csv")
                    shutil.copy2(OUT / "baseline_with_costs.csv", OUT / "baseline_results.csv")
                else:
                    ok, attempts, log = False, max(attempts, attempts2), log2
            result = {}
            if (OUT / "baseline_with_costs.csv").exists():
                try:
                    import pandas as pd
                    bdf = pd.read_csv(OUT / "baseline_with_costs.csv")
                    result = {
                        "strategies": int(len(bdf)),
                        "best_final_equity": float(bdf["final_equity"].max()),
                        "worst_max_drawdown": float(bdf["max_drawdown"].min()),
                    }
                except Exception:
                    pass
        else:
            ok, attempts, log = run_cmd(command, key)
            result = None
            result_file = OUT / f"specialist_{key}.json"
            if result_file.exists():
                result = read_json(result_file, None)
                if result and result.get("status") in {"error", "unavailable", "insufficient_data"}:
                    ok = False
                    log = result.get("detail", "specialist reported non-success")

        if ok:
            details[key] = {"status": "done", "attempts": attempts}
            if result is not None:
                details[key]["result"] = result
        else:
            details[key] = {"status": "degraded", "attempts": attempts, "detail": "handled by recovery supervisor"}
            repair_items.append({
                "stage": key,
                "tier": tier,
                "attempts": attempts,
                "known_fix_applied": any(token in log.lower() for token, _ in KNOWN_FIXES),
                "recoverable": True,
            })
            if tier == "core":
                core_failed = True

        write_status("running", key, attempts, details)

    # Advisory/optional experiments cannot mark the primary research cycle as
    # degraded. Only a core stage failure does.
    core_repairs = [x for x in repair_items if x.get("tier") == "core"]
    cycle_status = "degraded" if core_repairs else "completed"
    details["_cycle_status"] = cycle_status
    write_json(REPAIR, {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cycle": cycle,
        "items": repair_items,
        "next_action": "recover_and_continue" if repair_items else "continue_research",
    })
    write_json(CYCLE, {
        "cycle": cycle,
        "status": cycle_status,
        "next_action": "recover_and_continue" if repair_items else "continue_research",
        "goal_achieved": False,
    })
    extract_progress(details, cycle)
    write_status(cycle_status, None, 0, details)
    subprocess.run([sys.executable, str(ROOT / "research/strategy/mission_controller.py")], cwd=ROOT, check=False)

    # Core failures must surface to the external recovery engine. Optional
    # specialist failures remain non-fatal by design.
    if core_failed:
        raise SystemExit("Strategy Hunter core stage failed after deterministic retries; recovery engine must repair and resume.")


if __name__ == "__main__":
    main()
