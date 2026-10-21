"""Fail-closed read-only consumer of private ETF paper stress export.

Do not trust caller-provided quote-provenance or account verification claims.
An independent verifier is required before any automated risk decision.
"""
from evergreen_cross_asset_stress_v1 import evaluate as stress_evaluate

def evaluate(export, scenarios, *, max_stress_loss_fraction=0.05):
    if not isinstance(export,dict) or export.get("schema")!="oracle.evergreen-paper-stress-input.v1":
        raise ValueError("invalid stress export schema")
    if export.get("mode")!="RESEARCH_ONLY" or export.get("ordersEnabled") is not False or export.get("liveOrderAuthorized") is not False:
        raise ValueError("unsafe execution flags")
    if export.get("reportingCurrency")!="USD" or export.get("brokerFillsVerified") is not False:
        raise ValueError("unsupported currency or fill claims")
    if export.get("portfolioComplete") is not True or export.get("ledgerReconciled") is not True or export.get("missingMarks")!=[]:
        return _blocked("incomplete_or_unreconciled_portfolio")
    if export.get("quoteProvenanceVerified") is not False or export.get("stressEligible") is not False:
        raise ValueError("self-certified source or stress eligibility")
    if isinstance(max_stress_loss_fraction,bool) or not isinstance(max_stress_loss_fraction,(int,float)) or not 0<max_stress_loss_fraction<=1:
        raise ValueError("invalid stress threshold")
    if not isinstance(export.get("positions"),list):
        raise ValueError("invalid positions")
    for p in export["positions"]:
        if not isinstance(p,dict) or p.get("side")!="LONG" or p.get("riskGroup") not in ("SPY","QQQ","IWM","SMH","TLT","GLD"):
            raise ValueError("unsupported position")
    result=stress_evaluate({"mode":"RESEARCH_ONLY","ordersEnabled":False,
        "equity":export.get("equity"),"positions":export["positions"]},scenarios)
    breach=result["worstHypotheticalLossFraction"]>=max_stress_loss_fraction
    return {"schema":"oracle.evergreen-stress-bridge.v1","mode":"RESEARCH_ONLY",
        "stress":result,"stressThresholdBreached":breach,
        "researchRiskWarning":breach,"paperCandidateEligible":False,
        "sourceEvidenceVerified":False,"liveOrderAuthorized":False,"ordersEnabled":False,
        "reasons":["stress_threshold_breached"] if breach else ["independent_source_verification_missing"],
        "warning":"Hypothetical scenario calculation only; neither marks nor positions independently authenticated."}

def _blocked(reason):
    return {"schema":"oracle.evergreen-stress-bridge.v1","mode":"RESEARCH_ONLY",
        "stress":None,"stressThresholdBreached":None,"researchRiskWarning":True,
        "paperCandidateEligible":False,"sourceEvidenceVerified":False,
        "liveOrderAuthorized":False,"ordersEnabled":False,"reasons":[reason],
        "warning":"Incomplete portfolio cannot be stress tested or authorized."}
