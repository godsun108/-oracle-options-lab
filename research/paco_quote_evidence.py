"""Validate independently sourced option quote envelopes before PACO research.

A structurally valid quote is NOT independently authenticated market data.
This gate rejects missing provenance and future/stale timestamps, but cannot
establish a provider's truthfulness without external evidence.
"""
from datetime import datetime
from math import isfinite

def validate(raw, *, now_iso, max_age_seconds=2.0):
    now=datetime.fromisoformat(now_iso)
    if now.tzinfo is None:raise ValueError("timezone-aware clock required")
    if max_age_seconds<=0:raise ValueError("invalid age bound")
    clean=[]
    rejected=[]
    seen=set()
    for i,q in enumerate(raw):
        try:
            symbol=str(q["occ_symbol"])
            provider=str(q["provider"])
            provider_id=str(q["provider_quote_id"])
            stamp=datetime.fromisoformat(q["provider_timestamp"])
            if stamp.tzinfo is None:raise ValueError("naive provider timestamp")
            bid=float(q["bid"]);ask=float(q["ask"])
            bid_size=int(q["bid_size"]);ask_size=int(q["ask_size"])
            if not symbol or not provider or not provider_id:
                raise ValueError("missing quote identity")
            if (symbol,provider_id) in seen:
                raise ValueError("duplicate quote identity")
            age=(now-stamp).total_seconds()
            if not all(isfinite(x) for x in (bid,ask,age)):
                raise ValueError("nonfinite price")
            if age<0 or age>max_age_seconds or bid<0 or ask<=0 or ask<bid:
                raise ValueError("stale/future/crossed quote")
            if bid_size<=0 or ask_size<=0:
                raise ValueError("missing displayed liquidity")
            seen.add((symbol,provider_id))
            clean.append({"symbol":symbol,"bid":bid,"ask":ask,
                          "bid_size":bid_size,"ask_size":ask_size,
                          "age_seconds":round(age,6),
                          "provider":provider,"provider_quote_id":provider_id,
                          "provider_timestamp":q["provider_timestamp"],
                          "provenance_status":"DECLARED_NOT_INDEPENDENTLY_AUTHENTICATED"})
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            rejected.append({"index":i,"reason":str(exc)})
    return {"schema":"paco-quote-evidence-v1","quotes":clean,"rejected":rejected,
            "independently_authenticated":False,
            "broker_orders_enabled":False,
            "warning":"Provider identity/timestamps are declared inputs; authenticate at ingestion."}
