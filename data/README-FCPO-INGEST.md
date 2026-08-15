# FCPO historical data import

Source target: TradingView `MYX:FCPO1!` (Bursa Malaysia continuous front-month contract).

## Boss action when prompted
1. Open the FCPO1! chart in TradingView.
2. Load as much DAILY history as the chart/account allows by scrolling left.
3. Use **Download chart data…** to export CSV.
4. Put the exported CSV at `data/incoming/fcpo_tradingview.csv`.
5. Do not edit the raw export.

TradingView documents that chart data can be exported to CSV and that more history can be loaded by scrolling left before export.

## Automatic validation
The Leverage Data Worker will reject files that:
- are not identified as Bursa `MYX:FCPO1!` / FCPO data;
- do not contain OHLC columns;
- contain malformed timestamps or prices;
- contain duplicate/out-of-order rows;
- fail the minimum 250-row dataset gate;
- have unexplained gaps or contract-roll discontinuities.

The validated normalized dataset becomes the cached research source. No repeated external API calls are required after import.
