# Investing FCPOc1 Provisional Research Policy

## Purpose
Unblock Leverage FCPO research without treating a convenient public feed as production/live-trading evidence.

## Source
- Provider: Investing.com
- Instrument label: FCPOc1 / Palm Oil (Kuala Lumpur)
- Role: provisional research/backtest dataset
- Confidence: medium until independently cross-checked

## Allowed use
- Exploratory data analysis
- Indicator development
- Strategy screening
- Backtesting
- Out-of-sample and walk-forward experiments

## Not allowed
- Live trading decisions
- Broker order generation
- Claims that a strategy is validated for real money
- Treating the source as equivalent to official Bursa historical data

## Research gates
1. Preserve raw exported data unchanged.
2. Record source URL, export timestamp, symbol label, date range, and file hash.
3. Validate schema, duplicate dates, OHLC relationships, missing values, and volume parsing.
4. Minimum 250 clean rows before strategy-performance summaries.
5. Prefer 750+ rows for serious robustness work.
6. Independently cross-check a sample of dates against at least one additional FCPO source before any paper-trading gate.
7. Real-money gate remains blocked regardless of backtest results until the data provenance and strategy robustness gates are satisfied.

## Acquisition
Use the platform's own export/access mechanism where available. Do not bypass authentication, subscriptions, technical controls, or robots restrictions.

## Promotion rule
Investing FCPOc1 may be promoted from provisional to validated research data only after independent identity and historical-value cross-checks pass the Data Worker quality gate.
