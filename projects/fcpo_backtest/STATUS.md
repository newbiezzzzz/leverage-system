# FCPO Backtesting — initial status

- Project ID: P-FCPO-BACKTEST
- State: BLOCKED_ON_VALID_DATA
- Isolation: implemented on branch project/fcpo-backtesting-isolated; existing Strategy Hunter files and mission state were not edited.
- Data: no valid 1-minute FCPO data has been supplied to this project yet.
- Results: none. No backtest performance metrics have been generated.
- Engine: initial standard-library CSV validator and baseline long-only family comparison are present.
- Timeframes: 5m, 15m, 30m aggregation from 1m input.
- Costs: GitHub repository variables FCPO_FEE_PER_SIDE_RM and FCPO_SLIPPAGE_POINTS must be set to defensible values; zero or guessed costs must not be represented as real broker costs.
- Remaining gates: obtain permitted source data, complete provenance, validate session/gap/contract-roll behavior, test engine against known fixtures, improve trade accounting and train/validation/holdout split, then compare strategy families.
- Safety: research-only; no broker integration or live orders.
