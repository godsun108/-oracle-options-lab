# Oracle Q — Accelerated Edge Search Protocol v1

Status: RESEARCH / NO LIVE TRADING

## Purpose
Accelerate hypothesis exploration without converting repeated backtests into false discovery.

Oracle Q selects a diverse batch of preregistered candidate experiments. Classical chronological evaluation remains the judge.

## Firewall
Candidate selection may use only design metadata and information available before each candidate's outcome evaluation. It MUST NOT use the candidate's realized holdout P&L, profit factor, or test-window score as QUBO inputs.

All historical data through 2025 is burned for promotion. Historical experiments are discovery/diagnostic only. A candidate can become a paper-forward candidate only after its complete rule is frozen.

## Candidate axes
Generate candidates across predeclared families rather than repeatedly modifying O4:
- option structure: O1..O6
- signal horizon/family: frozen canonical signal variants already present in Oracle evidence
- regime inclusion: trend-only vs trend+Seldon
- decision target: win probability vs payoff/EV
- contract economics: absent vs entry-only price/liquidity features

Only combinations whose required inputs exist at decision time are eligible.

## QUBO scheduler
Binary x_i means candidate i is admitted to the next parallel research batch.

Maximize:
  information_value^T x
  - redundancy_lambda * x^T R x
  - complexity_gamma * complexity^T x

subject to a fixed batch-size budget.

information_value is based on preregistered design diversity / uncertainty reduction, NOT realized test performance.
R penalizes candidates sharing the same structure, target, feature family, and signal family.
Complexity penalizes extra degrees of freedom.

## Solvers
1. exact classical solver where tractable
2. simulated annealing / quantum-inspired solver
3. QAOA emulator on the identical QUBO

Solver quality is measured by QUBO objective and runtime. No solver gets different market information.

## Evaluation
Selected candidates are materialized as immutable manifests before scoring.
They are evaluated in parallel with:
- chronological training only
- actual Stage-9 bid/ask execution where applicable
- costs/liquidity retained
- unchanged outcome reporting
- multiplicity ledger containing every candidate tested

No historical winner is called an edge.

## Promotion
Historical discovery -> frozen candidate -> genuinely future paper-forward observations -> only then reconsider Proof-of-Edge status.
