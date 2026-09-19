#!/usr/bin/env python3
"""Download candidate Malaysian OHLCV using yfinance.

This is a DATA-GATE acquisition tool, not a backtester. The resulting files
must pass QA before they are used by Strategy Hunter. Failed symbols are
recorded explicitly and are never silently discarded.
"""
from __future__ import annotations

from pathlib import Path
import os

import pandas as pd
import yfinance as yf

START = "2015-01-01"
END = None
UNIVERSE = Path("data/shariah/shariah_snapshots.csv")
OUT = Path("data/ohlcv")
OUT.mkdir(parents=True, exist_ok=True)
FAILURES = OUT.parent / "download_failures.csv"


def main():
    u = pd.read_csv(UNIVERSE, dtype={"raw_code": str})
    symbols = sorted(u["yahoo_symbol"].dropna().unique())

    latest_only = os.environ.get("LATEST_ONLY", "0") == "1"
    if latest_only:
        latest_date = u["effective_date"].max()
        symbols = sorted(
            u.loc[u["effective_date"].eq(latest_date), "yahoo_symbol"]
            .dropna()
            .unique()
        )
        print("Using latest SC snapshot:", latest_date)

    max_symbols = int(os.environ.get("MAX_SYMBOLS", "0"))
    if max_symbols > 0:
        symbols = symbols[:max_symbols]

    print("Symbols:", len(symbols))
    failures = []

    for i in range(0, len(symbols), 50):
        batch = symbols[i : i + 50]
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
                d.columns = [
                    str(c).lower().replace(" ", "_") for c in d.columns
                ]

                if "date" not in d.columns or d.empty:
                    raise ValueError("no historical rows returned")

                d = d.dropna(subset=["date"])
                if d.empty:
                    raise ValueError("no dated historical rows returned")

                d["symbol"] = symbol
                path = OUT / f"{symbol.replace('.', '_')}.csv"
                d.to_csv(path, index=False)

            except Exception as exc:
                failures.append(
                    {"symbol": symbol, "error": repr(exc)}
                )
                print("SKIP", symbol, repr(exc))

        print("Completed", min(i + 50, len(symbols)), "/", len(symbols))

    pd.DataFrame(failures, columns=["symbol", "error"]).to_csv(
        FAILURES, index=False
    )
    print("Download failures:", len(failures))
    print("Failure log:", FAILURES)


if __name__ == "__main__":
    main()
