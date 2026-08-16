# Multi-Instrument Data Source Matrix V2

Updated: 2026-08-16

| Instrument | First source | Access | Current status | Notes |
|---|---|---|---|---|
| BTCUSDT | Binance public historical klines | Public | READY TO INGEST | Binance publishes downloadable historical klines and documents spot/USD-M futures data. Choose one market definition and keep it consistent. |
| XAUUSDT | Public XAUUSD historical dataset | Public dataset | CANDIDATE | Public GitHub datasets contain thousands of daily rows; provenance and exact feed semantics must be checked before validation. |
| CL | Public WTI/CL historical dataset | Public dataset | CANDIDATE | Must distinguish spot/CFD from actual WTI futures and document continuous-contract construction/rolls. |
| FCPO | Public/authorized Bursa/FCPO source | Not solved | BLOCKED | Continues in parallel. No FCPO source has passed identity + provenance + depth gate. |

## Priority
1. Ingest BTCUSDT first because the source is highly structured and directly downloadable.
2. Validate XAUUSD candidate and ingest second.
3. Validate CL candidate and define continuous-contract handling.
4. Continue FCPO discovery without blocking the other three.

## Common minimum
For daily strategy research, target at least 750 rows per instrument where available. 250 is the minimum exploratory gate.

## Important distinction
A public dataset is not automatically a validated trading feed. Each instrument requires identity, provenance, schema, OHLC integrity, timestamp and coverage checks before strategy results can be promoted.
