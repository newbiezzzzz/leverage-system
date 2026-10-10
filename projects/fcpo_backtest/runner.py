#!/usr/bin/env python3
"""Isolated FCPO OHLCV validation and baseline research runner; standard library only."""
from __future__ import annotations
import argparse, csv, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {"timestamp", "open", "high", "low", "close", "volume"}
SESSIONS = ((630, 750), (870, 1080), (1260, 1410))

def parse_time(raw):
    dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp has no timezone offset; normalize Malaysia time first.")
    return dt.astimezone(timezone.utc)

def in_session(dt):
    minute = (dt.hour * 60 + dt.minute + 480) % 1440
    return any(a <= minute < b for a,b in SESSIONS)

def load_bars(path):
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"Missing/empty input file: {path}")
    rows=[]
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
            raise ValueError("CSV requires timestamp,open,high,low,close,volume columns.")
        previous=None; seen=set()
        for line,raw in enumerate(reader,start=2):
            dt=parse_time(raw["timestamp"])
            v={k:float(raw[k]) for k in ("open","high","low","close","volume")}
            if not all(math.isfinite(x) for x in v.values()): raise ValueError(f"Non-finite value at line {line}")
            if min(v[k] for k in ("open","high","low","close"))<=0 or v["volume"]<0: raise ValueError(f"Invalid price/volume at line {line}")
            if v["high"]<max(v["open"],v["close"],v["low"]) or v["low"]>min(v["open"],v["close"],v["high"]): raise ValueError(f"Invalid OHLC at line {line}")
            if dt in seen or (previous is not None and dt<=previous): raise ValueError(f"Duplicate/out-of-order timestamp at line {line}")
            seen.add(dt); previous=dt; rows.append({"dt":dt,**v})
    if not rows: raise ValueError("CSV has a header but zero data rows.")
    return rows

