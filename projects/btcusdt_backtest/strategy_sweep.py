#!/usr/bin/env python3
"""Assumption-labelled BTCUSDT daily EMA50/EMA200 risk/reward sweep."""
from __future__ import annotations
import argparse, copy, csv, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import runner

def write_csv(path,rows):
 if not rows:path.write_text("",encoding="utf-8");return
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with path.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)

def validate_provenance(path):
 if not path.exists():raise ValueError("Missing data/btcusdt/DATA_SOURCE.md provenance note.")
 note=path.read_text(encoding="utf-8")
 labels=["Provider/source URL:","Date retrieved:","License/terms permitting this use:","Instrument/symbol:","Market type:","Raw timeframe:","First and last timestamps:","Timestamp timezone:","Session convention:","File checksum (SHA-256):"]
 missing=[k for k in labels if not any(line.strip().lstrip("- ").startswith(k) and line.split(":",1)[1].strip() for line in note.splitlines() if ":" in line)]
 if missing:raise ValueError("Incomplete data provenance fields: "+", ".join(missing))
 return note

def brief(x):return {"bars":x["bars"],"start":x["start"],"end":x["end"],"metrics":x["metrics"]}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--input",default="data/btcusdt/btcusdt_1m.csv")
 p.add_argument("--strategy",default="projects/btcusdt_backtest/strategies/active_strategy.json")
 p.add_argument("--output",default="artifacts/btcusdt_backtest");p.add_argument("--fee-rate-per-side",type=float);p.add_argument("--slippage-bps",type=float)
 a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 report={"project":"P-BTCUSDT-BACKTEST","status":"BLOCKED","research_only":True,"strategy_path":a.strategy,
         "objective":"Daily long-only EMA50 cross-above EMA200."}
 try:
  spec=json.loads(Path(a.strategy).read_text(encoding="utf-8"))
  if a.fee_rate_per_side is not None:spec["costs"]["fee_rate_per_side"]=a.fee_rate_per_side
  if a.slippage_bps is not None:spec["costs"]["slippage_bps_per_side"]=a.slippage_bps
  qty=runner.validate(spec);provenance=validate_provenance(Path("data/btcusdt/DATA_SOURCE.md"))
  raw=runner.load_bars(Path(a.input));tf=int(spec["timeframe_minutes"])
  download_report_path=Path("data/btcusdt/download_report.json")
  download_meta=json.loads(download_report_path.read_text(encoding="utf-8")) if download_report_path.exists() else {}
  source_interval=download_meta.get("timeframe","1m")
  if tf==1440 and source_interval=="1d":bars=raw
  elif tf==1:bars=raw
  else:bars=runner.aggregate(raw,tf)
  start_date=datetime.fromisoformat(spec.get("sweep",{}).get("analysis_start_date","2024-01-01"))
  start_date=start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
  ai=next((i for i,b in enumerate(bars) if b["dt"]>=start_date),None)
  if ai is None:raise ValueError("No candles at/after configured analysis start date.")
  count=len(bars)-ai
  if count<300:raise ValueError(f"Need at least 300 daily analysis bars after EMA warm-up; found {count}.")
  if len(bars)<201:raise ValueError("Need at least 201 daily bars for EMA200 warm-up.")
  data_hash=hashlib.sha256(Path(a.input).read_bytes()).hexdigest()
  if data_hash not in provenance:raise ValueError("DATA_SOURCE.md SHA-256 does not match input CSV.")
  if download_meta.get("csv_path") and Path(download_meta["csv_path"]).name!=Path(a.input).name:
   raise ValueError("download_report.json describes a different BTCUSDT input file.")
  source_gap_events=int(download_meta.get("missing_interval_events",download_meta.get("missing_minute_intervals",0)) or 0)
  expected_daily=(bars[-1]["dt"].date()-bars[0]["dt"].date()).days+1
  daily_bar_gap_count=max(0,expected_daily-len(bars)) if source_interval=="1d" else None
  capital=float(spec.get("starting_capital_usdt",1000));dev_end=ai+int(count*.60);val_end=ai+int(count*.80)
  grid=spec.get("sweep",{});stops=sorted({float(x) for x in grid.get("stop_loss_pct_values",[5])});rrs=sorted({float(x) for x in grid.get("target_r_multiple_values",[2])})
  if not stops or any(x<=0 or x>=100 for x in stops):raise ValueError("Stop-loss percentages must be between 0 and 100.")
  if not rrs or any(x<=0 for x in rrs):raise ValueError("Reward-to-risk multiples must be positive.")
  base_stop=float(grid.get("baseline_stop_loss_pct",5));base_rr=float(grid.get("baseline_target_r_multiple",2))
  if base_stop not in stops or base_rr not in rrs:raise ValueError("Predeclared reference profile must be in the grid.")
  rows=[];configs={};parts={}
  for sl in stops:
   for rr in rrs:
    v=copy.deepcopy(spec);v.pop("sweep",None);v["status"]="READY_FOR_BACKTEST";v["source_type"]="assumption_based_variant"
    v["exit"]={**spec["exit"],"mode":"stop_and_target","stop_points":None,"stop_loss_pct":sl,"target_points":None,"target_r_multiple":rr,"trailing_stop":None}
    runner.validate(v);profile=f"SL{sl:g}_RR{rr:g}";configs[profile]=v
    dev=runner.segment(bars,v,capital,ai,dev_end);val=runner.segment(bars,v,capital,dev_end,val_end);parts[profile]=(dev,val)
    rows.append({"profile":profile,"stop_loss_pct":sl,"reward_r":rr,"is_predeclared_reference":sl==base_stop and rr==base_rr,"development":dev["metrics"],"validation":val["metrics"]})
  base_profile=f"SL{base_stop:g}_RR{base_rr:g}";base=configs[base_profile];dev,val=parts[base_profile]
  # Only predeclared reference profile is evaluated on the holdout.
  hold=runner.segment(bars,base,capital,val_end,len(bars));full=runner.segment(bars,base,capital,ai,len(bars))
  eligible=[r for r in rows if r["validation"]["trades"]>0]
  leader=max(eligible,key=lambda r:(r["validation"]["net_return_usdt"],r["validation"]["profit_factor"] if r["validation"]["profit_factor"] is not None else -1,-r["validation"]["max_drawdown_pct"]),default=None)
  compare=[]
  for r in rows:
   d,v=r["development"],r["validation"]
   compare.append({"profile":r["profile"],"stop_loss_pct":r["stop_loss_pct"],"reward_r":r["reward_r"],"is_predeclared_reference":r["is_predeclared_reference"],
    "development_trades":d["trades"],"development_net_usdt":d["net_return_usdt"],"development_win_rate_pct":d["win_rate_pct"],"development_profit_factor":d["profit_factor"],"development_max_drawdown_pct":d["max_drawdown_pct"],
    "validation_trades":v["trades"],"validation_net_usdt":v["net_return_usdt"],"validation_win_rate_pct":v["win_rate_pct"],"validation_profit_factor":v["profit_factor"],"validation_max_drawdown_pct":v["max_drawdown_pct"]})
  write_csv(out/"variant_comparison.csv",sorted(compare,key=lambda x:(x["stop_loss_pct"],x["reward_r"])))
  write_csv(out/"monthly_reference.csv",full["monthly"]);write_csv(out/"trades_reference.csv",full["trades"])
  report_status="COMPLETED" if full["metrics"]["trades"] else "COMPLETED_NO_TRADES"
  if source_gap_events or (daily_bar_gap_count or 0):
   report_status += "_WITH_DATA_GAPS"
  report.update({"status":report_status,"strategy_id":spec["strategy_id"],"strategy_version":spec["version"],
   "strategy_sha256":hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),
   "data":{"source":"Binance public spot klines","source_timeframe":source_interval,"sha256":data_hash,"raw_rows":len(raw),"usable_daily_bars":len(bars),
    "download_status":download_meta.get("status"),"download_gap_events":source_gap_events,"download_missing_intervals_total":download_meta.get("missing_intervals_total"),
    "missing_daily_bars_in_observed_date_span":daily_bar_gap_count,"warmup_first_bar_utc":bars[0]["dt"].isoformat(),
    "analysis_start_utc":bars[ai]["dt"].isoformat(),"analysis_end_utc":bars[-1]["dt"].isoformat(),"analysis_daily_bars":count,"development_end_utc":bars[dev_end-1]["dt"].isoformat(),
    "validation_end_utc":bars[val_end-1]["dt"].isoformat(),"holdout_start_utc":bars[val_end]["dt"].isoformat(),"holdout_end_utc":bars[-1]["dt"].isoformat()},
   "assumptions":{"interpretation":"Enter on daily EMA50 cross above EMA200 close; fill at next daily open.","unspecified_by_image":["stop-loss distance","numeric reward-to-risk","position size","spot vs perpetual"],
    "drawdown_basis":"Closed-trade realized equity only; daily mark-to-market drawdown during open positions is not measured by this engine.",
    "stop_loss_pct_grid":stops,"target_r_multiple_grid":rrs,"predeclared_reference_profile":base_profile,"fixed_quantity_btc":qty,"starting_capital_usdt":capital,"market_type":spec["market_type"],
    "timeframe_minutes":tf,"fee_rate_per_side":spec["costs"]["fee_rate_per_side"],"slippage_bps_per_side":spec["costs"]["slippage_bps_per_side"],"intrabar_policy":"stop-first",
    "holdout_policy":"Only predeclared reference is run on holdout; holdout never ranks parameter settings.","monthly_return_basis":"Realized net PnL divided by starting capital and analysis duration; quantity is fixed."},
   "reference_profile_results":{"development":brief(dev),"validation":brief(val),"holdout":hold,"full_sample":full},
   "validation_leader":None if leader is None else {"profile":leader["profile"],"stop_loss_pct":leader["stop_loss_pct"],"reward_r":leader["reward_r"],"development_metrics":leader["development"],"validation_metrics":leader["validation"],"note":"Validation-only research lead; not run on holdout."},
   "variant_results":rows,"interpretation_note":"Assumption-based first test; screenshot does not define exact stop placement or numeric RR. Spot research only; no live orders or Shariah certification."})
  md=["# BTCUSDT daily EMA50/EMA200 first-test report","","Status: "+report["status"],"Analysis: "+report["data"]["analysis_start_utc"]+" to "+report["data"]["analysis_end_utc"],"Predeclared reference: "+base_profile,"",
   "| Segment | Trades | Wins | Losses | WR | Net USDT | Avg net/month USDT | PF | Max DD |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
  for name,part in [("Development",dev),("Validation",val),("Holdout",hold),("Full sample",full)]:
   m=part["metrics"];md.append("| "+name+" | "+str(m["trades"])+" | "+str(m["wins"])+" | "+str(m["losses"])+" | "+str(m["win_rate_pct"])+"% | "+str(m["net_return_usdt"])+" | "+str(m["monthly_average_net_return_usdt"])+" | "+str(m["profit_factor"])+" | "+str(m["max_drawdown_pct"])+"% |")
  md+=["","Grid: 3%, 5%, 8% stops vs 1R, 1.5R, 2R and 3R targets. Full grid covers development/validation only; holdout is calculated only for predeclared 5% / 2R.","",
   "| Profile | Dev trades | Dev net | Dev WR | Val trades | Val net | Val WR | Val PF | Val DD |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
  for r in sorted(rows,key=lambda x:(x["stop_loss_pct"],x["reward_r"])):
   d,v=r["development"],r["validation"];md.append("| "+r["profile"]+" | "+str(d["trades"])+" | "+str(d["net_return_usdt"])+" | "+str(d["win_rate_pct"])+"% | "+str(v["trades"])+" | "+str(v["net_return_usdt"])+" | "+str(v["win_rate_pct"])+"% | "+str(v["profit_factor"])+" | "+str(v["max_drawdown_pct"])+"% |")
  md+=["","Detailed report, monthly profile results and trade ledger are in latest_report.json, monthly_reference.csv and trades_reference.csv.","Costs assumed: 0.10% fee per side and 10 bps slippage per side. Spot research only, not a Shariah ruling or live-trading signal."]
  (out/"latest_report.json").write_text(json.dumps(report,indent=2,default=str)+"\n",encoding="utf-8");(out/"latest_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
  print(json.dumps({"status":report["status"],"reference_profile":base_profile,"full_sample":full["metrics"],"holdout":hold["metrics"],"validation_leader":report["validation_leader"]},indent=2,default=str));return 0
 except Exception as e:
  report["blocker"]=str(e);(out/"latest_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
  (out/"latest_report.md").write_text("# BTCUSDT first-test report\n\nStatus: BLOCKED\n\nBlocker: "+str(e)+"\n",encoding="utf-8")
  print(json.dumps(report,indent=2));return 2

if __name__=="__main__":raise SystemExit(main())
