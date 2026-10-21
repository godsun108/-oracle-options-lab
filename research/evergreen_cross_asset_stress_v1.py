"""Deterministic, read-only correlated shock stress of a paper portfolio.

Input notionals must already be in a single reporting currency. Shocks are
explicit caller-provided fractions, not forecasts or verified market data.
No order generation, broker calls, or self-certified eligibility.
"""
import math

def number(x,name,positive=False):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or (x<=0 if positive else x<0):
        raise ValueError("invalid "+name)
    return float(x)

def evaluate(snapshot,scenarios):
    if not isinstance(snapshot,dict) or snapshot.get("mode")!="RESEARCH_ONLY" or snapshot.get("ordersEnabled") is not False:
        raise ValueError("unsafe snapshot")
    equity=number(snapshot.get("equity"),"equity",True)
    positions=snapshot.get("positions")
    if not isinstance(positions,list) or not isinstance(scenarios,list) or not scenarios:
        raise ValueError("missing positions or scenarios")
    entries=[]
    for p in positions:
        if not isinstance(p,dict) or not isinstance(p.get("riskGroup"),str) or not p["riskGroup"] or p.get("side") not in ("LONG","SHORT"):
            raise ValueError("invalid position")
        entries.append((p["riskGroup"],p["side"],number(p.get("notional"),"notional")))
    results=[]
    for scenario in scenarios:
        if not isinstance(scenario,dict) or not isinstance(scenario.get("id"),str) or not scenario["id"]:
            raise ValueError("invalid scenario")
        shocks=scenario.get("groupShocks")
        if not isinstance(shocks,dict) or any(not isinstance(k,str) or not k for k in shocks):
            raise ValueError("invalid shocks")
        for group,_,_ in entries:
            if group not in shocks: raise ValueError("missing group shock")
        for shock in shocks.values():
            if isinstance(shock,bool) or not isinstance(shock,(int,float)) or not math.isfinite(shock) or shock< -1:
                raise ValueError("invalid shock")
        pnl=sum(n*(1 if side=="LONG" else -1)*shocks[group] for group,side,n in entries)
        results.append({"id":scenario["id"],"hypotheticalPnl":pnl,
                        "hypotheticalEquity":equity+pnl,
                        "hypotheticalLossFraction":max(0,-pnl/equity)})
    return {"schema":"oracle.evergreen-stress.v1","mode":"RESEARCH_ONLY",
            "scenarioCount":len(results),"results":results,
            "worstHypotheticalLossFraction":max(r["hypotheticalLossFraction"] for r in results),
            "liveOrderAuthorized":False,"ordersEnabled":False,"verifiedEdge":False,
            "warning":"User-defined instantaneous linear shocks only; excludes nonlinear derivatives, gap fills, funding, liquidation, FX conversion and execution costs. Not a live risk certificate."}
