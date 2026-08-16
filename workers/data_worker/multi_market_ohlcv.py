"""Reusable OHLCV normalization and validation helpers for Leverage."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    rows: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def normalize_row(row: Mapping[str, object]) -> dict[str, object]:
    """Normalize one source row into the canonical Leverage OHLCV shape."""
    missing = [c for c in REQUIRED_COLUMNS if c not in row]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    return {
        "timestamp": row["timestamp"],
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": float(row["volume"]),
    }


def validate_rows(rows: Sequence[Mapping[str, object]], minimum_rows: int = 250) -> ValidationResult:
    """Validate canonical OHLCV rows without making source-specific assumptions."""
    errors: list[str] = []
    warnings: list[str] = []
    normalized: list[dict[str, object]] = []

    if len(rows) < minimum_rows:
        errors.append(f"row count {len(rows)} is below minimum {minimum_rows}")

    previous_ts = None
    for idx, raw in enumerate(rows):
        try:
            item = normalize_row(raw)
            normalized.append(item)
        except (TypeError, ValueError) as exc:
            errors.append(f"row {idx}: {exc}")
            continue

        o, h, l, c, v = (item["open"], item["high"], item["low"], item["close"], item["volume"])
        if h < max(o, c, l):
            errors.append(f"row {idx}: high is below one of open/close/low")
        if l > min(o, c, h):
            errors.append(f"row {idx}: low is above one of open/close/high")
        if v < 0:
            errors.append(f"row {idx}: negative volume")

        ts = item["timestamp"]
        if previous_ts is not None and ts <= previous_ts:
            errors.append(f"row {idx}: timestamps are not strictly increasing")
        previous_ts = ts

    duplicate_count = len(normalized) - len({r["timestamp"] for r in normalized})
    if duplicate_count:
        errors.append(f"duplicate timestamps: {duplicate_count}")

    if len(rows) < 750 and len(rows) >= minimum_rows:
        warnings.append("passes minimum gate but is below preferred 750-row depth")

    return ValidationResult(not errors, len(rows), tuple(errors), tuple(warnings))
