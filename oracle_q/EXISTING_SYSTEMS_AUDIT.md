# Existing Oracle-Q systems: audit checkpoint

Inspected October 13, 2026. Research only; live orders remain disabled.

| Existing component | Verified implementation | Remaining boundary |
| --- | --- | --- |
| `qubo.py` | Binary portfolio utility, QUBO matrix, exhaustive baseline | Expected-return inputs and execution feasibility are not validated by optimization |
| `hypothesis_qubo.py` | Fixed-budget research scheduling using design diversity and complexity; exact and annealing solvers | Heuristic scores are not expected trading profits; no quantum hardware or QAOA implementation found |
| `edge_search_batch*.py` | Three design-only candidate manifest generators | Historical winners require separate future evidence |
| `regime_features.py` | Trend, rolling volatility and volume features | Not a validated regime-switching trading policy; feature availability needs independent audit |
| `walk_forward.py` | Regularized probability model and unconditional baseline | This patch purges unavailable labels; it does not validate features or macro vintages |
| `score_batch_001.py`, `score_batch_002.py` | Separate historical walk-forward scorers | Training now excludes unavailable exit labels and same-time signals; entry-time feature use still needs repair before reuse |
| `seldon_sidecar.py` | Research-only attachment, date/vintage checks | A vintage-safe flag alone does not independently attest provider data |
| `options_edge_gate.py` | Can reject a candidate with `NO_TRADE` | Historical gate is not authorization or proof of profitability |
| `research/edge_*` | Timestamped six-market paper ledger, continuity audit and cost stresses | No completed forward outcomes at last verified production run 38323178714 |

## Changes in this patch

The shared walk-forward model requires label availability (default `exit_date`), excludes same-time signals and unavailable outcomes, and returns a stable empty schema when training evidence is insufficient. Midnight/date-only availability values are treated conservatively as unavailable until the end of that date. Historical artifacts are not rewritten. Features remain the caller's responsibility.

The existing scheduler now validates candidate IDs, finite nonnegative design metadata and batch budgets; exact enumeration is capped at one million combinations. Empty and full annealing batches work without invalid swaps.

An opt-in `incremental=True` mode evaluates only the interactions changed by a candidate swap. The default retains full objective evaluation. Both are classical simulated annealing on a QUBO-compatible objective, not evidence of quantum advantage.

## Local exploratory benchmark

Synthetic design menus from `tests.test_hypothesis_qubo.candidates`, seed 108, 2,000 steps, three repetitions, median wall time, `OPENBLAS_NUM_THREADS=1`. Includes matrix construction. One environment only; not a market-performance test.

| Candidates / selected | Original seconds | Incremental seconds | Original / incremental | Original / incremental objective |
| --- | ---: | ---: | ---: | ---: |
| 48 / 8 | 0.105520 | 0.098175 | 1.075 | 9.17 / 9.17 |
| 126 / 18 | 0.157017 | 0.124733 | 1.259 | 35.14 / 35.08 |
| 256 / 18 | 0.258604 | 0.205713 | 1.257 | 104.09 / 104.09 |

Floating-point differences can alter annealing paths. The lower objective in the middle case prevents declaring a general quality-preserving speed advantage; incremental mode is not promoted to the default. Broader comparisons must evaluate objective gaps, seeds, runtime and identical information budgets.

## Next integration gates

1. Audit feature availability in older batch scorers before rerunning historical experiments; label-maturity regression coverage is now present.
2. Freeze prospective regime snapshots before future outcomes; do not backfill labels onto older signals as if recorded then.
3. Compare regime policies against the existing fixed strategies and cash, accounting for all tried variants.
4. Preserve abstention when data or evidence is insufficient. Cash avoids market exposure but is not guaranteed real profit; any interest model requires actual account terms and separate evidence.
5. Keep portfolio and execution risk limits separate from optimizer output. Human approval is required before live trading.

## Batch scorer chronology follow-up

Both batch scorers now use the shared label-availability filter before fitting the scaler or model. The 100-observation minimum counts only mature labels, and duplicate signal dates cannot train on one another. Empty results preserve the columns needed by report generation. Missing or impossible exit dates fail closed. The regression tests mutate unavailable outcomes and verify unchanged earlier predictions for both probability and regression targets.

Version-2 reports explicitly state that feature timing is unverified and live-trading eligibility is false. An exit date is a conservative historical label proxy, not proof of source publication time. Same-day closing-price features, entry-contract features, and macro publication/vintage provenance remain unresolved. These scorers are not cleared for prospective decisions.

Historical replay workflows are now manual-only: a code push must not automatically generate a new historical score from pinned external artifacts and an unpinned market-data URL. Oracle Guardrails still runs the deterministic regression suite automatically on pushes and pull requests, including these scorers' existing scikit-learn dependency. No historical scores, manifests, or forward-ledger events are rewritten.
