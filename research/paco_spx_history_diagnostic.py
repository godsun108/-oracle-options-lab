"""Diagnose SPX daily history coverage without exposing tokens or promoting signals."""
import argparse
import json
import os
from datetime import date
from pathlib import Path
from research.multi_market_observer import eligible_cutoff,request_history

SYMBOLS=("$SPX","SPX")
def diagnose(token,*,fetch=request_history,now=None):
    cutoff=eligible_cutoff(now)
    result={"schema":"paco-spx-history-diagnostic-v1","status":"NO_USABLE_SPX_HISTORY",
            "orders_enabled":False,"signal_verified":False,"source":"tradier",
            "cutoff":cutoff.isoformat(),"symbols":[]}
    if not token:
        result["status"]="TOKEN_MISSING"
        return result
    for symbol in SYMBOLS:
        item={"symbol":symbol,"status":"UNAVAILABLE","bars":0,"first_date":None,"last_date":None}
        try:
            rows=fetch(symbol,token,"1950-01-01",cutoff.isoformat())
            valid={}
            for row in rows:
                d=date.fromisoformat(str(row["date"])[:10])
                v=float(row["close"])
                if d<=cutoff and v>0 and v<float("inf"):
                    valid[d.isoformat()]=v
            if valid:
                days=sorted(valid)
                item.update(status="HISTORY_RETURNED",bars=len(days),first_date=days[0],last_date=days[-1])
            else:
                item["status"]="NO_BARS"
        except Exception as exc:
            # Diagnostics intentionally contain only exception class, never HTTP body or token.
            item["status"]="REQUEST_FAILED"
            item["error_type"]=type(exc).__name__
        result["symbols"].append(item)
    if any(x["bars"]>=252 for x in result["symbols"]):
        result["status"]="MINIMUM_BARS_AVAILABLE_COVERAGE_UNVERIFIED"
    elif any(x["bars"]>0 for x in result["symbols"]):
        result["status"]="INSUFFICIENT_HISTORY"
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=diagnose(os.getenv("TRADIER_TOKEN",""))
    Path(args.output).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("SPX coverage diagnostic:",result["status"])
    for row in result["symbols"]:
        print("SPX symbol:",row["symbol"],"status:",row["status"],"bars:",row["bars"],"range:",row["first_date"],row["last_date"])
if __name__=="__main__":main()
