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
    ("adaptive", "Guided improvement", "core"),
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
    return int(p.get("cycle", 0)) + 1


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
    previous = read_json(PROGRESS, {})
    payload = {
        "cycle": cycle,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "patterns_tested": patterns,
        "candidates": candidates,
        "robust_candidates": robust,
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
        if core_failed and tier == "core":
            details[key] = {"status": "skipped", "reason": "upstream_core_failure"}
            continue

        write_status("running", key, 0, details)
        command = (
            "python research/strategy/pattern_discovery.py"
            if key == "pattern_hunter"
            else "python research/strategy/adaptive_improvement.py"
            if key == "adaptive"
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

    cycle_status = "degraded" if repair_items else "completed"
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


if __name__ == "__main__":
    main()
