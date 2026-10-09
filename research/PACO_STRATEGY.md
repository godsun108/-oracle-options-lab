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
