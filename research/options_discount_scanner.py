"""Read-only option quote anomaly screening; never submits orders.

Reference midpoints are NOT executable exit prices. Only observed bid/ask
quotes are considered; no fill or instant profit is implied.
"""
import math

def screen(quotes, *, max_spread_pct=0.20, min_discount_pct=0.15,
           fee_per_contract=0.65, max_quote_age_seconds=2.0,
           market_regime="NEUTRAL"):
    if market_regime not in ("HIGH", "LOW", "NEUTRAL"):
        raise ValueError("unknown market regime")
    findings=[]
    for q in quotes:
        try:
            bid=float(q["bid"]); ask=float(q["ask"]); reference=float(q["reference_mid"])
            age=float(q["quote_age_seconds"]); size=int(q["ask_size"])
            dte=int(q["dte"])
            side=str(q["type"]).lower()
            if side not in ("put", "call"):
                continue
            if (side=="put" and not 30<=dte<=60) or (side=="call" and dte<30):
                continue
            if not all(math.isfinite(x) for x in (bid,ask,reference,age)):
                continue
            if bid<0 or ask<=0 or reference<=0 or ask<bid or age<0 or age>max_quote_age_seconds:
                continue
            if size<=0 or dte<0 or (ask-bid)/reference>max_spread_pct:
                continue
            discount=(reference-ask)/reference
            if discount<min_discount_pct:
                continue
            # Conservative immediately executable round-trip: buy ask, sell bid.
            net_per_contract=(bid-ask)*100-2*fee_per_contract
            findings.append({
                "symbol":str(q["symbol"]),"type":side,
                "regime":market_regime,
                "directional_priority":("HIGH" if side=="put" else "LOW")==market_regime,
                "ask":ask,"bid":bid,
                "reference_mid":reference,"discount_pct":round(100*discount,4),
                "ask_size":size,"dte":dte,
                "immediate_roundtrip_net_per_contract":round(net_per_contract,2),
                "instant_profit_verified":net_per_contract>0,
                "orders_enabled":False,"simulation_only":True,
                "warning":"Reference midpoint is not executable; displayed size and quotes can change before fills."
            })
        except (KeyError,ValueError,TypeError,OverflowError):
            continue
    return sorted(findings,key=lambda x:(x["directional_priority"],x["discount_pct"]),reverse=True)
