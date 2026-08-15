# FCPO Data Source Policy

## Objective
Build a zero-upfront-cost FCPO research dataset without depending on a paid real-time exchange feed.

## Primary public/reference sources

1. Bursa Malaysia
   - Contract specification and trading rules.
   - Use for authoritative contract mechanics, tick value, expiry and session rules.
   - Fetch only when specifications change.

2. MPOB
   - Daily CPO price reference.
   - Monthly production, stocks, exports, imports and FFB data.
   - Collect at low frequency and cache permanently.

3. Public FCPO historical reference
   - Investing.com FCPOc1 exposes free historical OHLC data for selected date ranges.
   - Treat as a reference/import source, not as an unlimited automated API.
   - Any acquired dataset must be cached locally and reused for analysis.

4. Optional fallback research connector
   - AkShare documents a FCPO symbol (FCPO) in its futures-data interfaces.
   - Use only as a fallback acquisition method if the source is accessible and its usage terms permit it.
   - Never poll continuously; one controlled acquisition followed by local caching.

## Data acquisition rules

- No live-order execution.
- No paid real-time dependency.
- No credentials stored in the repository.
- No repeated download for an unchanged date range.
- Cache raw data before transformation.
- Record source, acquisition time and date coverage.
- If a source is unavailable or rate-limited, switch to the next permitted source or wait for the next scheduled acquisition window.
- Never fabricate missing market observations.

## Research dataset target

Required columns:

`timestamp, open, high, low, close, volume`

Preferred timeframes:

`5m, 15m, 1h, 4h, 1d`

The first trustworthy backtest should not start until enough historical coverage exists to support both in-sample and out-of-sample testing plus walk-forward validation.
