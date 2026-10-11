# BTCUSDT User Strategy Intake

When the Owner provides written rules or a screenshot, create a new strategy ID and record:
- Market type: spot or USDT-margined perpetual; never mix data between them.
- Timeframe, UTC timezone, direction and any intended trading-session filter.
- Indicator names/settings/sources, exact entry and exit rules, stop/target/trailing/partial exit logic.
- Filters, position size in BTC, signal timing and order assumptions.
- Fee rate per side, slippage in basis points per side, and evidence/basis.
- Ambiguities and how each image-derived interpretation maps to a machine rule.

If a material detail changes outcomes, mark NEEDS_CLARIFICATION and ask one concise question. If assumptions are authorized, label that run assumption-based and separate it from faithful replication.

## Supported machine rules
Indicators: sma, ema, rsi, atr, bollinger / bollinger_bands. Conditions use left/operator/right. Operands: number, {"price":"close"}, {"constant":50}, {"indicator":"ema20","line":"value"}. Operators: gt, gte, lt, lte, eq, neq, crosses_above, crosses_below. Groups nest with logic all/any.

Signals are evaluated at bar close and entered at the next bar open. Stop-first is assumed if a candle touches both stop and target. Unsupported trailing stops, partial exits, dynamic risk sizing, funding, liquidation and order-book fill models must be called out, not silently approximated.

## Reporting
Report sample dates, timeframe, raw/usable bar count, trades, wins/losses, win rate, gross/net USDT, fees, slippage, monthly averages and monthly table, average winner/loser, profit factor, expectancy, maximum drawdown USDT/% and losing streak. Keep full sample and chronological 60/20/20 development/validation/holdout results separate. Never claim profitability from in-sample performance alone.
