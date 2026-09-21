#!/usr/bin/env python3
"""Strategy Hunter autonomous, recoverable research pipeline."""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"research"/"results"
OUT.mkdir(parents=True,exist_ok=True)
STATUS=OUT/"strategy_hunter_pipeline.json"
LOGS=OUT/"pipeline_logs"
LOGS.mkdir(exist_ok=True)
MAX_ATTEMPTS=5

STAGES=[
    ("baseline","Baseline backtest",None),
    ("pattern_hunter","Pattern Hunter","research/strategy/pattern_discovery.py"),
    ("vectorbt","VectorBT","research/strategy/specialist_runner.py vectorbt"),
    ("lightgbm","LightGBM","research/strategy/specialist_runner.py lightgbm"),
    ("symbolic","Symbolic Regression","research/strategy/specialist_runner.py symbolic"),
    ("qlib","Qlib","research/strategy/specialist_runner.py qlib"),
    ("optuna","Optuna","research/strategy/specialist_runner.py optuna"),
    ("lean","LEAN","research/strategy/specialist_runner.py lean"),
    ("chronos2","Chronos-2","research/strategy/specialist_runner.py chronos2"),
]

def git_publish():
    try:
        subprocess.run(["git","config","user.name","github-actions[bot]"],check=True,capture_output=True)
        subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True,capture_output=True)
        subprocess.run(["git","add",str(STATUS)],check=True)
        chk=subprocess.run(["git","diff","--cached","--quiet"])
        if chk.returncode==0: return
        subprocess.run(["git","commit","-m","chore: update Strategy Hunter pipeline status"],check=True,capture_output=True)
        for _ in range(3):
            pull=subprocess.run(["git","pull","--rebase","origin","main"],capture_output=True,text=True)
            if pull.returncode==0 and subprocess.run(["git","push"],capture_output=True,text=True).returncode==0:
                return
            subprocess.run(["git","rebase","--abort"],capture_output=True)
    except Exception as e:
        print("status publish warning:",e)

def write_status(status,stage=None,attempt=0,error=None,details=None):
    payload={
        "updated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "status":status,"stage":stage,"attempt":attempt,"error":error,
        "stages":details or {}
    }
    STATUS.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    git_publish()

def patch_known_failure(log):
    text=log.lower()
    changed=False
    baseline=ROOT/"research/strategy/baseline_research.py"
    pattern=ROOT/"research/strategy/pattern_discovery.py"
    if "truth value of a series is ambiguous" in text and baseline.exists():
        c=baseline.read_text(encoding="utf-8")
        old='breadth = (px > ind["ma200"]).where(eligible).mean()'
        new='breadth = (px > ind["ma200"].loc[date]).where(eligible).mean()'
        if old in c:
            baseline.write_text(c.replace(old,new),encoding="utf-8")
            changed=True
            print("AUTO-REPAIR: fixed regime breadth Series lookup")
    if "cost_hurdle" in text and "not defined" in text:
        c=pattern.read_text(encoding="utf-8") if pattern.exists() else ""
        if "COST_HURDLE" not in c or "from baseline_research import" in c and "COST_HURDLE" not in c.splitlines()[0:20].__str__():
            pass
        b=baseline.read_text(encoding="utf-8")
        if "COST_HURDLE =" not in b:
            needle='    return commission + COST_MODEL["platform_fee"] + clearing + stamp + sst\n\n\n'
            b=b.replace(needle,needle+'# Approximate round-trip transaction-cost hurdle for a 95% deployed RM1,000 account.\nCOST_HURDLE = 2.0 * fee(STARTING_CASH * CAPITAL_PCT) / (STARTING_CASH * CAPITAL_PCT)\n\n\n')
            baseline.write_text(b,encoding="utf-8"); changed=True
        if pattern.exists():
            c=pattern.read_text(encoding="utf-8")
            imp='from baseline_research import load_wide, universe_mask, indicators, MIN_PRICE, MAX_PRICE, fee, CAPITAL_PCT, STARTING_CASH'
            if imp in c and "COST_HURDLE" not in c.split(imp,1)[0]:
                c=c.replace(imp,imp+", COST_HURDLE")
                pattern.write_text(c,encoding="utf-8"); changed=True
    if changed:
        subprocess.run(["git","add",str(baseline),str(pattern)],check=False)
        subprocess.run(["git","commit","-m","fix: auto-repair Strategy Hunter research failure"],check=False)
        subprocess.run(["git","push"],check=False)
    return changed

