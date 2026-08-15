"""FCPO dataset validation rules for Project Leverage.

Rejects non-Bursa/FCPO sources and checks basic OHLCV integrity before a
historical dataset may enter strategy evaluation.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = {"timestamp", "open", "high", "low", "close", "volume"}
ALLOWED_SYMBOL_HINTS = {"FCPO1!", "MYX:FCPO1!", "Bursa Malaysia", "FCPO"}
REJECT_HINTS = {"CPOc1", "CPO", "CPOc1/CME", "CME", "ICE"}


def validate_csv(path: Path) -> dict:
    result = {"path": str(path), "valid": False, "rows": 0, "errors": [], "warnings": []}
    if not path.exists():
        result["errors"].append("dataset_missing")
        return result

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = set(reader.fieldnames or [])
        missing = REQUIRED - headers
        if missing:
            result["errors"].append(f"missing_columns:{','.join(sorted(missing))}")
            return result

        previous_ts = None
        for row in reader:
            result["rows"] += 1
            try:
                o = float(row["open"]); h = float(row["high"]); low = float(row["low"]); c = float(row["close"]); v = float(row["volume"] or 0)
                if not (low <= o <= h and low <= c <= h):
                    result["errors"].append(f"ohlc_invalid_at:{row.get('timestamp','')}")
                if v < 0:
                    result["errors"].append(f"negative_volume_at:{row.get('timestamp','')}")
            except (TypeError, ValueError):
                result["errors"].append(f"non_numeric_at:{row.get('timestamp','')}")

            ts = row.get("timestamp", "")
            if previous_ts and ts <= previous_ts:
                result["errors"].append(f"non_monotonic_timestamp_at:{ts}")
            previous_ts = ts

    if result["rows"] < 250:
        result["warnings"].append("insufficient_rows_for_strategy_validation")
    if result["rows"] < 750:
        result["warnings"].append("preferred_depth_not_reached")
    result["valid"] = not result["errors"]
    return result


if __name__ == "__main__":
    print(validate_csv(ROOT / "fcpo_ohlcv.csv"))