def aggregate(rows, minutes):
    groups={}
    for r in rows:
        dt=r["dt"]
        local_minute=(dt.hour*60+dt.minute+480)%1440
        session=next((i for i,(a,b) in enumerate(SESSIONS) if a<=local_minute<b),None)
        if session is None: continue
        start=SESSIONS[session][0]
        key=(dt.date(),session,(local_minute-start)//minutes)
        groups.setdefault(key,[]).append(r)
    out=[]
    for _,chunk in sorted(groups.items(),key=lambda kv:kv[1][0]["dt"]):
        # Require full minute coverage; missing minutes are excluded, never filled synthetically.
        if len(chunk)!=minutes: continue
        out.append({"dt":chunk[0]["dt"],"open":chunk[0]["open"],"high":max(x["high"] for x in chunk),
                    "low":min(x["low"] for x in chunk),"close":chunk[-1]["close"],"volume":sum(x["volume"] for x in chunk)})
    return out

def sma(values,n,i):
    return None if i+1<n else sum(values[i-n+1:i+1])/n

def signal(bars,family,i):
    closes=[b["close"] for b in bars[:i+1]]
    if family=="trend_momentum":
        fast,slow=sma(closes,8,i),sma(closes,21,i)
        pf,ps=(sma(closes,8,i-1),sma(closes,21,i-1)) if i else (None,None)
        return 1 if None not in (fast,slow,pf,ps) and pf<=ps and fast>slow else 0
    if family=="mean_reversion":
        mean=sma(closes,20,i)
        if mean is None or i<20:return 0
        dev=math.sqrt(sum((x-mean)**2 for x in closes[i-19:i+1])/20)
        return 1 if dev>0 and bars[i]["close"]<mean-1.5*dev else 0
    if family=="volatility_breakout":
        if i<20:return 0
        return 1 if bars[i]["close"]>max(b["high"] for b in bars[i-20:i]) else 0
    return 0

def backtest(bars,family,fee,slippage,stop_points,target_r):
    trades=[]; position=None
    for i in range(21,len(bars)-1):
        bar=bars[i]
        if position:
            stop=position["entry"]-stop_points
            target=position["entry"]+stop_points*target_r
            exit_price=stop if bar["low"]<=stop else (target if bar["high"]>=target else None)
            if exit_price is not None:
                gross=(exit_price-position["entry"])*25
                costs=2*fee+2*slippage*25
                trades.append({"entry_time":position["time"].isoformat(),"exit_time":bar["dt"].isoformat(),
                    "gross_rm":round(gross,2),"costs_rm":round(costs,2),"net_rm":round(gross-costs,2),
                    "exit_reason":"stop" if exit_price==stop else "target"})
                position=None
        if position is None and signal(bars,family,i):
            position={"entry":bars[i+1]["open"]+slippage,"time":bars[i+1]["dt"]}
    if position:
        bar=bars[-1]; gross=(bar["close"]-position["entry"])*25; costs=2*fee+2*slippage*25
        trades.append({"entry_time":position["time"].isoformat(),"exit_time":bar["dt"].isoformat(),
            "gross_rm":round(gross,2),"costs_rm":round(costs,2),"net_rm":round(gross-costs,2),"exit_reason":"end_of_data"})
    return trades

def summarize(trades,capital):
    if not trades:
        return {"trades":0,"wins":0,"losses":0,"win_rate_pct":None,"gross_return_rm":0,"net_return_rm":0,
                "monthly_net_return_pct":None,"average_winner_rm":None,"average_loser_rm":None,
                "profit_factor":None,"expectancy_rm_per_trade":None,"max_drawdown_pct":None,"total_costs_rm":0}
    nets=[t["net_rm"] for t in trades]; gross=[t["gross_rm"] for t in trades]
    wins=[x for x in nets if x>0]; losses=[x for x in nets if x<0]
    equity=capital; peak=capital; maxdd=0
    for p in nets:
        equity+=p; peak=max(peak,equity)
        if peak:maxdd=max(maxdd,(peak-equity)/peak*100)
    start=datetime.fromisoformat(trades[0]["entry_time"]); end=datetime.fromisoformat(trades[-1]["exit_time"])
    months=max((end-start).total_seconds()/(86400*30.4375),1/30.4375)
    return {"trades":len(trades),"wins":len(wins),"losses":len(losses),"win_rate_pct":round(len(wins)/len(trades)*100,2),
        "gross_return_rm":round(sum(gross),2),"net_return_rm":round(sum(nets),2),
        "monthly_net_return_pct":round(sum(nets)/capital/months*100,2),
        "average_winner_rm":round(sum(wins)/len(wins),2) if wins else 0,
        "average_loser_rm":round(sum(losses)/len(losses),2) if losses else 0,
        "profit_factor":round(sum(wins)/abs(sum(losses)),3) if losses else (None if wins else 0),
        "expectancy_rm_per_trade":round(sum(nets)/len(nets),2),"max_drawdown_pct":round(maxdd,2),
        "total_costs_rm":round(sum(t["costs_rm"] for t in trades),2)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="data/fcpo/fcpo_1m.csv")
    ap.add_argument("--output",default="artifacts/fcpo_backtest")
    ap.add_argument("--fee-per-side-rm",type=float,default=None)
    ap.add_argument("--slippage-points",type=float,default=None)
    ap.add_argument("--stop-points",type=float,default=10)
    ap.add_argument("--target-r",type=float,default=1.5)
    args=ap.parse_args(); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    report={"project":"P-FCPO-BACKTEST","status":"BLOCKED","research_only":True,"results":[],
        "assumptions":{"starting_capital_rm":1000,"contract_size_metric_tons":25,"tick_value_rm_per_point":25,
                       "stop_points":args.stop_points,"target_r":args.target_r}}
    try:
        if args.fee_per_side_rm is None or args.slippage_points is None:
            raise ValueError("Provide documented --fee-per-side-rm and --slippage-points before testing.")
        if args.fee_per_side_rm<0 or args.slippage_points<0 or args.stop_points<=0 or args.target_r<=0:
            raise ValueError("Costs/slippage must be non-negative and stop/target positive.")
        rows=load_bars(Path(args.input))
        report["data"]={"rows_1m":len(rows),"first_utc":rows[0]["dt"].isoformat(),"last_utc":rows[-1]["dt"].isoformat(),
                        "source_note_required":Path("data/fcpo/DATA_SOURCE.md").exists()}
        if not report["data"]["source_note_required"]: raise ValueError("Missing data/fcpo/DATA_SOURCE.md provenance note.")
        for tf in (5,15,30):
            bars=aggregate(rows,tf)
            if len(bars)<100:
                report["results"].append({"timeframe_minutes":tf,"bars":len(bars),"status":"INSUFFICIENT_DATA"});continue
            for family in ("trend_momentum","mean_reversion","volatility_breakout"):
                trades=backtest(bars,family,args.fee_per_side_rm,args.slippage_points,args.stop_points,args.target_r)
                report["results"].append({"timeframe_minutes":tf,"strategy_family":family,"bars":len(bars),
                                          "metrics":summarize(trades,1000),"trades_detail":trades})
        report["status"]="COMPLETED" if any(x.get("metrics",{}).get("trades",0)>0 for x in report["results"]) else "COMPLETED_NO_TRADES"
    except Exception as exc: report["blocker"]=str(exc)
    (out/"latest_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (out/"latest_report.md").write_text("# FCPO backtest report\n\n**Status:** "+report["status"]+"\n\n"+
        ("**Blocker:** "+report["blocker"]+"\n\n" if "blocker" in report else "")+
        "Research-only; no live orders. See latest_report.json for machine-readable details.\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2))
    return 2 if report["status"]=="BLOCKED" else 0
if __name__=="__main__":sys.exit(main())
