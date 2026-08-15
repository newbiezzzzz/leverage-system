import csv
import json
import math
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "fcpo_ohlcv.csv"
OUT = ROOT / "dashboard" / "research.json"

FEE_SLIPPAGE = 0.0008  # conservative placeholder; replace with verified FCPO costs


def sma(xs, n):
    out = [math.nan] * len(xs)
    if len(xs) < n:
        return out
    s = sum(xs[:n])
    out[n - 1] = s / n
    for i in range(n, len(xs)):
        s += xs[i] - xs[i - n]
        out[i] = s / n
    return out


def rolling_high(xs, n):
    return [max(xs[max(0, i - n):i]) if i > 0 else math.nan for i in range(len(xs))]


def ema(xs, n):
    out = [math.nan] * len(xs)
    if len(xs) < n:
        return out
    k = 2 / (n + 1)
    out[n - 1] = sum(xs[:n]) / n
    for i in range(n, len(xs)):
        out[i] = xs[i] * k + out[i - 1] * (1 - k)
    return out


def rsi(xs, n=14):
    out = [math.nan] * len(xs)
    if len(xs) <= n:
        return out
    gains, losses = [], []
    for i in range(1, len(xs)):
        d = xs[i] - xs[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:n]) / n
    al = sum(losses[:n]) / n
    out[n] = 100.0 if al == 0 else 100 - (100 / (1 + ag / al))
    for i in range(n + 1, len(xs)):
        g, l = gains[i - 1], losses[i - 1]
        ag = (ag * (n - 1) + g) / n
        al = (al * (n - 1) + l) / n
        out[i] = 100.0 if al == 0 else 100 - (100 / (1 + ag / al))
    return out


def load_rows():
    if not DATA.exists():
        return []
    with DATA.open("r", encoding="utf-8", newline="") as f:
        out = []
        for r in csv.DictReader(f):
            try:
                out.append({
                    "timestamp": r.get("timestamp", ""),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r.get("volume", 0) or 0),
                })
            except (KeyError, TypeError, ValueError):
                continue
    return out


def simulate_signal(closes, signal_fn):
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    pos = 0
    entry = None
    trades = 0
    for i, px in enumerate(closes):
        signal = signal_fn(i)
        if signal not in (-1, 0, 1):
            signal = 0
        if signal != pos:
            if pos and entry is not None:
                gross = (px / entry - 1.0) if pos == 1 else (entry / px - 1.0)
                equity *= max(0.0, 1.0 + gross - FEE_SLIPPAGE)
                trades += 1
            if signal:
                entry = px
            else:
                entry = None
            pos = signal
        peak = max(peak, equity)
        max_dd = max(max_dd, 1 - equity / peak)
    if pos and entry is not None and closes:
        px = closes[-1]
        gross = (px / entry - 1.0) if pos == 1 else (entry / px - 1.0)
        equity *= max(0.0, 1.0 + gross - FEE_SLIPPAGE)
        trades += 1
    return {"return": equity - 1.0, "max_drawdown": max_dd, "trades": trades}


def split_stats(stats, n):
    if n < 100:
        return {"status": "insufficient_data"}
    return stats


def run():
    rows = load_rows()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "worker": "research-worker",
        "project": "FCPO Trading Research",
        "instrument": "FCPO",
        "mode": "research_only",
        "status": "research_in_progress",
        "observations": len(rows),
        "strategy_candidates_tested": 0,
        "validated_strategies": 0,
        "strategy_results": [],
        "data_source": "cached local data/fcpo_ohlcv.csv",
        "cost_policy": "RM0; no external API calls during screening",
        "risk_gate": "REAL MONEY BLOCKED",
    }

    if len(rows) < 100:
        result["latest_result"] = "Waiting for >=100 valid FCPO OHLCV rows before screening; no strategy claims will be made from insufficient data."
    else:
        closes = [r["close"] for r in rows]
        highs = [r["high"] for r in rows]
        lows = [r["low"] for r in rows]
        candidates = []

        for fast, slow in [(10, 30), (20, 50), (20, 100), (50, 200)]:
            sf, ss = sma(closes, fast), sma(closes, slow)
            candidates.append(("trend-following", f"SMA {fast}/{slow}", lambda i, sf=sf, ss=ss: 1 if not math.isnan(sf[i]) and not math.isnan(ss[i]) and sf[i] > ss[i] else -1 if not math.isnan(sf[i]) and not math.isnan(ss[i]) else 0))

        rr = rsi(closes, 14)
        candidates.append(("mean-reversion", "RSI 14: 30/70", lambda i, rr=rr: 1 if not math.isnan(rr[i]) and rr[i] < 30 else -1 if not math.isnan(rr[i]) and rr[i] > 70 else 0))

        hh = rolling_high(highs, 20)
        candidates.append(("breakout", "20-bar high breakout", lambda i, hh=hh: 1 if not math.isnan(hh[i]) and closes[i] > hh[i] else 0))

        ef, es = ema(closes, 12), ema(closes, 26)
        candidates.append(("momentum", "EMA 12/26", lambda i, ef=ef, es=es: 1 if not math.isnan(ef[i]) and not math.isnan(es[i]) and ef[i] > es[i] else -1 if not math.isnan(ef[i]) and not math.isnan(es[i]) else 0))

        for family, name, fn in candidates:
            stats = simulate_signal(closes, fn)
            result["strategy_results"].append({"family": family, "name": name, **stats})

        result["strategy_candidates_tested"] = len(candidates)
        result["latest_result"] = "Initial technical screen complete. Candidates remain unvalidated until out-of-sample and walk-forward testing."
        result["status"] = "research_complete_initial_screen"

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
