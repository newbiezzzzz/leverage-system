# FCPO Trading Research — Initial Research Pack

## Project objective

Project 1 is now **FCPO trading research**. The system must build evidence first, then paper-trade, then validate risk/strategy, and only after a separate safety gate consider live money.

## Instrument facts

- Exchange: Bursa Malaysia Derivatives (BMD)
- Contract code: FCPO
- Underlying: Crude Palm Oil
- Contract size: 25 metric tons
- Minimum price fluctuation: RM1 per metric ton
- Therefore, one minimum tick is RM25 per contract.
- Contract months: spot month + next 11 succeeding months, then alternate months up to 36 months ahead.
- Regular sessions: Monday-Friday, 10:30-12:30 and 14:30-18:00 Malaysia time.
- After-hours (T+1): Monday-Thursday, 21:00-23:30 Malaysia time.
- Price-limit mechanism includes a 10% limit and, when triggered, a cooling-off/reservation process that can expand the limit to 15% for eligible future-delivery contracts.

Official source: Bursa Malaysia FCPO contract specifications.
https://www.bursamalaysia.com/sites/5d809dcf39fba22790cad230/assets/605322fb5b711a61ee8be2ae/BURSA_FCPO_Contract_Spec_EN_digital.pdf

## Public market reference

TradingView exposes Bursa Malaysia FCPO continuous and individual contract pages. The FCPO1! page provides a public market reference and exposes contract-month pages such as FCPOU2026 (September 2026) and FCPOV2026 (October 2026).

https://www.tradingview.com/symbols/MYX-FCPO1!/

The public page also exposes volume and open-interest fields, which are useful research variables. Public values may be delayed or dependent on the user's market-data entitlement, so Leverage must label source freshness instead of treating the page as an unrestricted real-time API.

## Fundamental research sources

### Bursa Malaysia

Use for contract specifications, exchange rules, trading sessions, price-limit mechanics and official product information.

https://www.bursamalaysia.com/

### MPOB

Use for Malaysian palm-oil fundamentals such as production, stocks, exports, imports, and related industry statistics. These variables can be aligned to FCPO price action to test whether fundamental shocks contain predictive information.

https://bepi.mpob.gov.my/

### Global palm-oil benchmark / macro

FRED publishes IMF-based palm-oil price series that can be used for longer-horizon context and regime analysis.

https://fred.stlouisfed.org/

## Research questions

1. What FCPO market regimes can be identified using price, volatility, volume and open interest?
2. Does FCPO momentum persist across intraday or daily horizons?
3. Does mean reversion work after large moves?
4. Do production, stocks and export changes from MPOB help explain or predict FCPO moves?
5. Does the relationship between FCPO and broader palm-oil benchmarks improve signal quality?
6. Which trading sessions have materially different volatility or trend characteristics?
7. How much does transaction cost, slippage and the RM25 minimum tick affect a strategy's edge?
8. Which features remain useful after out-of-sample testing and walk-forward validation?

## Zero-cost architecture

The permanent core will not depend on a paid live exchange feed.

**Free/authorized research inputs → Data Worker → cached dataset → Code Worker backtests → AI Manager evaluates evidence → paper trading → safety gate**

The system must not scrape private broker accounts or assume unlimited exchange data. When a source is unavailable or quota-limited, the dashboard must show the limitation and switch to a lower-cost fallback instead of repeatedly retrying.

## Current decision

Do not trade real FCPO yet.

Do not build a live execution bot yet.

First build the FCPO dataset and research baseline, then test simple strategies, then paper trade them, then measure robustness and drawdown.

## Research status

**FCPO research engine: ACTIVE**

Next research deliverables:

1. FCPO historical price dataset and source audit.
2. MPOB fundamental dataset and release-date alignment.
3. Feature engineering: returns, ATR, volatility, volume, open interest, session effects, regime labels.
4. Baseline strategies with strict out-of-sample testing.
5. Paper-trading journal and risk metrics.
