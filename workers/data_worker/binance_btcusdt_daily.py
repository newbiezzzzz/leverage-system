"""BTCUSDT daily ingestion adapter using Binance's public kline REST API.

The adapter is intentionally source-specific at the edge and emits the shared
Leverage OHLCV schema for validation by multi_market_ohlcv.py.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
INTERVAL = "1d"
SYMBOL = "BTCUSDT"
LIMIT = 1000


def _get(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "LeverageDataWorker/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_daily(limit: int = LIMIT, end_time_ms: int | None = None) -> list[dict[str, object]]:
    """Fetch the latest daily BTCUSDT spot klines and return canonical rows."""
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": min(max(limit, 1), LIMIT)}
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    url = f"{BINANCE_KLINES}?{urllib.parse.urlencode(params)}"
    raw = _get(url)
    rows: list[dict[str, object]] = []
    for item in raw:
        rows.append(
            {
                "timestamp": datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc).isoformat(),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            }
        )
    return rows


if __name__ == "__main__":
    sample = fetch_daily(5)
    for row in sample:
        print(row)
