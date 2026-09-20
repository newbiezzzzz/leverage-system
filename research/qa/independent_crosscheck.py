#!/usr/bin/env python3
"""Independent OHLCV cross-check: Yahoo/yfinance vs KLSE Screener.

This does not replace the main Yahoo dataset. It checks a deterministic sample
of current Shariah equities against a second public source and records the
comparison for auditability.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

SAMPLE = ["0056", "7086", "5183", "5296", "8869"]
OUT = Path("research/qa")
OUT.mkdir(parents=True, exist_ok=True)

KLS_URL = "https://www.klsescreener.com/v2/stocks/chart/{code}/embedded/10y"


def kls_history(code: str) -> pd.DataFrame:
    """Read KLSE Screener's current historical-price HTML table."""
    url = f"https://www.klsescreener.com/v2/stocks/historical_prices/{code}"
    r = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; Strategy-Hunter/1.0; "
                "+https://github.com/newbiezzzzz/leverage-system)"
            )
        },
    )
    r.raise_for_status()

    tables = pd.read_html(StringIO(r.text))
    target = None
    for t in tables:
        cols = {str(c).strip().lower() for c in t.columns}
        if {"date", "price", "open", "high", "low", "volume"} <= cols:
            target = t.copy()
            break

    if target is None:
        raise ValueError(
            f"KLSE historical price table not found; status={r.status_code}; "
            f"tables={len(tables)}"
        )

    target.columns = [str(c).strip().lower() for c in target.columns]
    target["date"] = pd.to_datetime(target["date"], errors="coerce").dt.normalize()

    for c in ["price", "open", "high", "low"]:
        target[c] = pd.to_numeric(target[c], errors="coerce")

    target["volume"] = (
        target["volume"].astype(str).str.replace(",", "", regex=False)
    )
    target["volume"] = pd.to_numeric(target["volume"], errors="coerce")

    out = target[
        ["date", "open", "high", "low", "price", "volume"]
    ].copy()
    out = out.rename(
        columns={
            "open": "open_kls",
            "high": "high_kls",
            "low": "low_kls",
            "price": "close_kls",
            "volume": "volume_kls",
        }
    )
    out = out.dropna(subset=["date", "open_kls", "high_kls", "low_kls", "close_kls"])
    return out.drop_duplicates("date").sort_values("date")


def yahoo_history(code: str) -> pd.DataFrame:
    sym = f"{code}.KL"
    d = yf.download(
        tickers=[sym],
        start="2016-09-01",
        end=None,
        auto_adjust=False,
        progress=False,
        threads=False,
        group_by="ticker",
    )
    if isinstance(d.columns, pd.MultiIndex):
        d = d[sym].copy()
    d = d.reset_index()
    d.columns = [str(c).lower().replace(" ", "_") for c in d.columns]
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    keep = ["date", "open", "high", "low", "close", "volume"]
    d = d[keep].copy()
    d.columns = [
        "date", "open_yf", "high_yf", "low_yf", "close_yf", "volume_yf"
    ]
    return d.drop_duplicates("date").sort_values("date")


def main() -> None:
    results = []
    errors = []

    for code in SAMPLE:
        try:
            kls = kls_history(code)
            yfdf = yahoo_history(code)
            merged = yfdf.merge(kls, on="date", how="inner")

            if merged.empty:
                raise ValueError("No overlapping dates")

            recent = merged.tail(10).copy()
            for field in ["open", "high", "low", "close"]:
                denom = recent[f"{field}_kls"].abs().clip(lower=1e-9)
                recent[f"{field}_rel_err"] = (
                    (recent[f"{field}_yf"] - recent[f"{field}_kls"]).abs() / denom
                )

            vdenom = recent["volume_kls"].abs().clip(lower=1.0)
            recent["volume_rel_err"] = (
                (recent["volume_yf"] - recent["volume_kls"]).abs() / vdenom
            )

            results.append(
                {
                    "code": code,
                    "status": "ok",
                    "overlap_rows": int(len(merged)),
                    "common_from": merged.date.min().date().isoformat(),
                    "common_to": merged.date.max().date().isoformat(),
                    "max_open_rel_err_10d": float(recent["open_rel_err"].max()),
                    "max_high_rel_err_10d": float(recent["high_rel_err"].max()),
                    "max_low_rel_err_10d": float(recent["low_rel_err"].max()),
                    "max_close_rel_err_10d": float(recent["close_rel_err"].max()),
                    "max_volume_rel_err_10d": float(recent["volume_rel_err"].max()),
                }
            )
        except Exception as exc:
            print("CROSSCHECK ERROR", code, repr(exc))
            errors.append({"code": code, "error": repr(exc)})
            results.append({"code": code, "status": "error", "error": repr(exc)})

    out = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_a": "Yahoo Finance via yfinance, auto_adjust=False",
        "source_b": "KLSE Screener 10y embedded chart endpoint",
        "sample": SAMPLE,
        "results": results,
        "errors": errors,
    }
    pd.DataFrame(results).to_csv(OUT / "independent_crosscheck.csv", index=False)

    import json
    (OUT / "independent_crosscheck.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )

    successful = [r for r in results if r.get("status") == "ok"]
    if len(successful) < len(SAMPLE):
        raise SystemExit(
            f"Independent cross-check FAILED: {len(successful)}/{len(SAMPLE)} symbols succeeded"
        )

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
