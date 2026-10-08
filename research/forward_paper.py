"""Incremental forward paper-state engine for completed bars.

Consumes one previously unseen completed bar at a time. Caller must persist
state atomically and ensure single-writer execution. No broker connectivity.
This models unlevered shares only, not options.
"""
from copy import deepcopy
from research.conditional_paper import Plan

def initial_state(cash=2000.0):
    if cash <= 0:
        raise ValueError("cash must be positive")
    return {"cash":float(cash),"position":None,"pending":None,"last_bar":None,
            "events":[],"orders_enabled":False,"mode":"FORWARD_PAPER_ONLY"}

def step(state, plan, bar, fee_per_share=0.0, slippage_per_share=0.01):
    plan.check()
    if not plan.validated:
        raise ValueError("strategy not validated")
    if fee_per_share<0 or slippage_per_share<0:
        raise ValueError("invalid costs")
    t=bar["time"]
    if state["last_bar"] is not None and t<=state["last_bar"]:
        raise ValueError("stale or duplicate bar")
    if not (0<bar["low"]<=bar["open"]<=bar["high"] and
            bar["low"]<=bar["close"]<=bar["high"]):
        raise ValueError("invalid bar")
    s=deepcopy(state)
    side=1 if plan.direction=="long" else -1
    # Fill a prior-bar signal at current open. Only cash-funded long shares
    # are implemented; short strategies are observed but never opened.
    if s["pending"] is not None and s["position"] is None:
        if side==1:
            entry=bar["open"]+slippage_per_share
            unit_risk=entry-plan.stop+2*(slippage_per_share+fee_per_share)
            if entry>plan.stop and unit_risk>0:
                qty=int(min((s["cash"]*plan.risk_fraction)//unit_risk,
                            s["cash"]//(entry+fee_per_share)))
                if qty>0:
                    s["cash"]-=qty*(entry+fee_per_share)
                    s["position"]={"entry":entry,"qty":qty,"entry_time":t,"bars_held":0}
                    s["events"].append({"type":"PAPER_ENTRY","time":t,"price":entry,"qty":qty})
        s["pending"]=None
    if s["position"] is not None:
        pos=s["position"]
        pos["bars_held"]+=1
        stop_hit=bar["low"]<=plan.stop
        target_hit=bar["high"]>=plan.target
        if stop_hit:
            exit_raw=min(bar["open"],plan.stop)
            reason="STOP"
        elif target_hit:
            exit_raw=plan.target
            reason="TARGET"
        elif pos["bars_held"]>=plan.max_bars:
            exit_raw=bar["close"]
            reason="TIME"
        else:
            exit_raw=None
        if exit_raw is not None:
            exit_price=exit_raw-slippage_per_share
            s["cash"]+=pos["qty"]*(exit_price-fee_per_share)
            pnl=pos["qty"]*(exit_price-pos["entry"])-2*pos["qty"]*fee_per_share
            s["events"].append({"type":"PAPER_EXIT","time":t,"price":exit_price,
                                "qty":pos["qty"],"pnl":round(pnl,2),"reason":reason})
            s["position"]=None
    if s["position"] is None and s["pending"] is None and side==1:
        if bar["close"]>=plan.trigger:
            s["pending"]={"signal_time":t}
            s["events"].append({"type":"PAPER_SIGNAL","time":t})
    s["last_bar"]=t
    return s
