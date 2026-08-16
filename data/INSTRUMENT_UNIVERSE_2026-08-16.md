# Leverage Technical Strategy Lab — Instrument Universe

## Objective
Find robust, primarily technical-analysis trading strategies that can generalize across multiple liquid instruments. The goal is not to discover a magical universal strategy; it is to identify strategies with repeatable, risk-adjusted behavior across distinct market structures.

## Primary instruments

| Instrument | Role | Research status | Data source direction |
|---|---|---|---|
| BTCUSDT | Crypto / 24-7 | Active | Binance public market-data endpoints / other authorized public sources |
| XAUUSDT | Gold / spot-style | Active | Public/authorized gold/FX source; exact feed to be validated |
| CL | WTI crude oil futures | Active | Public delayed/historical references; exact research feed to be validated |
| FCPO | Bursa Malaysia palm-oil futures | Active but data-limited | Dedicated FCPO source hunt continues |

## Why these four
They intentionally span different market structures:
- BTCUSDT: crypto, continuous 24/7 market
- XAUUSDT: precious-metal price behavior
- CL: major energy futures market
- FCPO: regional agricultural commodity futures

A strategy that survives all four is stronger evidence of generality than a strategy optimized on one instrument.

## Strategy philosophy
Technical analysis first. No fundamental inputs are required for the core strategy search. Fundamental/context data may be added later only as a separate experiment and must not leak into the pure-technical benchmark.

Strategy families to test include trend-following, momentum, breakout, mean reversion, volatility/regime filters, price action, volume confirmation, and multi-timeframe combinations.

## Validation gates
1. Clean and provenance-checked data per instrument.
2. Separate development, in-sample and out-of-sample periods.
3. Realistic fees and conservative slippage.
4. Parameter-sensitivity checks.
5. Walk-forward validation.
6. Multiple market-regime checks.
7. Cross-instrument robustness score.
8. Paper trading before any live deployment.

## Cross-instrument score
A strategy is not considered a candidate for Boss's live use merely because it makes money on one market. The research engine should rank strategies by:
- median risk-adjusted return across available instruments
- drawdown stability
- consistency of trade expectancy
- percentage of instruments passing out-of-sample tests
- walk-forward pass rate
- parameter sensitivity
- degradation from backtest to unseen data

## First-customer path
Boss is intended to be Customer #1 after the system demonstrates sufficient robustness. The intended sequence is:
research -> backtest -> out-of-sample -> walk-forward -> paper trade -> controlled live trial -> monitoring.

Real-money trading remains blocked until the safety gate is explicitly passed.

## Important rule
FCPO data scarcity must not block research on BTCUSDT, XAUUSDT, and CL. Instruments can advance independently; the final cross-instrument robustness score updates as each dataset becomes available.
