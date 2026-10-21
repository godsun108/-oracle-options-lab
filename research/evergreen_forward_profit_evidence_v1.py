"""Fail-closed forward paper profitability evidence aggregator.

Uses existing sequential settled-paper scorecard, never treats self-reported
settlements as independently authenticated broker or market observations.
"""
from edge_profitability_scorecard_v1 import score

def evaluate(payload, *, min_trades=30):
    if not isinstance(payload,dict) or payload.get("schema")!="oracle.forward-settlements.v1":
        raise ValueError("invalid settlement schema")
    if payload.get("mode")!="RESEARCH_ONLY" or payload.get("ordersEnabled") is not False:
        raise ValueError("live execution prohibited")
    trades=payload.get("trades")
    if not isinstance(trades,list): raise ValueError("invalid trades")
    result=score(trades,min_trades=min_trades)
    reasons=[]
    if not trades: reasons.append("no_settled_paper_trades")
    if not result["minimum_sample_met"]: reasons.append("insufficient_settled_sample")
    if not result["preliminary_edge_gate_passed"]: reasons.append("preliminary_profit_gate_not_met")
    reasons.extend(["independent_settlement_lineage_missing","market_quote_provenance_missing",
                    "cost_model_independent_audit_missing","walk_forward_benchmark_missing"])
    return {"schema":"oracle.evergreen-forward-profit-evidence.v1","mode":"RESEARCH_ONLY",
            "scorecard":result,"preliminarySelfReportedGatePassed":result["preliminary_edge_gate_passed"],
            "independentlyVerifiedProfitableEdge":False,
            "paperCandidateEligible":False,"liveOrderAuthorized":False,"ordersEnabled":False,
            "reasons":reasons,
            "warning":"Only sequential non-overlapping settled simulated trades accepted. No independent source, fill or cost verification; not evidence of deployable edge."}
