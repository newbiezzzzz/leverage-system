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
