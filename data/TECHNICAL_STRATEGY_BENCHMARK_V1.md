# Technical Strategy Benchmark V1

## Mission
Find technical-analysis strategies that are robust enough to work across BTCUSDT, XAUUSDT, CL and eventually FCPO, so the same strategy can become a candidate for Boss's own trading system.

## Core principle
We are looking for **cross-instrument robustness**, not the highest backtest return on one asset.

## Strategy families V1
1. Trend following: SMA/EMA cross, slope, moving-average regime
2. Momentum: ROC, RSI momentum, multi-lookback momentum
3. Breakout: Donchian/high-low breakouts, range expansion
4. Mean reversion: RSI/BB reversion, z-score style setups
5. Volatility/regime: ATR and realized-volatility filters
6. Price action: break/retest, range compression/expansion
7. Volume confirmation: only where the source volume is meaningful
8. Multi-timeframe confirmation

## Common test protocol
- Start with daily timeframe for a clean cross-market comparison.
- Later test 1H only after the daily benchmark is stable.
- Use identical signal logic across all instruments where semantics allow.
- Include realistic fees and conservative slippage.
- Separate in-sample and out-of-sample data.
- Use walk-forward validation.
- Test parameter sensitivity.
- Test multiple market regimes.
- Record number of trades, CAGR/annualized return, max drawdown, Sharpe/Sortino where appropriate, profit factor, win rate, average trade, exposure and stability.

## Cross-market gate
A candidate becomes **Cross-Market Robust** when:
- It passes the implementation/data-quality checks on all available markets.
- It is profitable or otherwise materially useful on at least 3 of 4 markets.
- It survives out-of-sample testing on the passing markets.
- It does not depend on a narrow parameter setting.
- Its edge remains after fees/slippage assumptions.

A strategy failing one market is not automatically discarded; the failure must be analysed for market-specific structure or data issues.

## Safety gate
- Research only until validation gates pass.
- Paper trading before any real-money trial.
- No automatic live execution.
- Boss becomes Customer #1 only after the strategy has evidence from unseen data and paper trading.

## Current phase
Data acquisition and standardized validation for BTCUSDT, XAUUSDT and CL. FCPO remains a parallel workstream and must not block the research engine.
