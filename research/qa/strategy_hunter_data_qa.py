#!/usr/bin/env python3
"""Strategy Hunter dataset QA.

Hard-fails structural/data-integrity problems that make a dataset unsafe to
backtest. Coverage gaps, download failures, and large price jumps are reported
for review instead of silently dropped.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA_ROOT = HERE.parent / "data" / "data"
OHLCV = DATA_ROOT / "ohlcv"
SHARIAH = DATA_ROOT / "shariah" / "shariah_snapshots.csv"
FAILURES = DATA_ROOT / "download_failures.csv"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    files = sorted(OHLCV.glob("*.csv"))
    report = {
        "dataset_root": str(DATA_ROOT),
        "ohlcv_files": len(files),
        "checks": {},
        "warnings": [],
        "file_manifest": [],
        "coverage": [],
        "suspicious_jumps": [],
    }

    if SHARIAH.exists():
        u = pd.read_csv(SHARIAH, dtype={"raw_code": str})
        report["shariah_snapshot_rows"] = int(len(u))
        report["shariah_unique_symbols"] = int(u["yahoo_symbol"].nunique())
        report["shariah_effective_dates"] = sorted(
            u["effective_date"].dropna().astype(str).unique().tolist()
        )
    else:
        raise SystemExit("QA FAILED: missing Shariah snapshot file")

    if FAILURES.exists():
        f = pd.read_csv(FAILURES)
        report["download_failures"] = int(len(f))
        if len(f):
            report["warnings"].append(
                f"{len(f)} symbols had no usable Yahoo historical data"
            )
            report["download_failure_symbols"] = (
                f["symbol"].dropna().astype(str).tolist()
            )
    else:
        report["download_failures"] = 0
        report["warnings"].append("Download failure log missing")

    if not files:
        raise SystemExit("QA FAILED: no OHLCV files found")

    required = {"date", "open", "high", "low", "close", "volume", "symbol"}
    duplicate_dates = 0
    impossible_ohlc = 0
    nonpositive = 0
    bad_order_files = 0
    required_errors = 0
    symbol_mismatches = 0
    empty_files = 0
    calendar_gap_files = 0
    suspicious_jumps = []
    target_start = pd.Timestamp("2015-01-01")

    for path in files:
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            required_errors += 1
            report["warnings"].append(f"{path.name}: unreadable CSV: {exc}")
            continue

        if df.empty:
            empty_files += 1
            continue

        missing = required - set(df.columns)
        if missing:
            required_errors += 1
            report["warnings"].append(
                f"{path.name}: missing columns {sorted(missing)}"
            )
            continue

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        duplicate_dates += int(df.duplicated(subset=["date"]).sum())

        valid_dates = df["date"].dropna()
        if not valid_dates.is_monotonic_increasing:
            bad_order_files += 1

        finite = df[["open", "high", "low", "close", "volume"]].notna().all(axis=1)
        required_errors += int((~finite).sum())

        valid = df[["open", "high", "low", "close"]].dropna()
        if not valid.empty:
            impossible_ohlc += int(
                (
                    (valid["high"] < valid[["open", "close", "low"]].max(axis=1))
                    | (valid["low"] > valid[["open", "close", "high"]].min(axis=1))
                ).sum()
            )
            nonpositive += int((valid <= 0).any(axis=1).sum())

        nonpositive += int((df["volume"].dropna() < 0).sum())

        symbols = df["symbol"].dropna().astype(str).unique().tolist()
        expected_symbol = path.stem.replace("_", ".", 1)
        if symbols and expected_symbol not in symbols:
            symbol_mismatches += 1

        if not valid_dates.empty:
            first, last = valid_dates.min(), valid_dates.max()
            row = {
                "file": path.name,
                "symbol": expected_symbol,
                "first_date": first.date().isoformat(),
                "last_date": last.date().isoformat(),
                "rows": int(len(valid_dates)),
                "starts_after_target": bool(first > target_start),
            }

            # Exchange holidays create normal multi-day gaps. Flag only long
            # gaps >= 8 calendar days so weekends/ordinary holidays do not
            # become false failures.
            if len(valid_dates) > 1:
                gap_days = valid_dates.diff().dt.days.dropna()
                max_gap = int(gap_days.max())
                row["max_calendar_gap_days"] = max_gap
                if max_gap >= 8:
                    calendar_gap_files += 1
            report["coverage"].append(row)

            ret = df["close"].pct_change()
            big = ret.abs() >= 0.50
            for idx in df.index[big.fillna(False)]:
                suspicious_jumps.append(
                    {
                        "file": path.name,
                        "symbol": expected_symbol,
                        "date": df.loc[idx, "date"].date().isoformat(),
                        "return": float(ret.loc[idx]),
                    }
                )

        report["file_manifest"].append(
            {
                "file": path.name,
                "sha256": sha256_file(path),
                "rows": int(len(df)),
            }
        )

    report["checks"] = {
        "duplicate_rows_by_date": duplicate_dates,
        "impossible_ohlc_rows": impossible_ohlc,
        "nonpositive_price_or_volume_rows": nonpositive,
        "files_with_bad_date_order": bad_order_files,
        "required_field_errors": required_errors,
        "symbol_filename_mismatches": symbol_mismatches,
        "empty_ohlcv_files": empty_files,
        "files_with_long_calendar_gaps_ge_8d": calendar_gap_files,
        "suspicious_abs_daily_jumps_ge_50pct": len(suspicious_jumps),
    }
    report["suspicious_jumps"] = suspicious_jumps[:500]
    report["dataset_sha256"] = hashlib.sha256(
        json.dumps(report["file_manifest"], sort_keys=True).encode()
    ).hexdigest()

    hard_failures = {
        key: value
        for key, value in report["checks"].items()
        if key
        in {
            "duplicate_rows_by_date",
            "impossible_ohlc_rows",
            "nonpositive_price_or_volume_rows",
            "files_with_bad_date_order",
            "required_field_errors",
            "symbol_filename_mismatches",
            "empty_ohlcv_files",
        }
        and value
    }
    report["hard_failures"] = hard_failures

    out = HERE / "strategy_hunter_data_qa.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ohlcv_files": report["ohlcv_files"],
                "shariah_snapshot_rows": report["shariah_snapshot_rows"],
                "shariah_unique_symbols": report["shariah_unique_symbols"],
                "download_failures": report["download_failures"],
                "checks": report["checks"],
                "warnings": report["warnings"],
                "dataset_sha256": report["dataset_sha256"],
                "hard_failures": hard_failures,
            },
            indent=2,
        )
    )

    if hard_failures:
        raise SystemExit("QA FAILED: structural integrity checks did not pass")

    print("QA PASSED: structural integrity checks are clean.")


if __name__ == "__main__":
    main()
