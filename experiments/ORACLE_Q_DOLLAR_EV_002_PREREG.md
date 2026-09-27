# Oracle Q Dollar-EV Experiment 002 — Preregistration

Status: FROZEN BEFORE SCORING
Promotion status: HISTORICAL DISCOVERY ONLY

## Motivation
Q-BATCH-001 exposed two historical anomalies whose selected trades had positive mean percentage option return but negative one-contract dollar P&L:
- QH016: O2_D40_2_3DTE, trend + Seldon12m + entry contract features, expected-return target
- QH019: O3_D25_2_3DTE, trend only, expected-return target

This experiment changes the prediction target from percentage option_return to one_contract_pnl. It does not optimize a threshold.

## Population and execution
Use the frozen Stage-9 realized options artifact from run 36257234984.
Only status=ok trades.
Execution remains T+1 EOD ask entry -> T+2 EOD bid exit. Spread is embedded.

## Frozen candidates
D016:
- structure O2_D40_2_3DTE
- features: ret_5, ret_20, dist_ma20, dist_ma50, dist_ma200, Seldon 12m probability, dte, entry_delta, spread_pct, premium_pct_spot, moneyness, log_open_interest
- target: one_contract_pnl dollars

D019:
- structure O3_D25_2_3DTE
- features: ret_5, ret_20, dist_ma20, dist_ma50, dist_ma200
- target: one_contract_pnl dollars

## Model
Expanding chronological ridge regression.
L2 alpha = 30.
Minimum training observations = 100.
No refit using future rows.

## Decision rule
Select a trade iff predicted one-contract dollar P&L > $0.
No alternate thresholds, ranking cutoffs, or post-result tuning.

## Historical diagnostics
Report separately for 2017-2021, 2022-2025, and FULL:
- MSE in dollar P&L
- MAE in dollar P&L
- prediction/realized-P&L correlation

For selected 2022-2025 trades report:
- trade count
- mean and total realized one-contract dollar P&L
- mean percentage option return
- win rate
- dollar profit factor (sum positive dollar P&L / absolute sum negative dollar P&L)
- max compounded drawdown using percentage option returns

## Interpretation
All history through 2025 is burned. Positive historical dollar expectancy is not an edge and cannot authorize trading. A historically interesting candidate must be frozen for genuinely future paper-forward evidence.
