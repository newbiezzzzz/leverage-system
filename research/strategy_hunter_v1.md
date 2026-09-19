# Strategy Hunter v1

Status: RESEARCH BUILD
Capital: RM1,000
Planned maximum drawdown: 10% (RM100)
Target trade frequency: 5-20 trades/month
User time: 5-10 minutes/day
Active positions at RM1,000: 1
Real-money movement: PROTECTED

## Mission

Find a trading strategy that can survive realistic testing for the user's objectives:

1. growth,
2. eventual monthly income,
3. consistency over maximum headline return.

No live trade is authorized by the research system merely because a backtest is profitable.

## Division of labour

### ChatGPT — Thinker

- research papers and current market/broker/Shariah information
- formulate testable hypotheses
- interpret experiment results
- challenge conclusions
- identify missing evidence and possible bias
- decide which experiment should run next

### Leverage — Orchestrator

- store strategy specifications, experiments, datasets, assumptions and results
- schedule/queue research jobs
- deduplicate experiments
- preserve an audit trail
- compare experiment versions
- enforce research-only and money-protection gates
- produce alerts/reports

### Specialist compute workers

- VectorBT: large parameter/asset sweeps and fast signal research
- Backtesting.py: execution-focused independent simulations
- Optuna: controlled parameter search and pruning; never treated as proof of edge
- LEAN: optional independent validation engine
- Google Colab: free cloud compute when local resources are insufficient

Use the smallest/cheapest suitable worker for each task. Do not force ChatGPT to perform bulk numerical computation.

## Research universe

Research broadly before narrowing:

- Malaysian equities
- US equities/ETFs
- other accessible markets where the full trading structure can be verified

Futures, FX, CFDs, crypto, options and other derivatives remain research candidates only. Their asset, contract, financing and trading structure must be separately assessed for Shariah compatibility and RM1,000 risk.

## Broker universe

Start with the user's existing accounts:

- Moomoo
- Phillip Nova

Do not open another broker account unless research shows both are unsuitable for a required strategy.

For each candidate, record the actual/current applicable:
- commission
- platform fee
- exchange/clearing fee
- spread
- slippage assumption
- financing/funding cost
- minimum order/lot size
- currency conversion cost
- market-data cost

## Shariah framework

Keep these fields separate:

- asset/company compliance
- trading mechanism
- financing
- short-sale structure
- derivatives/futures structure
- broker/account structure
- authority/source
- date of verification

For Malaysian securities, use the Securities Commission Malaysia Shariah-compliant securities list as the primary asset-level reference.

Historical tests must use point-in-time Shariah membership when possible. Do not apply today's list backwards to historical data.

Where credible authorities disagree:
- document the disagreement,
- identify the authority/date,
- do not silently choose one,
- escalate the unresolved point to the user for their own religious decision.

## Strategy families

Initial candidates:

- momentum
- breakout
- trend following
- mean reversion
- volatility/regime filters
- short-term shock/underreaction/overreaction
- hybrids
- AI-discovered strategies

AI-discovered strategies receive stricter validation because data mining can manufacture attractive backtests.

## Entry

Test:
- market order
- limit order
- confirmation entry

Include missed fills, spread and slippage where applicable.

## Risk and exits

Research/test suitable:
- fixed loss stops
- structure stops
- volatility/ATR stops
- trailing stops
- fixed profit targets
- R-multiple targets
- trend/technical exits
- partial exits
- no-fixed-target exits

Do not select these methods by intuition alone.

## Holding and monitoring

Let the strategy determine:
- intraday vs multi-day vs multi-week holding
- overnight/weekend exposure
- monitoring frequency

Test gap risk and market-closed risk where relevant.

## Validation pipeline

Candidate strategies must be attacked, not merely optimized:

1. research/evidence review
2. data-quality checks
3. baseline backtest
4. realistic transaction costs
5. realistic slippage/spread
6. in-sample vs out-of-sample
7. walk-forward validation
8. parameter-stability checks
9. regime/stress tests
10. alternative execution assumptions
11. independent-engine replication where practical
12. paper/forward observation when appropriate
13. small live transition only after the evidence gate

Record:
- number of variants tested
- parameter search space
- selection rule
- out-of-sample results
- drawdown
- turnover
- trade frequency
- cost sensitivity
- robustness/failure evidence

Never select the winner solely on highest historical return.

## Position sizing

RM1,000 starts with one active opportunity.

Position size must be derived from:
- stop distance,
- instrument lot size,
- transaction costs,
- liquidity,
- maximum account drawdown objective,
- risk-of-ruin considerations.

"One opportunity" does not mean risking the full RM1,000.

## Failure / retirement rule

Do not retire a strategy after a single losing month.

If live/forward behaviour becomes statistically or materially inconsistent with the validated behaviour:

1. flag anomaly,
2. temporarily suspend,
3. re-test/re-validate,
4. retire only if evidence indicates the edge is no longer reliable.

## Scaling

- RM1,000: one active opportunity
- RM5,000: research diversification
- RM10,000+: research multi-opportunity allocation

Scaling must be risk-based and evidence-based, not simply a multiple of account size.

## Reporting

Use the strategy's natural monitoring frequency.

Send an immediate alert when an actual user action is required.

Otherwise consolidate information at the minimum useful frequency.

## Hard gates

The system must not:
- place orders,
- transfer money,
- change broker settings,
- exceed the planned risk budget,
- label a strategy Shariah-compliant without documented basis,
- claim complete market/data coverage when sources are restricted,
- claim a backtest is proof of future profitability.

## First research objective

Build a point-in-time Malaysian Shariah equity universe and test, at minimum:

1. momentum,
2. breakout,
3. trend-following,
4. short-term shock/reaction,

with realistic Moomoo/Phillip cost assumptions and strict out-of-sample/walk-forward validation.

A strategy is a candidate only if it survives attempts to disprove it.

Current live capital remains untouched.
