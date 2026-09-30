#!/usr/bin/env python3
"""Strategy Hunter guided improvement: mutate promising interpretable patterns and test them OOS.

Selection uses development + selection periods only. The final holdout is never used
to choose a variant. This is an event-study discovery stage, not a live strategy.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import hashlib
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
PROGRESS_PATH=OUT/"strategy_hunter_progress.json"
MEMORY_PATH=OUT/"adaptive_search_memory.json"

def current_cycle():
    try:
        state=json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        return int(state.get("cycle",0))+1
    except Exception:
        return 1

def previous_focus():
    p=OUT/"pattern_discovery.csv"
    if not p.exists():
        return []
    try:
        df=pd.read_csv(p)
        if df.empty:
            return []
        d=df[df.period=="discovery"].groupby("pattern")["net_mean_vs_hurdle"].mean()
        v=df[df.period=="validation"].groupby("pattern")["net_mean_vs_hurdle"].mean()
        return [str(x) for x in d.add(v,fill_value=0.0).sort_values(ascending=False).head(4).index]
    except Exception:
        return []

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
    cycle=current_cycle()
    round_no=(cycle-1)%12
    focus=previous_focus()

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
    variants["relative_strength_20_bull"]=liquid&(rel20.ge(q80rel20,axis=0))&(cp>ind["ma100"])&breadth.ge(.55,axis=0)
    variants["relative_strength_20_neutral"]=liquid&(rel20.ge(q80rel20,axis=0))&(cp>ind["ma100"])&breadth.ge(.45,axis=0)&breadth.lt(.55,axis=0)
    variants["bottom20_reversal_bull"]=liquid&(mom5.le(q20,axis=0))&(cp>ind["ma200"])&breadth.ge(.55,axis=0)&(ind["avg_dollar"]>=500_000)
    variants["bottom10_reversal_bear"]=liquid&(mom5.le(q10,axis=0))&(cp>ind["ma200"])&breadth.le(.45,axis=0)&(ind["avg_dollar"]>=500_000)
    variants["slow_momentum_12_1_lowvol"]=liquid&(mom252>0)&(cp>ind["ma200"])&(vol20<=vol63)
    variants["slow_momentum_12_1_bull"]=liquid&(mom252>0)&(cp>ind["ma200"])&breadth.ge(.55,axis=0)

    # Dedicated Wyckoff Spring search. A spring is defined mechanically as
    # an intrabar undercut of prior support followed by a close back above it.
    # Variants sweep support depth, close location, and volume contraction.
    for lb in (10, 20, 30):
        support=lp.rolling(lb,min_periods=lb).min().shift(1)
        undercut=(lp/support-1.0)
        bar_range=(hp-lp).replace(0,np.nan)
        clv=(cp-lp)/bar_range
        for depth in (-0.005,-0.010,-0.020):
            for clv_min in (0.55,0.65,0.75):
                for vr_max in (0.90,1.20,1.50):
                    variants[
                        f"wyckoff_spring_lb{lb}_d{int(abs(depth)*1000)}_clv{int(clv_min*100)}_vr{vr_max:g}"
                    ]=(
                        liquid
                        & (undercut<=depth)
                        & (cp>support)
                        & (clv>=clv_min)
                        & (vr20<=vr_max)
                    )
        # Confirmed Spring -> Sign of Strength (SOS) variants. The spring
        # must occur on the prior session; today's close must exceed the
        # prior spring high, preventing look-ahead.
        spring=(undercut<=-0.01)&(cp>support)&(clv>=0.65)&(vr20<=1.50)
        for vr_min in (1.0,1.3,1.6):
            sos=spring.shift(1).fillna(False)&(cp>hp.shift(1))&(vr20>=vr_min)
            variants[f"wyckoff_spring_sos_lb{lb}_vr{vr_min:g}"]=liquid&sos

    # Cycle-specific adaptive search regions. Each round explores a different
    # parameter region; focus is derived from the previous cycle's results.
    if round_no==0:
        for lb in (30,45,60,90,120):
            mom=cp/cp.shift(lb)-1
            for th in (0.00,0.02,0.04,0.06,0.08,0.12):
                for tname,t in (("ma50",ind["ma50"]),("ma100",ind["ma100"]),("ma200",ind["ma200"])):
                    variants[f"adaptive_r0_mom_{lb}_{int(th*100)}_{tname}"]=liquid&(mom>th)&(cp>t)
    elif round_no==1:
        for lb in (15,25,35,50,75,100,150):
            mom=cp/cp.shift(lb)-1
            for th in (-0.01,0.00,0.01,0.025,0.04,0.055,0.075):
                for tname,t in (("ma50",ind["ma50"]),("ma100",ind["ma100"]),("ma200",ind["ma200"])):
                    variants[f"adaptive_r1_mom_{lb}_{int(round(th*1000))}_{tname}"]=liquid&(mom>th)&(cp>t)
        for vv in (0.60,0.75,0.90,1.00,1.10,1.25):
            variants[f"adaptive_r1_lowvol_{vv:g}"]=liquid&(mom60>0)&(cp>ind["ma100"])&(vol20<=vv*vol63)
    elif round_no==2:
        for b in (5,8,10,15,20,30,40,60):
            prev=cp.shift(1).rolling(b,min_periods=b).max()
            for vr in (0.90,1.10,1.30,1.50,1.80,2.20,3.00):
                for tname,t in (("ma50",ind["ma50"]),("ma100",ind["ma100"]),("ma200",ind["ma200"])):
                    variants[f"adaptive_r2_break_{b}_vr{vr:g}_{tname}"]=liquid&(cp>prev)&(cp>t)&(vr20>=vr)
                for contraction in (0.65,0.80,0.95,1.10):
                    variants[f"adaptive_r2_break_{b}_vr{vr:g}_vc{contraction:g}"]=liquid&(cp>prev)&(cp>ind["ma100"])&(vr20>=vr)&(vol20<=contraction*vol63)
    elif round_no==3:
        for lb in (20,40,60,90,120):
            mom=cp/cp.shift(lb)-1
            for drop in (-0.02,-0.03,-0.04,-0.05,-0.06,-0.08,-0.10,-0.12):
                for rebound_lb in (3,5,10):
                    rebound=cp/cp.shift(rebound_lb)-1
                    variants[f"adaptive_r3_pull_{lb}_{int(abs(drop)*100)}_r{rebound_lb}"]=liquid&(mom>0)&(mom5<=drop)&(rebound>0)&(cp>ind["ma100"])
        for drop in (-0.03,-0.05,-0.07,-0.10,-0.15):
            for vr in (0.80,1.00,1.25,1.50,2.00):
                variants[f"adaptive_r3_rev_{int(abs(drop)*100)}_vr{vr:g}"]=liquid&(mom5<=drop)&(cp>ind["ma200"])&(vr20>=vr)&(ind["avg_dollar"]>=500_000)
    elif round_no==4:
        for pct in (0.70,0.75,0.80,0.85,0.90):
            q=rel20.where(liquid).quantile(pct,axis=1)
            for lb in (20,40,60,90):
                mom=cp/cp.shift(lb)-1
                for tname,t in (("ma50",ind["ma50"]),("ma100",ind["ma100"]),("ma200",ind["ma200"])):
                    for br_lo,br_hi in ((0.00,1.01),(0.45,1.01),(0.55,1.01),(0.00,0.45),(0.40,0.60)):
                        variants[f"adaptive_r4_rel_p{int(pct*100)}_lb{lb}_{tname}_br{int(br_lo*100)}_{int(br_hi*100)}"]=liquid&(rel20>=q)&(mom>0)&(cp>t)&breadth.ge(br_lo,axis=0)&breadth.lt(br_hi,axis=0)
    elif round_no==5:
        # New family: volatility-state and mean-reversion combinations.
        rsi7=100-(100/(1+(cp.pct_change().clip(lower=0).rolling(7).mean() /
            (-cp.pct_change().clip(upper=0).rolling(7).mean()).replace(0,np.nan))))
        for lb in (5,10,20):
            for dd in (-0.03,-0.05,-0.08,-0.12):
                variants[f"adaptive_r5_meanrev_dd{int(abs(dd)*100)}_lb{lb}"]=liquid&(cp/cp.shift(lb)-1<=dd)&(cp>ind["ma200"])&(mom20>0)
        for ratio in (0.50,0.70,0.90,1.10):
            variants[f"adaptive_r5_rsi_vol_{ratio:g}"]=liquid&(rsi7<35)&(cp>ind["ma100"])&(vol20<=ratio*vol63)

    elif round_no==6:
        # Volatility compression -> expansion.
        vol5=cp.pct_change().rolling(5,min_periods=5).std()
        for ratio in (0.40,0.55,0.70,0.85):
            for lb in (5,10,20,40):
                prev=cp.shift(1).rolling(lb,min_periods=lb).max()
                variants[f"adaptive_r6_squeeze_{int(ratio*100)}_b{lb}"]=liquid&(vol5<=ratio*vol20)&(cp>prev)&(cp>ind["ma100"])
        for ratio in (0.75,0.90,1.10,1.30):
            variants[f"adaptive_r6_vol_expansion_{ratio:g}"]=liquid&(vol5>=ratio*vol20)&(mom20>0)&(cp>ind["ma100"])

    elif round_no==7:
        # Gap continuation/recovery family.
        gap=(op/cp.shift(1))-1
        for g in (0.02,0.04,0.06,0.08):
            variants[f"adaptive_r7_gap_up_{int(g*100)}"]=liquid&(gap>=g)&(mom20>0)&(cp>ind["ma50"])
            variants[f"adaptive_r7_gap_recover_{int(g*100)}"]=liquid&(gap<=-g)&(cp>ind["ma200"])&(mom5>0)
        for vr in (1.2,1.5,2.0,3.0):
            variants[f"adaptive_r7_gap_volume_{vr:g}"]=liquid&(gap>0.02)&(vr20>=vr)&(cp>ind["ma100"])

    elif round_no==8:
        # Cross-sectional multi-factor ranking.
        score=(mom20.rank(axis=1,pct=True)+mom60.rank(axis=1,pct=True)+
               rel20.rank(axis=1,pct=True)+(-vol20).rank(axis=1,pct=True))/4
        for q in (0.70,0.80,0.90,0.95):
            threshold=score.where(liquid).quantile(q,axis=1)
            for tname,t in (("ma100",ind["ma100"]),("ma200",ind["ma200"])):
                variants[f"adaptive_r8_multifactor_q{int(q*100)}_{tname}"]=liquid&(score>=threshold)&(cp>t)

    elif round_no==9:
        # Trend-transition family.
        for fast,slow in ((10,30),(20,50),(30,100),(50,200)):
            fma=cp.rolling(fast,min_periods=fast).mean()
            sma=cp.rolling(slow,min_periods=slow).mean()
            accel=fma/fma.shift(5)-1
            variants[f"adaptive_r9_cross_{fast}_{slow}"]=liquid&(fma>sma)&(fma.shift(1)<=sma.shift(1))&(accel>0)
            variants[f"adaptive_r9_cross_hold_{fast}_{slow}"]=liquid&(fma>sma)&(accel>0)&(mom20>0)

    elif round_no==10:
        # Relative-strength regime matrix with different market breadth states.
        for br in (0.30,0.40,0.50,0.60,0.70):
            for relq in (0.70,0.80,0.90):
                q=rel20.where(liquid).quantile(relq,axis=1)
                for lb in (20,40,60,90):
                    mom=cp/cp.shift(lb)-1
                    variants[f"adaptive_r10_regime_br{int(br*100)}_q{int(relq*100)}_m{lb}"]=liquid&(mom>0)&(cp>ind["ma100"])&breadth.ge(br,axis=0)&(rel20>=q)

    elif round_no==11:
        # Hybrid volatility + momentum + relative strength combinations.
        for br in (0.35,0.45,0.55,0.65):
            for vr in (0.70,0.90,1.10,1.40):
                for relq in (0.70,0.80,0.90):
                    q=rel20.where(liquid).quantile(relq,axis=1)
                    variants[f"adaptive_r11_hybrid_br{int(br*100)}_v{vr:g}_q{int(relq*100)}"]=liquid&(mom60>0)&(cp>ind["ma100"])&breadth.ge(br,axis=0)&(vol20<=vr*vol63)&(rel20>=q)

    else:
        for br in (0.35,0.45,0.50,0.55,0.65):
            for vv in (0.70,0.85,1.00,1.20,1.50):
                for mom_lb,mom_min in ((20,0.00),(40,0.02),(60,0.05),(90,0.08),(120,0.10)):
                    mom=cp/cp.shift(mom_lb)-1
                    variants[f"adaptive_r5_regime_br{int(br*100)}_v{vv:g}_m{mom_lb}_{int(mom_min*100)}"]=liquid&(mom>mom_min)&(cp>ind["ma100"])&breadth.ge(br,axis=0)&(vol20<=vv*vol63)
        for drop in (-0.03,-0.05,-0.07,-0.10):
            for br in (0.25,0.35,0.45):
                for vr in (1.0,1.5,2.0):
                    variants[f"adaptive_r5_weak_rev_{int(abs(drop)*100)}_br{int(br*100)}_vr{vr:g}"]=liquid&(mom5<=drop)&(cp>ind["ma200"])&breadth.le(br,axis=0)&(vr20>=vr)

    # Frontier exploration after the fixed 12-round grid. The previous design
    # repeated the same regions after round 11, allowing later cycles to add zero
    # genuinely new variants.
    if cycle > 12:
        rng=np.random.default_rng(10000+cycle)
        for j in range(48):
            lb=int(rng.choice([10,15,20,30,45,60,75,90,120,150,180,240]))
            th=float(rng.choice([-0.05,-0.02,0.0,0.02,0.04,0.06,0.08,0.12,0.18]))
            ma_name,ma=rng.choice([("ma50",ind["ma50"]),("ma100",ind["ma100"]),("ma200",ind["ma200"])])
            relq=float(rng.choice([0.60,0.70,0.80,0.90,0.95]))
            q=rel20.where(liquid).quantile(relq,axis=1)
            br=float(rng.choice([0.30,0.40,0.50,0.60,0.70]))
            vr=float(rng.choice([0.60,0.80,1.00,1.20,1.50,2.00]))
            mom=cp/cp.shift(lb)-1
            variants[f"frontier_c{cycle}_v{j}_lb{lb}_th{int(th*100)}_{ma_name}_q{int(relq*100)}_br{int(br*100)}_vr{vr:g}"]=liquid&(mom>th)&(cp>ma)&(rel20>=q)&breadth.ge(br,axis=0)&(vol20<=vr*vol63)

    # Keep the previous top families visible in the experiment record.
    for fam in focus:
        if fam in variants:
            variants[f"focus_cycle{cycle}_{fam}"]=variants[fam]

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
            # Selection only: development must be positive after costs; the
            # selection period must remain positive with >=50% wins.
            if dr>0 and sr>0 and sw>=.50:
                selected.append({"pattern":name,"horizon_days":int(h),"development_net_mean":dr,"selection_net_mean":sr,"selection_win_rate":sw,"holdout_net_mean":hr,"holdout_win_rate":hw,"holdout_observations":hn})
    out=pd.DataFrame(selected)
    if not out.empty:
        out["robust_holdout"]= (out.holdout_net_mean>0) & (out.holdout_win_rate>=.50) & (out.holdout_observations>=200)
        out=out.sort_values(["robust_holdout","holdout_net_mean","selection_net_mean"],ascending=False).head(30)
    out.to_csv(OUT/"adaptive_candidates.csv",index=False)
    signatures=[hashlib.sha256(name.encode("utf-8")).hexdigest()[:16] for name in variants]
    memory={}
    try:
        memory=json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        memory={}
    seen=set(memory.get("tested_variant_signatures",[]))
    before=len(seen)
    seen.update(signatures)
    memory.update({
        "last_cycle":cycle,
        "search_round":round_no,
        "focus_patterns":focus,
        "last_variant_count":len(variants),
        "unique_variants_tested":len(seen),
        "new_variants_this_cycle":len(seen)-before,
        "tested_variant_signatures":sorted(seen)[-50000:],
    })
    MEMORY_PATH.write_text(json.dumps(memory,indent=2)+"\n",encoding="utf-8")
    report={"status":"tested","cycle":cycle,"search_round":round_no,"focus_patterns":focus,"variants":len(variants),"new_unique_variants":len(seen)-before,"unique_variants_tested":len(seen),"candidate_count":int(len(out)),"robust_holdout_count":int(out.robust_holdout.sum()) if not out.empty else 0,"cost_hurdle":COST_HURDLE}
    (OUT/"specialist_adaptive.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not out.empty: print(out.to_string(index=False))

if __name__=="__main__":
    main()
