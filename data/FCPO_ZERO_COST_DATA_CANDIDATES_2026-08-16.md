# FCPO zero-cost data candidates — 2026-08-16

## Candidate A — QuantConnect/Dropbox CSV: REJECTED

A public QuantConnect FCPO custom-data example referenced an external Dropbox CSV and documented OHLCV parsing. Its example values were `7792.9 / 7799.9 / 7722.65 / 7748.7 / 116534670`.

Those exact OHLCV values are independently published as **NIFTY historical data**, not FCPO. This means the public example does not establish trustworthy FCPO instrument identity for the referenced file. Leverage therefore rejects this candidate rather than risking contamination of the FCPO research dataset.

Evidence:
- QuantConnect source: https://www.quantconnect.com/terminal/cache/embedded_backtest_13ef97bbe59e03f051b1dd23285f45bc.html
- Independent historical NIFTY evidence with matching values: https://indianjournalofcomputerscience.com/index.php/ijrcm/article/download/103700/76866/241333

Decision: **REJECTED — likely mislabeled/non-FCPO data**

## Current status

The zero-cost FCPO historical-data bottleneck remains open.

Primary current candidate:
- Investing.com FCPOc1 / Palm Oil (Kuala Lumpur, MYR), provisional research source. Free historical data and free-account export are documented, but Boss does not yet have a completed zero-cost acquisition path.

Supporting sources:
- Kenanga Futures FCPO Daily Preview PDFs — context/cross-check only.
- TA Futures Market Prices — current-day structured FCPO fields; historical backfill not established.

## Research policy

No dataset enters the FCPO backtest engine until provenance, instrument identity, OHLCV integrity, date coverage and duplicate checks pass. No strategy-performance claim, paper trading, or live trading can proceed from a source that fails these gates.
