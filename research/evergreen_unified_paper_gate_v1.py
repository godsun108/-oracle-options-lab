"""Combined research-only portfolio and stress decision. No broker integration.

The independent verification prerequisites remain unfulfilled: therefore the
combined gate can explain hypothetical risk, but cannot approve actual orders.
"""
from evergreen_portfolio_risk_v1 import assess as portfolio_assess
from evergreen_stress_bridge_v1 import evaluate as stress_evaluate

def assess(snapshot, proposal, mandate, stress_export, scenarios):
    portfolio=portfolio_assess(snapshot,proposal,mandate)
    stress=stress_evaluate(stress_export,scenarios)
    reasons=[]
    if not portfolio["paperCandidateEligible"]:
        reasons.extend("portfolio:"+r for r in portfolio["reasons"])
    if stress["stressThresholdBreached"] is True:
        reasons.append("stress:threshold_breached")
    if stress["stress"] is None:
        reasons.append("stress:incomplete")
    # Both sources are currently untrusted. Never infer independent verification
    # from their own claimed flags or from passing hypothetical risk checks.
    reasons.append("independent_market_and_account_verification_missing")
    return {"schema":"oracle.evergreen-unified-paper-gate.v1",
            "mode":"RESEARCH_ONLY","portfolio":portfolio,"stress":stress,
            "hypotheticalRiskWithinLimits":portfolio["paperCandidateEligible"] and
                stress["stressThresholdBreached"] is False,
            "paperCandidateEligible":False,"liveOrderAuthorized":False,
            "ordersEnabled":False,"reasons":list(dict.fromkeys(reasons)),
            "warning":"Risk simulation only; independent verification and actual ledger integration required before paper execution."}
