"""Read-only PACO SPX record-close signal evidence, with fail-closed history checks."""
import argparse
import json
import math
import os
import urllib.error
from datetime import date,datetime,timezone
from pathlib import Path
from research.multi_market_observer import eligible_cutoff,request_history
from research.spx_ath_spy_puts import signal

def produce(token,collection,*,fetch=request_history,now=None):
    output={"schema":"paco-spx-signal-evidence-v1","orders_enabled":False,
            "status":"SIGNAL_EVIDENCE_UNAVAILABLE","spx_record_close":False,
            "candidates":[],"performance_established":False,
            "warning":"SPX history coverage may not establish an all-time record; no trades inferred."}
    if not token or collection.get("status")!="COLLECTED" or collection.get("orders_enabled") is not False:
        return output
    cutoff=eligible_cutoff(now)
    # The signal date must predate option entry observation, so never use today's incomplete close.
    try:
        rows=fetch("SPX",token,"1950-01-01",cutoff.isoformat())
        bars={}
        for row in rows:
            d=date.fromisoformat(str(row["date"])[:10])
            close=float(row["close"])
            if d<=cutoff and math.isfinite(close) and close>0:
                bars[d.isoformat()]=close
        ordered=[{"date":d,"close":v} for d,v in sorted(bars.items())]
        if len(ordered)<252:
            output["status"]="INSUFFICIENT_HISTORY"
            return output
        last=ordered[-1]["date"]
        entry=str(collection.get("collected_at",""))[:10]
        if not entry or last>=entry:
            output["status"]="SIGNAL_DATE_NOT_PRIOR_TO_ENTRY"
            return output
        contracts=[]
        for snap in collection.get("snapshots",[]):
            for c in snap.get("contracts",[]):
                contracts.append({"symbol":c.get("occ_symbol"),"type":c.get("type"),
                                  "expiration":c.get("expiration"),"strike":c.get("strike"),
                                  "bid":c.get("bid"),"ask":c.get("ask")})
        s=signal(ordered,contracts,as_of=last)
        output.update(s)
        output["source"]="tradier"
        output["underlying_requested"]="SPX"
        output["history_first_date"]=ordered[0]["date"]
        output["history_last_date"]=last
        output["history_coverage_complete_verified"]=False
        output["status"]="HISTORICAL_COVERAGE_UNVERIFIED" if s.get("spx_record_close") else s["status"]
        # A finite returned window cannot establish an all-time high.
        # Do not pass unverified candidates into the performance gate.
        output["candidates"]=[]
    except (urllib.error.URLError,TimeoutError,ValueError,TypeError,KeyError,OverflowError) as exc:
        output["status"]="SPX_HISTORY_UNAVAILABLE"
        output["error_type"]=type(exc).__name__
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--collection",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=produce(os.getenv("TRADIER_TOKEN",""),json.loads(Path(a.collection).read_text()))
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PACO SPX signal evidence:",result["status"])
if __name__=="__main__":main()
