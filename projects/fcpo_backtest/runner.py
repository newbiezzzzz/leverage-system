#!/usr/bin/env python3
"""Declarative isolated FCPO strategy backtester; standard library only."""
import argparse,csv,hashlib,json,math,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
REQ={"timestamp","open","high","low","close","volume"}; PV=25.0
SESSIONS=((630,750),(870,1080),(1260,1410))

def dtparse(s):
 d=datetime.fromisoformat(s.strip().replace("Z","+00:00"))
 if d.tzinfo is None: raise ValueError("Timestamp requires an explicit timezone offset.")
 return d.astimezone(timezone.utc)
def load_bars(path):
 if not path.exists() or not path.stat().st_size: raise ValueError("Missing/empty FCPO data: "+str(path))
 out=[]
 with path.open(newline="",encoding="utf-8-sig") as f:
  r=csv.DictReader(f)
  if not r.fieldnames or not REQ.issubset(r.fieldnames): raise ValueError("CSV needs timestamp,open,high,low,close,volume.")
  prev=None
  for ln,x in enumerate(r,2):
   try:
    d=dtparse(x["timestamp"]); v={k:float(x[k]) for k in ("open","high","low","close","volume")}
   except Exception as e: raise ValueError(f"Bad timestamp/value at CSV line {ln}: {e}") from e
   if not all(math.isfinite(z) for z in v.values()): raise ValueError(f"Non-finite value at line {ln}")
   if min(v[k] for k in ("open","high","low","close"))<=0 or v["volume"]<0: raise ValueError(f"Invalid price/volume at line {ln}")
   if v["high"]<max(v["open"],v["close"],v["low"]) or v["low"]>min(v["open"],v["close"],v["high"]): raise ValueError(f"Invalid OHLC at line {ln}")
   if prev is not None and d<=prev: raise ValueError(f"Duplicate/out-of-order timestamp at line {ln}")
   prev=d; out.append({"dt":d,**v})
 if not out: raise ValueError("CSV has header but zero data rows.")
 return out
def lm(d): return (d.hour*60+d.minute+480)%1440
def in_session(d,sessions=None):
 m=lm(d)
 if sessions:
  for s in sessions:
   a,b=s.split("-"); a=int(a[:2])*60+int(a[3:]); b=int(b[:2])*60+int(b[3:])
   if a<=m<b:return True
  return False
 return any(a<=m<b for a,b in SESSIONS)
