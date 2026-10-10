# FCPO Data-Acquisition Checklist

Objective: acquire authentic, licensed historical data so Leverage can backtest the Owner's later-supplied FCPO strategy. No synthetic candles, no unsupported substitutions, and no paid purchase without explicit Owner approval. Keep this work inside the isolated FCPO backtest project; do not modify Strategy Hunter.

## A. Search and contact

- [ ] Check Portara/CQG's FCPO and MPO listings for sample availability, exact instrument identity, coverage dates, timeframes, contract-month files, continuous-series methodology, roll log, timezone, and CSV schema.
- [ ] Confirm sample download terms before use. Sample data may test ingestion only, not strategy profitability.
- [ ] Request a written quote from Portara/CQG for the smallest useful research-use package: daily and 1-minute OHLCV, individual contracts, continuous series, roll metadata, historical coverage, update fees, storage rights, and any restrictions on local/private use.
- [ ] Ask Bursa Malaysia/Bursa Malaysia Derivatives for equivalent historical futures package options, minimum purchase, available intervals, contract-level coverage, licence terms, and delivery format.
- [ ] Compare the quotes and terms side by side; do not buy or subscribe until the Owner explicitly approves.
- [ ] Check whether the Owner's existing broker/platform supports FCPO CSV export or historical-data API. Verify the actual FCPO symbol, history depth, and permitted use; do not assume stock API support means futures support.
- [ ] Check TradingView export for FCPO1! and individual contract charts. Record the account's actual export/history limits and whether the continuous series is synthetic or adjusted.
- [ ] Continue targeted searches of public archives, GitHub, Kaggle, and daily-history sources. Accept a source only after instrument identity, source provenance, coverage, file access, and licence are verified.
- [ ] If intraday history is not affordable, assess licensed daily bars as a separate fallback for daily strategies only. Do not turn daily OHLC into invented intraday candles.

## B. Source qualification (required before ingestion)

- [ ] Exact exchange/instrument identity confirmed as Bursa Malaysia FCPO or an explicitly justified equivalent.
- [ ] Contract codes/months included are documented.
- [ ] Individual-contract data versus continuous-series data is identified.
- [ ] Continuous roll dates, roll trigger, adjustment method, and roll log are supplied or reconstructible.
- [ ] Bar interval is stated (tick, 1-minute, daily, etc.) and source timestamps are defined.
- [ ] Timezone and daylight/session conventions are documented.
- [ ] First and last timestamps and expected historical coverage are confirmed from an actual sample/file.
- [ ] Licence explicitly permits the intended private research/backtesting use and storage. Redistribution rights are checked separately before committing data to a public repository.
- [ ] Price, volume, adjustment, and missing-bar semantics are documented.
- [ ] Written quote and ongoing costs are recorded if paid.

## C. File ingestion and audit

- [ ] Preserve the original downloaded/exported file unchanged and record its source URL/provider and acquisition date.
- [ ] Compute and record SHA-256 checksum, file size, row count, first/last timestamps, and detected interval.
- [ ] Convert to the canonical CSV schema `timestamp,open,high,low,close,volume` without changing price values; timestamps must carry an explicit timezone or have a documented normalization step.
- [ ] Validate numeric fields, finite values, positive OHLC prices, nonnegative volume, and OHLC consistency.
- [ ] Detect duplicate/out-of-order timestamps and unexpected interval gaps.
- [ ] Audit sessions, holidays, overnight sessions, zero-volume bars, partial first/last bars, and daylight/timezone issues.
- [ ] Check roll boundaries for jumps, duplicate bars, missing contracts, and adjustment artifacts.
- [ ] Compare a sample of bars against the source platform or a second reliable source where possible.
- [ ] Write complete provenance to `data/fcpo/DATA_SOURCE.md`; do not leave placeholders or claim validation passed prematurely.
- [ ] Keep vendor data out of public Git commits unless the licence explicitly permits redistribution. Prefer private storage or an approved artifact location where required.

## D. Engine verification and smoke test

- [ ] Confirm the dedicated FCPO workflow and regression tests pass; record the actual CI run rather than assuming success.
- [ ] Test the parser on a small permitted sample or a small Owner-exported file.
- [ ] Confirm session filtering and 1m-to-5m/15m/30m aggregation do not fabricate incomplete bars.
- [ ] Confirm the same input and strategy produce reproducible outputs.
- [ ] Confirm no look-ahead: signals use only available bars and execution timing follows the declared strategy.
- [ ] Confirm commissions, fees, slippage, contract value and tick size are explicit and sourced/configured, not invented.
- [ ] Confirm individual expiry contracts and continuous series are not accidentally mixed.
- [ ] Label sample-only or short-history runs as ingestion/engine smoke tests, never as evidence of profitability.

## E. Enable an actual user-strategy backtest

- [ ] Obtain the Owner's actual strategy rules or screenshot; do not substitute a generic strategy.
- [ ] Extract rules and ask only material clarification questions.
- [ ] Save a versioned strategy specification with assumptions and unresolved rules clearly marked.
- [ ] Reject unsupported features until implemented and tested; do not silently approximate trailing stops, partial exits, dynamic sizing, queue/fill simulation, or contract rolls.
- [ ] Confirm data coverage is long enough for the strategy and chosen timeframe.
- [ ] Run chronological development/validation/holdout evaluation and walk-forward checks where data allows.
- [ ] Report the sample period, source, trade ledger, monthly results, net/gross P&L, costs, win rate, expectancy, profit factor, drawdown, and limitations.
- [ ] Report contract-level loss risk and margin feasibility separately from the RM1,000 research starting-capital assumption.
- [ ] Keep all work research-only; no broker connection or live orders.

## F. Stop conditions

Stop and mark **BLOCKED** if source identity, permission, contract series, timestamps, or data integrity cannot be verified; if the strategy needs unsupported execution behavior; or if the required timeframe/history is absent. Never fill missing history with generated bars or present an empty-data run as a performance result.

## Current status

- [ ] No verified licensed historical FCPO file is currently recorded for this project.
- [ ] No vendor purchase is authorized by this checklist.
- [ ] Next actions: verify Portara sample and MPO identity; obtain comparable Portara and Bursa quotes; check Owner-platform CSV/export options; continue open-data search; update provenance only after an actual file is received and audited.
