"""Read-only Tradier option chain adapter; no order endpoints.

Tradier chain snapshots often omit independently reliable per-quote timestamps
and unique quote IDs. Such data MUST NOT be passed off as authenticated,
fresh two-second quote evidence. Capture snapshots for research with provenance
and mark quote freshness UNVERIFIED.
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE="https://api.tradier.com/v1"

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
    results=[]
    for item in raw:
        try:
            if item.get("option_type") not in ("put","call"):continue
            symbol_id=str(item["symbol"])
            bid=float(item["bid"]);ask=float(item["ask"])
            bid_size=int(item.get("bidsize") or 0)
            ask_size=int(item.get("asksize") or 0)
            if not symbol_id or bid<0 or ask<=0 or bid>ask:continue
            results.append({"occ_symbol":symbol_id,"type":item["option_type"],
                            "expiration":expiration,"strike":item.get("strike"),
                            "bid":bid,"ask":ask,"bid_size":bid_size,"ask_size":ask_size,
                            "provider":"tradier","snapshot_observed_at":observed_at,
                            "provider_timestamp":None,"provider_quote_id":None,
                            "quote_freshness_verified":False,
                            "executable_fill_verified":False})
        except (KeyError,TypeError,ValueError,OverflowError):continue
    return {"schema":"paco-tradier-option-chain-snapshot-v1",
            "provider":"tradier","underlying":symbol,"expiration":expiration,
            "observed_at":observed_at,"contracts":results,
            "quote_freshness_verified":False,"orders_enabled":False,
            "warning":"Snapshot retrieval time is not provider quote time. Never infer two-second freshness."}
