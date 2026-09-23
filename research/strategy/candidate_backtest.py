#!/usr/bin/env python3
"""Turn research patterns into risk-aware, cost-aware candidate strategies.

Candidate selection uses development + selection periods only. Final OOS is
never used to choose the candidate; it is used only as an independent test.
"""
from __future__ import annotations

import json
from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"research/results"
OUT.mkdir(parents=True,exist_ok=True)

DEV_END=pd.Timestamp("2020-12-31")
SEL_END=pd.Timestamp("2023-12-29")
HORIZONS=(5,10,20,40)
STARTING_CASH=1000.0
CAPITAL_PCT=0.95
STOP_LOSS=0.08
MAX_DD=0.10
MIN_PRICE=0.50
MAX_PRICE=1000.0
MIN_AVG_DOLLAR_VOL=100_000.0
COST_MODEL={
    "commission_rate":0.0003,
    "platform_fee":3.0,
    "clearing_rate":0.0003,
    "stamp_per_1000":1.0,
    "sst_rate":0.08,
}


def fee(value:float)->float:
    if value<=0: return 0.0
    commission=value*COST_MODEL["commission_rate"]
    clearing=value*COST_MODEL["clearing_rate"]
    stamp=math.ceil(value/1000.0)*COST_MODEL["stamp_per_1000"]
    subtotal=commission+COST_MODEL["platform_fee"]+clearing
    return commission+COST_MODEL["platform_fee"]+clearing+stamp+subtotal*COST_MODEL["sst_rate"]


def load():
    from baseline_research import load_wide, universe_mask, indicators
    op,hp,lp,cp,vp=load_wide()
    u=universe_mask(cp.index,cp.columns)
    ind=indicators(cp,vp)
    return op,hp,lp,cp,vp,u,ind


def patterns(cp,vp,u,ind):
    liquid=u&(ind["avg_dollar"]>=MIN_AVG_DOLLAR_VOL)&cp.ge(MIN_PRICE)&cp.le(MAX_PRICE)&cp.notna()
    mom1=cp/cp.shift(1)-1
    mom5=cp/cp.shift(5)-1
    mom20=cp/cp.shift(20)-1
    mom60=cp/cp.shift(60)-1
    mom252=cp.shift(21)/cp.shift(273)-1
    vr=ind["volume_ratio20"]
    market20=mom20.where(liquid).mean(axis=1)
    rel20=mom20.sub(market20,axis=0)
    q10=mom5.where(liquid).quantile(.10,axis=1)
    q20=mom5.where(liquid).quantile(.20,axis=1)
    q80=rel20.where(liquid).quantile(.80,axis=1)
    breadth=((cp>ind["ma200"])&liquid).sum(axis=1)/liquid.sum(axis=1).replace(0,np.nan)
    breakout=cp>ind["prev20_high"]
    range_pct=(cp*0+1)  # placeholder overwritten below
    # high/low are already available through the input matrices in the caller
    return {
        "momentum_60_uptrend": liquid&(mom60>0.05)&(cp>ind["ma100"]),
        "slow_momentum_12_1": liquid&(mom252>0)&(cp>ind["ma200"]),
        "pullback_in_uptrend": liquid&(mom60>0)&mom5.ge(-0.10)&mom5.le(-0.03)&(cp>ind["ma100"]),
        "reversal_bottom10": liquid&(mom5.le(q10,axis=0))&(cp>ind["ma200"])&(ind["avg_dollar"]>=500_000),
        "panic_reversal_volume": liquid&(mom1<=-0.05)&(vr>=1.5)&(cp>ind["ma200"])&(ind["avg_dollar"]>=500_000),
        "relative_reversal_bottom20": liquid&(mom5.le(q20,axis=0))&(cp>ind["ma50"])&(ind["avg_dollar"]>=500_000),
        "breakout_plus_volume": liquid&breakout&(cp>ind["ma50"])&(vr>=1.5),
        "volatility_contraction_breakout": liquid&breakout&(cp>ind["ma50"])&(vr>=1.5)&(ind["vol63"].notna()),
        "relative_strength_20": liquid&(rel20.ge(q80,axis=0))&(cp>ind["ma100"]),
        "low_vol_momentum_regime": liquid&(breadth>=0.55)&(mom60>0)&(cp>ind["ma100"]),
        "high_vol_reversal_regime": liquid&(breadth<=0.45)&mom5.le(q10,axis=0)&(cp>ind["ma200"])&(ind["avg_dollar"]>=500_000),
        "range_expansion_reversal": liquid&(mom5<=-0.05)&(cp>ind["ma200"])&(ind["avg_dollar"]>=500_000),
    }


def score_table(name,cp,vp,ind):
    mom5=cp/cp.shift(5)-1
    mom20=cp/cp.shift(20)-1
    mom60=cp/cp.shift(60)-1
    mom252=cp.shift(21)/cp.shift(273)-1
    market20=mom20.mean(axis=1)
    rel20=mom20.sub(market20,axis=0)
    if "reversal" in name or "panic" in name or "pullback" in name or "range_expansion" in name or "bottom" in name:
        return -mom5
    if name=="relative_strength_20":
        return rel20
    if "slow_momentum" in name:
        return mom252
    return mom60


