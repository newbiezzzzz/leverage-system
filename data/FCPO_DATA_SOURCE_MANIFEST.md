# FCPO Data Source Manifest

## Primary market instrument
- Bursa Malaysia Derivatives FCPO
- TradingView symbol: `MYX:FCPO1!` (continuous reference)

## Preferred acquisition path
1. Load the maximum available daily history for `MYX:FCPO1!` in an account that permits viewing/exporting the required history.
2. Export chart data to CSV when the feature is available.
3. Keep the raw CSV unchanged in the acquisition workspace.
4. Import a copy into Leverage.
5. Run validation before any strategy test.

## Official fallback
Bursa Malaysia exposes historical-data information/products for derivatives. Historical-data distribution can be subject to Bursa licensing/permission requirements; Leverage must not bypass those controls.

## Free/public supporting data
- MPOB daily CPO prices
- MPOB monthly production, stocks, exports, imports and FFB prices
- Bursa Malaysia FCPO contract specifications

## Hard rejection rules
- Reject `CPOc1` / CME data as a substitute for Bursa FCPO.
- Reject non-Bursa palm-oil proxies from the strategy dataset.
- Reject malformed or non-monotonic timestamps.
- Reject duplicate bars unless explicitly documented.
- Reject datasets below the minimum research depth gate.

## Research depth gate
- Minimum: 250 validated daily rows
- Preferred: 750+ validated daily rows
- Intraday testing is deferred until daily research has established viable hypotheses.

## Cost rule
- RM0 target for the Leverage research system.
- No paid real-time feed dependency.
- No scraping bypasses.
- Acquire once, cache locally, reuse internally.

## Strategy publication gate
No strategy performance may be presented as evidence until the dataset passes provenance, integrity, depth and instrument-identity checks and the strategy survives out-of-sample and walk-forward validation.
