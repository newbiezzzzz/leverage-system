# FCPO Data Sources & Cost Policy

## Primary research data

1. Investing.com FCPOc1 historical data — public historical daily OHLC/volume view. Use only through permitted viewing/export functionality; do not scrape aggressively or treat the page as an unlimited API.
2. MPOB — official daily CPO prices and monthly Malaysian palm-oil industry data (production, stocks, exports, imports, FFB prices).
3. Bursa Malaysia — official FCPO contract specifications and market-structure/reference information.

## Zero-cost policy

- No paid real-time feed dependency.
- No brokerage login dependency.
- No API key required for the research worker.
- External data is acquired only when permitted and then cached locally.
- Backtests must run from cached local data so repeated strategy tests create no external requests.
- If a source introduces a quota, licensing restriction, or access failure, the worker enters SAFE MODE and does not fabricate data.

## Required OHLCV format

`timestamp,open,high,low,close,volume`

Recommended coverage: continuous daily and intraday FCPO data with explicit contract/roll metadata where available.

## Important futures-data rule

Do not mix contract months blindly. A continuous series must document its roll rule and adjustment method. Strategy validation should separately verify results on individual contracts where feasible.
