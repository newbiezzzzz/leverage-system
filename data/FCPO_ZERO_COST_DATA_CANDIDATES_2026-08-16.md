# FCPO zero-cost data candidates — 2026-08-16

## Candidate A — Public QuantConnect custom CSV reference

A public QuantConnect FCPO custom-data example references an external CSV URL hosted on Dropbox and parses fields for `Open`, `High`, `Low`, `Close`, and `Volume`. The example includes an FCPO record dated 2011-09-13 and runs an FCPO strategy over 2019, demonstrating that the referenced dataset was intended for multi-year FCPO research. Source: QuantConnect embedded backtest / custom data example.

Reference URL mentioned by the public QuantConnect example:
`https://www.dropbox.com/s/ivtywe3avc4m1mn/fcpo.csv?dl=1`

Status: **PUBLIC LEGACY DATASET CANDIDATE — NOT YET INGESTED**

Strengths:
- Zero-cost/public link in a public research example.
- Explicit OHLCV schema.
- Contains historical FCPO data from at least 2011 and was used for a 2019 backtest.

Cautions:
- The underlying Dropbox file could not be downloaded from the current worker environment, so coverage and current availability have not been independently verified.
- The public example does not establish the original licensing/provenance of the CSV.
- Do not promote to production/live-trading data until provenance, integrity, and coverage are verified.

## Research policy

This candidate can be used only as a **legacy exploratory dataset** if the file can be obtained legally and its provenance is documented. It must not be mixed silently with current FCPOc1 data. Any strategy discovered on this dataset must later be re-tested on an independent, newer FCPO source before paper trading.

## Next test

1. Verify public file availability through an approved access path.
2. Download without bypassing access controls.
3. Compute row count/date coverage and validate OHLCV schema.
4. Check several overlapping dates against independent FCPO references.
5. If clean, load as `legacy_fcpo_ohlcv` and use for preliminary strategy research while current-data acquisition continues in parallel.
