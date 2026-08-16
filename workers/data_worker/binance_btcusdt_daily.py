"""BTCUSDT daily ingestion adapter using Binance's public kline REST API.

The adapter is source-specific at the edge and emits the shared Leverage OHLCV
schema for validation by multi_market_ohlcv.py. It also supports the CLI used
by the GitHub Actions acquisition workflow.
"""
from __future__ import annotations

import argparse
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
INTERVAL = "1d"
SYMBOL = "BTCUSDT"
LIMIT = 1000


def _get(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "LeverageDataWorker/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Binance returned an unexpected payload: {payload!r}")
    return payload


def fetch_daily(limit: int = LIMIT, end_time_ms: int | None = None) -> list[dict[str, object]]:
    """Fetch the latest daily BTCUSDT spot klines and return canonical rows."""
    params: dict[str, object] = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": min(max(int(limit), 1), LIMIT),
    }
    if end_time_ms is not None:
        params["endTime"] = int(end_time_ms)
    url = f"{BINANCE_KLINES}?{urllib.parse.urlencode(params)}"
    raw = _get(url)
    rows: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, list) or len(item) < 6:
            raise RuntimeError(f"Malformed Binance kline row: {item!r}")
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
    rows.sort(key=lambda row: str(row["timestamp"]))
    return rows


def write_csv(rows: list[dict[str, object]], output: str) -> None:
    """Write canonical rows to CSV with a deterministic column order."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire BTCUSDT daily research data from Binance.")
    parser.add_argument("--rows", type=int, default=500, help="Number of daily rows to request (max 1000).")
    parser.add_argument("--output", default="data/raw/btcusdt_daily.csv", help="Output CSV path.")
    args = parser.parse_args()

    rows = fetch_daily(args.rows)
    if len(rows) < args.rows:
        raise RuntimeError(f"Binance returned only {len(rows)} rows; requested {args.rows}.")
    write_csv(rows, args.output)
    print(f"Saved {len(rows)} BTCUSDT daily rows to {args.output}")


if __name__ == "__main__":
    main()
