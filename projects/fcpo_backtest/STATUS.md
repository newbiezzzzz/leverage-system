# FCPO User-Strategy Backtesting — status

- Project ID: P-FCPO-BACKTEST
- Purpose: Owner supplies text or a screenshot/photo; Leverage extracts the exact rules, records ambiguity, creates a versioned JSON spec and backtests that strategy.
- Isolation: separate `projects/fcpo_backtest/` directory and dedicated workflow. Strategy Hunter mission/state/workflows are out of scope and must remain untouched.
- Engine: declarative strategy runner merged to main in PR #36. Supports SMA/EMA/RSI/ATR/Bollinger indicators, nested AND/OR conditions, explicit crossovers/crossunders, next-bar entries, long/short direction, fixed stop/target, opposite-signal/time exits, conservative stop-first collisions, explicit fees/slippage, integer contracts, monthly summaries and chronological 60/20/20 reports.
- Regression suite: tests added for data validation, indicators, crossovers, missing costs, unsupported indicators, collision priority, next-bar execution, costs, monthly metrics, short-side PnL, integer contracts and look-ahead rejection. **Awaiting GitHub Actions result; do not call tests passed until verified.**
- Unsupported rules: trailing stops, partial exits, dynamic risk sizing, order queue/fill simulation and automated contract rolling are not silently approximated; implement them before testing a spec that relies on them.
- Data: no valid licensed/provenanced intraday FCPO dataset has been verified for this project. Runner checks the data file and required provenance fields. No real strategy performance results exist.
- Costs: must be documented in the strategy JSON or explicitly overridden; no invented fee/slippage values.
- Capital: RM1,000 starting capital; one FCPO contract may have stop risk exceeding capital and broker margin remains a separate required check.
- Safety: research-only; no broker integration, live orders or movement of funds.
- Next gates: CI passes; licensed/provenanced data acquired; user submits a strategy; ambiguities resolved; completed strategy spec generated; actual run and report audited.
