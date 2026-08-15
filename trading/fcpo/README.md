# FCPO Trading Research

Project 1 for Leverage.

## Objective
Find robust FCPO technical-analysis strategies before any real capital is exposed.

## Research flow
1. Acquire free/public FCPO-compatible historical and fundamental data.
2. Cache data locally before analysis.
3. Generate technical strategy candidates.
4. Backtest with costs and slippage.
5. Reject overfit candidates.
6. Run out-of-sample and walk-forward validation.
7. Paper trade finalists.
8. Only after a separate safety gate may real-money execution be considered.

## Capital policy
Real-money trading is disabled during research and validation.

## Data policy
The system must not depend on a paid real-time FCPO feed, scrape private trading accounts, or hammer public endpoints. External data is fetched conservatively and cached for reuse.

## Initial technical families
- Trend: SMA/EMA crossovers, ADX filters, Donchian breakouts
- Momentum: RSI, stochastic, ROC
- Volatility: ATR, Bollinger Bands, Keltner Channels
- Price action: previous-day breakout, opening-range breakout, breakout/retest
- Volume: expansion and confirmation
- Multi-timeframe: lower-timeframe signal with higher-timeframe trend filter
