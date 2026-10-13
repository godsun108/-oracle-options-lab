"""One read-only single-date probe per rejected market; never a price fallback."""
import argparse
import hashlib
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
from research.multi_market_observer import request_history, SYMBOLS


def valid_open(row):
    try:
        value=float(row["open"])
        return math.isfinite(value) and value>0
    except (KeyError,TypeError,ValueError):
        return False


def diagnose(report, token, *, fetch=request_history):
    if report.get("schema")!="oracle-q-edge-lab-v1" or report.get("orders_enabled") is not False:
        raise ValueError("invalid diagnostic source")
    targets=[]; seen=set()
    for market in report["reports"]:
        symbol=market["symbol"]
        if symbol not in SYMBOLS or symbol in seen:
            raise ValueError("invalid or duplicate diagnostic market")
        seen.add(symbol)
        if market.get("status")!="DATA_OR_VALIDATION_FAILURE":
            continue
        day=market.get("diagnostic",{}).get("date")
        if not day:
            continue
        date.fromisoformat(day)
        originals=[row for row in market.get("source_evidence",{}).get("rows",[])
                   if row.get("date")==day]
        if len(originals)==1 and not valid_open(originals[0]):
            targets.append((symbol,day,originals[0]))
    if targets and not token:
        raise ValueError("missing read-only credential")
    results=[]
    for symbol,day,original in targets:
        result={"symbol":symbol,"date":day,"original_row":original,
                "request_started_at":datetime.now(timezone.utc).isoformat()}
        try:
            rows=fetch(symbol,token,day,day)  # Exactly one probe, no retries.
            result["received_at"]=datetime.now(timezone.utc).isoformat()
            raw=json.dumps(rows,sort_keys=True,separators=(",",":"),allow_nan=True)
            result["parsed_response_text"]=raw
            result["parsed_response_text_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
            matches=[r for r in rows if isinstance(r,dict) and r.get("date")==day] if isinstance(rows,list) else []
            result["status"]=("SINGLE_DATE_OPEN_VALID_BROAD_RESPONSE_INVALID"
                              if len(matches)==1 and valid_open(matches[0]) else
                              "SINGLE_DATE_OPEN_UNAVAILABLE_OR_INVALID")
        except (OSError,ValueError,TypeError,KeyError) as exc:
            result.update(status="PROBE_FAILED",error_type=type(exc).__name__)
        results.append(result)
    return {"schema":"oracle-q-history-diagnostic-v1","status":"DIAGNOSTIC_ONLY",
            "results":results,"orders_enabled":False,"usable_for_forward_settlement":False,
            "warning":"Separate request and receipt time; differences do not identify provider root cause. Never substitute probe rows into signals or ledger."}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    report=json.loads(Path(args.report).read_text())
    result=diagnose(report,os.getenv("TRADIER_TOKEN",""))
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Historical source diagnostics:",[(r["symbol"],r["date"],r["status"]) for r in result["results"]])


if __name__=="__main__":main()
