# PACO Strategy & System

**PACO** is the named research system within Oracle-Q for directional SPY option selection and anomalously discounted option offers.

## PACO strategy
- At SPX all-time highs: prioritize SPY puts expiring approximately 30–60 calendar days out.
- At qualifying SPX lows: prioritize SPY calls with at least 30 calendar days remaining. The definition of a qualifying low remains to be specified and tested.
- Continue monitoring bargains in **both** calls and puts, even when only one direction receives priority.
- Preferred entry execution window: near the close; preferred exit execution window: next market open, as previously discussed. These are execution preferences, **not** automatic expiry or holding-period assumptions. Actual exit logic remains to be validated.

## PACO bargain scanner
- Search for unusually low option asks relative to a defensible, contemporaneous reference.
- Validate quote freshness, displayed size, spread, expiry, and option type.
- Separate reference-value discounts from **executable** bid/ask profitability.
- Do not presume displayed liquidity will fill or that a reference midpoint can be sold.
- No live orders, rapid-fire broker execution, or established trading edge. Simulation and evidence come first.

Implementation in this PR: `research/options_discount_scanner.py`.
The directional SPX high trigger is being developed separately in PR #31; this document unifies the research concept without claiming integration is complete.

## PACO put-to-call rotation hypothesis (2026-10-09)

1. On a verified SPX all-time-high event, generate a **put entry signal**. The research specification calls for taking each eligible high signal, but fills are not guaranteed and the simulator must enforce position, capital, and quote-validity limits. Never place an unbounded order.
2. Prioritize SPY puts with approximately 30–60 days to expiration. Record the entry ask, bid, spread, IV, delta, timestamp and fees.
3. Once the put position is exited, start a **24–48 hour call-hunt window**. This is a search window, not an automatic call purchase. Calls require at least 30 DTE.
4. Within that window compare executable ask, bid/ask spread, IV percentile/rank where properly sourced, and contract liquidity. Scan for unusually favorable asks without assuming reference midpoints are tradable.
5. Benchmark three call-entry policies: immediate, within 24 hours, and within 48 hours. Report missed moves, premium decay, fees, drawdown, and P&L from actual historical option quotes where available.
6. If no suitable call is available, the correct outcome is **NO_FILL**, not an invented purchase. A put signal is never evidence that calls are automatically underpriced afterward.

**Research guardrails:** All actions are simulated; no real-money auto trader. The strategy's edge, the definition of the put exit, and the low-side call trigger have not been validated. A 24–48 hour window does not guarantee avoiding elevated premiums.
