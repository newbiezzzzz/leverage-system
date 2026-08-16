# Leverage Multi-Instrument Technical Strategy Lab — 2026-08-16

## Objective
Find the most robust technical-analysis strategy or small strategy set that can survive across BTCUSDT, XAUUSDT, CL and FCPO. The objective is cross-instrument robustness, not optimization for one market.

## Test universe
| Instrument | Market type | Priority | Data status | Notes |
|---|---|---:|---|---|
| BTCUSDT | Crypto | P1 | Accessible via public Binance historical klines/datasets | 24/7; use exchange-native BTCUSDT spot as benchmark |
| XAUUSDT | Gold spot | P1 | Public GitHub datasets available; provenance must be recorded | Use consistent source/timezone and volume semantics |
| CL | WTI crude futures | P1 | Data-source discovery in parallel | Contract-roll handling required |
| FCPO | Bursa palm-oil futures | P2 | Data-limited | Must not block the other instruments |

## Technical-only benchmark
Initial strategy families:
- Trend following
- Momentum
- Breakout
- Mean reversion
- Volatility/regime filters
- Price action
- Volume confirmation where volume is meaningful
- Multi-timeframe combinations

## Cross-instrument acceptance rule
A candidate strategy is not considered robust merely because it performs well on one market.

Minimum research gate:
- Common rules and implementation across instruments
- In-sample + out-of-sample separation
- Walk-forward validation
- Realistic fees and conservative slippage
- Parameter sensitivity testing
- Market-regime testing
- Prefer candidates that pass on at least 3 of 4 instruments
- A single-market failure does not automatically reject a strategy, but must be explained

## Trading path
Research -> backtest -> out-of-sample -> walk-forward -> paper trade -> controlled live trial.

Real money remains blocked until all safety and robustness gates are passed.

## Data policy
- Prefer RM0/public/authorized sources.
- Do not bypass subscriptions, rate limits, access controls or robots restrictions.
- Preserve raw files and provenance.
- Do not mix different instrument definitions silently.
- For futures, contract-roll rules must be explicit.

## Current priority
Start data acquisition and standardized validation for BTCUSDT, XAUUSDT and CL in parallel while continuing FCPO source discovery. FCPO is a parallel workstream, not the project bottleneck.