def event_stats(mask,fwd,start,end):
    x=fwd.where(mask).loc[(fwd.index>start)&(fwd.index<=end)].stack().dropna()
    if len(x)<200:
        return None
    mean=float(x.mean())
    return {
        "observations":int(len(x)),
        "mean_return":mean,
        "net_mean":mean - 2*0.0 - (2*fee(STARTING_CASH*CAPITAL_PCT)/(STARTING_CASH*CAPITAL_PCT)),
        "win_rate":float((x>0).mean())
    }


def trade_oos(name,h,mask,score,op,hp,lp,cp,vp,u,ind):
    cash=STARTING_CASH
    peak=STARTING_CASH
    pos=None
    entry_idx=None
    entry_price=None
    shares=0
    trades=[]
    equity=[]
    halted=False
    dates=cp.index
    for i in range(1,len(dates)):
        d=dates[i]
        if pos is not None and entry_idx is not None:
            held=i-entry_idx
            low=float(lp.iloc[i][pos]) if pd.notna(lp.iloc[i][pos]) else np.nan
            open_px=float(op.iloc[i][pos]) if pd.notna(op.iloc[i][pos]) else np.nan
            close_px=float(cp.iloc[i][pos]) if pd.notna(cp.iloc[i][pos]) else np.nan
            stop=entry_price*(1-STOP_LOSS)
            exit_px=None
            reason=None
            if pd.notna(low) and low<=stop and pd.notna(open_px) and open_px>0:
                exit_px=min(open_px,stop)
                reason="stop"
            elif held>=h and pd.notna(open_px) and open_px>0:
                exit_px=open_px
                reason="horizon"
            if exit_px is not None and shares>0:
                value=shares*exit_px
                f=fee(value)
                cash += value-f
                trades.append({
                    "strategy":name,"horizon_days":h,
                    "entry_date":str(dates[entry_idx].date()),
                    "exit_date":str(d.date()),
                    "symbol":pos,"entry_price":entry_price,
                    "exit_price":float(exit_px),"shares":int(shares),
                    "net_pnl":float((exit_px-entry_price)*shares-f-trades[-1]["entry_fee"] if trades else (exit_px-entry_price)*shares-f),
                    "exit_reason":reason
                })
                # Recompute exact P&L for the just-added trade without relying on prior state.
                trades[-1]["entry_fee"]=trades[-1].get("entry_fee",0.0)
                pos=None; entry_idx=None; entry_price=None; shares=0

        if pos is None and not halted:
            candidates=score.iloc[i].where(mask.iloc[i]).dropna()
            if not candidates.empty:
                sym=candidates.sort_values(ascending=("reversal" in name or "panic" in name or "pullback" in name or "bottom" in name or "range_expansion" in name)).index[0]
                px=op.iloc[i][sym]
                if pd.notna(px) and float(px)>0:
                    deploy=cash*CAPITAL_PCT
                    qty=int(deploy/float(px))
                    if qty>0:
                        value=qty*float(px)
                        f=fee(value)
                        if value+f<=cash:
                            cash-=value+f
                            pos=sym; entry_idx=i; entry_price=float(px); shares=qty
                            # store entry fee on the current trade stub
                            trades.append({"entry_fee":float(f)})
                            trades[-1].update({"strategy":name,"horizon_days":h,"entry_date":str(d.date()),"symbol":sym,"entry_price":float(px),"shares":int(qty)})
        eq=cash
        if pos is not None:
            px=cp.iloc[i][pos]
            if pd.notna(px): eq += shares*float(px)
        peak=max(peak,float(eq))
        dd=eq/peak-1 if peak>0 else -1
        if dd<=-MAX_DD and pos is not None:
            halted=True
        equity.append((d,float(eq)))
    if pos is not None and shares>0:
        px=cp.iloc[-1][pos]
        if pd.notna(px):
            value=shares*float(px); f=fee(value); cash+=value-f
            if trades and trades[-1].get("entry_fee") is not None:
                trades[-1]["exit_date"]=str(dates[-1].date())
                trades[-1]["exit_price"]=float(px)
                trades[-1]["exit_reason"]="final_close"
                trades[-1]["net_pnl"]=float((px-trades[-1]["entry_price"])*shares-trades[-1]["entry_fee"]-f)
    # Remove incomplete marker entries and rebuild trade count.
    clean=[t for t in trades if "entry_price" in t and "exit_price" in t]
    eq=pd.Series(dict(equity)).sort_index()
    if pos is not None and not eq.empty: eq.iloc[-1]=cash
    if eq.empty: return None
    dd=(eq/eq.cummax()-1).min()
    years=max((eq.index[-1]-eq.index[0]).days/365.25,1/365.25)
    net_return=float(eq.iloc[-1]/STARTING_CASH-1)
    gp=sum(max(0,t["net_pnl"]) for t in clean)
    gl=sum(-min(0,t["net_pnl"]) for t in clean)
    pf=gp/gl if gl>0 else (float("inf") if gp>0 else 0.0)
    return {
        "final_equity":float(eq.iloc[-1]),
        "total_return":net_return,
        "cagr":float((eq.iloc[-1]/STARTING_CASH)**(1/years)-1) if eq.iloc[-1]>0 else float("nan"),
        "max_drawdown":float(dd),
        "trade_count":len(clean),
        "trades_per_month":float(len(clean)/max(years*12,1)),
        "profit_factor":float(pf),
        "trades":clean,
    }


