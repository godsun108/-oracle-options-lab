"""PACO paper portfolio report, based on verified hypothetical fill records.

Realized cashflows are not investment returns unless entry cost basis is matched.
Open-position marks use supplied *fresh* bids and are not guaranteed exits.
"""
from math import isfinite
from research.paco_paper_ledger import verify

def report(ledger, marks=None, *, max_age_seconds=2.0):
    if type(max_age_seconds) not in (int,float) or not isfinite(max_age_seconds) or max_age_seconds<=0:
        raise ValueError("invalid age bound")
    audit=verify(ledger)
    lots={}
    realized=0.0
    closed=0
    for e in ledger["entries"]:
        sym=e["symbol"];qty=e["quantity"];fee=e["fee"]
        if e["side"]=="BUY":
            lots.setdefault(sym,[]).append([qty,e["price"]*100+fee/qty])
        else:
            left=qty;proceeds=qty*e["price"]*100-fee
            cost=0.0
            while left:
                if not lots.get(sym):raise ValueError("unmatched sale")
                lot=lots[sym][0];take=min(left,lot[0])
                cost+=take*lot[1];lot[0]-=take;left-=take
                if lot[0]==0:lots[sym].pop(0)
            realized+=proceeds-cost
            closed+=qty
    unrealized=0.0;marked=True
    marks=marks or {}
    missing=[]
    for sym,held in ledger["positions"].items():
        m=marks.get(sym)
        if not m:
            marked=False;missing.append(sym);continue
        try:
            if any(isinstance(m[k],bool) for k in ("bid","age_seconds")) or type(m["bid_size"]) is not int:
                raise ValueError("invalid mark")
            bid=float(m["bid"]);age=float(m["age_seconds"]);size=m["bid_size"]
        except (KeyError,TypeError,ValueError,OverflowError):
            marked=False;missing.append(sym);continue
        if not (isfinite(bid) and isfinite(age) and bid>=0 and 0<=age<=max_age_seconds and size>=held):
            marked=False;missing.append(sym);continue
        basis=sum(qty*unit for qty,unit in lots[sym])
        unrealized+=bid*100*held-basis
    complete=marked
    return {"schema":"paco-paper-performance-v1",
            "audit_verified":audit["verified"],
            "quote_evidence_entries":audit["quote_evidence_entries"],
            "legacy_entries_without_quote_evidence":audit["legacy_entries_without_quote_evidence"],
            "independent_quote_freshness_verified":False,
            "broker_fills_verified":False,
            "hypothetical_trades":audit["entry_count"],
            "closed_contracts":closed,
            "open_contracts":audit["open_contracts"],
            "paper_cash":audit["cash"],
            "hypothetical_realized_pnl":round(realized,2),
            "hypothetical_unrealized_pnl":round(unrealized,2) if complete else None,
            "hypothetical_total_pnl":round(realized+unrealized,2) if complete else None,
            "unmarked_symbols":missing,
            "all_positions_marked":complete,
            "live_performance_established":False,
            "historical_edge_established":False,
            "orders_enabled":False,
            "warning":"Hypothetical ask/bid fill proxies only; no evidence of actual executions or live edge."}
