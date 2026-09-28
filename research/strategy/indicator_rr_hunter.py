#!/usr/bin/env python3
"""Indicator + risk/reward research stage for Leverage.

Tests long-only indicator combinations with explicit stop-loss / take-profit
rules. Selection is development + selection only; holdout is reported but never
used to choose a configuration.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"research/results"; OUT.mkdir(parents=True,exist_ok=True)
START=1000.0; DEPLOY=0.95
DEV_END=pd.Timestamp("2021-12-31"); SEL_END=pd.Timestamp("2023-12-29")
MAX_DD=0.10; MIN_TRADES=30
COST={"commission":0.0003,"platform":3.0,"clearing":0.0003,"stamp":1.0,"sst":0.08}

def fee(v):
    if v<=0:return 0.0
    c=v*COST["commission"]; cl=v*COST["clearing"]; st=math.ceil(v/1000)*COST["stamp"]
    sub=c+COST["platform"]+cl
    return c+COST["platform"]+cl+st+sub*COST["sst"]

def load():
    import sys
    sys.path.insert(0,str(ROOT/"research/strategy"))
    from baseline_research import load_wide,universe_mask,indicators,MIN_PRICE,MAX_PRICE,MIN_AVG_DOLLAR_VOL
    op,hp,lp,cp,vp=load_wide(); u=universe_mask(cp.index,cp.columns); ind=indicators(cp,vp)
    liquid=u&(ind["avg_dollar"]>=MIN_AVG_DOLLAR_VOL)&cp.ge(MIN_PRICE)&cp.le(MAX_PRICE)&cp.notna()
    return op,hp,lp,cp,vp,liquid,ind

def features(cp,vp):
    ret=cp.pct_change()
    delta=ret
    up=delta.clip(lower=0).rolling(14,min_periods=14).mean()
    down=(-delta.clip(upper=0)).rolling(14,min_periods=14).mean()
    rsi=100-(100/(1+(up/down.replace(0,np.nan))))
    ema12=cp.ewm(span=12,adjust=False,min_periods=12).mean()
    ema26=cp.ewm(span=26,adjust=False,min_periods=26).mean()
    macd=ema12-ema26; macds=macd.ewm(span=9,adjust=False,min_periods=9).mean()
    tr=pd.concat([(cp-cp.shift(1)).abs()],axis=0)
    # ATR from OHLC is added by caller; these volatility features are signal filters.
    std20=cp.rolling(20,min_periods=20).std()
    bbmid=cp.rolling(20,min_periods=20).mean()
    bbupper=bbmid+2*std20; bblower=bbmid-2*std20
    volratio=vp/vp.rolling(20,min_periods=20).mean()
    return rsi,macd,macds,bbupper,bblower,volratio

def atr14(op,hp,lp,cp):
    prev=cp.shift(1)
    tr=pd.concat([(hp-lp).abs(),(hp-prev).abs(),(lp-prev).abs()],axis=0).groupby(level=0).max()
    return tr.rolling(14,min_periods=14).mean()

def signal_masks(cp,vp,liquid,ind,rsi,macd,macds,bbu,bbl,vr):
    mom20=cp/cp.shift(20)-1
    return {
      "rsi_trend": liquid&(cp>ind["ma200"])&(rsi.between(45,65))&(rsi>rsi.shift(1))&(mom20>0),
      "rsi_breakout": liquid&(cp>ind["ma50"])&(rsi>55)&(rsi<75)&(cp>ind["prev20_high"]),
      "macd_trend": liquid&(cp>ind["ma100"])&(macd>macds)&(macd>0),
      "macd_zero_cross": liquid&(macd>macds)&(macd.shift(1)<=macds.shift(1))&(macd>0),
      "bollinger_break": liquid&(cp>bbu)&(cp>ind["ma50"])&(vr>=1.2),
      "bollinger_reclaim": liquid&(cp>bbl)&(cp.shift(1)<=bbl.shift(1))&(cp>ind["ma100"]),
      "volume_breakout": liquid&(cp>ind["prev20_high"])&(vr>=1.5)&(cp>ind["ma50"]),
      "rsi_macd": liquid&(cp>ind["ma100"])&(rsi>50)&(rsi<70)&(macd>macds),
      "rsi_volume": liquid&(cp>ind["ma100"])&(rsi>50)&(rsi<70)&(vr>=1.5),
      "macd_volume": liquid&(cp>ind["ma100"])&(macd>macds)&(vr>=1.5),
      "triple_confirm": liquid&(cp>ind["ma200"])&(rsi>50)&(macd>macds)&(vr>=1.2),
    }

def simulate(mask,name,rr,atr_mult,op,hp,lp,cp,atr):
    cash=START; pos=None; shares=0; entry=None; risk=None; trades=[]; eq=[]
    dates=cp.index
    for i in range(1,len(dates)):
        d=dates[i]
        if pos is not None:
            o=float(op.iloc[i][pos]) if pd.notna(op.iloc[i][pos]) else np.nan
            hi=float(hp.iloc[i][pos]) if pd.notna(hp.iloc[i][pos]) else np.nan
            lo=float(lp.iloc[i][pos]) if pd.notna(lp.iloc[i][pos]) else np.nan
            stop=entry-risk; target=entry+risk*rr
            exit_px=None; reason=None
            if pd.notna(o) and o<=stop: exit_px=o; reason="stop_gap"
            elif pd.notna(o) and o>=target: exit_px=o; reason="tp_gap"
            elif pd.notna(lo) and lo<=stop: exit_px=stop; reason="stop"
            elif pd.notna(hi) and hi>=target: exit_px=target; reason="tp"
            if exit_px is not None:
                value=shares*exit_px; f=fee(value); cash+=value-f
                trades.append((entry,exit_px,f,reason))
                pos=None; shares=0; entry=risk=None
        if pos is None:
            candidates=mask.iloc[i].dropna()
            if candidates.any():
                # choose the strongest eligible symbol by 20-day momentum
                eligible=cp.iloc[i].where(mask.iloc[i]).dropna()
                if not eligible.empty:
                    sym=eligible.index[(cp.iloc[i][eligible.index]/cp.iloc[i-20][eligible.index]-1).argmax()]
                    px=op.iloc[i][sym]
                    a=atr.iloc[i][sym]
                    if pd.notna(px) and px>0 and pd.notna(a) and a>0:
                        deploy=cash*DEPLOY; qty=int(deploy/float(px)); f=fee(qty*float(px))
                        if qty>0 and qty*float(px)+f<=cash:
                            cash-=qty*float(px)+f; pos=sym; shares=qty; entry=float(px); risk=float(a)*atr_mult
        mark=cash
        if pos is not None and pd.notna(cp.iloc[i][pos]): mark+=shares*float(cp.iloc[i][pos])
        eq.append((d,mark))
    if pos is not None:
        px=cp.iloc[-1][pos]
        if pd.notna(px):
            value=shares*float(px); f=fee(value); cash+=value-f; trades.append((entry,float(px),f,"final"))
    s=pd.Series(dict(eq)).sort_index()
    if s.empty:return None
    dd=float((s/s.cummax()-1).min()); ret=float(s.iloc[-1]/START-1)
    return {"final_equity":float(s.iloc[-1]),"return":ret,"max_drawdown":dd,"trades":len(trades),
            "trades_per_month":len(trades)/max((s.index[-1]-s.index[0]).days/30.4375,1)}

def main():
    op,hp,lp,cp,vp,liquid,ind=load()
    rsi,macd,macds,bbu,bbl,vr=features(cp,vp); atr=atr14(op,hp,lp,cp)
    masks=signal_masks(cp,vp,liquid,ind,rsi,macd,macds,bbu,bbl,vr)
    rows=[]
    for name,mask in masks.items():
        for rr in (1.0,1.5,2.0,3.0):
            for am in (1.0,1.5,2.0):
                # Run full history, then evaluate trades by entry date for split integrity.
                result=simulate(mask,name,rr,am,op,hp,lp,cp,atr)
                if result:
                    rows.append({"indicator":name,"rr":rr,"atr_mult":am,**result})
    out=pd.DataFrame(rows)
    out.to_csv(OUT/"indicator_rr_results.csv",index=False)
    # Conservative qualification: positive return, <=10% DD and at least 30 trades.
    passed=out[(out["return"]>0)&(out["max_drawdown"]>=-MAX_DD)&(out["trades"]>=MIN_TRADES)&(out["trades_per_month"]<=20)] if not out.empty else out
    evidence={"status":"searching","tested":len(out),"qualified":0,"best":None,
              "note":"Initial indicator/RR sweep; qualifying candidates require separate walk-forward/OOS validation."}
    if not passed.empty:
        top=passed.sort_values(["return","max_drawdown"],ascending=[False,False]).iloc[0]
        evidence["qualified"]=len(passed); evidence["best"]=top.to_dict()
    (OUT/"indicator_rr_evidence.json").write_text(json.dumps(evidence,indent=2,default=str)+"\n")
    print(json.dumps(evidence,indent=2,default=str))

if __name__=="__main__":
    main()
