#!/usr/bin/env python3
"""Strategy Hunter dataset QA.

Hard-fails only on structural/data-integrity problems that make a dataset
unsafe to backtest. Coverage gaps and suspicious price jumps are reported for
review rather than silently dropped.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "data"
OHLCV = ROOT / "ohlcv"
SHARIAH = ROOT / "shariah" / "shariah_snapshots.csv"
OUT = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    files = sorted(OHLCV.glob("*.csv"))
    report = {
        "dataset_root": str(ROOT),
        "ohlcv_files": len(files),
        "checks": {},
        "warnings": [],
        "file_manifest": [],
    }

    if SHARIAH.exists():
        u = pd.read_csv(SHARIAH, dtype={"raw_code": str})
        report["shariah_snapshot_rows"] = int(len(u))
        report["shariah_unique_symbols"] = int(u["yahoo_symbol"].nunique())
    else:
        u = pd.DataFrame()
        report["warnings"].append("Missing Shariah snapshot file")

    if not files:
        raise SystemExit("QA FAILED: no OHLCV files found")

    required = {"date", "open", "high", "low", "close", "volume", "symbol"}
    dup = bad_ohlc = nonpositive = bad_order = bad_required = symbol_mismatch = 0
    coverage = []
    jumps = []

    expected_start = pd.Timestamp("2015-01-01")

    for path in files:
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            report["warnings"].append(f"Unreadable CSV {path.name}: {exc}")
            bad_required += 1
            continue

        missing = required - set(df.columns)
        if missing:
            bad_required += 1
            report["warnings"].append(f"{path.name}: missing columns {sorted(missing)}")
            continue

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        dups = int(df.duplicated(subset=["date"]).sum())
        dup += dups

        if df["date"].isna().any():
            bad_required += int(df["date"].isna().sum())

        if not df["date"].dropna().is_monotonic_increasing:
            bad_order += 1

        finite = df[["open", "high", "low", "close", "volume"]].notna().all(axis=1)
        bad_required += int((~finite).sum())

        valid = df[["open", "high", "low", "close"]].dropna()
        if not valid.empty:
            bad_ohlc += int(
                (
                    (valid["high"] < valid[["open", "close", "low"]].max(axis=1))
                    | (valid["low"] > valid[["open", "close", "high"]].min(axis=1))
                ).sum()
            )
            nonpositive += int((valid <= 0).any(axis=1).sum())

        vol = df["volume"].dropna()
        nonpositive += int((vol < 0).sum())

        symbols = df["symbol"].dropna().astype(str).unique().tolist()
        expected_symbol = path.stem.replace("_", ".", 1)
        if symbols and expected_symbol not in symbols:
            symbol_mismatch += 1

        valid_dates = df["date"].dropna()
        if not valid_dates.empty:
            first = valid_dates.min()
            last = valid_dates.max()
            coverage.append({
                "file": path.name,
                "symbol": expected_symbol,
                "first_date": first.date().isoformat(),
                "last_date": last.date().isoformat(),
                "rows": int(len(valid_dates)),
                "starts_after_target": bool(first > expected_start),
            })

            ret = df["close"].pct_change()
            big = ret.abs() >= 0.50
            for idx in df.index[big.fillna(False)]:
                jumps.append({
                    "file": path.name,
                    "symbol": expected_symbol,
                    "date": df.loc[idx, "date"].date().isoformat(),
                    "return": float(ret.loc[idx]),
                })

        report["file_manifest"].append({
            "file": path.name,
            "sha256": sha256_file(path),
            "rows": int(len(df)),
        })

    report["checks"] = {
        "duplicate_rows_by_date": dup,
        "impossible_ohlc_rows": bad_ohlc,
        "nonpositive_price_or_volume_rows": nonpositive,
        "files_with_bad_date_order": bad_order,
        "required_field_errors": bad_required,
        "symbol_filename_mismatches": symbol_mismatch,
        "suspicious_abs_daily_jumps_ge_50pct": len(jumps),
    }
    report["coverage"] = coverage
    report["suspicious_jumps"] = jumps[:500]

    # Hard-fail integrity checks.
    hard_failures = {
        k: v for k, v in report["checks"].items()
        if k in {
            "duplicate_rows_by_date",
            "impossible_ohlc_rows",
            "nonpositive_price_or_volume_rows",
            "files_with_bad_date_order",
            "required_field_errors",
            "symbol_filename_mismatches",
        } and v
    }
    report["hard_failures"] = hard_failures
    report["dataset_sha256"] = hashlib.sha256(
        json.dumps(report["file_manifest"], sort_keys=True).encode()
    ).hexdigest()

    OUT_PATH = OUT / "strategy_hunter_data_qa.json"
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({
        "ohlcv_files": report["ohlcv_files"],
        "shariah_snapshot_rows": report.get("shariah_snapshot_rows"),
        "checks": report["checks"],
        "warnings": report["warnings"],
        "dataset_sha256": report["dataset_sha256"],
        "hard_failures": hard_failures,
    }, indent=2))

    if hard_failures:
        raise SystemExit("QA FAILED: structural integrity checks did not pass")

    print("QA PASSED: structural integrity checks are clean.")


if __name__ == "__main__":
    main()
