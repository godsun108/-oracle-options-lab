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


## Oracle AI copilot layer
The AI layer is an analyst/orchestrator, not an oracle with permission to rewrite evidence. It may:
- summarize frozen experiment outputs and data-quality diagnostics;
- generate candidate hypotheses for a *future* preregistered experiment;
- translate approved constraints into optimizer configuration;
- compare classical, quantum-inspired, and quantum-emulated outputs;
- produce provenance-rich research briefs and flag anomalies.

It may not:
- see or use locked holdout outcomes while designing a rule;
- silently alter signals, thresholds, execution assumptions, or risk limits;
- choose a backtest winner and present it as validated;
- place trades without a separate explicit execution/risk-control layer.

Every AI recommendation should be machine-readable and include: timestamp/data cutoff, inputs used, experiment ID, assumptions, proposed action, confidence/uncertainty, and evidence references. This makes the AI useful for speed without letting it contaminate the experiment.
