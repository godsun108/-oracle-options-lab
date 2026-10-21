"""Fail-closed, research-only perpetual learning candidate gate.

A candidate can be queued for human review, never autonomously promoted.
No brokerage execution, no parameter self-modification, no claims of profit.
"""
import math

def evaluate(candidate):
    if not isinstance(candidate,dict): raise ValueError("invalid candidate")
    if candidate.get("mode")!="RESEARCH_ONLY" or candidate.get("ordersEnabled") is not False:
        raise ValueError("live execution prohibited")
    required=("candidateId","baselineId","evidenceHash")
    if any(not isinstance(candidate.get(k),str) or not candidate[k].strip() for k in required):
        raise ValueError("missing identity or evidence")
    if candidate["candidateId"]==candidate["baselineId"]:
        raise ValueError("candidate must differ from baseline")
    metrics=("forwardSessions","completedTrades","netReturnDifference","bootstrapLowerBound",
             "maxDrawdown","baselineMaxDrawdown","costStressNetReturnDifference")
    if any(isinstance(candidate.get(k),bool) or not isinstance(candidate.get(k),(int,float)) or
           not math.isfinite(candidate[k]) for k in metrics):
        raise ValueError("missing or nonfinite evidence metrics")
    conditions={
        "forward_sessions":candidate["forwardSessions"]>=60,
        "completed_trades":candidate["completedTrades"]>=20,
        "positive_paired_improvement":candidate["netReturnDifference"]>0,
        "positive_uncertainty_bound":candidate["bootstrapLowerBound"]>0,
        "drawdown_not_worse":0<=candidate["maxDrawdown"]<=candidate["baselineMaxDrawdown"]<=1,
        "cost_stress_survives":candidate["costStressNetReturnDifference"]>0,
        "independent_lineage":candidate.get("independentLineageVerified") is True,
        "forward_only":candidate.get("forwardOnlyVerified") is True,
        "costs_complete":candidate.get("allCostsVerified") is True,
        "benchmark_complete":candidate.get("benchmarkVerified") is True,
    }
    return {"schema":"oracle.evergreen-learning-gate.v1","mode":"RESEARCH_ONLY",
      "candidateId":candidate["candidateId"],"baselineId":candidate["baselineId"],
      "evidenceHash":candidate["evidenceHash"],"criteria":conditions,
      "reviewEligible":all(conditions.values()),"promotionAuthorized":False,
      "ordersEnabled":False,"brokerFillsVerified":False,
      "reasons":[k for k,v in conditions.items() if not v],
      "warning":"Research eligibility only; human review, independent audit and separate authorization required. No autonomous live trading."}