def run_cmd(cmd,stage,env_extra=None):
    attempts=0
    last=""
    env=os.environ.copy()
    if env_extra:
        env.update(env_extra)
    while attempts<MAX_ATTEMPTS:
        attempts+=1
        log_path=LOGS/f"{stage}_attempt_{attempts}.log"
        print(f"\n=== {stage} attempt {attempts}/{MAX_ATTEMPTS} ===")
        p=subprocess.run(cmd,shell=True,cwd=ROOT,capture_output=True,text=True,env=env)
        last=(p.stdout or "")+(p.stderr or "")
        log_path.write_text(last,encoding="utf-8")
        if p.returncode==0:
            return True,attempts,last
        repaired=patch_known_failure(last)
        if repaired:
            print("Re-running after automatic repair.")
            continue
        time.sleep(min(10*attempts,30))
    return False,attempts,last

def baseline_stage():
    ok,a,log=run_cmd("python research/strategy/baseline_research.py","baseline_costs")
    if not ok: return False,a,log
    shutil_cmd=subprocess.run(["cp","research/results/baseline_results.csv","research/results/baseline_with_costs.csv"],cwd=ROOT,capture_output=True,text=True)
    if shutil_cmd.returncode: return False,a,shutil_cmd.stderr
    ok2,a2,log2=run_cmd("python research/strategy/baseline_research.py","baseline_nocosts",{"SH_DISABLE_COSTS":"1"})
    if not ok2: return False,max(a,a2),log2
    log=log2
    subprocess.run(["cp","research/results/baseline_results.csv","research/results/baseline_no_costs.csv"],cwd=ROOT)
    subprocess.run(["cp","research/results/baseline_with_costs.csv","research/results/baseline_results.csv"],cwd=ROOT)
    return True,a,log

def main():
    details={}
    write_status("running","baseline",0,details=details)
    ok,a,log=baseline_stage()
    details["baseline"]={"status":"done" if ok else "failed","attempts":a}
    if (OUT/"baseline_with_costs.csv").exists():
        try:
            bdf=__import__("pandas").read_csv(OUT/"baseline_with_costs.csv")
            details["baseline"]["result"]={"strategies":int(len(bdf)),"best_final_equity":float(bdf["final_equity"].max()),"worst_max_drawdown":float(bdf["max_drawdown"].min())}
        except Exception:
            pass
    write_status("running" if ok else "failed","pattern_hunter" if ok else "baseline",a,None if ok else log[-3000:],details)
    for key,label,cmd in STAGES[1:]:
        write_status("running",key,0,details=details)
        if key=="pattern_hunter":
            run=["python","research/strategy/pattern_discovery.py"]
            ok,a,log=run_cmd(" ".join(run),key)
        else:
            ok,a,log=run_cmd(f"python {cmd}",key)
        details[key]={"status":"done" if ok else "failed","attempts":a}
        result_file=OUT/f"specialist_{key}.json"
        if result_file.exists():
            try:
                specialist_result=json.loads(result_file.read_text(encoding="utf-8"))
                details[key]["result"]=specialist_result
            except Exception:
                pass
        if not ok:
            details[key]["error"]=log[-2500:]
            # Independent specialists are allowed to fail without stopping the
            # pipeline. Later specialists still get their chance where possible.
            write_status("running",None,a,details=details)
            continue
        write_status("running",None,a,details=details)

    any_failed=any(v.get("status")=="failed" for v in details.values())
    write_status("completed_with_errors" if any_failed else "completed","done",0,details=details)

if __name__=="__main__":
    main()
