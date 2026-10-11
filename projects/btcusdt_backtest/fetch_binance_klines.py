#!/usr/bin/env python3
"""Fetch Binance public BTCUSDT 1m klines and normalize them for Leverage backtests.

One-time acquisition run marker; keep this comment unchanged unless intentionally retriggering.

Downloads monthly archives for complete months and daily archives for partial months.
The resulting CSV is research data; consult the source terms before redistribution.
"""
import argparse
import csv
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from calendar import monthrange

FIELDS = ["timestamp", "open", "high", "low", "close", "volume"]
BASE = "https://data.binance.vision/data"

def utc_iso(ms):
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat().replace("+00:00", "Z")

def fetch_zip(url, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Leverage-Research-Backtest/1.0"})
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = response.read()
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:
                    raise ValueError("Archive contains no CSV: " + url)
                with zf.open(names[0]) as f:
                    return list(csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig", newline="")))
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not retrieve archive {url}: {last}")

def rows_from_csv(rows, start_ms, end_ms):
    for row in rows:
        if not row or len(row) < 6:
            continue
        try:
            ms = int(row[0])
            vals = [float(row[i]) for i in range(1, 6)]
        except (ValueError, TypeError):
            # Some archive files include a header row.
            continue
        if start_ms <= ms < end_ms:
            yield (ms, *vals)

def source_prefix(market_type):
    return "spot" if market_type == "spot" else "futures/um"

def month_start(d):
    return date(d.year, d.month, 1)

def next_month(d):
    return date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)

def get_archive_rows(symbol, market_type, start_date, end_date):
    prefix = source_prefix(market_type)
    start_ms = int(datetime.combine(start_date, datetime.min.time(), timezone.utc).timestamp() * 1000)
    end_exclusive = int(datetime.combine(end_date + timedelta(days=1), datetime.min.time(), timezone.utc).timestamp() * 1000)
    all_rows = {}
    month = month_start(start_date)
    last_month = month_start(end_date)
    while month <= last_month:
        month_end = date(month.year, month.month, monthrange(month.year, month.month)[1])
        fully_covered = start_date <= month and end_date >= month_end
        if fully_covered:
            url = f"{BASE}/{prefix}/monthly/klines/{symbol}/1m/{symbol}-1m-{month:%Y-%m}.zip"
            rows = fetch_zip(url)
            for r in rows_from_csv(rows, start_ms, end_exclusive):
                all_rows[r[0]] = r
        else:
            day = max(start_date, month)
            stop = min(end_date, month_end)
            while day <= stop:
                url = f"{BASE}/{prefix}/daily/klines/{symbol}/1m/{symbol}-1m-{day:%Y-%m-%d}.zip"
                rows = fetch_zip(url)
                for r in rows_from_csv(rows, start_ms, end_exclusive):
                    all_rows[r[0]] = r
                day += timedelta(days=1)
        month = next_month(month)
    return [all_rows[k] for k in sorted(all_rows)]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market-type", choices=["spot", "usdt_perpetual"], default="spot")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--start-date", default="2024-01-01")
    p.add_argument("--end-date", default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat())
    p.add_argument("--output", default="data/btcusdt/btcusdt_1m.csv")
    p.add_argument("--metadata", default="data/btcusdt/download_report.json")
    args = p.parse_args()
    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)
    if end < start:
        p.error("end-date must be on or after start-date")
    if args.symbol != "BTCUSDT":
        p.error("This project is currently configured for BTCUSDT only.")
    rows = get_archive_rows(args.symbol, args.market_type, start, end)
    if not rows:
        raise SystemExit("No candles retrieved; refusing to create an empty dataset.")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for ms, op, hi, lo, cl, vol in rows:
            w.writerow([utc_iso(ms), format(op, ".12g"), format(hi, ".12g"), format(lo, ".12g"), format(cl, ".12g"), format(vol, ".12g")])
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    gaps = sum(1 for a, b in zip(rows, rows[1:]) if b[0] - a[0] != 60000)
    meta = {
        "status": "RETRIEVED_WITH_GAPS" if gaps else "RETRIEVED",
        "source_url": f"{BASE}/{source_prefix(args.market_type)}/",
        "symbol": args.symbol,
        "market_type": args.market_type,
        "timeframe": "1m",
        "start_date_requested": start.isoformat(),
        "end_date_requested": end.isoformat(),
        "first_candle_utc": utc_iso(rows[0][0]),
        "last_candle_utc": utc_iso(rows[-1][0]),
        "rows": len(rows),
        "missing_minute_intervals": gaps,
        "sha256": digest,
        "csv_path": str(out),
        "note": "Archive retrieval is confirmed for this run; check coverage/gaps and source terms before interpreting strategy results."
    }
    mp = Path(args.metadata)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    source_note = Path("data/btcusdt/DATA_SOURCE.md")
    source_note.parent.mkdir(parents=True, exist_ok=True)
    note = (
        "# BTCUSDT historical data provenance\n\n"
        + "Provider/source URL: " + meta["source_url"] + "\n"
        + "Date retrieved: " + datetime.now(timezone.utc).isoformat() + "\n"
        + "License/terms permitting this use: Binance public data archive; private research copy. Verify applicable terms before redistribution or commercial reuse.\n"
        + "Instrument/symbol: " + args.symbol + "\n"
        + "Market type: " + args.market_type + "\n"
        + "Raw timeframe: 1m\n"
        + "First and last timestamps: " + meta["first_candle_utc"] + " to " + meta["last_candle_utc"] + "\n"
        + "Timestamp timezone: UTC\n"
        + "Session convention: 24/7\n"
        + "File checksum (SHA-256): " + digest + "\n"
        + "Data file: " + str(out) + "\n"
    )
    source_note.write_text(note, encoding="utf-8")
    print(json.dumps(meta, indent=2))
    if gaps:
        print("WARNING: Missing minute intervals detected. The backtester will not fabricate candles.")

if __name__ == "__main__":
    main()
