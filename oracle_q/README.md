# Oracle Q — Quantum-Inspired Decision Layer

Oracle Q is an experimental decision/optimization branch for the Oracle options lab. It is deliberately separated from Stage 9 so it cannot alter the frozen signal or contaminate holdout evidence.

## Research question
Given market-state probabilities and a fixed menu of option positions with estimated payoff distributions, can a QUBO/Ising optimizer select portfolios that improve risk-adjusted realized performance versus an identical classical optimization baseline?

## Guardrails
- Quantum methods do not receive privileged future information.
- Inputs are generated only from information available at decision time.
- Classical and quantum-inspired solvers receive the exact same objective, constraints, and candidate positions.
- Transaction costs, bid/ask execution, liquidity filters, and position limits remain explicit.
- Walk-forward evaluation is mandatory; no tuning on the final test window.
- Quantum advantage is not assumed. If a classical solver is as good or better, that is the result.

## Proposed objective
For binary position vector x, maximize expected portfolio utility:

    mu^T x - lambda * x^T Sigma x - gamma * cost^T x

subject to capital, concentration, and exposure constraints. Constraints can be converted to QUBO penalty terms for QAOA/annealing-style experiments.

## Experimental ladder
1. Deterministic classical baseline.
2. Simulated annealing / quantum-inspired QUBO baseline.
3. QAOA circuit emulator on tractable candidate sets.
4. Walk-forward comparison on identical historical decisions.
5. Hardware experiment only if the emulator demonstrates a reason to incur hardware complexity.

Stage 9 remains the current empirical priority. Oracle Q begins as an isolated research scaffold.