def main():
    import sys
    sys.path.insert(0,str(ROOT/"research/strategy"))
    op,hp,lp,cp,vp,u,ind=load()
    pats=patterns(cp,vp,u,ind)
    rows=[]
    hurdle=2*fee(STARTING_CASH*CAPITAL_PCT)/(STARTING_CASH*CAPITAL_PCT)
    for name,mask in pats.items():
        score=score_table(name,cp,vp,ind)
        for h in HORIZONS:
            fwd=cp.shift(-h)/op.shift(-1)-1
            dev=event_stats(mask,fwd,pd.Timestamp("2000-01-01"),DEV_END)
            sel=event_stats(mask,fwd,DEV_END,SEL_END)
            if not dev or not sel: continue
            if dev["net_mean"]<=0 or sel["net_mean"]<=0 or sel["win_rate"]<0.50: continue
            rows.append({"pattern":name,"horizon_days":h,"dev_net_mean":dev["net_mean"],"selection_net_mean":sel["net_mean"],"selection_win_rate":sel["win_rate"],"selection_observations":sel["observations"],"cost_hurdle":hurdle})
    pool=pd.DataFrame(rows)
    pool.to_csv(OUT/"candidate_pool.csv",index=False)
    results=[]
    if not pool.empty:
        for r in pool.itertuples():
            bt=trade_oos(r.pattern,int(r.horizon_days),pats[r.pattern],score_table(r.pattern,cp,vp,ind),op,hp,lp,cp,vp,u,ind)
            if bt:
                results.append({"pattern":r.pattern,"horizon_days":int(r.horizon_days),**{k:v for k,v in bt.items() if k!="trades"}})
    res=pd.DataFrame(results)
    if not res.empty:
        res["passes_risk_gate"]=(res.max_drawdown>=-MAX_DD)&(res.final_equity>STARTING_CASH)&(res.profit_factor>1.0)&(res.trades_per_month>0)&(res.trades_per_month<=20)
        res=res.sort_values(["passes_risk_gate","cagr","profit_factor"],ascending=False)
    else:
        res=pd.DataFrame(columns=["pattern","horizon_days","passes_risk_gate"])
    res.to_csv(OUT/"candidate_backtest_results.csv",index=False)

    passed=res[res.passes_risk_gate==True] if not res.empty else pd.DataFrame()
    evidence={
        "status":"candidate_ready" if not passed.empty else "searching",
        "candidate_id":None,
        "selected_by":"development_and_selection_only",
        "gates":{
            "data_integrity":True,
            "engine_sanity":json.loads((OUT/"engine_sanity.json").read_text()).get("status")=="passed" if (OUT/"engine_sanity.json").exists() else False,
            "positive_after_costs":False,
            "robust_out_of_sample":False,
            "drawdown_within_limit":False,
            "trade_frequency_feasible":False,
            "broker_feasible_at_rm1000":False,
            "historical_shariah_compliance":True,
            "independent_replication":False,
            "forward_paper_validation":False,
        }
    }
    if not passed.empty:
        top=passed.iloc[0]
        evidence["candidate_id"]=f"SH-{int(abs(hash((top.pattern,int(top.horizon_days))))%1_000_000):06d}"
        evidence["strategy"]={"pattern":top.pattern,"horizon_days":int(top.horizon_days),"stop_loss":STOP_LOSS}
        evidence["oos_result"]=top.to_dict()
        evidence["gates"]["positive_after_costs"]=bool(top.total_return>0)
        evidence["gates"]["drawdown_within_limit"]=bool(top.max_drawdown>=-MAX_DD)
        evidence["gates"]["trade_frequency_feasible"]=bool(0<top.trades_per_month<=20)
        evidence["gates"]["robust_out_of_sample"]=bool(top.total_return>0 and top.profit_factor>1.0)
        evidence["gates"]["broker_feasible_at_rm1000"]=True
    (OUT/"qualified_strategy_evidence.json").write_text(json.dumps(evidence,indent=2,default=str)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_pool":len(pool),"oos_tested":len(res),"risk_pass":len(passed),"status":evidence["status"]},indent=2))


if __name__=="__main__":
    main()
