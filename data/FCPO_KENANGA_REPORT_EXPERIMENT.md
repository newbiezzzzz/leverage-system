# FCPO Kenanga Public Daily Report Experiment

Date tested: 2026-08-16

## Objective
Evaluate whether Kenanga Futures' publicly accessible FCPO Daily Preview PDFs can supply enough machine-readable historical OHLCV data for Leverage's FCPO research dataset.

## Verified strengths
- Kenanga publishes FCPO Daily Preview reports as public one-page PDFs.
- The reports explicitly identify Bursa Malaysia FCPO and a "CPO Futures 3rd month daily chart".
- The reports contain a contract table with settlement, open-interest change, value and high/low-related fields, plus market commentary and supporting fundamental data.
- Public reports are discoverable for multiple years, including 2024, 2025 and 2026.

## Extraction test result
The PDF text layer is **not sufficient by itself to reconstruct a clean daily OHLCV row for the 3rd-month FCPO contract**. In tested reports, the extracted contract table does not consistently expose all required fields (especially a reliable daily open and unambiguous daily volume for the target 3rd-month row). Some values are present only through chart/layout relationships that should not be guessed from text order.

Example tested report:
- Kenanga FCPO Daily Preview, 1 July 2026
- Public PDF: https://www.kenangafutures.com.my/wp-content/uploads/2026/07/KF-FCPO-Daily-Preview-01-Jul-2026-web.pdf
- The report clearly states the September 2026 contract settled at RM4,542 and contains contract statistics, but the extracted text does not provide a safe full OHLCV record for that day.

## Decision
**Do not promote Kenanga reports to the primary FCPO OHLCV source.**

Keep Kenanga as a **supporting/cross-check source** for:
- contract identity and rollover context
- settlement cross-checks
- market/fundamental context
- future experiments using visual/table extraction when a reliable PDF acquisition path is available

## Next experiment
Investigate sources that expose structured daily FCPO OHLCV directly. TA Futures' public Market Prices page demonstrably exposes FCPO Last/Net Change/Open/High/Low/Volume/Settlement, but the publicly indexed page does not provide a historical archive through the same interface. This is therefore a strong **current-day collector** candidate, not yet a historical backfill source.

## Research gate
No strategy-performance claim is permitted until at least 250 validated rows are sourced with verifiable FCPO/Bursa provenance; 750+ rows remain preferred.
