# FCPO Data Provenance — complete before research

- Provider/source URL:
- Date retrieved:
- License/terms permitting this use:
- Instrument/symbol:
- Contract months included:
- Continuous-contract roll method (if applicable):
- Raw timeframe:
- First and last timestamps:
- Timestamp timezone:
- Session convention:
- Missing bars/gaps and handling:
- Corporate/contract adjustments:
- File checksum (SHA-256):
- Person/process that acquired the data:

Do not mark this file complete with placeholders. The runner blocks if this file is absent; reviewers must also verify that these fields are meaningfully filled. Use genuine FCPO data only. Do not commit vendor data unless its license permits redistribution.

## Acquisition status (checked 2026-10-11)

**BLOCKED — no licensed free 1-minute FCPO dataset has been verified for this project.** Do not fill the provenance fields below until a real dataset is obtained and its terms are checked.

- Public vendor lead: Portara lists historical FCPO 1-minute intraday CSV data for purchase and states that its free-tier offer is currently unavailable: https://portaracqg.com/futures/int/fcpo
- Contract reference: Bursa Malaysia's FCPO product booklet specifies a 25-metric-ton contract and RM1 minimum price fluctuation per metric ton (RM25 per tick), with Malaysia-time trading sessions: https://www.bursamalaysia.com/sites/5d809dcf39fba22790cad230/assets/66b1a73ccd34aa39822c2114/20240220_FCPO_Booklet_A4_Lores_Final_draft.pdf
- The official contract specification does not itself provide a downloadable historical intraday dataset.
- Do not use synthetic candles or live-chart screenshots as historical backtest data. Keep the engine blocked until an authentic source file and its license/provenance are recorded.

## Historical-data search log — 2026-10-11

### Result: no complete free dataset verified; free sample lead identified

1. **Portara FCPO 1-minute sample and full history** — https://portaracqg.com/futures/int/fcpo/
   - The page identifies an intraday sample download control and lists the full historical 1-minute dataset from 2007-01-23 through 2014-11-21 as 49.5 MB, CSV. It says the full-history data is sold and the downloader's free tier is currently unavailable.
   - The sample is a potential parser/smoke-test input only. It has not been retrieved into this repository or license-cleared for performance backtesting. The full historical dataset is stale after 2014-11-21 and is not sufficient alone for present-day strategy validation.
   - The provider's documented CSV columns are date, time, open, high, low, close, volume; Malaysia/Singapore UTC+8 is available; continuous data can include contractName and a roll log. These details are useful for the ingestion contract.
2. **Bursa Malaysia Historical Data Packages** — https://www.bursamalaysia.com/market/products-services/information-products/historical-data-packages/
   - Official lead for exchange-sourced historical derivatives data; no free downloadable intraday FCPO file was verified. Bursa's information-services guidelines describe historical data packages as a subscription product and state redistribution requires written permission. Ask the provider for permitted research use and price before using.
3. **TradingView FCPO1! continuous chart** — https://www.tradingview.com/symbols/MYX-FCPO1%21/
   - Useful for visual inspection/current continuous chart, but no freely downloadable raw OHLCV CSV endpoint was verified in this search. A chart display is not a data file.
4. **iFCPO** — https://ifcpo.com.my/futures/FCPO
   - Provides a continuous contract chart and current market information; no bulk historical CSV export was verified.
5. **Commodities-API FCPO endpoint** — https://commodities-api.com/symbols/FCPO
   - Offers API-based historical daily rates since October 2024, but the documented response is a commodity-rate/conversion API rather than a verified exchange-traded FCPO contract OHLCV series. Do not substitute it for FCPO futures candles.

### Next safe action

- Attempt to retrieve the provider's explicitly offered sample for ingestion testing, after confirming sample-use terms. Do not use sample-only data as evidence of strategy profitability.
- Continue seeking an explicitly free, licensed, downloadable FCPO OHLCV dataset with a known contract series and timestamps. Until then, keep real backtesting status BLOCKED.
- If no qualifying free dataset exists, report the cheapest authentic data option and ask the Owner before incurring any cost. Do not make a purchase or subscribe automatically.
