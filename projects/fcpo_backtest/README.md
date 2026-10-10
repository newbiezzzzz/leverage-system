# FCPO Backtesting Project (isolated)

## Purpose
A standalone Leverage project for FCPO (Crude Palm Oil Futures) historical-data validation and research backtests on 5-minute, 15-minute, and 30-minute bars. It does not replace or write to the existing Strategy Hunter mission.

## Isolation contract
- Own directory: `projects/fcpo_backtest/`
- Own workflow: `.github/workflows/fcpo-backtest.yml`
- Own input data: `data/fcpo/`
- Own outputs: `artifacts/fcpo_backtest/`
- Must not modify `control_plane/mission_state.json`, `control_plane/leverage_mission.json`, the current decision record, or Strategy Hunter output files.
- Research only; never sends orders or touches broker credentials.
- Workflow runs independently and does not cancel or supersede existing workflows.

## Current verified blocker
The repository's existing `data/fcpo_ohlcv.csv` was previously inspected and contains only a header, no bars. Therefore this project must not publish performance metrics until real, traceable FCPO data is available.

## Input format
Place a CSV at `data/fcpo/fcpo_1m.csv` with columns:
`timestamp,open,high,low,close,volume`

Requirements:
- Timestamp is ISO-8601 with an explicit timezone offset, or documented Malaysia time (Asia/Kuala_Lumpur).
- Rows represent genuine FCPO contract data; record vendor/source, permitted use, contract month/continuous-roll method, timezone, and coverage in `data/fcpo/DATA_SOURCE.md`.
- OHLC values must be positive, high >= open/close/low, low <= open/close/high; timestamps unique and increasing after normalization.
- No synthetic, interpolated, proxy, or unrelated palm-oil data may be used as if it were FCPO.

## Planned research
1. Validate source, schema, gaps, sessions, contract rolls, and coverage.
2. Aggregate valid 1-minute bars into 5m/15m/30m bars without crossing session breaks.
3. Compare trend/momentum, mean-reversion, and volatility-breakout hypotheses.
4. Execute signals no earlier than the next bar; explicitly resolve stop/target collisions conservatively.
5. Deduct commissions/fees and slippage using documented settings; report sensitivity if actual broker costs are unknown.
6. Separate development, validation, and sealed holdout periods; run walk-forward and parameter-stability checks.
7. Report trades/month, wins/losses, win rate, gross/net return, average winner/loser, profit factor, expectancy, costs, and maximum drawdown.
8. Do not qualify a strategy without independent replication and the Leverage mission's risk, feasibility, and Shariah gates.

## Run locally
```bash
python projects/fcpo_backtest/runner.py --input data/fcpo/fcpo_1m.csv --output artifacts/fcpo_backtest
```

If data is absent or empty, the runner emits a blocked status report and exits non-zero. That is not a backtest result.
