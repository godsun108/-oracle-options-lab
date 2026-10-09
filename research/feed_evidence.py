"""Fail-closed evidence gate for actual read-only Tradier observation artifacts.

Checks provenance and freshness, never infers trading profitability.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
from research.multi_market_observer import SYMBOLS, eligible_cutoff

def assess(payload, now=None):
    cutoff=eligible_cutoff(now)
    problems=[]
    if payload.get("schema")!="oracle-q-multi-market-observation-v1":
        problems.append("SCHEMA_MISMATCH")
    if payload.get("provider")!="tradier" or payload.get("orders_enabled") is not False or payload.get("research_only") is not True:
        problems.append("UNSAFE_OR_UNKNOWN_PROVENANCE")
    results=payload.get("results")
    if not isinstance(results,list):
        results=[]
        problems.append("RESULTS_MISSING")
    if len(results)!=len(SYMBOLS) or [r.get("symbol") for r in results if isinstance(r,dict)]!=list(SYMBOLS):
        problems.append("SYMBOL_COVERAGE_MISMATCH")
    for item in results:
        if not isinstance(item,dict):
            problems.append("INVALID_RESULT")
            continue
        symbol=item.get("symbol","UNKNOWN")
        if item.get("status")!="OBSERVATION_ONLY":
            problems.append(symbol+":NOT_OBSERVED")
            continue
        try:
            day=dt.date.fromisoformat(item["as_of"])
            if day>cutoff or (cutoff-day).days>5 or item.get("bars",0)<200:
                problems.append(symbol+":STALE_OR_INSUFFICIENT")
        except (KeyError,TypeError,ValueError):
            problems.append(symbol+":INVALID_DATE")
    return {"schema":"oracle-q-feed-evidence-v1","status":"PASS" if not problems else "FAIL",
            "cutoff":cutoff.isoformat(),"observed":sum(1 for r in results if isinstance(r,dict) and r.get("status")=="OBSERVATION_ONLY"),
            "expected":len(SYMBOLS),"problems":problems,"orders_enabled":False,
            "claim":"read-only observation quality only; no strategy edge established"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=assess(json.loads(Path(a.input).read_text(encoding="utf-8")))
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
