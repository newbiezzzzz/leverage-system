# Strategy Hunter v1 — Data Acquisition Gate

Status: ACTIVE
Date: 2026-09-20
Purpose: establish a reproducible RM0 research dataset before any strategy backtest.

## Hard requirements

1. Historical OHLCV must have documented source/provenance.
2. Universe membership must be point-in-time where possible.
3. Corporate actions must be handled or explicitly documented.
4. Delisted/suspended names must not be silently removed from historical tests.
5. No survivorship-biased "today's winners" universe.
6. No live broker orders.
7. Missing data must be recorded rather than filled invisibly.

## Primary universe

Malaysian listed equities.

Primary asset-level Shariah authority:
Securities Commission Malaysia (SC) Shariah Advisory Council.

SC publishes the Shariah-compliant securities list twice yearly. The 29 May 2026 list is current for the present research date, while historical lists are available for earlier review dates.

## Point-in-time universe construction

Create review-date snapshots for every available SC list.

For a trading date D:
- use the most recent SC effective list whose effective date is <= D;
- do not use a later list;
- preserve the effective date and source document;
- record additions/removals between snapshots.

If historical membership cannot be reconstructed for a date range, mark the affected experiment as LIMITED rather than pretending the universe is point-in-time.

## OHLCV fields

Minimum:
- date
- ticker/code
- open
- high
- low
- close
- volume

Preferred:
- adjusted close or corporate-action events
- suspension flags
- listing/delisting dates
- split/bonus/right issues
- dividend information

## Data-source hierarchy

A source is acceptable only after checking:
- historical depth
- ticker continuity
- missing dates
- corporate actions
- licensing/usage constraints
- reproducibility
- free-tier availability

Potential RM0 sources to investigate:
- Bursa/public data routes
- public repositories that reproduce Bursa daily data
- iSaham API/free access where actually available
- other openly documented sources

No source is automatically accepted merely because it is accessible.

## Dataset QA

Before backtesting:
- duplicate rows = 0
- impossible OHLC relationships = 0
- negative prices/volume = 0 unless source explicitly defines otherwise
- date ordering validated
- trading-calendar gaps classified
- ticker changes mapped where possible
- delisted/suspended names retained where data exists
- random sample manually cross-checked against an independent source

## First test window

Prefer a sufficiently long period covering multiple market regimes.

Minimum target: 2015-01-01 through the latest complete trading day available.

If the free dataset cannot reliably support this window, reduce the window and label the limitation.

## First baseline

Do not optimize yet.

Run fixed, predeclared baselines for:
- momentum
- breakout
- trend following
- shock/reaction

Only after baseline results exist may Optuna search a constrained parameter space.

## Experiment record

Every run must store:
- dataset version/hash
- universe version
- date range
- strategy version
- parameters
- number of variants tried
- transaction-cost assumptions
- slippage assumptions
- in-sample period
- out-of-sample period
- walk-forward method
- total return
- CAGR/annualized return where applicable
- max drawdown
- trade count
- win rate
- profit factor
- turnover
- cost sensitivity
- failure/stress notes

## Current gate

DATA GATE = NOT PASSED

Reason:
A clean point-in-time Malaysian Shariah universe + sufficiently complete OHLCV dataset has not yet been demonstrated.

Next action:
Acquire candidate datasets, compare them, perform QA, and select the best reproducible RM0 dataset before running strategy tests.
