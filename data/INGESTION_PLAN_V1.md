# Multi-Instrument Ingestion Plan V1

## Objective
Get enough clean daily OHLCV history into the canonical contract for BTCUSDT, XAUUSDT and CL while FCPO remains a parallel data-discovery track.

## Sequence
1. BTCUSDT — Binance public klines. Start with spot BTCUSDT daily data; optionally add USD-M futures as a separate series later.
2. XAUUSDT — validate a public XAUUSD daily dataset; do not mix OTC/CFD feed identities.
3. CL — validate WTI futures data and document continuous-contract roll construction before comparison.
4. FCPO — continue source discovery until Bursa/FCPO identity and provenance pass.

## Dataset gate
- Exploratory minimum: 250 daily rows.
- Preferred: 750+ daily rows.
- Required before benchmark results: timestamp integrity, OHLC integrity, duplicate check, missing-date report, source provenance, instrument identity.

## Strategy-engine requirement
The strategy engine must accept only the canonical normalized schema and instrument metadata. It must never contain market-specific parsing logic.

## First benchmark
Daily timeframe. Technical-only signals. Same logic across markets where semantics allow. Fees/slippage are instrument-specific inputs, not hard-coded into signal logic.
