# FCPO User-Strategy Backtesting Project

## Purpose
This is a **user-supplied strategy testing bench**, not an autonomous strategy-discovery project. The Owner supplies a strategy in plain language, rules, a chart screenshot, or a photo of written rules. Leverage analyzes it, extracts the exact rules, flags ambiguities, converts it into a structured strategy specification, then runs a reproducible historical backtest.

This project is separate from the existing Strategy Hunter. It must never alter Strategy Hunter's mission state, decision record, datasets, or workflow.

## Owner workflow
1. **Submit strategy:** send a written explanation or image to ChatGPT. Include timeframe if known; missing details may be inferred only when clearly visible/defined.
2. **Extract rules:** Leverage identifies instrument/contract, timeframe, session, indicators and parameters, exact entry conditions, exit conditions, stop loss, take profit/trailing rules, filters, position sizing, and long/short permissions.
3. **Resolve ambiguity:** Leverage lists only the specific details that materially prevent faithful testing. If the image is unclear, ask for a clearer image or the missing rule; do not silently invent rules.
4. **Create versioned spec:** save the interpreted rules in `strategies/<strategy_id>.json` with an explanation of how each visible/written rule maps to a machine rule. Preserve the original user description/image reference where available.
5. **Data gate:** validate genuine FCPO historical data, its source/license, contract months/roll method, timezone, sessions, gaps, and coverage.
6. **Backtest:** execute on the requested timeframe. If the user asks for comparisons, test 5m, 15m and 30m separately. Signals must not use future bars; execution occurs at the next tradable bar unless the user-defined rule explicitly specifies another executable timing.
7. **Report:** show trades per month, wins/losses, win rate, gross/net RM return, monthly average net return, average winner/loser, profit factor, expectancy, maximum drawdown, fees, slippage, sample period, and trade-by-trade ledger.
8. **Validation:** after an initial run, use chronological development/validation/holdout splits, walk-forward checks, and parameter stability where data permits. Report in-sample and out-of-sample separately.

## Rules of integrity
- No fabricated or synthetic historical results. Empty data means BLOCKED, not zero-profit evidence.
- Preserve the supplied strategy's intent. Do not silently replace it with a generic SMA strategy.
- Separate **faithful replication** from **optional improvement variants**; never mix their results.
- If an image is ambiguous, label the interpretation as an assumption and request the missing material detail before claiming an exact replication.
- State whether each cost is sourced, configured, estimated, or unknown.
- FCPO is a futures contract. A one-contract position may be infeasible for RM1,000 due to margin and risk. Report contract-level RM risk and broker/margin feasibility; do not assume fractional contracts.
- No broker connection, live orders, or money movement. Research-only.

## Data
Place licensed/provenanced 1-minute FCPO OHLCV at `data/fcpo/fcpo_1m.csv` with columns `timestamp,open,high,low,close,volume`. Fill in `data/fcpo/DATA_SOURCE.md`. Do not commit vendor data unless redistribution is permitted.

## Strategy specifications
- Template: `projects/fcpo_backtest/strategies/strategy_template.json`
- Intake guide: `projects/fcpo_backtest/STRATEGY_INTAKE.md`
- Output: `artifacts/fcpo_backtest/`

## Current status
The isolated project now includes a declarative user-strategy runner, JSON schema, regression tests, and a workflow that validates the project without pretending a performance test ran. CI must pass before this engine is marked verified. Valid, licensed/provenanced FCPO history and a completed user strategy JSON with documented costs are still required before any real performance result can be produced.

 
## Engine contract

- Run a completed spec with: `python projects/fcpo_backtest/runner.py --strategy projects/fcpo_backtest/strategies/<strategy_id>.json --input data/fcpo/fcpo_1m.csv --output artifacts/fcpo_backtest`.
- Costs are declared in the strategy spec; optional CLI overrides are `--fee-per-side-rm` and `--slippage-points`.
- Implemented indicators: SMA, EMA, RSI, ATR and Bollinger Bands. Conditions support nested AND/OR groups, price/indicator/constant operands, comparisons, crossovers and crossunders.
- Implemented exits: fixed stop/target, opposite signal, time exit, stop/target plus opposite signal, and stop/target plus time exit. If stop and target are touched in one candle, stop is assumed first.
- Signals are evaluated at bar close and entered at the next bar open; adverse slippage is charged explicitly per side. Integer contracts only; FCPO point value is RM25/point/contract.
- Reports include full sample and chronological 60/20/20 development/validation/holdout results, trade ledger, monthly totals, win rate, gross/net return, costs, average winner/loser, PF, expectancy, largest loss, losing streak and drawdown in RM/%.
- Not implemented: trailing stops, partial exits, dynamic risk-based sizing, order queue/fill modelling and automated contract rolling. Unsupported features must be rejected, never approximated silently.
- GitHub Actions validates and tests by default. It runs a performance backtest only when a completed strategy JSON path is explicitly supplied. A blocked report is not a performance result.
