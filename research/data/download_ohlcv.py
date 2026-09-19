#!/usr/bin/env python3
"""Download candidate Malaysian OHLCV using yfinance.

This is a DATA-GATE acquisition tool, not a backtester. The resulting files
must pass QA before they are used by Strategy Hunter.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import yfinance as yf

START = "2015-01-01"
END = None
UNIVERSE = Path("data/shariah/shariah_snapshots.csv")
OUT = Path("data/ohlcv")
OUT.mkdir(parents=True, exist_ok=True)

def main():
    u = pd.read_csv(UNIVERSE, dtype={"raw_code": str})
    symbols = sorted(u["yahoo_symbol"].dropna().unique())
    print("Symbols:", len(symbols))
    # Batch downloads reduce request overhead.
    for i in range(0, len(symbols), 50):
        batch = symbols[i:i+50]
        data = yf.download(
            tickers=batch,
            start=START,
            end=END,
            auto_adjust=False,
            group_by="ticker",
            threads=True,
            progress=False,
        )
        for symbol in batch:
            try:
                if len(batch) == 1:
                    d = data.copy()
                else:
                    d = data[symbol].copy()
                d = d.reset_index()
                d.columns = [str(c).lower().replace(" ", "_") for c in d.columns]
                if "date" not in d.columns:
                    continue
                d["symbol"] = symbol
                d.to_csv(OUT / f"{symbol.replace('.', '_')}.csv", index=False)
            except Exception as exc:
                print("SKIP", symbol, repr(exc))
        print("Completed", min(i+50, len(symbols)), "/", len(symbols))

if __name__ == "__main__":
    main()
