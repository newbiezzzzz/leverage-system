from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class InstrumentSpec:
    instrument: str
    market_type: str
    timezone: str
    continuous: bool = False
    volume_semantics: str = "source_defined"


INSTRUMENTS = {
    "BTCUSDT": InstrumentSpec("BTCUSDT", "crypto_spot_or_futures", "UTC", False, "exchange_volume"),
    "XAUUSDT": InstrumentSpec("XAUUSDT", "spot_or_cfd_style", "UTC", False, "source_volume_or_na"),
    "CL": InstrumentSpec("CL", "commodity_futures", "America/New_York", True, "contract_volume"),
    "FCPO": InstrumentSpec("FCPO", "commodity_futures", "Asia/Kuala_Lumpur", True, "contract_volume"),
}


def validate_ohlcv(df: pd.DataFrame, instrument: str, *, min_rows: int = 250) -> dict:
    if instrument not in INSTRUMENTS:
        raise ValueError(f"Unsupported instrument: {instrument}")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    out = df[REQUIRED_COLUMNS].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    for col in REQUIRED_COLUMNS[1:]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    checks = {
        "rows": int(len(out)),
        "min_rows_pass": len(out) >= min_rows,
        "null_rows": int(out.isna().any(axis=1).sum()),
        "duplicate_timestamps": int(out["timestamp"].duplicated().sum()),
        "nonpositive_prices": int((out[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
        "invalid_ranges": int(((out["high"] < out[["open", "low", "close"]].max(axis=1)) |
                               (out["low"] > out[["open", "high", "close"]].min(axis=1))).sum()),
    }
    checks["quality_pass"] = all(v == 0 for k, v in checks.items() if k not in {"rows", "min_rows_pass"}) and bool(checks["min_rows_pass"])
    return checks
