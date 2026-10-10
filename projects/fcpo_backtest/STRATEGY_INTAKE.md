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

## D. Machine-rule mapping used by the engine

Indicator entries use `id`, `type`, optional `period`, `source`, and (for Bollinger Bands) `stddev`. Supported types: `sma`, `ema`, `rsi`, `atr`, `bollinger` / `bollinger_bands`.

A condition is an object with `left`, `operator`, and `right`. An operand can be a number, `{"price":"close"}`, `{"constant":50}`, or `{"indicator":"rsi14","line":"value"}`. Supported operators are `gt`, `gte`, `lt`, `lte`, `eq`, `neq`, `crosses_above`, and `crosses_below`. Group conditions with `{"logic":"all","conditions":[...]}` for AND or `{"logic":"any","conditions":[...]}` for OR; groups may be nested.

Example only (not a strategy recommendation): “Close crosses above EMA 20” maps to an EMA indicator with id `ema20`, type `ema`, period `20`, and an entry condition whose left operand is `{"price":"close"}`, operator is `crosses_above`, and right operand is `{"indicator":"ema20"}`.

## E. Supported execution boundaries

- Signal evaluated at completed bar close; market entry at the next bar open.
- One position at a time; integer fixed contract count.
- Conservative stop-first assumption if a candle touches both stop and target.
- Supported exit modes are fixed stop/target, opposite signal, time exit, stop/target plus opposite signal, and stop/target plus time exit.
- Trailing stops, partial exits, dynamic risk sizing, limit/stop queue modelling, and automatic futures-roll construction are not implemented. If the supplied strategy depends on one of these, report the gap and do not label the strategy faithfully tested.
- Costs are mandatory. Store fee per side per contract and slippage points per side in the spec, with the source/basis recorded. A zero assumption must be explicit, not an omitted field.
- The spec must identify the actual dated contract or continuous-series/roll method. “Must be documented” is a template placeholder, not a valid setting.

