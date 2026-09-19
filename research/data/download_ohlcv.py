#!/usr/bin/env python3
"""Download and clean candidate Malaysian OHLCV using yfinance.

Raw vendor anomalies are excluded by generic, deterministic rules and recorded
in data/qa_exclusions.csv. No values are imputed.
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
EXCLUSIONS = OUT.parent / "qa_exclusions.csv"


def classify_exclusions(df: pd.DataFrame, symbol: str):
    numeric = ["open", "high", "low", "close", "volume"]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    exclusions = []

    all_missing = df[numeric].isna().all(axis=1)
    for idx in df.index[all_missing]:
        exclusions.append(
            {
                "symbol": symbol,
                "date": str(df.loc[idx, "date"]),
                "reason": "all_ohlcv_missing",
            }
        )

    partial_missing = (
        ~all_missing
        & ~df[numeric].notna().all(axis=1)
    )
    for idx in df.index[partial_missing]:
        exclusions.append(
            {
                "symbol": symbol,
                "date": str(df.loc[idx, "date"]),
                "reason": "partial_ohlcv_missing",
            }
        )

    valid = df[numeric[:4]].notna().all(axis=1)
    impossible = (
        valid
        & (
            (df["high"] < df[["open", "close", "low"]].max(axis=1))
            | (df["low"] > df[["open", "close", "high"]].min(axis=1))
        )
    )
    for idx in df.index[impossible]:
        exclusions.append(
            {
                "symbol": symbol,
                "date": str(df.loc[idx, "date"]),
                "reason": "impossible_ohlc",
            }
        )

    remove = all_missing | partial_missing | impossible
    return df.loc[~remove].copy(), exclusions


def main():
    u = pd.read_csv(UNIVERSE, dtype={"raw_code": str})
    symbols = sorted(u["yahoo_symbol"].dropna().unique())

    if os.environ.get("LATEST_ONLY", "0") == "1":
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
    exclusions = []

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
                d = data.copy() if len(batch) == 1 else data[symbol].copy()
                d = d.reset_index()
                d.columns = [str(c).lower().replace(" ", "_") for c in d.columns]

                if "date" not in d.columns or d.empty:
                    raise ValueError("no historical rows returned")

                d = d.dropna(subset=["date"])
                if d.empty:
                    raise ValueError("no dated historical rows returned")

                d["symbol"] = symbol
                clean, rows_excluded = classify_exclusions(d, symbol)
                exclusions.extend(rows_excluded)

                if clean.empty:
                    raise ValueError("no usable rows after deterministic cleaning")

                clean.to_csv(
                    OUT / f"{symbol.replace('.', '_')}.csv",
                    index=False,
                )
            except Exception as exc:
                failures.append({"symbol": symbol, "error": repr(exc)})
                print("SKIP", symbol, repr(exc))

        print("Completed", min(i + 50, len(symbols)), "/", len(symbols))

    pd.DataFrame(failures, columns=["symbol", "error"]).to_csv(
        FAILURES, index=False
    )
    pd.DataFrame(
        exclusions,
        columns=["symbol", "date", "reason"],
    ).to_csv(EXCLUSIONS, index=False)

    print("Download failures:", len(failures))
    print("Cleaned-row exclusions:", len(exclusions))
    print("Failure log:", FAILURES)
    print("Exclusion log:", EXCLUSIONS)


if __name__ == "__main__":
    main()
