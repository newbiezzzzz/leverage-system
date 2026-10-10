# FCPO User-Strategy Backtesting — status

- Project ID: P-FCPO-BACKTEST
- Purpose: Owner provides strategy rules or a screenshot/photo; Leverage extracts the rules, records interpretation, creates a versioned strategy specification, and backtests that supplied strategy.
- Explicitly not: an autonomous strategy-discovery project; not a replacement for Strategy Hunter.
- Isolation: separate directory/workflow; no edits to Strategy Hunter mission state or current project configuration.
- Intake guide: STRATEGY_INTAKE.md
- Strategy template: strategies/strategy_template.json
- Engine: initial runner is still a generic research scaffold and does not yet faithfully execute the full strategy-spec schema. Do not claim user-defined strategy testing is fully implemented until that engine gap is closed and tests pass.
- Data: valid, licensed/provenanced FCPO intraday OHLCV is still required. No real strategy backtest results exist yet.
- Costs: must use documented fees and slippage; unknowns must be labeled, not invented.
- Safety: research-only, no broker integration, no live orders.
- Next implementation: make the runner execute a user-supplied strategy JSON, support the needed indicator/condition and exit rules, validate trade accounting against fixtures, and emit monthly/trade-by-trade results.
