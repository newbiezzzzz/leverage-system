# BTCUSDT User-Strategy Backtesting Project

## Purpose
A separate, research-only bench for backtesting strategies supplied by the Owner in text or screenshots. It is not the autonomous Strategy Hunter and must not change Strategy Hunter state, workflows, data, or decisions.

## Owner workflow
1. Submit strategy rules in plain language or an image.
2. Extract instrument type (spot or USDT-margined perpetual), timeframe, indicators, entry/exit, stops/targets, filters, sizing, and costs.
3. Record material ambiguities; never silently invent rules.
4. Save a versioned machine-readable strategy JSON.
5. Validate genuine BTCUSDT candles, source/terms, timeframe, UTC timestamps, gaps, duplicates, and coverage.
6. Run the strategy with signal-on-close / entry-at-next-bar-open unless the user's rule requires another supported model.
7. Report trades/month, wins/losses, win rate, gross/net USDT, average monthly net return, average winner/loser, profit factor, expectancy, maximum drawdown, costs, sample dates, and trade ledger.
8. Keep chronological development/validation/holdout results separate. Do not tune on the holdout.

## Historical data
Binance public data archive is the initial free source candidate:
- Spot archive: https://data.binance.vision/data/spot/
- USDⓈ-M futures archive: https://data.binance.vision/data/futures/um/
- API docs: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints

Use 1-minute klines as the raw format for resampling. Download begins 2023-01-01 for EMA warm-up; the active EMA50/EMA200 experiment is evaluated from 2024-01-01 through the latest available date. Use one market type consistently; do not mix spot and perpetual prices. Store files locally or as workflow artifacts rather than committing bulk vendor data. Record source, retrieval date, applicable terms, symbol, market type, timeframe, timestamp timezone, coverage, session convention, and SHA-256 in data/btcusdt/DATA_SOURCE.md. A visible chart is not proof that a downloadable dataset was successfully retrieved.

Expected CSV columns: timestamp,open,high,low,close,volume. Timestamps must be ISO-8601 with explicit timezone. BTCUSDT trades 24/7; empty sessions mean no time filter. Only complete contiguous 1-minute buckets are resampled.

## Supported rules
Indicators: SMA, EMA, RSI, ATR and Bollinger Bands. Conditions support nested AND/OR groups, price/indicator/constant operands, comparisons and crossovers. Supported exits include fixed stop/target, opposite signal and time exit combinations. If a rule is unsupported, reject it explicitly instead of approximating silently.

Stops may be absolute quote-currency points or a percentage of entry price; an R-multiple target is calculated from that position's stop distance. Fees are a fraction of traded notional per side; slippage is basis points per side. These are configuration assumptions and must be documented, not assumed to be actual exchange fees. Position quantity is BTC and can be fractional. Spot mode does not allow shorting in live trading; short-side research must be explicitly marked as a theoretical model or use a derivatives dataset. Perpetual funding, liquidation, maintenance margin, exchange filters, order-book impact, and exact fills are not yet modeled, so perpetual results are approximate until those are implemented.

## Integrity
- No fabricated or synthetic historical results.
- Missing/empty data means BLOCKED, not zero-profit evidence.
- Preserve supplied strategy intent; do not substitute a generic strategy.
- Keep faithful replication separate from optional variants.
- Research only: no broker connection, live orders, or money movement.

## Run
```bash
python projects/btcusdt_backtest/runner.py --strategy projects/btcusdt_backtest/strategies/strategy_template.json --input data/btcusdt/btcusdt_1m.csv --output artifacts/btcusdt_backtest
```
A performance run requires a completed strategy JSON, valid CSV, and complete data-provenance note.


Historical acquisition is validated by a separate GitHub Actions run; do not treat a planned download as retrieved until its report artifact confirms row count and coverage.\n


## First screenshot-derived BTCUSDT experiment
The active strategy formalizes a daily long-only EMA50 cross-above EMA200 signal and executes on the next daily candle open. The screenshot does not specify a stop distance or numeric reward-to-risk value, so the initial assumption-based grid compares 3%, 5%, and 8% stop distances with 1R, 1.5R, 2R, and 3R targets. The predeclared reference profile is 5% stop / 2R. Variant selection uses development and validation metrics only; the holdout is only reported for the predeclared reference profile, not repeatedly searched. The experiment uses spot candles, 0.005 BTC fixed quantity, a 0.10% fee per side (standard regular-user baseline), and 10 bps slippage per side. These cost settings are assumptions and should be updated to match the actual account/order route. This is research only, not a Shariah certification or live-trading signal.
