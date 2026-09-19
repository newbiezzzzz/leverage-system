# Strategy Hunter data acquisition

## Purpose

Build a reproducible, RM0 candidate dataset before any backtest.

### Step 1 — Shariah snapshots

Run:

    python build_shariah_universe.py

The script discovers SC Malaysia's historical Shariah-list PDFs from the official
SC list page, records the PDF hash and effective date, and extracts Table 1
(stock-code membership) into:

    data/shariah/shariah_snapshots.csv

### Step 2 — OHLCV

Run:

    python download_ohlcv.py

This uses yfinance as a candidate free acquisition route and saves one CSV per
symbol. It is not automatically considered authoritative. QA and an independent
cross-check are mandatory.

## Important limitations

- Yahoo/yfinance availability and historical coverage can change.
- Corporate actions and ticker changes need independent verification.
- A historical SC list is authoritative for its stated effective date, but
  extracting stock codes from PDFs is an automated convenience and must be QA'd.
- No current Shariah list is applied backwards.
- No strategy result may be produced until the data QA gate passes.

## Smoke-test trigger

A data-pipeline change on the main branch should trigger the GitHub Actions
smoke test before the full dataset is attempted.
