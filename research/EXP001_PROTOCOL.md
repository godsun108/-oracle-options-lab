# EXP-001 / EXP-010 Research Protocol

Status: PREREGISTERED DESIGN — NO VERIFIED PERFORMANCE.

## EXP-001
Universe: SPY, QQQ, IWM, EFA, EEM, TLT, GLD. Use survivorship-aware, point-in-time, adjusted total-return prices. Monthly 252-trading-observation absolute momentum signal, positive assets equally weighted, otherwise cash. Signals determined at month-end using only available observations; apply changes at next eligible execution time. Include bid-ask spreads, slippage, fees and cash yields. Compare with frozen equal-weight buy-and-hold and cash benchmarks.

## EXP-010
Run deterministic randomized signals on the identical dates and universe. Track the full number of trials and reject false discoveries using predeclared thresholds and untouched holdout observations.

## Promotion rules
No live orders. Data provenance and hashes required. Training, validation and final holdout must be chronologically separate and fixed before testing. Evaluate transaction-cost stress, missing-data handling, walk-forward robustness, benchmark excess returns, drawdowns, turnover, and independent replication. Simulated results must never be represented as realized trading profits.

## Engineering
A standalone Python prototype and five local unit tests were developed separately; repository integration and CI verification remain pending. No broker connection is needed.
