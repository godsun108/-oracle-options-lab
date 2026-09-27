# Oracle Q Accelerated Edge Search — Batch 002 Preregistration

Status: FROZEN BEFORE OUTCOME SCORING

## Purpose
Widen the information families after Batch 001 showed that changing only option structure/target/regime around one canonical signal was insufficient.

The underlying event population remains Canonical Signal v1. Batch 002 does NOT optimize a new signal threshold. Instead it tests predeclared, point-in-time feature families describing market state at the canonical signal.

## Feature families
All are available at or before T0 close:
- TREND: ret_5, ret_20, dist_ma20, dist_ma50, dist_ma200
- VOL: rv10, rv20, rv60, vol_ratio_10_60
- VOLUME: volume_ratio20
- MIXED: TREND + VOL + VOLUME
- MACRO: TREND + vintage-safe Seldon 12m probability
- CONTRACT: TREND + entry-time contract features (dte, delta, spread_pct, premium_pct_spot, moneyness, log_open_interest)
- FULL: MIXED + Seldon 12m + entry-time contract features

## Candidate axes
- O1..O6 frozen Stage-9 option structures
- target: win_probability OR one_contract_dollar_pnl
- feature family: seven families above

Total candidate universe: 6 * 2 * 7 = 84.

## Scheduler firewall
The QUBO/annealing scheduler receives only candidate metadata, complexity, and design-diversity information. It receives no realized option_return, one_contract_pnl, holdout score, profit factor, or previous candidate outcome.

Select 12 candidates for Batch 002.

## Evaluation
After the 12-candidate manifest is frozen:
- expanding chronological model only
- min train 100
- L2 = 30
- probability: logistic, natural decision boundary p > .5
- dollar EV: ridge, natural decision boundary predicted dollar P&L > 0
- execution remains frozen Stage-9 T+1 ask -> T+2 bid
- report every candidate unchanged

## Multiplicity / promotion
All history through 2025 is burned discovery evidence. Batch 002 may identify hypotheses worth freezing, but cannot establish an edge or authorize live trading. No post-result threshold/model/feature edits are allowed to be described as validation.
