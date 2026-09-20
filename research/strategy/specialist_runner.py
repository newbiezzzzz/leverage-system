#!/usr/bin/env python3
"""Small, RM0-friendly specialist technology experiments for Strategy Hunter."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "results"
DATA = ROOT / "research" / "data" / "data" / "ohlcv"
OUT.mkdir(parents=True, exist_ok=True)


def install(pkg: str) -> tuple[bool, str]:
    try:
        p = subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], capture_output=True, text=True, timeout=900)
        return p.returncode == 0, (p.stdout + p.stderr)[-4000:]
    except Exception as e:
        return False, str(e)


def vectorbt_stage():
    ok, log = install("vectorbt")
    if not ok:
        return {"tool": "VectorBT", "status": "unavailable", "added_value": False, "detail": log}
    try:
        import vectorbt as vbt
        files = sorted(DATA.glob("*.csv"))[:10]
        t0 = time.perf_counter()
        runs = 0
        for p in files:
            d = pd.read_csv(p, parse_dates=["date"]).sort_values("date")
            s = d["split_adj_close"].dropna().tail(1500)
            if len(s) < 100:
                continue
            fast = vbt.MA.run(s, 20)
            slow = vbt.MA.run(s, 50)
            entries = fast.ma_crossed_above(slow)
            exits = fast.ma_crossed_below(slow)
            pf = vbt.Portfolio.from_signals(s, entries, exits, init_cash=1000)
            _ = float(pf.final_value())
            runs += 1
        elapsed = time.perf_counter() - t0
        return {"tool":"VectorBT","status":"tested","added_value":True,"detail":f"Vectorized MA benchmark ran on {runs} real OHLCV symbols in {elapsed:.3f}s","version":getattr(vbt,"__version__","unknown")}
    except Exception as e:
        return {"tool":"VectorBT","status":"error","added_value":False,"detail":repr(e)}


def lightgbm_stage():
    ok, log = install("lightgbm")
    if not ok:
        return {"tool":"LightGBM","status":"unavailable","added_value":False,"detail":log}
    try:
        from lightgbm import LGBMRegressor
        rows=[]
        for p in sorted(DATA.glob("*.csv"))[:12]:
            d=pd.read_csv(p,parse_dates=["date"]).sort_values("date")
            c=d["split_adj_close"].astype(float)
            v=d["split_adj_volume"].astype(float)
            x=pd.DataFrame({
                "date":d["date"],
                "ret5":c/c.shift(5)-1,
                "ret20":c/c.shift(20)-1,
                "ret60":c/c.shift(60)-1,
                "vol20":(c.pct_change().rolling(20).std()),
                "volume_ratio20":v/v.rolling(20).mean(),
                "target5":c.shift(-5)/c-1,
            }).dropna()
            rows.append(x)
        df=pd.concat(rows,ignore_index=True)
        train=df[df.date<=pd.Timestamp("2023-12-29")]
        test=df[df.date>pd.Timestamp("2023-12-29")]
        features=["ret5","ret20","ret60","vol20","volume_ratio20"]
        if len(train)<1000 or len(test)<300:
            return {"tool":"LightGBM","status":"insufficient_data","added_value":False,"detail":f"train={len(train)}, test={len(test)}"}
        model=LGBMRegressor(n_estimators=120,num_leaves=15,learning_rate=0.05,verbosity=-1)
        model.fit(train[features],train.target5)
        pred=model.predict(test[features])
        corr=float(np.corrcoef(pred,test.target5)[0,1])
        rmse=float(np.sqrt(np.mean((pred-test.target5)**2)))
        base_rmse=float(np.sqrt(np.mean((test.target5-test.target5.mean())**2)))
        return {"tool":"LightGBM","status":"tested","added_value":bool(np.isfinite(corr)),"detail":f"OOS 5-day-return correlation={corr:.4f}; RMSE={rmse:.4f}; mean-only RMSE={base_rmse:.4f}","oos_correlation":corr,"oos_rmse":rmse,"baseline_rmse":base_rmse}
    except Exception as e:
        return {"tool":"LightGBM","status":"error","added_value":False,"detail":repr(e)}


def optuna_stage():
    ok, log = install("optuna")
    if not ok:
        return {"tool":"Optuna","status":"unavailable","added_value":False,"detail":log}
    try:
        import optuna
        p=OUT/"pattern_discovery.csv"
        if not p.exists():
            return {"tool":"Optuna","status":"waiting","added_value":False,"detail":"Pattern discovery output not available"}
        df=pd.read_csv(p)
        disc=df[df.period=="discovery"].dropna(subset=["mean_return"])
        val=df[df.period=="validation"]
        if disc.empty:
            return {"tool":"Optuna","status":"no_candidates","added_value":False,"detail":"No discovery observations"}
        lookup={(r.pattern,int(r.horizon_days)):r for r in val.itertuples()}
        def objective(trial):
            name=trial.suggest_categorical("pattern",sorted(disc.pattern.unique().tolist()))
            horizon=trial.suggest_categorical("horizon",sorted(disc.horizon_days.unique().tolist()))
            z=disc[(disc.pattern==name)&(disc.horizon_days==horizon)]
            if z.empty: return -1e9
            return float(z.iloc[0].mean_return)
        study=optuna.create_study(direction="maximize")
        study.optimize(objective,n_trials=min(48,len(disc)*2),show_progress_bar=False)
        key=(study.best_params["pattern"],int(study.best_params["horizon"]))
        vr=lookup.get(key)
        out={"tool":"Optuna","status":"tested","added_value":vr is not None,"detail":f"Discovery-selected pattern={key[0]}, horizon={key[1]}d; held-out validation available={vr is not None}","best_discovery_mean":float(study.best_value)}
        if vr is not None:
            out.update({"validation_mean":float(vr.mean_return),"validation_win_rate":float(vr.win_rate),"validation_observations":int(vr.observations)})
        return out
    except Exception as e:
        return {"tool":"Optuna","status":"error","added_value":False,"detail":repr(e)}


def lean_stage():
    ok, log = install("lean")
    if not ok:
        return {"tool":"LEAN","status":"unavailable","added_value":False,"detail":log}
    try:
        p=subprocess.run(["lean","--version"],capture_output=True,text=True,timeout=60)
        detail=(p.stdout+p.stderr).strip()
        # Full LEAN backtesting needs a local Docker/data environment; keep this
        # RM0 pipeline at the CLI replication-preflight level.
        return {"tool":"LEAN","status":"tested_cli","added_value":True,"detail":detail}
    except Exception as e:
        return {"tool":"LEAN","status":"error","added_value":False,"detail":repr(e)}


def chronos2_stage():
    ok, log = install("chronos-forecasting")
    if not ok:
        return {"tool":"Chronos-2","status":"unavailable","added_value":False,"detail":log}
    try:
        from chronos import Chronos2Pipeline
        return {"tool":"Chronos-2","status":"package_ready","added_value":True,"detail":"Chronos2Pipeline import succeeded; model download/inference is deferred to avoid unnecessary 478MB model pull in the base pass."}
    except Exception as e:
        return {"tool":"Chronos-2","status":"error","added_value":False,"detail":repr(e)}


STAGES={"vectorbt":vectorbt_stage,"lightgbm":lightgbm_stage,"optuna":optuna_stage,"lean":lean_stage,"chronos2":chronos2_stage}


def main():
    if len(sys.argv)!=2 or sys.argv[1] not in STAGES:
        raise SystemExit("usage: specialist_runner.py {vectorbt|lightgbm|optuna|lean|chronos2}")
    stage=sys.argv[1]
    result=STAGES[stage]()
    (OUT/f"specialist_{stage}.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
