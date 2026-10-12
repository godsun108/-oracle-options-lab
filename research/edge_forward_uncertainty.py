"""Exploratory block-bootstrap diagnostics, not an edge-certification procedure.

Preserves 18-hypothesis family-wise adjustment and reports uncertainty only
after at least 60 paired forward observations. Serial dependence and
selection biases can still invalidate these descriptive estimates.
"""
import math
import random
import statistics

RESAMPLES=2000
BLOCK_LENGTH=5
SEED=20261012
FAMILY_ALPHA=0.05

def assess(excess_returns, *, family_size, minimum=60):
    if not isinstance(family_size,int) or isinstance(family_size,bool) or family_size<1:
        raise ValueError("invalid hypothesis family")
    if not isinstance(excess_returns,list):
        raise ValueError("paired excess must be a list")
    if any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) for x in excess_returns):
        raise ValueError("nonfinite paired excess")
    n=len(excess_returns)
    result={"method":"circular_moving_block_bootstrap_one_sided_null",
            "block_length":BLOCK_LENGTH,"resamples":RESAMPLES,
            "hypothesis_family_size":family_size,
            "minimum_paired_forward_observations":minimum,
            "paired_forward_observations":n,
            "statistical_evidence":"NOT_ESTIMABLE",
            "raw_one_sided_p":None,
            "bonferroni_adjusted_p":None,
            "bootstrap_mean_excess_95pct_interval":None,
            "statistically_confirmed_edge":False,
            "eligible_for_live_trading":False}
    if n<minimum:
        return result
    observed=statistics.fmean(excess_returns)
    centered=[x-observed for x in excess_returns]
    rng=random.Random(SEED)
    null_means=[]
    raw_means=[]
    for _ in range(RESAMPLES):
        indices=[]
        while len(indices)<n:
            start=rng.randrange(n)
            indices.extend((start+j)%n for j in range(BLOCK_LENGTH))
        indices=indices[:n]
        null_means.append(statistics.fmean(centered[j] for j in indices))
        raw_means.append(statistics.fmean(excess_returns[j] for j in indices))
    # +1 smoothing avoids spuriously reporting p=0 from finite simulations.
    raw_p=(1+sum(x>=observed for x in null_means))/(RESAMPLES+1)
    ordered=sorted(raw_means)
    lo=ordered[int(0.025*(RESAMPLES-1))]
    hi=ordered[int(0.975*(RESAMPLES-1))]
    result.update({
        "statistical_evidence":"EXPLORATORY_UNCERTAINTY_ESTIMATE_ONLY",
        "raw_one_sided_p":round(raw_p,6),
        "bonferroni_adjusted_p":round(min(1,raw_p*family_size),6),
        "bootstrap_mean_excess_95pct_interval":[round(lo,6),round(hi,6)],
        "observed_mean_excess_pct":round(observed,6),
        "warning":"Exploratory bootstrap; overlapping observations, nonstationarity, multiple looks, strategy selection and fill uncertainty remain. No statistical edge certification."
    })
    return result
