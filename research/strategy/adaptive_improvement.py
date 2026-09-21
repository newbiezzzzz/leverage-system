#!/usr/bin/env python3
"""Strategy Hunter guided improvement: mutate promising interpretable patterns and test them OOS.

Selection uses development + selection periods only. The final holdout is never used
to choose a variant. This is an event-study discovery stage, not a live strategy.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research/strategy"))
from baseline_research import load_wide, universe_mask, indicators, MIN_PRICE, MAX_PRICE, MIN_AVG_DOLLAR_VOL, COST_HURDLE

OUT=ROOT/"research/results"
OUT.mkdir(parents=True,exist_ok=True)
DEV_END=pd.Timestamp("2021-12-31")
SEL_END=pd.Timestamp("2023-12-29")
HORIZONS=(5,10,20,40)

def eval_mask(name,mask,fwd,period):
    x=fwd.where(mask).loc[period].stack().dropna()
    if len(x)<200:
        return None
    mean=float(x.mean()); win=float((x>0).mean())
    return {"pattern":name,"observations":int(len(x)),"mean_return":mean,"net_mean":mean-COST_HURDLE,"win_rate":win}

def main():
    op,hp,lp,cp,vp=load_wide()
    universe=universe_mask(cp.index,cp.columns)
    ind=indicators(cp,vp)
    liquid=universe & (ind["avg_dollar"]>=MIN_AVG_DOLLAR_VOL) & cp.ge(MIN_PRICE) & cp.le(MAX_PRICE) & cp.notna()

    mom5=cp/cp.shift(5)-1
    mom20=cp/cp.shift(20)-1
    mom60=cp/cp.shift(60)-1
    mom126=cp/cp.shift(126)-1
    mom252=cp.shift(21)/cp.shift(273)-1
    vol20=cp.pct_change().rolling(20,min_periods=20).std()
    vol63=cp.pct_change().rolling(63,min_periods=63).std()
    vr20=vp/vp.rolling(20,min_periods=20).mean()
    market5=mom5.where(liquid).mean(axis=1)
    market20=mom20.where(liquid).mean(axis=1)
    rel5=mom5.sub(market5,axis=0)
    rel20=mom20.sub(market20,axis=0)
    q10=mom5.where(liquid).quantile(.10,axis=1)
    q20=mom5.where(liquid).quantile(.20,axis=1)
    q80rel20=rel20.where(liquid).quantile(.80,axis=1)
    breadth=((cp>ind["ma200"]) & liquid).sum(axis=1)/liquid.sum(axis=1).replace(0,np.nan)

    variants={}
    # Momentum mutations
    for lb,mom in [(20,cp/cp.shift(20)-1),(40,cp/cp.shift(40)-1),(60,mom60),(90,cp/cp.shift(90)-1),(120,cp/cp.shift(120)-1)]:
        for threshold in (0.0,.03,.05,.10):
            for trend_name,trend in (("ma100",ind["ma100"]),("ma200",ind["ma200"])):
                variants[f"momentum_{lb}_{int(threshold*100)}_{trend_name}"]=liquid&(mom>threshold)&(cp>trend)
    # Pullback mutations
    for lb,mom in [(40,cp/cp.shift(40)-1),(60,mom60),(90,cp/cp.shift(90)-1)]:
        for drop in (-.03,-.05,-.08,-.10):
            variants[f"pullback_{lb}_{int(abs(drop)*100)}"]=liquid&(mom>0)&(mom5<=drop)&(mom5>=-.15)&(cp>ind["ma100"])
    # Reversal mutations
    for drop in (-.03,-.04,-.05,-.06,-.08):
        for ma_name,ma in (("ma100",ind["ma100"]),("ma200",ind["ma200"])):
            for vr in (1.0,1.5,2.0):
                variants[f"reversal_{int(abs(drop)*100)}_{ma_name}_vr{vr:g}"]=liquid&(mom5<=drop)&(cp>ma)&(vr20>=vr)&(ind["avg_dollar"]>=500_000)
    # Breakout mutations
    for b in (10,20,40):
        prev=cp.shift(1).rolling(b,min_periods=b).max()
        for vr in (1.0,1.5,2.0):
            for trend in (ind["ma50"],ind["ma100"]):
                tag="ma50" if trend is ind["ma50"] else "ma100"
                variants[f"breakout_{b}_vr{vr:g}_{tag}"]=liquid&(cp>prev)&(cp>trend)&(vr20>=vr)
    # Relative strength / regime combinations
    variants["relative_strength_20_bull"]=liquid&(rel20>=q80rel20)&(cp>ind["ma100"])&breadth.ge(.55,axis=0)
    variants["relative_strength_20_neutral"]=liquid&(rel20>=q80rel20)&(cp>ind["ma100"])&breadth.ge(.45,axis=0)&breadth.lt(.55,axis=0)
    variants["bottom20_reversal_bull"]=liquid&(mom5<=q20)&(cp>ind["ma200"])&breadth.ge(.55,axis=0)&(ind["avg_dollar"]>=500_000)
    variants["bottom10_reversal_bear"]=liquid&(mom5<=q10)&(cp>ind["ma200"])&breadth.le(.45,axis=0)&(ind["avg_dollar"]>=500_000)
    variants["slow_momentum_12_1_lowvol"]=liquid&(mom252>0)&(cp>ind["ma200"])&(vol20<=vol63)
    variants["slow_momentum_12_1_bull"]=liquid&(mom252>0)&(cp>ind["ma200"])&breadth.ge(.55,axis=0)

    fwd={h:(cp.shift(-h)/op.shift(-1))-1 for h in HORIZONS}
    period_dev=fwd[5].index<=DEV_END
    period_sel=(fwd[5].index>DEV_END)&(fwd[5].index<=SEL_END)
    period_hold=fwd[5].index>SEL_END

    rows=[]
    for name,mask in variants.items():
        for h in HORIZONS:
            for pname,pmask in (("development",period_dev),("selection",period_sel),("holdout",period_hold)):
                r=eval_mask(name,mask,fwd[h],pmask)
                if r:
                    r["horizon_days"]=h; r["period"]=pname; rows.append(r)
    df=pd.DataFrame(rows)
    df.to_csv(OUT/"adaptive_improvements.csv",index=False)
    selected=[]
    if not df.empty:
        for (name,h),g in df.groupby(["pattern","horizon_days"]):
            d=g[g.period=="development"]; s=g[g.period=="selection"]; hold=g[g.period=="holdout"]
            if d.empty or s.empty or hold.empty: continue
            dr=float(d.iloc[0].net_mean); sr=float(s.iloc[0].net_mean); sw=float(s.iloc[0].win_rate)
            hr=float(hold.iloc[0].net_mean); hw=float(hold.iloc[0].win_rate); hn=int(hold.iloc[0].observations)
            # Selection only: must beat costs and have >=50% win rate.
            if dr>COST_HURDLE and sr>0 and sw>=.50:
                selected.append({"pattern":name,"horizon_days":int(h),"development_net_mean":dr,"selection_net_mean":sr,"selection_win_rate":sw,"holdout_net_mean":hr,"holdout_win_rate":hw,"holdout_observations":hn})
    out=pd.DataFrame(selected)
    if not out.empty:
        out["robust_holdout"]= (out.holdout_net_mean>0) & (out.holdout_win_rate>=.50) & (out.holdout_observations>=200)
        out=out.sort_values(["robust_holdout","holdout_net_mean","selection_net_mean"],ascending=False).head(30)
    out.to_csv(OUT/"adaptive_candidates.csv",index=False)
    report={"status":"tested","variants":len(variants),"candidate_count":int(len(out)),"robust_holdout_count":int(out.robust_holdout.sum()) if not out.empty else 0,"cost_hurdle":COST_HURDLE}
    (OUT/"specialist_adaptive.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not out.empty: print(out.to_string(index=False))

if __name__=="__main__":
    main()
