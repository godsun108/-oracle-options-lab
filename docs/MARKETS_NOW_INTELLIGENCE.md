# Markets Now Intelligence Extensions

The dashboard adds three research-only modules:

## Genesis Market Analyst

The v1 analyst is a deterministic, auditable second-pass rules engine. It challenges each fresh scanner candidate on:
- scanner score threshold;
- provider quote timestamp verification;
- bid/ask spread;
- open interest and option volume;
- preferred days-to-expiration range;
- delta band; and
- directional trend alignment.

It does not call a Genesis model yet. The label describes the planned integration point, not a claim that Genesis inference has already been wired in. Failed checks remain visible as review items; passing the configured checks does not create a trade instruction. Event calendar, IV context, broker quote verification, and personal risk review remain manual.

## Options Strategy Lab

The calculator models expiration payoff for long calls, long puts, bull call debit spreads, and bear put debit spreads. It shows maximum loss, maximum profit (or unlimited upside for a long call), breakeven, and selected expiration-price checkpoints. Premiums are entered per share and multiplied by 100 per standard contract. Fees, slippage, dividends, early exercise/assignment, and broker-specific treatment are excluded.

This is an educational calculator, not a pricing model or live option quote. Spread inputs must represent a debit spread.

## Performance Intelligence

The performance view reads numeric realized P&L values from the existing device-local journal. It summarizes count, win rate, net and average P&L, and maximum observed peak-to-trough drawdown. It does not upload journal entries or synchronize devices. Unrecorded P&L entries are excluded.

The UI reminds users that 30–50 consistently recorded paper trades are a starting sample, not proof of an edge. Fees and realistic execution costs should be included in journal results.

## Safety boundary

All three modules are read-only. They do not connect to brokerage accounts, submit/cancel orders, or grant Genesis authority to trade. A stale or unavailable snapshot cannot pass the analyst challenge. No displayed score is a probability of profit.
