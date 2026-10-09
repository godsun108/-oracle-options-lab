"""Append-only, idempotent verified no-trade cash observation history.

No strategy trades, returns, or broker orders. Caller must persist output across runs.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA="oracle-q-cash-observation-ledger-v1"

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def append(ledger,baseline):
    if baseline.get("schema")!="oracle-q-cash-baseline-v1" or baseline.get("status")!="NO_TRADE_CASH_BASELINE":
        raise ValueError("unverified baseline")
    if baseline.get("orders_enabled") is not False or baseline.get("strategy_enabled") is not False:
        raise ValueError("unsafe baseline")
    if baseline.get("trades")!=0 or baseline.get("initial_cash")!=baseline.get("ending_cash"):
        raise ValueError("baseline must be no-trade cash")
    if baseline.get("return_pct")!=0 or baseline.get("realized_pnl")!=0 or baseline.get("unrealized_pnl")!=0:
        raise ValueError("nonzero performance claim")
    day=baseline.get("as_of")
    source=baseline.get("source_sha256")
    if not isinstance(day,str) or not isinstance(source,str) or len(source)!=64:
        raise ValueError("invalid observation identity")
    if ledger is None:
        entries=[]
        initial=baseline["initial_cash"]
    else:
        if ledger.get("schema")!=SCHEMA or ledger.get("orders_enabled") is not False:
            raise ValueError("invalid ledger")
        entries=ledger.get("entries")
        if not isinstance(entries,list):
            raise ValueError("invalid entries")
        initial=ledger.get("initial_cash")
        if initial!=baseline["initial_cash"]:
            raise ValueError("cash amount changed")
        previous=""
        for entry in entries:
            if entry.get("previous_hash")!=previous:
                raise ValueError("broken ledger chain")
            data={k:v for k,v in entry.items() if k!="entry_hash"}
            if digest(data)!=entry.get("entry_hash"):
                raise ValueError("ledger tampered")
            previous=entry["entry_hash"]
    if entries:
        last=entries[-1]
        if day<last["as_of"]:
            raise ValueError("observation time regression")
        if day==last["as_of"]:
            if source==last["source_sha256"]:
                return {"schema":SCHEMA,"initial_cash":initial,"orders_enabled":False,"entries":entries}
            raise ValueError("conflicting observation for same day")
    prev=entries[-1]["entry_hash"] if entries else ""
    entry={"as_of":day,"source_sha256":source,"cash":initial,"trades":0,"previous_hash":prev}
    entry["entry_hash"]=digest(entry)
    return {"schema":SCHEMA,"initial_cash":initial,"orders_enabled":False,"entries":entries+[entry]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True)
    p.add_argument("--state",required=True)
    args=p.parse_args()
    path=Path(args.state)
    old=json.loads(path.read_text()) if path.exists() else None
    baseline=json.loads(Path(args.baseline).read_text())
    new=append(old,baseline)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(new,sort_keys=True,indent=2)+"\n")
    tmp.replace(path)
    print("Cash observation checkpoints:",len(new["entries"]))
if __name__=="__main__":
    main()