def aggregate(rows,n):
 groups={}
 for r in rows:
  m=lm(r["dt"]); si=next((i for i,(a,b) in enumerate(SESSIONS) if a<=m<b),None)
  if si is None:continue
  groups.setdefault((r["dt"].date(),si,(m-SESSIONS[si][0])//n),[]).append(r)
 out=[]
 for _,c in sorted(groups.items(),key=lambda kv:kv[1][0]["dt"]):
  if len(c)==n:out.append({"dt":c[0]["dt"],"open":c[0]["open"],"high":max(x["high"] for x in c),"low":min(x["low"] for x in c),"close":c[-1]["close"],"volume":sum(x["volume"] for x in c)})
 return out
def sma(v,n):
 o=[None]*len(v)
 for i in range(n-1,len(v)):
  c=v[i-n+1:i+1]
  if all(x is not None for x in c):o[i]=sum(c)/n
 return o
def ema(v,n):
 o=[None]*len(v); seed=[]; a=2/(n+1)
 for i,x in enumerate(v):
  if x is None:continue
  if i==0 or o[i-1] is None:
   seed.append(x)
   if len(seed)==n:o[i]=sum(seed)/n
  else:o[i]=a*x+(1-a)*o[i-1]
 return o
def ind(bars,s):
 name=s["id"]; typ=s["type"].lower(); n=int(s.get("period",14)); src=s.get("source","close")
 if n<1:raise ValueError(f"{name}: period must be positive")
 if src not in {"open","high","low","close","volume","hl2","hlc3","ohlc4"}:raise ValueError(f"{name}: unsupported source {src}")
 v=[({"hl2":(b["high"]+b["low"])/2,"hlc3":(b["high"]+b["low"]+b["close"])/3,"ohlc4":(b["open"]+b["high"]+b["low"]+b["close"])/4}.get(src,b.get(src))) for b in bars]
 if typ in {"sma","ema"}:return {"value":sma(v,n) if typ=="sma" else ema(v,n)}
 if typ=="rsi":
  out=[None]*len(v); g=[0.]*len(v); l=[0.]*len(v)
  for i in range(1,len(v)):g[i]=max(v[i]-v[i-1],0);l[i]=max(v[i-1]-v[i],0)
  for i in range(n,len(v)):
   ag=sum(g[i-n+1:i+1])/n;al=sum(l[i-n+1:i+1])/n
   out[i]=100. if al==0 and ag>0 else (50. if al==0 else 100-100/(1+ag/al))
  return {"value":out}
 if typ=="atr":
  tr=[b["high"]-b["low"] if i==0 else max(b["high"]-b["low"],abs(b["high"]-bars[i-1]["close"]),abs(b["low"]-bars[i-1]["close"])) for i,b in enumerate(bars)]
  return {"value":sma(tr,n)}
 if typ in {"bollinger","bollinger_bands"}:
  mid=sma(v,n);up=[None]*len(v);lo=[None]*len(v);mult=float(s.get("stddev",2))
  for i,m in enumerate(mid):
   if m is not None:
    sd=math.sqrt(sum((x-m)**2 for x in v[i-n+1:i+1])/n);up[i]=m+mult*sd;lo[i]=m-mult*sd
  return {"middle":mid,"upper":up,"lower":lo}
 raise ValueError(f"Unsupported indicator type {typ} ({name}); will not approximate.")
def resolve(x,i,bars,inds):
 if isinstance(x,(int,float)):return float(x)
 if not isinstance(x,dict):raise ValueError(f"Invalid operand {x!r}")
 if "constant" in x:return float(x["constant"])
 if "price" in x:
  if x["price"] not in {"open","high","low","close","volume"}:raise ValueError("Unsupported price field")
  return bars[i][x["price"]]
 if "indicator" in x:
  n=x["indicator"];line=x.get("line","value")
  if n not in inds or line not in inds[n]:raise ValueError(f"Unknown indicator line {n}.{line}")
  return inds[n][line][i]
 raise ValueError(f"Invalid operand {x!r}")
def cond(c,i,bars,inds):
 op=c.get("operator");a=resolve(c.get("left"),i,bars,inds);b=resolve(c.get("right"),i,bars,inds)
 if a is None or b is None:return False
 if op in {"crosses_above","crosses_below"}:
  if i<1:return False
  ap=resolve(c["left"],i-1,bars,inds);bp=resolve(c["right"],i-1,bars,inds)
  if ap is None or bp is None:return False
  return ap<=bp and a>b if op=="crosses_above" else ap>=bp and a<b
 ops={"gt":lambda:a>b,"gte":lambda:a>=b,"lt":lambda:a<b,"lte":lambda:a<=b,"eq":lambda:a==b,"neq":lambda:a!=b}
 if op not in ops:raise ValueError(f"Unsupported condition operator {op}")
 return ops[op]()
def ev(g,i,bars,inds):
 if isinstance(g,list):g={"logic":"all","conditions":g}
 if not g:return False
 cs=g.get("conditions",[]);logic=g.get("logic","all")
 if logic not in {"all","any"}:raise ValueError(f"Unsupported logic {logic}")
 def one(c):return ev(c,i,bars,inds) if "conditions" in c else cond(c,i,bars,inds)
 return bool(cs) and (all(one(c) for c in cs) if logic=="all" else any(one(c) for c in cs))
def validate(s):
 for k in ("strategy_id","version","instrument","timeframe_minutes","direction","indicators","entry","exit","position_sizing","execution","costs"):
  if k not in s:raise ValueError("Strategy spec missing "+k)
 if s["instrument"]!="FCPO":raise ValueError("Engine currently supports FCPO only.")
 if int(s["timeframe_minutes"]) not in {1,5,15,30}:raise ValueError("timeframe_minutes must be 1,5,15,30.")
 if s["direction"] not in {"long_only","short_only","both"}:raise ValueError("Invalid direction.")
 if s.get("status") in {"NEEDS_CLARIFICATION","NEEDS_RULE_EXTRACTION"}:raise ValueError("Strategy is not approved for execution; resolve rule extraction/clarification first.")
 if not s["entry"].get("conditions"):raise ValueError("Entry conditions are empty; do not backtest an unconfigured template.")
 if s["exit"].get("trailing_stop") is not None:raise ValueError("Trailing stop is not implemented yet; remove it or use only after an explicit supported rule implementation.")
 sz=s["position_sizing"]
 if sz.get("mode") not in {"one_contract","fixed_contracts"}:raise ValueError("Only explicit integer contract sizing is supported.")
 q=sz.get("contracts",1)
 if int(q)<1 or float(q)!=int(q):raise ValueError("FCPO contracts must be a positive integer.")
 if s["execution"].get("allow_lookahead",False):raise ValueError("Look-ahead prohibited.")
 if s["execution"].get("signal_timing","bar_close")!="bar_close" or s["execution"].get("entry_timing","next_bar_open")!="next_bar_open":raise ValueError("Only bar-close signals and next-bar-open entries are supported.")
 c=s["costs"]
 if c.get("fee_per_side_rm_per_contract") is None or c.get("slippage_points_per_side") is None:raise ValueError("Explicit fee and slippage assumptions are required.")
 if float(c["fee_per_side_rm_per_contract"])<0 or float(c["slippage_points_per_side"])<0:raise ValueError("Fees/slippage cannot be negative.")
 ex=s["exit"];mode=ex.get("mode")
 if mode not in {"stop_and_target","fixed_stop_target","opposite_signal","time_exit","stop_target_or_signal","stop_target_or_time"}:raise ValueError("Unsupported exit mode "+str(mode))
 if mode in {"stop_and_target","fixed_stop_target","stop_target_or_signal","stop_target_or_time"} and (float(ex.get("stop_points") or 0)<=0 or (float(ex.get("target_points") or 0)<=0 and float(ex.get("target_r_multiple") or 0)<=0)):raise ValueError("Stop and target points/R multiple must be positive.")
 if mode in {"time_exit","stop_target_or_time"} and int(ex.get("time_exit_bars") or 0)<1:raise ValueError("time_exit_bars must be positive.")
 ids=[x.get("id") for x in s["indicators"]]
 if None in ids or len(ids)!=len(set(ids)):raise ValueError("Indicator ids must be present and unique.")
 return int(q)
def calc_inds(bars,s):return {x["id"]:ind(bars,x) for x in s["indicators"]}
def backtest(bars,s,capital=1000):
 q=validate(s);inds=calc_inds(bars,s);cost=s["costs"];fee=float(cost["fee_per_side_rm_per_contract"])*q;slip=float(cost["slippage_points_per_side"])
 ex=s["exit"];mode=ex["mode"];sp=float(ex.get("stop_points") or 0);tp=float(ex.get("target_points") or sp*float(ex.get("target_r_multiple") or 0));trades=[];pos=None
 for i in range(len(bars)-1):
  b=bars[i]
  if pos:
   stop_hit=(b["low"]<=pos["stop"] if pos["side"]=="long" else b["high"]>=pos["stop"]) if pos["stop"] is not None else False
   target_hit=(b["high"]>=pos["target"] if pos["side"]=="long" else b["low"]<=pos["target"]) if pos["target"] is not None else False
   xp=None;reason=None
   if stop_hit or target_hit:xp=pos["stop"] if stop_hit else pos["target"];reason="stop" if stop_hit else "target"
   if xp is None and mode in {"opposite_signal","stop_target_or_signal"}:
    opposite=ev(s.get("short_entry",{}),i,bars,inds) if pos["side"]=="long" else ev(s["entry"],i,bars,inds)
    if opposite:xp=b["close"];reason="opposite_signal"
   if xp is None and mode in {"time_exit","stop_target_or_time"} and i-pos["entry_i"]+1>=int(ex["time_exit_bars"]):xp=b["close"];reason="time_exit"
   if xp is not None:
    sign=1 if pos["side"]=="long" else -1;gross=(xp-pos["entry"])*sign*PV*q;slip_rm=2*slip*PV*q;fees=2*fee
    trades.append({"entry_time":pos["time"].isoformat(),"exit_time":b["dt"].isoformat(),"side":pos["side"],"contracts":q,"entry_price":round(pos["entry"],4),"exit_price":round(xp,4),"gross_rm":round(gross,2),"fees_rm":round(fees,2),"slippage_rm":round(slip_rm,2),"costs_rm":round(fees+slip_rm,2),"net_rm":round(gross-fees-slip_rm,2),"exit_reason":reason,"bars_held":i-pos["entry_i"]+1});pos=None
  if pos is None and in_session(b["dt"],s.get("sessions")):
   long=ev(s["entry"],i,bars,inds) if s["direction"] in {"long_only","both"} else False
   short=ev(s.get("short_entry",{}),i,bars,inds) if s["direction"] in {"short_only","both"} else False
   if long and short:raise ValueError("Both long and short rules fired simultaneously; clarify priority.")
   if long or short:
    side="long" if long else "short";entry=bars[i+1]["open"]
    pos={"side":side,"entry":entry,"time":bars[i+1]["dt"],"entry_i":i+1,"stop":(entry-sp if side=="long" else entry+sp) if sp else None,"target":(entry+tp if side=="long" else entry-tp) if tp else None}
 if pos:
  b=bars[-1];sign=1 if pos["side"]=="long" else -1;gross=(b["close"]-pos["entry"])*sign*PV*q;slip_rm=2*slip*PV*q;fees=2*fee
  trades.append({"entry_time":pos["time"].isoformat(),"exit_time":b["dt"].isoformat(),"side":pos["side"],"contracts":q,"entry_price":round(pos["entry"],4),"exit_price":b["close"],"gross_rm":round(gross,2),"fees_rm":round(fees,2),"slippage_rm":round(slip_rm,2),"costs_rm":round(fees+slip_rm,2),"net_rm":round(gross-fees-slip_rm,2),"exit_reason":"end_of_data","bars_held":len(bars)-pos["entry_i"]})
 return trades
def summary(ts,capital=1000):
 n=[t["net_rm"] for t in ts];w=[x for x in n if x>0];l=[x for x in n if x<0];eq=peak=capital;dd=ddpct=0;streak=stmax=0
 for x in n:
  eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq);ddpct=max(ddpct,(peak-eq)/peak*100 if peak>0 else 0);streak=streak+1 if x<0 else 0;stmax=max(stmax,streak)
 months=max((datetime.fromisoformat(ts[-1]["exit_time"])-datetime.fromisoformat(ts[0]["entry_time"])).total_seconds()/(86400*30.4375),1/30.4375) if ts else 0
 net=sum(n)
 return {"trades":len(ts),"wins":len(w),"losses":len(l),"win_rate_pct":round(len(w)/len(ts)*100,2) if ts else None,"gross_return_rm":round(sum(t["gross_rm"] for t in ts),2),"fees_rm":round(sum(t["fees_rm"] for t in ts),2),"slippage_rm":round(sum(t["slippage_rm"] for t in ts),2),"total_costs_rm":round(sum(t["costs_rm"] for t in ts),2),"net_return_rm":round(net,2),"monthly_average_net_return_rm":round(net/months,2) if months else None,"monthly_average_net_return_pct":round(net/capital/months*100,2) if months and capital else None,"average_winner_rm":round(sum(w)/len(w),2) if w else 0,"average_loser_rm":round(sum(l)/len(l),2) if l else 0,"profit_factor":round(sum(w)/abs(sum(l)),3) if l else (None if w else 0),"expectancy_rm_per_trade":round(net/len(ts),2) if ts else None,"max_drawdown_rm":round(dd,2),"max_drawdown_pct":round(ddpct,2),"largest_loss_rm":round(min(n),2) if n else None,"max_consecutive_losses":stmax}
def monthly(ts,bars=None):
 d=defaultdict(list)
 for t in ts:d[t["entry_time"][:7]].append(t)
 months=set(d)
 if bars:
  cur=bars[0]["dt"].year*12+bars[0]["dt"].month-1;last=bars[-1]["dt"].year*12+bars[-1]["dt"].month-1
  for z in range(cur,last+1):months.add(f"{z//12:04d}-{z%12+1:02d}")
 out=[]
 for m in sorted(months):
  items=d.get(m,[]);n=[t["net_rm"] for t in items];out.append({"month":m,"trades":len(items),"wins":sum(x>0 for x in n),"losses":sum(x<0 for x in n),"win_rate_pct":round(sum(x>0 for x in n)/len(n)*100,2) if n else None,"gross_rm":round(sum(t["gross_rm"] for t in items),2),"fees_rm":round(sum(t["fees_rm"] for t in items),2),"slippage_rm":round(sum(t["slippage_rm"] for t in items),2),"net_rm":round(sum(n),2)})
 return out
def segment(bars,s,capital):
 t=backtest(bars,s,capital);m=summary(t,capital)
 months=max((bars[-1]["dt"]-bars[0]["dt"]).total_seconds()/(86400*30.4375),1/30.4375) if len(bars)>1 else 0
 net=m["net_return_rm"];m["monthly_average_net_return_rm"]=round(net/months,2) if months else None;m["monthly_average_net_return_pct"]=round(net/capital/months*100,2) if months and capital else None
 return {"bars":len(bars),"start":bars[0]["dt"].isoformat() if bars else None,"end":bars[-1]["dt"].isoformat() if bars else None,"metrics":m,"monthly":monthly(t,bars),"trades":t}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--input",default="data/fcpo/fcpo_1m.csv");p.add_argument("--strategy",default="projects/fcpo_backtest/strategies/strategy_template.json");p.add_argument("--output",default="artifacts/fcpo_backtest");p.add_argument("--fee-per-side-rm",type=float);p.add_argument("--slippage-points",type=float);a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True);r={"project":"P-FCPO-BACKTEST","status":"BLOCKED","research_only":True,"strategy_path":a.strategy}
 try:
  s=json.loads(Path(a.strategy).read_text(encoding="utf-8"))
  if a.fee_per_side_rm is not None:s["costs"]["fee_per_side_rm_per_contract"]=a.fee_per_side_rm
  if a.slippage_points is not None:s["costs"]["slippage_points_per_side"]=a.slippage_points
  q=validate(s);raw=load_bars(Path(a.input));note=Path("data/fcpo/DATA_SOURCE.md")
  if not note.exists():raise ValueError("Missing data/fcpo/DATA_SOURCE.md provenance note.")
  provenance=note.read_text(encoding="utf-8")
  required=["Provider/source URL:","Date retrieved:","License/terms permitting this use:","Instrument/symbol:","Contract months included:","Raw timeframe:","First and last timestamps:","Timestamp timezone:","Session convention:","File checksum (SHA-256):"]
  missing=[line for line in required if not any(x.strip() and not x.strip().startswith("#") and x.strip().lstrip("- ").startswith(line) and x.split(":",1)[1].strip() for x in provenance.splitlines())]
  if missing:raise ValueError("Incomplete data provenance fields: "+", ".join(missing))
  tf=int(s["timeframe_minutes"]);bars=raw if tf==1 else aggregate(raw,tf)
  if len(bars)<100:raise ValueError(f"Only {len(bars)} usable {tf}m bars; at least 100 required for a diagnostic run.")
  capital=float(s.get("starting_capital_rm",1000))
  if capital<=0:raise ValueError("starting_capital_rm must be positive.")
  risk=float(s["exit"].get("stop_points") or 0)*PV*q
  n=len(bars);a0=int(n*.6);b0=int(n*.8)
  r.update({"status":"COMPLETED","strategy_id":s["strategy_id"],"strategy_version":s["version"],"strategy_sha256":hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest(),"timeframe_minutes":tf,"instrument":"FCPO","contract_count":q,"starting_capital_rm":capital,"contract_stop_risk_rm":risk or None,"contract_stop_risk_pct_of_capital":round(risk/capital*100,2) if risk else None,"contract_feasibility":"RISK_EXCEEDS_CAPITAL" if risk>=capital else "BROKER_MARGIN_CHECK_REQUIRED","data":{"raw_rows":len(raw),"usable_bars":n,"first_bar":bars[0]["dt"].isoformat(),"last_bar":bars[-1]["dt"].isoformat()},"results":{"full_sample":segment(bars,s,capital),"development":segment(bars[:a0],s,capital) if a0>=100 else {"status":"INSUFFICIENT_DATA","bars":a0},"validation":segment(bars[a0:b0],s,capital) if b0-a0>=100 else {"status":"INSUFFICIENT_DATA","bars":b0-a0},"holdout":segment(bars[b0:],s,capital) if n-b0>=100 else {"status":"INSUFFICIENT_DATA","bars":n-b0}},"validation_note":"Chronological 60/20/20 split; do not tune on holdout."})
 except Exception as e:r["blocker"]=str(e)
 (o/"latest_report.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
 (o/"latest_report.md").write_text("# FCPO user-strategy backtest\n\nStatus: "+r["status"]+"\n\n"+("Blocker: "+r["blocker"]+"\n\n" if "blocker" in r else "")+"Research only; no broker integration or live orders. Full ledger/monthly output is in latest_report.json.\n",encoding="utf-8")
 print(json.dumps({k:v for k,v in r.items() if k!="results"},indent=2));return 2 if r["status"]=="BLOCKED" else 0
if __name__=="__main__":sys.exit(main())
