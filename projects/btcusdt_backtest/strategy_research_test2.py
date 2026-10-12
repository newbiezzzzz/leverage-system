#!/usr/bin/env python3
"""BTCUSDT Test #2: volatility breakout and mean reversion on 15m, 1h and 4h."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner

TIMEFRAMES = {15: "15m", 60: "1h", 240: "4h"}
CAPITAL = 1000.0
QTY = 0.005
FEE = 0.001
SLIP_BPS = 10.0
SLIP = SLIP_BPS / 10000.0
ATR_PERIOD = 14
ATR_BASE_PERIOD = 20
FAST_EMA = 50
SLOW_EMA = 200
BB_PERIOD = 20
BB_STD = 2.0
MEAN_MAX_HOURS = 72


def sma_values(values, period):
    out = [None] * len(values)
    for i in range(period - 1, len(values)):
        chunk = values[i-period+1:i+1]
        if all(x is not None and math.isfinite(float(x)) for x in chunk):
            out[i] = sum(chunk) / period
    return out


def donchian_upper(bars, period):
    """Previous-period high, with the current candle excluded to avoid lookahead."""
    out = [None] * len(bars)
    highs = [float(b["high"]) for b in bars]
    for i in range(period, len(bars)):
        out[i] = max(highs[i-period:i])
    return out


def build_panel(bars):
    close = [b["close"] for b in bars]
    vol = [b["volume"] for b in bars]
    atr = runner.ind(bars, {"id":"atr14", "type":"atr", "period":ATR_PERIOD})["value"]
    bb = runner.ind(bars, {"id":"bb20", "type":"bollinger", "period":BB_PERIOD, "source":"close", "stddev":BB_STD})
    return {
        "ema_fast": runner.ema(close, FAST_EMA),
        "ema_slow": runner.ema(close, SLOW_EMA),
        "atr": atr, "atr_base": sma_values(atr, ATR_BASE_PERIOD),
        "vol_base": sma_values(vol, 20),
        "rsi": runner.ind(bars, {"id":"rsi14", "type":"rsi", "period":14})["value"],
        "bb_mid": bb["middle"], "bb_upper": bb["upper"], "bb_lower": bb["lower"],
        "donchian20": donchian_upper(bars, 20),
        "donchian55": donchian_upper(bars, 55),
    }


def breakout_signal(bars, p, i, lookback):
    if i < 1:
        return False
    upper = p["donchian" + str(lookback)]
    vals = (upper[i], upper[i-1], p["ema_fast"][i], p["ema_slow"][i],
            p["atr"][i], p["atr_base"][i], p["vol_base"][i])
    if any(x is None for x in vals):
        return False
    return (
        bars[i-1]["close"] <= upper[i-1] and bars[i]["close"] > upper[i]
        and bars[i]["close"] > p["ema_fast"][i] > p["ema_slow"][i]
        and p["atr"][i] > p["atr_base"][i]
        and bars[i]["volume"] > p["vol_base"][i]
    )


def mean_reversion_signal(bars, p, i, rsi_threshold):
    if i < 1:
        return False
    vals = (p["bb_lower"][i], p["bb_lower"][i-1], p["rsi"][i],
            p["ema_fast"][i], p["ema_slow"][i], p["atr"][i], p["atr_base"][i])
    if any(x is None for x in vals):
        return False
    return (
        bars[i-1]["close"] >= p["bb_lower"][i-1]
        and bars[i]["close"] < p["bb_lower"][i]
        and p["rsi"][i] < rsi_threshold
        and p["ema_fast"][i] > p["ema_slow"][i]
        and p["atr"][i] <= 1.5 * p["atr_base"][i]
    )


def mean_exit_signal(bars, p, i):
    if i < 1 or p["bb_mid"][i] is None or p["bb_mid"][i-1] is None:
        return False
    return bars[i-1]["close"] <= p["bb_mid"][i-1] and bars[i]["close"] > p["bb_mid"][i]


def close_trade(pos, exit_price, exit_time, reason, trades):
    gross = (exit_price - pos["entry_price"]) * QTY
    fees = (pos["entry_price"] + exit_price) * QTY * FEE
    slippage = (pos["entry_price"] + exit_price) * QTY * SLIP
    trades.append({
        "entry_time":pos["entry_time"].isoformat(), "exit_time":exit_time.isoformat(),
        "side":"long", "quantity_btc":QTY, "entry_price":round(pos["entry_price"],4),
        "exit_price":round(exit_price,4), "gross_usdt":round(gross,6),
        "fees_usdt":round(fees,6), "slippage_usdt":round(slippage,6),
        "total_costs_usdt":round(fees+slippage,6), "net_usdt":round(gross-fees-slippage,6),
        "exit_reason":reason, "bars_held":max(1,pos["bars_held"]),
        "stop_price":round(pos["stop_price"],4),
        "target_price":None if pos["target_price"] is None else round(pos["target_price"],4),
    })
    return gross - fees - slippage


def summarize(trades, bars, dd, dd_pct, adverse_dd, adverse_pct):
    n = [float(t["net_usdt"]) for t in trades]
    wins = [x for x in n if x > 0]
    losses = [x for x in n if x < 0]
    months = max((bars[-1]["dt"]-bars[0]["dt"]).total_seconds()/(86400*30.4375), 1/30.4375) if len(bars)>1 else 1/30.4375
    pf = sum(wins)/abs(sum(losses)) if losses else (None if wins else 0.0)
    streak = max_streak = 0
    for x in n:
        streak = streak + 1 if x < 0 else 0
        max_streak = max(max_streak, streak)
    net = sum(n)
    return {
        "trades":len(trades), "wins":len(wins), "losses":len(losses),
        "win_rate_pct":round(len(wins)/len(trades)*100,2) if trades else None,
        "gross_return_usdt":round(sum(t["gross_usdt"] for t in trades),2),
        "fees_usdt":round(sum(t["fees_usdt"] for t in trades),2),
        "slippage_usdt":round(sum(t["slippage_usdt"] for t in trades),2),
        "total_costs_usdt":round(sum(t["total_costs_usdt"] for t in trades),2),
        "net_return_usdt":round(net,2),
        "monthly_average_net_return_usdt":round(net/months,2),
        "monthly_average_net_return_pct":round(net/CAPITAL/months*100,3),
        "trades_per_month":round(len(trades)/months,2),
        "average_winner_usdt":round(sum(wins)/len(wins),2) if wins else 0.0,
        "average_loser_usdt":round(sum(losses)/len(losses),2) if losses else 0.0,
        "profit_factor":None if pf is None else round(pf,3),
        "expectancy_usdt_per_trade":round(net/len(trades),3) if trades else None,
        "largest_loss_usdt":round(min(losses),2) if losses else None,
        "max_consecutive_losses":max_streak,
        "max_drawdown_usdt_mark_to_market":round(dd,2),
        "max_drawdown_pct_mark_to_market":round(dd_pct,2),
        "max_adverse_intrabar_drawdown_usdt":round(adverse_dd,2),
        "max_adverse_intrabar_drawdown_pct":round(adverse_pct,2),
    }


def is_qualified(validation, holdout):
    return (
        validation["trades"] >= 20 and holdout["trades"] >= 10
        and validation["net_return_usdt"] > 0 and holdout["net_return_usdt"] > 0
        and validation["profit_factor"] is not None and validation["profit_factor"] > 1
        and holdout["profit_factor"] is not None and holdout["profit_factor"] > 1
        and validation["max_drawdown_pct_mark_to_market"] <= 10
        and holdout["max_drawdown_pct_mark_to_market"] <= 10
    )


def simulate(bars, panel, family, config, start, end, timeframe_minutes):
    trades = []
    realized = 0.0
    pos = pending_entry = pending_exit = None
    peak_equity = CAPITAL
    max_dd = max_dd_pct = adverse_dd = adverse_pct = 0.0
    max_hold = max(1, int(MEAN_MAX_HOURS * 60 / timeframe_minutes))

    def mark(equity, adverse=False):
        nonlocal peak_equity, max_dd, max_dd_pct, adverse_dd, adverse_pct
        peak_equity = max(peak_equity, equity)
        dd = max(0.0, peak_equity-equity)
        pct = dd/peak_equity*100 if peak_equity>0 else 0.0
        max_dd = max(max_dd, dd)
        max_dd_pct = max(max_dd_pct, pct)
        if adverse:
            adverse_dd = max(adverse_dd, dd)
            adverse_pct = max(adverse_pct, pct)

    for i in range(start, end):
        bar = bars[i]
        closed_this_bar = False

        # Signal-based exits are executed at the next candle open.
        if pos is not None and pending_exit is not None:
            realized += close_trade(pos, bar["open"], bar["dt"], pending_exit, trades)
            pos = pending_exit = None
            closed_this_bar = True

        # Signal entries use the next candle's open and ATR known at signal close.
        if pos is None and pending_entry is not None:
            risk = float(pending_entry["atr"]) * float(pending_entry["stop_atr"])
            if risk > 0:
                entry = float(bar["open"])
                target = entry + risk * float(pending_entry.get("target_r",0) or 0) if pending_entry.get("target_r") else None
                pos = {"entry_price":entry, "entry_time":bar["dt"], "entry_index":i,
                       "stop_price":entry-risk, "target_price":target, "bars_held":0}
            pending_entry = None

        if pos is not None:
            pos["bars_held"] += 1
            stop, target = pos["stop_price"], pos["target_price"]
            gap_stop = bar["open"] <= stop
            stop_hit = gap_stop or bar["low"] <= stop
            target_hit = target is not None and bar["high"] >= target
            if stop_hit:
                fill = min(float(bar["open"]),stop) if gap_stop else stop
                realized += close_trade(pos,fill,bar["dt"],"stop",trades)
                pos = pending_exit = None
                closed_this_bar = True
            elif target_hit:
                realized += close_trade(pos,target,bar["dt"],"target",trades)
                pos = pending_exit = None
                closed_this_bar = True
            else:
                # Conservative OHLC drawdown approximation when no bracket triggered.
                rate = FEE + SLIP
                high_eq = CAPITAL + realized + (bar["high"]-pos["entry_price"])*QTY
                high_eq -= (pos["entry_price"]+bar["high"])*QTY*rate
                mark(high_eq)
                low_eq = CAPITAL + realized + (bar["low"]-pos["entry_price"])*QTY
                low_eq -= (pos["entry_price"]+bar["low"])*QTY*rate
                mark(low_eq,True)
                close_eq = CAPITAL + realized + (bar["close"]-pos["entry_price"])*QTY
                close_eq -= (pos["entry_price"]+bar["close"])*QTY*rate
                mark(close_eq)
                if family == "mean_reversion" and mean_exit_signal(bars,panel,i):
                    pending_exit = "revert_to_bollinger_mid"
                elif family == "mean_reversion" and pos["bars_held"] >= max_hold:
                    pending_exit = "maximum_holding_time"

        if pos is None:
            mark(CAPITAL + realized)
        if pos is None and pending_entry is None and not closed_this_bar and i < end-1:
            signal = breakout_signal(bars,panel,i,config["lookback"]) if family=="breakout" else mean_reversion_signal(bars,panel,i,config["rsi_threshold"])
            atr = panel["atr"][i]
            if signal and atr is not None and atr > 0:
                pending_entry = {"atr":atr,"stop_atr":config["stop_atr"],"target_r":config.get("target_r")}

    if pos is not None:
        last = bars[end-1]
        realized += close_trade(pos,last["close"],last["dt"],"segment_end",trades)
        mark(CAPITAL + realized)
    return {"bars":end-start,"start":bars[start]["dt"].isoformat(),"end":bars[end-1]["dt"].isoformat(),
            "metrics":summarize(trades,bars[start:end],max_dd,max_dd_pct,adverse_dd,adverse_pct),"trades":trades}


def monthly_summary(trades, first_dt, last_dt):
    grouped = defaultdict(list)
    first = first_dt.year*12 + first_dt.month-1
    last = last_dt.year*12 + last_dt.month-1
    for k in range(first,last+1):
        grouped[f"{k//12:04d}-{k%12+1:02d}"] = []
    for t in trades:
        grouped.setdefault(t["exit_time"][:7],[]).append(t)
    out=[]
    for month in sorted(grouped):
        vals=grouped[month]; n=[float(t["net_usdt"]) for t in vals]
        out.append({"month":month,"trades":len(vals),"wins":sum(x>0 for x in n),"losses":sum(x<0 for x in n),
            "win_rate_pct":round(sum(x>0 for x in n)/len(n)*100,2) if n else None,
            "gross_usdt":round(sum(float(t["gross_usdt"]) for t in vals),2),
            "fees_usdt":round(sum(float(t["fees_usdt"]) for t in vals),2),
            "slippage_usdt":round(sum(float(t["slippage_usdt"]) for t in vals),2),
            "net_usdt":round(sum(n),2)})
    return out


def write_csv(path, rows):
    if not rows:
        path.write_text("",encoding="utf-8")
        return
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader();w.writerows(rows)


def run():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",default="data/btcusdt/btcusdt_1m.csv")
    ap.add_argument("--config",default="projects/btcusdt_backtest/strategies/strategy_test2.json")
    ap.add_argument("--output",default="artifacts/btcusdt_test2")
    args=ap.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report={"test_id":"BTCUSDT-TEST-002","status":"BLOCKED","live_orders":False,
            "purpose":"Compare volatility breakout and mean reversion on BTCUSDT spot."}
    try:
        cfg=json.loads(Path(args.config).read_text(encoding="utf-8"))
        input_path=Path(args.input);raw=runner.load_bars(input_path)
        digest=hashlib.sha256(input_path.read_bytes()).hexdigest()
        mp=Path("data/btcusdt/download_report.json"); np=Path("data/btcusdt/DATA_SOURCE.md")
        if not mp.exists() or not np.exists():raise ValueError("Missing source metadata/provenance.")
        meta=json.loads(mp.read_text(encoding="utf-8"));note=np.read_text(encoding="utf-8")
        if meta.get("timeframe")!="1m":raise ValueError("Test 2 requires 1-minute source candles.")
        if meta.get("sha256")!=digest or digest not in note:raise ValueError("Input checksum does not match provenance.")
        if meta.get("market_type")!="spot" or meta.get("symbol")!="BTCUSDT":raise ValueError("BTCUSDT spot data required.")
        if len(raw)<100000:raise ValueError("Historical file is unexpectedly small.")
        analysis_start=datetime.fromisoformat(cfg["analysis_start"].replace("Z","+00:00"))
        tf_results={};comparison=[];trade_rows=[];month_rows=[];qualified=[]
        for tf,tf_name in TIMEFRAMES.items():
            bars=runner.aggregate(raw,tf);panel=build_panel(bars)
            ai=next((i for i,b in enumerate(bars) if b["dt"]>=analysis_start),None)
            if ai is None:raise ValueError("No usable "+tf_name+" bars at/after analysis start.")
            n=len(bars)-ai
            if n<1000:raise ValueError("Insufficient "+tf_name+" analysis bars: "+str(n))
            dev_end=ai+int(n*.60);val_end=ai+int(n*.80)
            configs=[]
            for lookback in cfg["breakout"]["donchian_lookbacks"]:
                for rr in cfg["breakout"]["target_r_multiples"]:
                    configs.append({"family":"breakout","name":"Donchian"+str(lookback)+"_"+str(rr)+"R",
                        "lookback":int(lookback),"stop_atr":float(cfg["breakout"]["stop_atr"]),"target_r":float(rr),
                        "baseline":int(lookback)==int(cfg["breakout"]["baseline_lookback"]) and float(rr)==float(cfg["breakout"]["baseline_target_r"])})
            for threshold in cfg["mean_reversion"]["rsi_thresholds"]:
                for stop_atr in cfg["mean_reversion"]["stop_atr_multiples"]:
                    configs.append({"family":"mean_reversion","name":"RSI"+str(threshold)+"_Stop"+str(stop_atr)+"ATR",
                        "rsi_threshold":float(threshold),"stop_atr":float(stop_atr),"target_r":None,
                        "baseline":float(threshold)==float(cfg["mean_reversion"]["baseline_rsi"]) and float(stop_atr)==float(cfg["mean_reversion"]["baseline_stop_atr"])})
            rows=[]
            for v in configs:
                dev=simulate(bars,panel,v["family"],v,ai,dev_end,tf)
                val=simulate(bars,panel,v["family"],v,dev_end,val_end,tf)
                row={"timeframe":tf_name,"family":v["family"],"profile":v["name"],"predeclared_baseline":v["baseline"],
                     "development":dev["metrics"],"validation":val["metrics"]}
                rows.append(row)
                flat={"timeframe":tf_name,"family":v["family"],"profile":v["name"],"predeclared_baseline":v["baseline"]}
                flat.update({"development_"+k:x for k,x in dev["metrics"].items()})
                flat.update({"validation_"+k:x for k,x in val["metrics"].items()})
                comparison.append(flat)
            baselines={}
            for fam in ("breakout","mean_reversion"):
                v=next(x for x in configs if x["family"]==fam and x["baseline"])
                dev=simulate(bars,panel,fam,v,ai,dev_end,tf)
                val=simulate(bars,panel,fam,v,dev_end,val_end,tf)
                hold=simulate(bars,panel,fam,v,val_end,len(bars),tf)
                full=simulate(bars,panel,fam,v,ai,len(bars),tf)
                qual=is_qualified(val["metrics"],hold["metrics"])
                if qual:qualified.append(tf_name+"_"+fam)
                baselines[fam]={"profile":v["name"],"development":dev,"validation":val,"holdout":hold,"full_sample":full,
                    "qualification":{"qualified":qual,"max_drawdown_gate_pct":10,"min_validation_trades":20,"min_holdout_trades":10,
                     "reason":"All gates passed." if qual else "One or more trade-count, net-PnL, profit-factor, or mark-to-market drawdown gates failed."}}
                for split,res in (("full_sample",full),("development",dev),("validation",val),("holdout",hold)):
                    for t in res["trades"]:trade_rows.append({"timeframe":tf_name,"family":fam,"profile":v["name"],"split":split,**t})
                for m in monthly_summary(full["trades"],bars[ai]["dt"],bars[-1]["dt"]):
                    month_rows.append({"timeframe":tf_name,"family":fam,"profile":v["name"],**m})
            tf_results[tf_name]={"bars_total":len(bars),"analysis_bars":n,"analysis_start":bars[ai]["dt"].isoformat(),
                "analysis_end":bars[-1]["dt"].isoformat(),"development_end":bars[dev_end-1]["dt"].isoformat(),
                "validation_end":bars[val_end-1]["dt"].isoformat(),"holdout_start":bars[val_end]["dt"].isoformat(),
                "comparison":rows,"baseline_results":baselines}
        report.update({"status":"COMPLETED","data":{"provider":meta.get("source_url"),"market_type":meta.get("market_type"),
            "symbol":meta.get("symbol"),"source_timeframe":meta.get("timeframe"),"first_candle":meta.get("first_candle_utc"),
            "last_candle":meta.get("last_candle_utc"),"raw_rows":len(raw),"raw_gap_events":meta.get("missing_interval_events",meta.get("missing_minute_intervals")),
            "raw_missing_intervals_total":meta.get("missing_intervals_total"),"sha256":digest,"analysis_start":cfg["analysis_start"]},
          "assumptions":{"quantity_btc":QTY,"starting_capital_usdt":CAPITAL,"fee_rate_per_side":FEE,"slippage_bps_per_side":SLIP_BPS,
            "execution":"Close signals; next-candle-open entry and signal-based exits.","intrabar_collision":"Stop first when stop and target both touched.",
            "market":"Spot long-only; no shorts, leverage, funding, liquidation or order-book impact.",
            "breakout":"Prior Donchian 20/55 close breakout; EMA50>EMA200, close>EMA50, ATR14 above its 20-bar mean and volume above its 20-bar mean; stop 2x ATR, target 2R/3R.",
            "mean_reversion":"Close crosses below Bollinger(20,2) lower band; RSI14<25/30; EMA50>EMA200; ATR14 <=1.5x its 20-bar mean; stop 2x/3x ATR; exit next open after close crosses above BB middle or after 72 hours.",
            "periods":"2023 history is warm-up only; performance starts 2024-01-01; chronological 60/20/20 development/validation/holdout.",
            "holdout":"Only each predeclared baseline is tested on holdout; no parameter selection uses holdout.",
            "drawdown":"Conservative OHLC mark-to-market approximation, not tick-level equity.",
            "qualification":"Validation >=20 trades and holdout >=10; positive net PnL and PF>1 in both; mark-to-market DD <=10% in both."},
          "timeframes":tf_results,"qualified_baseline_profiles":qualified,
          "qualification_summary":"A baseline is qualified only when all predeclared validation and holdout gates pass."})
        (out/"latest_report.json").write_text(json.dumps(report,indent=2,default=str)+"\n",encoding="utf-8")
        md=["# BTCUSDT Test 2: Breakout vs Mean Reversion","","Status: "+report["status"],
            "Sample starts 2024-01-01; one-minute spot data resampled to 15m, 1h and 4h.",
            "Assumed costs: 0.10% fee per side and 10 bps slippage each side; fixed position 0.005 BTC; initial equity 1,000 USDT.","",
            "| Strategy | TF | Split | Trades | WR | Net USDT | Avg net/month USDT | PF | MTM Max DD |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|"]
        for tf_name,data in tf_results.items():
            for fam in ("breakout","mean_reversion"):
                b=data["baseline_results"][fam]
                for split in ("development","validation","holdout","full_sample"):
                    m=b[split]["metrics"]
                    md.append("| "+fam+" | "+tf_name+" | "+split+" | "+str(m["trades"])+" | "+str(m["win_rate_pct"])+"% | "+str(m["net_return_usdt"])+" | "+str(m["monthly_average_net_return_usdt"])+" | "+str(m["profit_factor"])+" | "+str(m["max_drawdown_pct_mark_to_market"])+"% |")
        md += ["","## Baseline qualification",""]
        for tf_name,data in tf_results.items():
            for fam,b in data["baseline_results"].items():
                q=b["qualification"];md.append("- "+tf_name+" "+fam+": "+("QUALIFIED" if q["qualified"] else "NOT QUALIFIED")+" — "+q["reason"])
        md += ["","## Development/validation parameter comparison","","| Strategy | TF | Profile | Dev trades | Dev net | Val trades | Val net | Val WR | Val PF | Val MTM DD |",
                "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in comparison:
            md.append("| "+r["family"]+" | "+r["timeframe"]+" | "+r["profile"]+" | "+str(r["development_trades"])+" | "+str(r["development_net_return_usdt"])+" | "+str(r["validation_trades"])+" | "+str(r["validation_net_return_usdt"])+" | "+str(r["validation_win_rate_pct"])+"% | "+str(r["validation_profit_factor"])+" | "+str(r["validation_max_drawdown_pct_mark_to_market"])+"% |")
        md += ["","## Limitations","",
               "- Results are spot long-only, not derivatives or short-selling results.",
               "- Fees/slippage are assumptions. Order-book impact and variable slippage are not simulated.",
               "- Intra-candle path is unknown; stop-first applies when both stop and target are touched.",
               "- Drawdown uses OHLC mark-to-market approximations, not tick-by-tick equity.",
               "- The holdout is not used for ranking variants. Small samples do not qualify even when returns are positive.",
               "- See latest_report.json, variant_comparison.csv, baseline_trades.csv and monthly_baseline.csv for details."]
        (out/"latest_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
        write_csv(out/"variant_comparison.csv",comparison)
        write_csv(out/"baseline_trades.csv",trade_rows)
        write_csv(out/"monthly_baseline.csv",month_rows)
        print(json.dumps({"test_id":report["test_id"],"status":report["status"],"raw_rows":len(raw),
            "raw_gap_events":report["data"]["raw_gap_events"],"qualified_baselines":qualified,
            "baselines":{tf:{fam:{sp:x[sp]["metrics"] for sp in ("development","validation","holdout","full_sample")}
                for fam,x in data["baseline_results"].items()} for tf,data in tf_results.items()}},indent=2,default=str))
        return 0
    except Exception as exc:
        report["blocker"]=str(exc)
        (out/"latest_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        (out/"latest_report.md").write_text("# BTCUSDT Test 2\n\nStatus: BLOCKED\n\nBlocker: "+str(exc)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2));return 2


def main():
    return run()


if __name__=="__main__":
    raise SystemExit(main())
