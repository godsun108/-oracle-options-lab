# Oracle × Seldon Fusion Experiment 002 — Economic Value Preregistration

Status: PREREGISTERED / RESEARCH ONLY
Parent evidence: Fusion 001 run 36354506749, artifact 10943243430.
Oracle benchmark: run 36257234984, realized Stage-9 O4_ATM_7_10DTE trades.

## Question
Does the incremental probability information observed in Fusion 001 correspond to better realized option economics on genuinely out-of-sample O4 trades?

## Frozen inputs
- Fusion-001 base and fused probabilities. No model refit.
- O4_ATM_7_10DTE realized option trades.
- Entry T+1 EOD ask; exit T+2 EOD bid, as frozen by Stage 9.
- Locked evaluation period: 2022-2025.

## Primary test
Within 2022-2025, rank eligible trades independently by the already-frozen p_model_base and p_model_fused.
For each model, select the top quartile (top 25%) by probability, using the quartile rule itself as preregistered here before inspecting ranked P&L.
Compare mean one-contract return, mean one-contract P&L, profit factor, win rate, compounded max drawdown, and trade count.

Primary economic comparison: fused top-quartile mean one-contract return minus base top-quartile mean one-contract return.

## Controls
- Report all eligible 2022-2025 O4 trades as an unconditional benchmark.
- Report overlap between base and fused selected trades.
- No threshold search.
- No alternate quartile/decile selection after outcomes are observed.
- No changing option structure, holding period, execution prices, or Seldon horizon after outcomes are observed.
- Report negative, null, or positive results unchanged.

## Interpretation
A positive result is evidence only for this historical economic-value test. It does not establish a live trading edge and does not authorize trading.
A negative/null result falsifies the claim that Fusion-001's probability improvement translated into better O4 economics under this frozen selection rule.
Any promotion remains subject to Oracle's Proof-of-Edge ladder, including robustness and genuinely unseen paper-forward evidence.
