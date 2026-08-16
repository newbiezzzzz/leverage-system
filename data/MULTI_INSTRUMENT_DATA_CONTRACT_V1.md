# Multi-Instrument Data Contract V1

## Purpose
Normalize BTCUSDT, XAUUSDT, CL and FCPO into one technical-strategy research format so strategy logic is instrument-agnostic.

## Canonical fields
- `timestamp_utc`
- `instrument`
- `source_symbol`
- `market_type`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume` (nullable)
- `source_name`
- `source_url`
- `timezone_original` (nullable)
- `contract_id` (nullable)
- `roll_group` (nullable)
- `data_tier`

## Rules
1. All timestamps are normalized to UTC.
2. OHLC must satisfy `high >= max(open, close, low)` and `low <= min(open, close, high)`.
3. Duplicate timestamps for the same instrument/source-series are rejected.
4. Missing dates are recorded; they are not silently forward-filled.
5. Volume is preserved when meaningful. Strategies must not use volume where the source semantics are incompatible.
6. Every dataset keeps immutable provenance metadata.
7. Continuous futures series (CL and FCPO) must record contract/roll metadata separately from spot/crypto series.
8. Daily V1 is the benchmark timeframe. Intraday follows only after the daily benchmark is stable.
9. Data tiers:
   - `provisional`: suitable for exploratory research, not for paper/live decisions.
   - `validated`: passes provenance, identity, schema and integrity checks.
   - `production_candidate`: validated plus independent cross-source agreement on sampled dates.

## Instrument definitions
### BTCUSDT
- Target: Binance BTCUSDT spot or USD-M futures, explicitly labeled.
- Do not mix spot and perpetual futures silently.

### XAUUSDT
- Target: XAU/USD or XAU/USDT series with clearly documented price semantics.
- Source identity and timezone must be recorded because OTC/CFD feeds can differ.

### CL
- Target: WTI crude oil futures.
- Continuous-series construction must document front/second contract and roll methodology.

### FCPO
- Target: Bursa Malaysia FCPO.
- Current phase is source discovery; no dataset enters validation until Bursa/FCPO identity is proven.

## Research safety
No dataset can unlock paper/live trading by itself. Strategy validation still requires out-of-sample, walk-forward, parameter sensitivity, realistic fees/slippage and cross-instrument robustness.
