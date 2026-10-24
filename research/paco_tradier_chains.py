"""Read-only Tradier option chain adapter; no order endpoints.

Retain provider bid/ask timestamps and assess their declared age separately.
Provider time is not independent authentication or evidence of execution.
Reference: https://docs.tradier.com/reference/brokerage-api-markets-get-options-chains
"""
import json
from math import isfinite
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE="https://api.tradier.com/v1"

def timing_evidence(item, observed_at):
    observed=datetime.fromisoformat(observed_at.replace("Z","+00:00"))
    if observed.tzinfo is None:raise ValueError("timezone-aware observation required")
    result={"timestamp_basis":"provider-declared Unix time; seconds or milliseconds recorded per side",
            "independent_quote_freshness_verified":False}
    for side in ("bid","ask"):
        value=item.get(side+"_date")
        evidence={"raw_unix_timestamp":value if type(value) is int else None,
                  "timestamp":None,"age_seconds":None,"unit":None,"status":"MISSING_OR_INVALID"}
        if type(value) is int and value>0:
            try:
                # Observed production artifact 12578169176 returns 13-digit milliseconds.
                # Keep the original integer and explicit unit; reject microseconds/other ranges.
                if 1_000_000_000<=value<10_000_000_000:
                    seconds=value;evidence["unit"]="seconds"
                elif 1_000_000_000_000<=value<10_000_000_000_000:
                    seconds=value/1000;evidence["unit"]="milliseconds"
                else:raise ValueError("unsupported timestamp unit")
                stamp=datetime.fromtimestamp(seconds,timezone.utc)
                age=(observed-stamp).total_seconds()
                evidence.update(timestamp=stamp.isoformat(),age_seconds=age,
                                status="FUTURE" if age<0 else "STALE" if age>2 else "WITHIN_2_SECONDS")
            except (ValueError,OverflowError,OSError):
                evidence["status"]="UNSUPPORTED_TIMESTAMP"
        result[side]=evidence
    result["both_sides_within_2_seconds"]=all(result[s]["status"]=="WITHIN_2_SECONDS" for s in ("bid","ask"))
    return result


def fetch_chain(symbol, expiration, token, *, opener=urllib.request.urlopen,
                observed_at=None):
    if symbol!="SPY":raise ValueError("PACO option-chain scope is SPY only")
    if not token:raise ValueError("read-only token required")
    datetime.strptime(expiration,"%Y-%m-%d")
    params=urllib.parse.urlencode({"symbol":symbol,"expiration":expiration,"greeks":"true"})
    req=urllib.request.Request(BASE+"/markets/options/chains?"+params,headers={
        "Authorization":"Bearer "+token,"Accept":"application/json",
        "User-Agent":"oracle-paco-readonly-research/1"})
    with opener(req,timeout=25) as response:
        data=json.load(response)
    raw=(data.get("options") or {}).get("option") or []
    if isinstance(raw,dict):raw=[raw]
    observed_at=observed_at or datetime.now(timezone.utc).isoformat()
    timing_evidence({},observed_at)  # validate the observation clock even for empty chains
    results=[]
    for item in raw:
        try:
            if item.get("option_type") not in ("put","call"):continue
            symbol_id=str(item["symbol"])
            bid=float(item["bid"]);ask=float(item["ask"])
            bid_size=int(item.get("bidsize") or 0)
            ask_size=int(item.get("asksize") or 0)
            if not symbol_id or not all(isfinite(x) for x in (bid,ask)) or bid<0 or ask<=0 or bid>ask or bid_size<0 or ask_size<0:continue
            timing=timing_evidence(item,observed_at)
            results.append({"occ_symbol":symbol_id,"type":item["option_type"],
                            "expiration":expiration,"strike":item.get("strike"),
                            "bid":bid,"ask":ask,"bid_size":bid_size,"ask_size":ask_size,
                            "provider":"tradier","snapshot_observed_at":observed_at,
                            "provider_timestamp":None,"provider_quote_id":None,
                            "provider_quote_timing":timing,
                            "quote_freshness_verified":False,
                            "executable_fill_verified":False})
        except (KeyError,TypeError,ValueError,OverflowError):continue
    return {"schema":"paco-tradier-option-chain-snapshot-v1",
            "provider":"tradier","underlying":symbol,"expiration":expiration,
            "observed_at":observed_at,"contracts":results,
            "provider_timestamp_contracts":sum(all(c["provider_quote_timing"][s]["timestamp"] is not None for s in ("bid","ask")) for c in results),
            "provider_recent_contracts":sum(c["provider_quote_timing"]["both_sides_within_2_seconds"] for c in results),
            "quote_freshness_verified":False,"orders_enabled":False,
            "warning":"Snapshot retrieval time is not provider quote time. Never infer two-second freshness."}
