"""PACO Terminator: read-only, conservative options position review.

No live orders, auto-cancellation, or profit guarantees. User chooses actual
exit. Every quote and position must be provided from independently sourced data.
"""
from datetime import datetime
from math import isfinite

def evaluate(positions, quotes, *, now_iso, thresholds=(25,50,100,500,1000), fee_per_contract=0.65):
    now=datetime.fromisoformat(now_iso)
    if now.tzinfo is None:
        raise ValueError("timezone-aware time required")
    if fee_per_contract<0:
        raise ValueError("negative fee")
    result=[]
    for p in positions:
        symbol=p["symbol"]
        qty=int(p["quantity"])
        paid=float(p["entry_ask"])
        if qty<=0 or paid<=0 or not isfinite(paid):
            raise ValueError("invalid long-option position")
        q=quotes.get(symbol)
        if not q:
            result.append({"symbol":symbol,"status":"NO_QUOTE","suggestion":"REVIEW_MANUALLY"})
            continue
        bid=float(q["bid"]); ask=float(q["ask"])
        age=float(q["age_seconds"]); size=int(q["bid_size"])
        if not all(isfinite(x) for x in (bid,ask,age)) or bid<0 or ask<bid or age<0 or age>2 or size<=0:
            result.append({"symbol":symbol,"status":"UNRELIABLE_QUOTE","suggestion":"REVIEW_MANUALLY"})
            continue
        # Conservative executable-price proxy, not a fill promise.
        net_one=(bid-paid)*100-2*fee_per_contract
        invested=paid*100+fee_per_contract
        pct=100*net_one/invested
        crossed=[x for x in thresholds if pct>=x]
        scenarios=[]
        for sell_qty in sorted(set([0,1,qty//2,qty])):
            if not 0<=sell_qty<=qty:continue
            # Bid size caps a single immediate exit, but may change.
            if sell_qty>size:continue
            scenarios.append({"sell_contracts":sell_qty,"retain_contracts":qty-sell_qty,
                              "estimated_realized_pnl":round(net_one*sell_qty,2),
                              "requires_human_confirmation":True})
        result.append({"symbol":symbol,"status":"PAPER_REVIEW","quantity":qty,
                       "bid":bid,"ask":ask,"bid_size":size,
                       "estimated_exit_return_pct":round(pct,2),
                       "thresholds_crossed":crossed,"scenarios":scenarios,
                       "suggestion":"REVIEW_AT_OPEN" if crossed else "MONITOR",
                       "orders_enabled":False,"cancelled_orders_verified":False,
                       "disclaimer":"No orders placed/cancelled. Bid-size and fill are not guaranteed."})
    return {"schema":"paco-terminator-paper-review-v1","as_of":now_iso,
            "orders_enabled":False,"human_decision_required":True,"positions":result}
