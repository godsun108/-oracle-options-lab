# Oracle × Seldon Fusion Experiment 003 — Payoff-Aware Expected Value

Status: PREREGISTERED / RESEARCH ONLY

## Scientific reset
Fusion 001 and 002 exposed 2022-2025 outcomes. Therefore 2022-2025 is permanently burned for model promotion and MUST NOT be described as unseen evidence again.

## Question
Can signal-time Oracle trend features plus Seldon's vintage-safe 12-month unemployment probability estimate realized O4 option payoff magnitude better than an expanding historical-mean EV baseline?

## Frozen population and execution
- O4_ATM_7_10DTE, status=ok, from frozen Stage-9 run 36257234984.
- Realized option_return already reflects T+1 EOD ask entry and T+2 EOD bid exit.
- Oracle features: ret_5, ret_20, dist_ma20, dist_ma50, dist_ma200.
- Seldon feature: latest vintage-safe 12m P(UNRATE higher) available on/before signal date.
- No option outcome or future macro value may enter features.

## Models
Two expanding chronological ridge regressions predict realized option_return:
A. Oracle base features.
B. Same features + Seldon probability.
L2=30 and minimum training observations=100, matching the established fusion regularization convention.
Training uses only observations strictly earlier than each prediction date.

## Evaluation
Historical diagnostics are reported for 2017-2021, 2022-2025, and FULL prediction history. Because 2022-2025 is burned, these are research diagnostics only.

Primary forecast comparison: mean squared error of predicted option_return, fused minus base. Lower is better.
Secondary diagnostics: mean absolute error and correlation between predicted and realized return.

Economic diagnostic, frozen before inspection:
- Rank each model's 2022-2025 predictions by predicted EV.
- Select trades only where predicted EV > 0.
- Report trade count, mean realized option_return, one-contract P&L, win rate, profit factor, and compounded drawdown.
- No threshold optimization.

## Promotion boundary
Experiment 003 cannot establish a live edge because its historical outcomes are already exposed.
If the frozen model appears useful, the next stage is PAPER-FORWARD: preserve the model unchanged and score genuinely future signals/outcomes after this preregistration.
No live trading authorization.
