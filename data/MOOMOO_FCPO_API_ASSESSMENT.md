# Moomoo FCPO API Assessment

Date checked: 2026-08-16

## Decision

**Do not use Moomoo OpenAPI as the FCPO production data source at this time.**

The current official Moomoo API documentation lists Malaysian market securities (stocks, ETFs, warrants, REITs) but does **not** list Malaysian futures as supported market-data products. The authority/quota documentation also states that Japanese and Malaysian futures are unsupported for API market data.

This means `FCPOmain.BMD` may exist in the Moomoo product/app ecosystem, but its availability does not prove that the OpenAPI can retrieve its historical OHLCV data.

## Important distinction

Moomoo's historical K-line API supports date ranges, daily candles, and pagination in general. That capability is real, but the market/contract must first be supported by the account/API market-data authority. General futures support is not enough to establish Bursa Malaysia FCPO support.

## Leverage policy

- Primary zero-cost FCPO source: continue investigating legitimate public/authorized Bursa FCPO historical data.
- TradingView CSV export: keep as a manual fallback, but **do not treat it as RM0 core** because CSV chart export requires a paid plan.
- Moomoo: keep as an **experimental candidate only** and re-check official documentation/release notes periodically.
- Never assume `FCPOmain.BMD` is API-accessible without a successful authorized API response.
- Never scrape or bypass broker/platform restrictions.

## Current blocker

The Leverage dataset gate requires at least **250 validated FCPO OHLCV rows** (750+ preferred), with provenance, source identity, timestamp ordering, OHLCV integrity, and contract-roll checks before strategy performance can be published.

## Next data work

Research and test legitimate RM0/authorized sources that can provide Bursa Malaysia FCPO historical OHLCV at sufficient depth, then route the source into the existing Data Worker validation/cache pipeline.
