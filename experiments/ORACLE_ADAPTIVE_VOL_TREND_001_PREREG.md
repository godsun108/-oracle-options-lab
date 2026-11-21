# Oracle Adaptive Volatility-Targeted Trend — Candidate 001

Status: PREREGISTERED RESEARCH HYPOTHESIS ONLY. Not a validated strategy, not a signal recommendation, and not eligible for broker orders.

## Purpose

Test one tightly specified improvement to the existing long/cash ETF baselines: retain a simple trend gate, but scale exposure down when realized volatility rises. The objective is not to maximize a backtest. It is to determine whether a fixed risk-targeting rule improves net portfolio outcomes and drawdown without introducing look-ahead bias.

The existing 18-agent season and all prior ledgers remain immutable. This candidate runs in an isolated challenger lane and cannot replace an incumbent.

## Candidate identity

- Candidate ID: `adaptive_vol_trend_001`
- Parent/control: the same-market `tsmom_63` and `trend_200` agents, plus buy-and-hold and zero-yield cash comparators
- Universe: SPY, QQQ, IWM, SMH, TLT, GLD; each market scored separately
- Direction: long or cash only; no shorting, options, margin, leverage, or pyramiding
- Decision cadence: once per completed daily session
- Price basis: unadjusted daily opens, matching the current Oracle-Q open-only evidence lane
- Starting capital for simulation: equal capital per market/candidate, reported separately from any real account

## Frozen rule

At the opening of session t, compute all features only from valid completed opening-price observations strictly before t:

1. 63-session momentum: latest available prior open divided by the open 63 sessions earlier, minus one.
2. 200-session trend: latest available prior open divided by the arithmetic mean of the latest 200 prior opens, minus one.
3. 20-session annualized realized volatility: sample standard deviation of the latest 20 prior open-to-open log returns, multiplied by sqrt(252).

The target exposure for session t is:

- 0% if either 63-session momentum is not strictly positive or price is not strictly above its 200-session average.
- Otherwise, min(100%, 10% / annualized 20-session realized volatility).
- If any required observation is missing, invalid, stale, or volatility is zero/non-finite, target exposure is 0% and the reason is recorded as NO_TRADE_DATA.
- Exposure is never negative and never exceeds 100%. No volatility floor, fitted threshold, or parameter search is permitted.

The target weight is established at the next session's opening price and held from that open to the following session's open. A signal may not use the same opening price at which its position is notionally entered.

## Accounting and cost model

- Apply 10 basis points of assumed friction to each 100% of absolute exposure turnover: cost fraction = 0.001 × abs(new_weight - prior_weight), charged at the rebalance.
- Charge the initial entry and final liquidation consistently.
- No interest is credited to cash in the primary comparison. Report a separate cash-yield sensitivity only if an independently sourced, timestamped rate series is available.
- Report gross and net returns, dollar P&L, exposure, turnover, number of rebalances, annualized volatility, maximum drawdown, worst session, and time in cash.
- Report a second fixed stress at 25 basis points per 100% turnover. These are assumed costs, not measured spreads or broker fills.
- No overlapping positions, fractional-share feasibility claims, or live execution claims.

## Comparators and paired evaluation

For every market and identical session window, report:

1. Candidate 001 at its fixed target weights.
2. Existing `tsmom_63` long/cash control.
3. Existing `trend_200` long/cash control.
4. Buy-and-hold, with entry/exit costs treated consistently.
5. Zero-yield cash.

The primary comparison is candidate net compounded return versus the better of the two fixed trend controls, with drawdown and turnover shown alongside. Also report candidate excess versus buy-and-hold. Never rank markets with different observation windows as if they were paired.

## Evidence protocol

- Keep historical exploration separate from prospective evidence.
- Any historical run is exploratory only and must disclose that it has been used for design.
- Freeze candidate ID, code SHA, parameter values, data-source hashes, cost assumptions, and evaluation windows before the first prospective observation.
- Run at least 60 complete paired prospective sessions per market before review; incomplete sessions do not count and missing data is not imputed.
- Report every market independently. Do not pool 6 markets as 6 independent samples; equity ETFs and SMH have material correlation.
- Use block-bootstrap uncertainty and family-wise adjustment for the full tested candidate family. Record every candidate trial, including failed variants.
- Require positive paired net improvement, a positive uncertainty lower bound after the preregistered multiple-testing adjustment, no worse maximum drawdown than the selected incumbent, and positive 25-bps stress results before human review.
- A 60-session threshold is a review threshold, not proof of a durable edge. Continue the prospective test if uncertainty remains wide.

## Required implementation tests

- Features at t use only observations strictly before t.
- Mutating any future bar cannot change an earlier target weight.
- Missing, duplicate, out-of-order, non-finite, or non-positive opens fail closed or produce explicit NO_TRADE_DATA; no silent row dropping or price repair.
- Exposure is always in [0, 1], including extreme volatility cases.
- A zero or invalid volatility estimate never causes division by zero or a full-size position.
- Turnover costs are charged on absolute weight changes, including initial entry and final liquidation.
- Candidate and controls use the same paired dates and cost convention.
- Replaying identical source data and code reproduces identical results.
- The output explicitly states `orders_enabled=false`, `broker_fills_verified=false`, `edge_proven=false`, and `eligible_for_live_trading=false`.

## Governance

This candidate can only be evaluated in a shadow challenger lane. No autonomous parameter tuning, self-promotion, historical ledger edits, Tradier order submission, or changes to the frozen 18-agent season are permitted. Any later live pilot would require a separate, explicit human authorization and independently verified broker controls.
