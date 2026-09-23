# Regime model protocol v1

Purpose: diagnose *why* the frozen Stage 9 phenomenon changed through time without using 2022–2025 to retroactively redesign the Stage 9 rule.

Inputs are point-in-time features at the signal close: short/medium returns, distance from 20/50/200-day averages, realized volatility at 10/20/60 days, volatility-ratio, and prior-20-day-relative volume when available.

The first pass is descriptive. It asks whether signal outcomes differ across market states. Any state filter or model suggested after examining Stage 9 outcomes is explicitly **exploratory** and cannot be called validated on those same observations.

A future model comparison must use walk-forward fitting. At each decision date, training data must end before that date. Baselines include unconditional historical probability and a simple regularized classical model. More complex AI/quantum methods must improve out-of-sample decision utility after transaction costs to justify their complexity.

No LLM receives future outcome columns in the decision packet.
