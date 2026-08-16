# FCPO Historical Data Source Research — 2026-08-16

## Objective
Find a legitimate, preferably RM0 source for Bursa Malaysia FCPO historical OHLCV with enough depth for Leverage backtesting.

## Findings

| Source | Bursa FCPO identity | Historical OHLCV | Cost | Automation | Decision |
|---|---|---|---|---|---|
| TradingView MYX:FCPO1! | Yes | Yes | CSV export requires paid plan | Manual export | Paid fallback only |
| Moomoo OpenAPI / FCPOmain.BMD | FCPO exists in Moomoo ecosystem, but current OpenAPI market-support documentation does not list Malaysian futures quotation support | General historical K-line API exists | Unknown | Potentially | Experimental / re-check later; not production |
| Bursa Malaysia Historical Data Packages | Yes | Yes | Subscription / request process | Not established as RM0 | Official paid fallback |
| MPOB daily CPO data | Yes, CPO reference data | Daily CPO reference prices, not FCPO OHLCV | Public web access | Can be researched | Fundamental/context feature, not FCPO price replacement |
| Investing.com FCPOc1 | Displays Malaysia palm-oil futures OHLCV | Yes | Free web history | Not accepted | Rejected as primary source because provenance/symbol is not verified as MYX:FCPO1! |
| Portara/CQG | Yes | Yes | Paid | Yes | Paid benchmark, not RM0 |

## Current best path
1. Continue searching for a legitimate public/authorized FCPO OHLCV source that allows sufficient history and local caching.
2. Keep TradingView CSV as a paid/manual fallback only.
3. Keep Moomoo `FCPOmain.BMD` as a periodic re-check candidate because Moomoo's AI documentation suggests historical futures capabilities, but do not rely on it until official API support for Malaysian FCPO is demonstrated.
4. Use MPOB daily CPO and monthly palm-oil statistics as contextual/fundamental features once the FCPO price series is solved.

## Research gate
- Minimum 250 validated FCPO OHLCV rows.
- Preferred 750+ daily rows.
- Instrument identity and provenance required.
- OHLCV integrity, timestamp order, gaps and continuous-contract roll handling must be checked.
- No scraping bypasses, private broker scraping or licensing workarounds.
- Real-money trading remains blocked.

## Web evidence
- Bursa Malaysia identifies Historical Data Packages as archived market data covering derivatives; enquiries/subscriptions are handled through Bursa Information Services.
- MPOB publishes daily CPO reference prices and monthly industry statistics.
- Portara offers historical FCPO daily/intraday data commercially; its free tier is currently unavailable.
