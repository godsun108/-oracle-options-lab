# Oracle × Seldon Fusion Experiment 004 — Price-Aware Option EV

Status: PREREGISTERED / RESEARCH ONLY
All historical outcomes through 2025 are burned for promotion. This experiment is diagnostic/development research only.

## Question
Do contemporaneously observable option-contract economics improve prediction of O4 realized option returns beyond trend/macro features?

## Population
Frozen Stage-9 O4_ATM_7_10DTE status=ok trades from run 36257234984.
Frozen execution remains T+1 EOD ask entry and T+2 EOD bid exit.

## Information available at entry
Oracle trend: ret_5, ret_20, dist_ma20, dist_ma50, dist_ma200.
Seldon: vintage-safe 12m P(UNRATE higher), latest snapshot on/before signal date.
Contract: dte, entry_delta, entry_bid, entry_ask, entry_open_interest, strike, entry_spot_unadjusted.

Derived entry-only contract features:
- spread_pct = (entry_ask-entry_bid)/entry_ask
- premium_pct_spot = entry_ask/entry_spot_unadjusted
- moneyness = strike/entry_spot_unadjusted - 1
- log_open_interest = log1p(entry_open_interest)

## Frozen model comparison
Expanding chronological ridge regression, L2=30, minimum training=100:
A BASE: Oracle trend only.
B MACRO: Oracle trend + Seldon.
C PRICE: Oracle trend + contract-derived features.
D FULL: Oracle trend + Seldon + contract-derived features.

No future/exit variables enter any model.

## Evaluation
Report 2017-2021, 2022-2025, FULL diagnostics:
- MSE (primary forecast metric)
- MAE
- prediction/realized-return correlation

Frozen economic diagnostic for 2022-2025:
For each model independently, select only predicted_EV > 0 and report count, mean realized option_return, mean/total one-contract P&L, win rate, profit factor, max compounded drawdown.
No threshold optimization.

## Interpretation / promotion
Historical improvement may identify a model worth freezing but cannot establish a live edge because outcomes through 2025 are already exposed.
No model advances to live capital from Experiment 004.
Any candidate must next be frozen for genuinely future PAPER-FORWARD evidence.
