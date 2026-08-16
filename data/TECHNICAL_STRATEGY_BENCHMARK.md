# Technical Strategy Benchmark

## Objective
Find robust technical-analysis strategies that can be used across multiple instruments, not a single overfit strategy for one market.

## Initial universe
- BTCUSDT
- XAUUSDT
- CL
- FCPO

## Discovery design
Use the same rule families, indicator definitions, parameter search boundaries and validation pipeline for every instrument so results are comparable.

### Strategy families
1. Trend following — moving-average structure, ADX-style trend filters.
2. Momentum — rate-of-change, relative-strength style measures.
3. Breakout — Donchian/range/volatility breakouts.
4. Mean reversion — distance from moving averages/bands with regime filters.
5. Volatility/regime — ATR/realized-volatility conditions that gate other strategies.
6. Price action — candle/range structure without discretionary labeling.
7. Volume confirmation — volume expansion/contracting filters where reliable volume exists.
8. Multi-timeframe — higher-timeframe regime + lower-timeframe trigger.

## Common benchmark
Initial discovery should start with a common daily timeframe where possible. Intraday testing is a second phase after the daily benchmark is stable.

### Minimum acceptance gates
- >=250 clean observations for exploratory screening.
- Prefer >=750 daily observations.
- Intraday candidates should use a substantially larger bar count before conclusions.
- Fees and conservative slippage included.
- In-sample and out-of-sample separation.
- Walk-forward validation.
- Parameter sensitivity checks.
- Multiple regime checks.
- At least 3 of the 4 instruments should show compatible robustness before a strategy is treated as cross-market.

## Scoring
Rank by:
- risk-adjusted return
- max drawdown stability
- trade expectancy consistency
- out-of-sample pass rate
- walk-forward pass rate
- cross-instrument pass count
- sensitivity to parameters
- degradation from development to unseen data

Do not rank solely by CAGR or total return.

## First-customer path
Boss is the intended first customer. Passing the benchmark does not automatically mean live deployment. Required sequence:
research -> backtest -> out-of-sample -> walk-forward -> paper trade -> controlled live trial -> monitoring.

Real-money trading remains blocked until the explicit safety gate is passed.
