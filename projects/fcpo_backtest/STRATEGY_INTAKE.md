# User Strategy Intake Protocol

When the Owner provides text or a photo, create a new strategy ID and produce these outputs.

## A. Faithful rule extraction
Record:
- Source: written rules, chart screenshot, or photo; retain original wording/visual evidence where available.
- Instrument and contract type: FCPO; specify dated contract or continuous series.
- Timeframe(s): exact requested bars; do not assume 5m if not specified.
- Trading sessions and excluded periods.
- Direction: long only, short only, or both.
- Indicators: name, exact settings, price source, and any offsets.
- Entry: every condition, AND/OR grouping, crossover/crossunder semantics, candle-close vs intrabar semantics.
- Exit: opposite signal, fixed stop/target, trailing stop, time exit, partial exits, or combinations.
- Position sizing: contracts, fixed RM risk, or formula; respect integer contract count.
- Filters: volume, trend, volatility, news, day/time, and market regime.
- Execution assumptions: signal timestamp, next-bar/open/intrabar entry, limit/stop order behavior.
- Costs: commission/exchange/clearing/broker fees and adverse slippage per side.
- Unknowns: anything not legible or not specified.

## B. Before a run
Create `strategies/<strategy_id>.json` using the template. The specification must preserve the user's actual rules, not an invented substitute. Each interpretation of an image-based rule should be linked to a brief evidence note such as "blue line appears to be EMA 20; label is not legible — needs confirmation."

If a missing detail changes trade outcomes materially, mark the spec `NEEDS_CLARIFICATION` and ask one concise question containing the unresolved detail. If the user says to use reasonable assumptions, record them explicitly and run a separate assumption-based version, never label it exact.

## C. After a run
Report:
- strategy ID and rule version/hash
- timeframe, instrument/contract series, sample dates and usable bar count
- trades, wins, losses, win rate
- gross return RM, fees RM, slippage RM, net return RM
- monthly average net return RM and %, with month-by-month results
- average winning/losing trade, profit factor, expectancy/trade
- max drawdown in RM and %, losing streak, largest loss
- long/short breakdown if applicable
- all parameters and costs
- comparison with a simple benchmark only if useful
- limitations, out-of-sample results, and whether one FCPO contract is feasible for the assumed account size

Never describe a strategy as profitable from an in-sample result alone.
