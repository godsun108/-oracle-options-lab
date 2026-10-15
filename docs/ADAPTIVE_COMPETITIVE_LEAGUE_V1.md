# Competitive Adaptive Trading League — Governance v1

Status: DESIGN ONLY. No strategy promotion, automated code mutation, live trading, or verified profits are implemented by this document.

## Reuse and isolation
Extend the existing six-market ETF paper league and Oracle-Q audit/validation components; do not duplicate scorers, ledger, market data pipelines or signal identities. The preregistered `etf-open-paper-2026-10-v1` season (first signal October 15, 2026; first hypothetical entry October 16; 60 windows) is immutable. Its six teams are SPY, QQQ, IWM, SMH, TLT, GLD, each with three fixed long/cash strategies and $10,000 hypothetical starting capital. No changes to this season's rules, fingerprints, scoring or ledger.

## Competition hierarchy
1. Intra-market: multiple candidate teams compete under equal capital, data cutoff, costs, risk limits, and forward windows; measure first qualifying net profit, largest net dollar profit, risk-adjusted return, robustness and validated improvement.
2. Inter-market: compare market champions with risk-normalized scores and identical forward evaluation windows; absolute profit is reported separately and never compared across unequal capital allocations.
3. All-Star: evaluate diversified portfolio contribution, correlation, drawdowns, capacity, tail losses and stability. Abstention is an acceptable outcome. No claim of profits in all regimes.

## Champion/challenger versioning
Agents can propose new features, strategies, risk rules and models in isolated development branches. Each candidate receives immutable ID, parent champion ID, version, code SHA, data snapshot hashes, hypothesis, parameter bounds, test count, cost model, risk budget and preregistered evaluation windows. The frozen incumbent continues running unchanged. Candidate backtests are screening evidence only. Independent verification, multiple-testing correction, holdout evaluation, adversarial negative controls and a fresh prospective paper window are required before promotion.

## Non-rewriteable scoring
Research scores, prospective paper scores and broker-reconciled live scores are separate. Promotion is effective prospectively at a new timestamped boundary. Team lifetime returns must use an append-only, capital-flow-adjusted accounting series and include failed/retired versions; do not replace old outcomes with a challenger backtest or splice cherry-picked performance. Report version-level and team-level histories side by side. A new challenger may improve future scores only. Never report hypothetical results as realized profits.

## Eligibility gates
Reject missing source provenance, noncausal features, stale quotes, unmodeled spreads/fees, incomplete windows, invalid labels, excessive leverage or drawdowns, or insufficient evidence. Require independent score recomputation from auditable fills/quotes. Holdouts are inaccessible to strategy-design agents. Audit trial counts and prohibit retrospective benchmark edits. Frozen season scoring cannot be modified to accommodate challengers.

## Agent roles
Hypothesis researchers propose ideas; implementation agents produce code; independent validators verify; risk governors enforce limits; scorekeepers use read-only evidence. No agent can approve its own promotion, edit historical ledgers, or activate live orders. Live trading requires a separate explicit human authorization and broker-specific controls.

## Phased delivery
Phase A: inspect existing strategy and score components and map reusable interfaces. Phase B: add immutable challenger registry and negative controls with tests. Phase C: prospective shadow competitions with no interference to existing season. Phase D: promotion decisions after qualifying forward evidence. Phase E: separately approved, limited-capital live pilots, if ever justified.

## Falsifiable acceptance tests
- Synthetic random-signal challengers must not be promoted at a frequency above preregistered false-discovery tolerance.
- Modifying a locked candidate after registration must invalidate eligibility.
- Replaying identical evidence must reproduce scores exactly within documented numeric tolerance.
- Promoting a challenger must not change any pre-promotion team or incumbent return.
- Missing forward windows must not be filled with zero returns or fabricated cash decisions.
- A candidate with superior gross returns but inferior net risk-adjusted results must not automatically win.
