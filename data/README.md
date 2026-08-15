# FCPO historical data pipeline

Project Leverage does not use an unrestricted or paid live FCPO feed.

## Accepted source paths

1. Permitted free/public FCPO historical data that you manually export/import.
2. TradingView FCPO1! chart CSV exports when your account provides the export capability.
3. Other legally downloadable/public FCPO OHLCV datasets that match the data contract.

## Data contract

Required columns:

- timestamp
- open
- high
- low
- close
- volume (optional; defaults to 0)

The research worker reads `data/fcpo_ohlcv.csv` and never calls a market-data API during strategy analysis.

## Important

Do not add broker credentials, API keys, private account data, or scraped data that violates a provider's terms.

A larger dataset is required before a strategy can be considered meaningful. The current seed dataset is only a development fixture and must not be treated as evidence of profitability.
