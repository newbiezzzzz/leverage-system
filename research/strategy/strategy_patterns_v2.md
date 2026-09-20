# Strategy Hunter v2 — pattern research notes

## Evidence considered

1. Malaysian Shariah-compliant stocks: a 2016 study reported strong return persistence and momentum profitability in Malaysian Shariah-compliant stocks, with persistence reported out to longer holding periods. It also attributed the effect primarily to underreaction rather than industry or small-size effects.
2. Malaysian equities: a 2014 study of 700 stocks reported short-term momentum profits and found that industry momentum portfolios were profitable in its sample.
3. Malaysian short-horizon reversal: a 2000 study reported contrarian profits that were positively related to trading activity, with actively/frequently traded securities producing higher contrarian profits.
4. Southeast Asian markets: a 2013 study found moving-average and trading-range breakout rules had predictive power in Malaysia and other emerging Southeast Asian markets, especially for shorter-term variants.
5. Trading costs: research on emerging markets shows that transaction costs can materially destroy anomaly profitability. Strategy Hunter therefore keeps broker costs in the test and prefers lower-turnover variants.

## New fixed rules to test

These are research candidates, not claims of profitability.

- Slow Momentum: 12-month return excluding the latest 1 month; price above 200-day average; hold 40 trading days.
- Volume-Confirmed Momentum: 6-month return divided by 63-day volatility; price above 100-day average; 20-day traded value above RM100k; hold 30 trading days.
- Trend Pullback: price above 100-day average, positive 60-day return, 5-day drop between -3% and -10%; exit when price closes back above 20-day average or after 15 trading days.
- Active Reversal: 5-day drop <= -6%, price above 200-day average, 20-day traded value >= RM500k; hold up to 10 trading days or until a 5% rebound.
- Breakout + Volume: close above prior 20-day high, price above 50-day average, volume >= 1.5x 20-day average; exit below prior 10-day low or after 30 trading days.

## Research rule

Do not optimize these parameters on the full sample. First run fixed rules on the corrected engine, then use separate in-sample/out-of-sample and walk-forward tests. No live money until all gates pass.
