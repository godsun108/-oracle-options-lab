# Seldon → Oracle Research Contract

Status: RESEARCH_ONLY

Seldon may provide macro-regime features to Oracle only as dated, provenance-bearing research inputs. This interface does not authorize a trade and must not bypass Oracle's proof-of-edge or paper-forward gates.

## Required Seldon payload

- `as_of`: vintage-safe information cutoff.
- `source_experiment`: immutable Seldon experiment/version.
- `target`: exact forecast target.
- `horizon`: forecast horizon.
- `probability`: model probability in [0,1].
- `baseline_probability`: contemporaneous baseline probability.
- `evidence`: sample size, Brier score, baseline Brier score, Brier skill, calibration error.
- `vintage_safe`: must be true.
- `status`: `RESEARCH_FEATURE_ONLY`.

## Oracle rules

1. Join Seldon features by information available on or before each Oracle signal date. No future macro revisions.
2. Freeze the integration rule before inspecting option outcomes for the evaluation period.
3. Compare Oracle-with-Seldon against the same Oracle model without Seldon.
4. Preserve chronology and locked holdouts.
5. Seldon may improve, worsen, or leave unchanged Oracle's evidence score. No forced directional interpretation.
6. A better probability score is not automatically a profitable options strategy.
7. Live trading remains outside this research contract.

## Experiment 004 evidence snapshot

Frozen before scoring; vintage-safe; evaluation begins 2015-01-31.

| Horizon | n | Brier | Historical-frequency Brier | Skill vs historical | Skill vs p=0.5 | Calibration MAE |
|---|---:|---:|---:|---:|---:|---:|
| 6m | 38 | 0.168099 | 0.190910 | 11.95% | 32.76% | 0.101504 |
| 12m | 36 | 0.177438 | 0.208123 | 14.74% | 29.02% | 0.226190 |
| 18m | 34 | 0.173469 | 0.231882 | 25.19% | 30.61% | 0.138655 |

These are forecasting results for whether unemployment is higher at the specified horizon. They are not SPY-return or option-P&L results.
