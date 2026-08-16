# Leverage Data Source Matrix — 2026-08-16

## Goal
Provide enough clean historical OHLCV data for the four-market Technical Strategy Lab without making FCPO block the other instruments.

| Market | Research symbol | Preferred benchmark | Zero-cost/public candidate | Current status |
|---|---|---|---|---|
| Crypto | BTCUSDT | Binance spot BTCUSDT | Binance historical klines / public downloadable datasets | READY TO INGEST |
| Gold | XAUUSDT | XAUUSD spot benchmark | Public GitHub XAUUSD OHLCV datasets; e.g. ork-ad sample and FeziweMelvin history | READY TO VALIDATE |
| Crude | CL | NYMEX WTI continuous/front-month benchmark | Public CL/WIT historical sources; TradersUnion exposes CL/USD history and CSV download; more rigorous continuous-contract source still to be selected | SOURCE VALIDATION |
| Palm oil | FCPO | Bursa Malaysia FCPO | Current zero-cost structured historical source not yet verified | BLOCKED |

## Important instrument rules

### BTCUSDT
Use exchange-native Binance spot BTCUSDT for the benchmark. Keep timezone UTC and use completed candles only.

### XAUUSDT
The research label remains XAUUSDT, but the data benchmark is XAUUSD spot because the underlying economic instrument is gold priced in USD. Broker-specific XAUUSDT/USDT contract feeds can later be used as an execution-validation layer.

### CL
CL means NYMEX WTI crude oil futures. Do not silently substitute EIA WTI spot data for futures. A spot series may be used as a separate context series, but strategy performance labelled CL must use a clearly defined futures series with explicit roll methodology.

### FCPO
FCPO means Bursa Malaysia Crude Palm Oil Futures. Do not use generic palm oil/CPO spot or unrelated futures as the FCPO benchmark.

## Common dataset contract
Required normalized columns:
`timestamp, open, high, low, close, volume`

Required metadata:
`instrument, source, source_url, timeframe, timezone, contract_definition, retrieval_date, provenance_status`

Validation gates:
- OHLC relationships valid
- no duplicate timestamps
- monotonic timestamps
- no impossible negative prices
- volume parsing correct
- session/calendar rules documented
- futures contract roll rules documented for CL/FCPO
- source identity independently checked

## Strategy-lab rule
A strategy must be tested with the same signal definitions and equivalent data assumptions across BTCUSDT, XAUUSDT, CL and FCPO. Strategy ranking is based on robustness across instruments, not the best single-market result.

## Priority
Start with BTCUSDT and XAUUSDT immediately; validate CL in parallel; continue FCPO source discovery without blocking the lab.
