"""BTCUSDT daily ingestion adapter using Binance public market-data services.

Primary source: Binance public market-data REST endpoint. If the REST endpoint
is unavailable (for example HTTP 451 from a runner region), the adapter falls
back to Binance's public historical kline archive at data.binance.vision.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASES = [
    "https://data-api.binance.vision/api/v3/klines",
    "https://api.binance.com/api/v3/klines",
]
ARCHIVE_BASE = "https://data.binance.vision/data/spot/monthly/klines"
INTERVAL = "1d"
SYMBOL = "BTCUSDT"
LIMIT = 1000


def _get_json(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LeverageDataWorker/1.1", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Binance returned an unexpected payload: {payload!r}")
    return payload


def _http_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "LeverageDataWorker/1.1"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def _canonical_rows(raw: list[Any]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, list) or len(item) < 6:
            raise RuntimeError(f"Malformed Binance kline row: {item!r}")
        rows.append(
            {
                "timestamp": datetime.fromtimestamp(float(item[0]) / 1000, tz=timezone.utc).isoformat(),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            }
        )
    rows.sort(key=lambda row: str(row["timestamp"]))
    return rows


def _fetch_api(limit: int) -> list[dict[str, object]]:
    last_error: Exception | None = None
    for base in API_BASES:
        params = urllib.parse.urlencode({"symbol": SYMBOL, "interval": INTERVAL, "limit": min(max(limit, 1), LIMIT)})
        url = f"{base}?{params}"
        try:
            return _canonical_rows(_get_json(url))
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
            last_error = exc
    raise RuntimeError(f"All Binance REST endpoints failed: {last_error}")


def _month_urls(year: int, month: int) -> tuple[str, str]:
    stamp = f"{year:04d}-{month:02d}"
    path = f"{ARCHIVE_BASE}/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{stamp}.zip"
    return path, path.replace("/monthly/", "/daily/")


def _read_archive_csv(data: bytes) -> list[dict[str, object]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError("Archive contains no CSV")
        with archive.open(names[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8")
            reader = csv.reader(text)
            rows = list(reader)

    if rows and rows[0] and rows[0][0].strip().lower() in {"open time", "open_time", "timestamp"}:
        rows = rows[1:]

    out: list[dict[str, object]] = []
    for row in rows:
        if len(row) < 6:
            continue
        out.append(
            {
                "timestamp": datetime.fromtimestamp(float(row[0]) / 1000, tz=timezone.utc).isoformat(),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    return out


def _fetch_archive(target_rows: int) -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    collected: list[dict[str, object]] = []
    year, month = now.year, now.month

    for _ in range(24):
        monthly_url, daily_url = _month_urls(year, month)
        loaded = False
        for url in (monthly_url, daily_url):
            try:
                collected.extend(_read_archive_csv(_http_bytes(url)))
                loaded = True
                break
            except (urllib.error.HTTPError, urllib.error.URLError, zipfile.BadZipFile, RuntimeError):
                continue
        if not loaded and collected:
            # Older archive data is optional once enough history is accumulated.
            pass

        if len(collected) >= target_rows:
            break
        month -= 1
        if month == 0:
            month, year = 12, year - 1

    collected.sort(key=lambda row: str(row["timestamp"]))
    # Deduplicate archive overlaps and retain the newest requested rows.
    deduped = {str(row["timestamp"]): row for row in collected}
    rows = [deduped[key] for key in sorted(deduped)]
    return rows[-target_rows:]


def fetch_daily(limit: int = LIMIT) -> list[dict[str, object]]:
    """Fetch daily BTCUSDT rows, using REST first and archive fallback."""
    try:
        rows = _fetch_api(limit)
        print("SOURCE: Binance public market-data REST")
        return rows
    except RuntimeError as rest_error:
        print(f"REST unavailable: {rest_error}")
        rows = _fetch_archive(limit)
        if len(rows) < limit:
            raise RuntimeError(f"Archive returned only {len(rows)} rows; requested {limit}.")
        print("SOURCE: Binance public historical archive")
        return rows


def write_csv(rows: list[dict[str, object]], output: str) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire BTCUSDT daily research data from Binance.")
    parser.add_argument("--rows", type=int, default=500, help="Number of daily rows to request (max 1000).")
    parser.add_argument("--output", default="data/raw/btcusdt_daily.csv", help="Output CSV path.")
    args = parser.parse_args()

    if args.rows < 1 or args.rows > LIMIT:
        raise SystemExit(f"--rows must be between 1 and {LIMIT}")

    rows = fetch_daily(args.rows)
    if len(rows) < args.rows:
        raise RuntimeError(f"Binance returned only {len(rows)} rows; requested {args.rows}.")
    write_csv(rows, args.output)
    print(f"Saved {len(rows)} BTCUSDT daily rows to {args.output}")


if __name__ == "__main__":
    main()
