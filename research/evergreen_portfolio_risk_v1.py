"""Fail-closed, portfolio-wide paper risk governor. No broker calls.

All monetary values are in one reporting currency. The caller must independently
verify positions, quotes, FX conversion, and broker balances; this module cannot.
"""
import math

def _number(value, name, *, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < minimum:
        raise ValueError("invalid "+name)
    return float(value)

def assess(snapshot, proposal, mandate):
    if not all(isinstance(x,dict) for x in (snapshot,proposal,mandate)):
        raise ValueError("invalid inputs")
    if snapshot.get("mode")!="RESEARCH_ONLY" or snapshot.get("ordersEnabled") is not False or mandate.get("ordersEnabled") is not False:
        raise ValueError("live execution prohibited")
    if snapshot.get("reconciled") is not True or snapshot.get("quotesVerified") is not True or snapshot.get("fxConversionsVerified") is not True:
        return _result(False,["portfolio_evidence_unverified"])
    equity=_number(snapshot.get("equity"),"equity",minimum=0.01)
    peak=_number(snapshot.get("peakEquity"),"peak equity",minimum=0.01)
    day_start=_number(snapshot.get("dayStartEquity"),"day start equity",minimum=0.01)
    gross=_number(snapshot.get("grossExposure"),"gross exposure")
    positions=snapshot.get("positions")
    if not isinstance(positions,list): raise ValueError("invalid positions")
    groups={}
    for p in positions:
        if not isinstance(p,dict) or not isinstance(p.get("riskGroup"),str) or not p["riskGroup"]: raise ValueError("invalid position")
        v=_number(p.get("notional"),"position notional")
        groups[p["riskGroup"]]=groups.get(p["riskGroup"],0)+v
    if abs(sum(groups.values())-gross)>max(0.01,gross*1e-6):
        return _result(False,["exposure_reconciliation_failed"])
    action=proposal.get("action")
    if action not in ("OPEN","CLOSE","REDUCE"): raise ValueError("invalid action")
    notional=_number(proposal.get("notional"),"proposal notional")
    group=proposal.get("riskGroup")
    if not isinstance(group,str) or not group: raise ValueError("invalid risk group")
    # CLOSE/REDUCE may lower risk but must never be silently treated as
    # opening capacity. A separate broker position validator is required.
    if action!="OPEN": return _result(False,["closing_order_requires_position_reconciliation"])
    if mandate.get("killSwitch") is not False: return _result(False,["kill_switch_active"])
    capital=_number(mandate.get("capitalLimit"),"capital limit",minimum=0.01)
    max_position=_number(mandate.get("maxPositionFraction"),"position fraction")
    max_gross=_number(mandate.get("maxGrossFraction"),"gross fraction")
    max_group=_number(mandate.get("maxGroupFraction"),"group fraction")
    daily_limit=_number(mandate.get("dailyLossFraction"),"daily loss fraction")
    dd_limit=_number(mandate.get("drawdownFraction"),"drawdown fraction")
    if any(x>1 for x in (max_position,max_gross,max_group,daily_limit,dd_limit)):
        raise ValueError("risk fraction exceeds one")
    reasons=[]
    if equity>capital+1e-8: reasons.append("equity_exceeds_mandate_capital")
    if (day_start-equity)/day_start>=daily_limit: reasons.append("daily_loss_halt")
    if (peak-equity)/peak>=dd_limit: reasons.append("drawdown_halt")
    if notional>min(capital,equity)*max_position: reasons.append("position_limit")
    if gross+notional>min(capital,equity)*max_gross: reasons.append("gross_exposure_limit")
    if groups.get(group,0)+notional>min(capital,equity)*max_group: reasons.append("correlated_group_limit")
    if proposal.get("verifiedVenueSession") is not True: reasons.append("venue_unverified")
    if proposal.get("verifiedQuote") is not True: reasons.append("quote_unverified")
    if proposal.get("independentStrategyEvidence") is not True: reasons.append("strategy_evidence_unverified")
    return _result(not reasons,reasons)

def _result(eligible,reasons):
    return {"schema":"oracle.evergreen-portfolio-paper-risk.v1",
            "mode":"RESEARCH_ONLY","paperCandidateEligible":eligible,
            "liveOrderAuthorized":False,"ordersEnabled":False,
            "reasons":reasons,
            "warning":"Advisory paper gate only. Never grants broker permissions, live execution, or capital authority."}
