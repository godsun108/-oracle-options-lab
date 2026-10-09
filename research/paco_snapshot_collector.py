"""Read-only PACO snapshot collector; records real provider response evidence.

Runs alongside Oracle-Q observer. No options orders, inferred fills or
two-second quote freshness claims. All raw response snapshots are research only.
"""
import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date,datetime,timezone
from pathlib import Path
from research.paco_tradier_chains import fetch_chain,BASE

def expirations(token, *, opener=urllib.request.urlopen):
    req=urllib.request.Request(BASE+"/markets/options/expirations?"+
        urllib.parse.urlencode({"symbol":"SPY","includeAllRoots":"false"}),
        headers={"Authorization":"Bearer "+token,"Accept":"application/json",
                 "User-Agent":"oracle-paco-readonly-research/1"})
    with opener(req,timeout=25) as response:
        data=json.load(response)
    rows=(data.get("expirations") or {}).get("date") or []
    return [rows] if isinstance(rows,str) else rows

def collect(token, *, today=None, fetch_expirations=None, fetch_options=None):
    if not token:raise ValueError("TRADIER_TOKEN missing")
    today=today or datetime.now(timezone.utc).date()
    get_exp=fetch_expirations or (lambda:expirations(token))
    get_chain=fetch_options or (lambda exp:fetch_chain("SPY",exp,token))
    valid=[]
    for value in get_exp():
        try:
            d=date.fromisoformat(value)
            if 30<=(d-today).days<=60:valid.append(value)
        except (ValueError,TypeError):continue
    valid=sorted(set(valid))
    if not valid:raise ValueError("no SPY expiration in 30-60 DTE range")
    snapshots=[get_chain(exp) for exp in valid[:2]]
    if any(s.get("provider")!="tradier" or s.get("orders_enabled") is not False for s in snapshots):
        raise ValueError("unexpected snapshot source or permissions")
    result={"schema":"paco-readonly-chain-collection-v1",
            "collected_at":datetime.now(timezone.utc).isoformat(),
            "source":"tradier","expirations_requested":valid[:2],
            "snapshots":snapshots,"orders_enabled":False,
            "provider_quote_freshness_verified":False,
            "trading_performance_available":False}
    result["sha256"]=hashlib.sha256(json.dumps(result,sort_keys=True,
                                               separators=(",",":")).encode()).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        result=collect(os.getenv("TRADIER_TOKEN",""))
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError, TypeError, TimeoutError) as exc:
        result={"schema":"paco-readonly-chain-collection-v1",
                "status":"FAILED","orders_enabled":False,"snapshots":[],
                "provider_quote_freshness_verified":False,
                "error_type":type(exc).__name__,
                "http_status":exc.code if isinstance(exc,urllib.error.HTTPError) else None,
                "reason":"OPTIONS_FEED_UNAVAILABLE_OR_UNAUTHORIZED"}
    else:
        result["status"]="COLLECTED" if result["snapshots"] else "EMPTY"
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PACO status:",result["status"],"snapshots:",len(result["snapshots"]))
    if result["status"]=="FAILED":
        print("PACO options collection failed:",result["error_type"],result["http_status"])
        raise SystemExit(1)
if __name__=="__main__":main()
