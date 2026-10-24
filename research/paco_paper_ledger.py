"""PACO paper ledger: deterministic hypothetical fill accounting, never orders.

Caller supplies timestamped quote evidence and explicit BUY/SELL intents.
No claims of executable fills; conservative ask-to-buy, bid-to-sell proxy.
"""
import hashlib
import json
from datetime import datetime, timezone
from math import isfinite

def _hash(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def timestamp(value):
    try:
        stamp=datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("invalid timestamp") from exc
    if stamp.tzinfo is None:raise ValueError("timestamp must include timezone")
    return stamp.astimezone(timezone.utc)


def quote_evidence(quote, side, quantity, as_of):
    result={}
    for name in ("bid", "ask", "age_seconds"):
        if isinstance(quote[name], bool):raise ValueError("boolean quote value")
        result[name]=float(quote[name])
        if not isfinite(result[name]):raise ValueError("nonfinite quote")
    for name in ("bid_size", "ask_size"):
        size=quote[name]
        if type(size) is not int or size<0:raise ValueError("invalid displayed size")
        result[name]=size
    if not (0<=result['bid']<=result['ask'] and result['ask']>0 and 0<=result['age_seconds']<=2):
        raise ValueError("unreliable quote")
    if result['ask_size' if side=='BUY' else 'bid_size']<quantity:
        raise ValueError("insufficient displayed size")
    for name in ('provider', 'provider_quote_id', 'provider_timestamp'):
        if name in quote:
            if not isinstance(quote[name],str) or not quote[name].strip():
                raise ValueError("invalid declared provenance")
            result[name]=quote[name]
    if 'provider_timestamp' in result:
        age=(timestamp(as_of)-timestamp(result['provider_timestamp'])).total_seconds()
        if not 0<=age<=2 or abs(age-result['age_seconds'])>0.000001:
            raise ValueError("quote timestamp and age disagree")
    return result


def initial(cash=2000.0):
    if isinstance(cash,bool):raise ValueError("invalid cash")
    cash=float(cash)
    if not isfinite(cash) or cash<0:raise ValueError("invalid cash")
    return {"schema":"paco-paper-ledger-v1","initial_cash":cash,
            "cash":cash,"positions":{},"entries":[],"head_hash":"GENESIS",
            "orders_enabled":False,"simulation_only":True}

def record(ledger, *, symbol, side, quantity, quote, as_of, fee_per_contract=0.65):
    verify(ledger)
    stamp=timestamp(as_of)
    if ledger['entries'] and stamp<=timestamp(ledger['entries'][-1]['as_of']):
        raise ValueError("nonmonotonic timestamp")
    if side not in ("BUY","SELL") or not isinstance(symbol,str) or not symbol.strip() or type(quantity)!=int or quantity<=0:
        raise ValueError("invalid intent")
    evidence=quote_evidence(quote,side,quantity,as_of)
    bid=evidence['bid'];ask=evidence['ask']
    if type(fee_per_contract) not in (int,float) or not isfinite(fee_per_contract) or fee_per_contract<0:
        raise ValueError("invalid fee")
    current=int(ledger["positions"].get(symbol,0))
    price=ask if side=="BUY" else bid
    fee=round(quantity*fee_per_contract,4)
    delta=quantity*price*100
    if side=="BUY":
        if ledger["cash"]<delta+fee:raise ValueError("insufficient paper cash")
        new_cash=round(ledger["cash"]-delta-fee,4)
        new_position=current+quantity
    else:
        if current<quantity:raise ValueError("cannot paper-sell unheld options")
        new_cash=round(ledger["cash"]+delta-fee,4)
        new_position=current-quantity
    if new_cash<0:raise ValueError("insufficient cash for sale fee")
    entry={"as_of":as_of,"symbol":symbol,"side":side,"quantity":quantity,
           "price":price,"fee":round(fee,4),"prev_hash":ledger["head_hash"],
           "kind":"HYPOTHETICAL_QUOTE_FILL_NOT_EXECUTED",
           "quote_evidence":evidence}
    entry["entry_hash"]=_hash(entry)
    result={**ledger,"cash":new_cash,"positions":dict(ledger["positions"]),
            "entries":[*ledger["entries"],entry],"head_hash":entry["entry_hash"]}
    if new_position:result["positions"][symbol]=new_position
    else:result["positions"].pop(symbol,None)
    return result

def verify(ledger):
    if ledger["schema"]!="paco-paper-ledger-v1" or ledger["orders_enabled"] is not False or ledger.get("simulation_only") is not True:
        raise ValueError("invalid ledger")
    state=initial(ledger["initial_cash"])
    previous_time=None; quoted=0
    for e in ledger["entries"]:
        if e["prev_hash"]!=state["head_hash"] or _hash({k:v for k,v in e.items() if k!="entry_hash"})!=e["entry_hash"]:
            raise ValueError("broken hash chain")
        side=e["side"];qty=e["quantity"];price=e["price"];fee=e["fee"];symbol=e["symbol"]
        if (side not in ("BUY","SELL") or type(qty)!=int or qty<=0
                or not isinstance(symbol,str) or not symbol.strip()
                or type(price) not in (int,float) or not isfinite(price) or price<0
                or (side=="BUY" and price==0)
                or type(fee) not in (int,float) or not isfinite(fee) or fee<0):
            raise ValueError("invalid entry")
        moment=timestamp(e['as_of'])
        if previous_time is not None and moment<=previous_time:raise ValueError("nonmonotonic timestamp")
        previous_time=moment
        if e.get('kind')!='HYPOTHETICAL_QUOTE_FILL_NOT_EXECUTED':raise ValueError("invalid fill kind")
        if 'quote_evidence' in e:
            q=quote_evidence(e['quote_evidence'],side,qty,e['as_of'])
            if price!=q['ask' if side=='BUY' else 'bid']:raise ValueError("fill price disagrees with quote")
            quoted+=1
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
    if type(ledger["cash"]) not in (int,float) or not isfinite(ledger["cash"]):raise ValueError("invalid saved cash")
    if (round(state["cash"],4)!=round(ledger["cash"],4)
            or state["positions"]!=ledger["positions"] or state["head_hash"]!=ledger["head_hash"]):
        raise ValueError("ledger state mismatch")
    return {"verified":True,"entry_count":len(ledger["entries"]),"cash":state["cash"],
            "open_contracts":sum(state["positions"].values()),
            "quote_evidence_entries":quoted,"legacy_entries_without_quote_evidence":len(ledger["entries"])-quoted,
            "independent_quote_freshness_verified":False,
            "performance_established":False,"orders_enabled":False}
