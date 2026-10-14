# Forward input scope

The production paper workflow explicitly requests exactly the latest 200 exchange
sessions, fixed before the provider response is seen. This is the existing maximum
lookback: trend uses 200 opens, momentum 64, reversal 6. The rules and their IDs do
not change. Regression tests compare identical signals on full and bounded inputs.

This is not a fallback after a failed backtest and does not trim a bad response.
All requested sessions must be present, current, unique, and contain positive finite
opens. Extra out-of-window rows also fail. Source snapshots and deterministic replay
remain mandatory, as do registration timing, delayed outcomes, source-price
continuity and previous-ledger restoration. The existing 25-session settlement
evidence window is unchanged; long outages can still require explicit recovery.

Reports are labeled `FORWARD_OPEN_INPUTS_ONLY` and contain no historical performance
statistics. Daily production no longer reruns the 850-calendar-day backtest. That
research remains available explicitly through `python -m research.edge_lab --mode
historical` and still rejects invalid old prices. In particular, the March 6, 2025
IWM/GLD defects are unresolved, not repaired or declared irrelevant to backtests.

This separates historical experiment availability from the data dependencies of
prospective signals. It does not certify source authenticity, executable fills or
profitability. No price substitutions, live orders or new providers are enabled.

## Explicit market isolation

Production opts into `--allow-partial` at collection, replay, ledger, and scorecard
stages. A `DATA_OR_VALIDATION_FAILURE` blocks that entire market for this run: no
new signals, price checkpoints, or settlements. Its prior events and pending
signals remain unchanged. No substitute prices or retroactive signals are added.
Every other market must pass its full source replay and ledger checks. Missing or
duplicated markets, unknown failure states, and an all-blocked run still fail.
Default command behavior remains strict; historical mode cannot opt out of failure.

A successful partial workflow means evidence for the validated subset was safely
processed, not that all six feeds are healthy. The report, replay, ledger and
scorecard name blocked markets; Actions emits a warning and its summary labels
collection health. All 18 pairs remain in the scorecard and Bonferroni family,
including blocked pairs with no new outcomes. Missing outcomes are not zero
returns. Availability can bias evidence, so partial coverage is not evidence of
profitability. A later recovery must still match recorded price checkpoints.

## Prospective descriptive regimes

`open-trend63-vol20-v1` records 63-session opening-price momentum and the
sample standard deviation of the latest 20 opening log returns, annualized by
sqrt(252). Nonnegative momentum is UP_OR_FLAT; negative is DOWN. Volatility
at or above 20 percent is HIGH_VOL, otherwise LOW_VOL. This fixed, exploratory
threshold is not fitted, economically universal, or asserted optimal. These
are price descriptors, not recession labels, forecasts, or trading filters.

The source replay recomputes the metrics from the retained price window. New
signals include the context and its window hash inside their hash-linked event.
Existing signals are never backfilled, and unchanged same-session reruns do not
rewrite labels. Earlier signals therefore remain unclassified. Partial-market
failures still block all new registrations for those markets.

Regime classification does not create new strategies or change the 18-hypothesis
family. No regime-level significance or profitability is estimated. Any future
regime-specific selection or inferential testing requires an explicitly expanded
testing plan; pooled observations are not proof of performance in every regime.
