"""PACO paper ledger: deterministic hypothetical fill accounting, never orders.

Caller supplies timestamped quote evidence and explicit BUY/SELL intents.
No claims of executable fills; conservative ask-to-buy, bid-to-sell proxy.
"""
import hashlib
import json
from datetime import datetime
from math import isfinite

def _hash(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def initial(cash=2000.0):
    cash=float(cash)
    if not isfinite(cash) or cash<0:raise ValueError("invalid cash")
    return {"schema":"paco-paper-ledger-v1","initial_cash":cash,
            "cash":cash,"positions":{},"entries":[],"head_hash":"GENESIS",
            "orders_enabled":False,"simulation_only":True}

def record(ledger, *, symbol, side, quantity, quote, as_of, fee_per_contract=0.65):
    if ledger.get("orders_enabled") is not False or ledger.get("schema")!="paco-paper-ledger-v1":
        raise ValueError("not a paper ledger")
    stamp=datetime.fromisoformat(as_of)
    if stamp.tzinfo is None:raise ValueError("timestamp must include timezone")
    if ledger["entries"] and as_of<=ledger["entries"][-1]["as_of"]:
        raise ValueError("nonmonotonic timestamp")
    if side not in ("BUY","SELL") or not symbol or type(quantity)!=int or quantity<=0:
        raise ValueError("invalid intent")
    bid=float(quote["bid"]);ask=float(quote["ask"])
    age=float(quote["age_seconds"]);size=int(quote["ask_size" if side=="BUY" else "bid_size"])
    if not all(isfinite(x) for x in (bid,ask,age,fee_per_contract)):
        raise ValueError("nonfinite quote")
    if bid<0 or ask<=0 or bid>ask or age<0 or age>2 or size<quantity or fee_per_contract<0:
        raise ValueError("unreliable quote or insufficient displayed size")
    current=int(ledger["positions"].get(symbol,0))
    price=ask if side=="BUY" else bid
    fee=quantity*fee_per_contract
    delta=quantity*price*100
    if side=="BUY":
        if ledger["cash"]<delta+fee:raise ValueError("insufficient paper cash")
        new_cash=round(ledger["cash"]-delta-fee,4)
        new_position=current+quantity
    else:
        if current<quantity:raise ValueError("cannot paper-sell unheld options")
        new_cash=round(ledger["cash"]+delta-fee,4)
        new_position=current-quantity
    entry={"as_of":as_of,"symbol":symbol,"side":side,"quantity":quantity,
           "price":price,"fee":round(fee,4),"prev_hash":ledger["head_hash"],
           "kind":"HYPOTHETICAL_QUOTE_FILL_NOT_EXECUTED"}
    entry["entry_hash"]=_hash(entry)
    result={**ledger,"cash":new_cash,"positions":dict(ledger["positions"]),
            "entries":[*ledger["entries"],entry],"head_hash":entry["entry_hash"]}
    if new_position:result["positions"][symbol]=new_position
    else:result["positions"].pop(symbol,None)
    return result

def verify(ledger):
    if ledger["schema"]!="paco-paper-ledger-v1" or ledger["orders_enabled"] is not False:
        raise ValueError("invalid ledger")
    state=initial(ledger["initial_cash"])
    for e in ledger["entries"]:
        if e["prev_hash"]!=state["head_hash"] or _hash({k:v for k,v in e.items() if k!="entry_hash"})!=e["entry_hash"]:
            raise ValueError("broken hash chain")
        side=e["side"];qty=e["quantity"];price=e["price"];fee=e["fee"];symbol=e["symbol"]
        if side not in ("BUY","SELL") or type(qty)!=int or qty<=0 or price<=0 or fee<0:
            raise ValueError("invalid entry")
        current=state["positions"].get(symbol,0)
        if side=="BUY":
            state["cash"]=round(state["cash"]-qty*price*100-fee,4)
            state["positions"][symbol]=current+qty
        else:
            if current<qty:raise ValueError("short sale in long-only ledger")
            state["cash"]=round(state["cash"]+qty*price*100-fee,4)
            if current==qty:state["positions"].pop(symbol)
            else:state["positions"][symbol]=current-qty
        if state["cash"]<0:raise ValueError("negative cash")
        state["head_hash"]=e["entry_hash"]
    if (round(state["cash"],4)!=round(ledger["cash"],4)
            or state["positions"]!=ledger["positions"] or state["head_hash"]!=ledger["head_hash"]):
        raise ValueError("ledger state mismatch")
    return {"verified":True,"entry_count":len(ledger["entries"]),"cash":state["cash"],
            "open_contracts":sum(state["positions"].values()),
            "performance_established":False,"orders_enabled":False}
