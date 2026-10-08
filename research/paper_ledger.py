"""Append-only local JSONL paper simulation ledger; never places broker orders."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from research.conditional_paper import Plan, simulate

def append_record(path, record):
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(record,sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(encoded.encode()).hexdigest()
    entry={"record_sha256":digest,"record":record}
    # Fail closed on duplicate deterministic records.
    if dest.exists():
        for line in dest.read_text(encoding="utf-8").splitlines():
            old=json.loads(line)
            if old.get("record_sha256")==digest:
                return {"status":"DUPLICATE","sha256":digest}
    with dest.open("a",encoding="utf-8") as stream:
        stream.write(json.dumps(entry,sort_keys=True)+"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {"status":"APPENDED","sha256":digest}

def evaluate(spec):
    if spec.get("mode")!="HISTORICAL_SIMULATION_ONLY":
        raise ValueError("historical simulation mode required")
    plan=Plan(**spec["plan"])
    result=simulate(plan,spec["bars"],capital=spec.get("capital",2000),
                    fee_per_share=spec.get("fee_per_share",0),
                    slippage_per_share=spec.get("slippage_per_share",0.01))
    return {"mode":"HISTORICAL_SIMULATION_ONLY","plan":spec["plan"],
            "result":result,"bar_count":len(spec["bars"]),
            "data_provenance":spec.get("data_provenance","UNSPECIFIED"),
            "orders_enabled":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--spec",required=True)
    parser.add_argument("--ledger",default="paper_records/paper_ledger.jsonl")
    args=parser.parse_args()
    with open(args.spec,encoding="utf-8") as stream:
        spec=json.load(stream)
    print(json.dumps(append_record(args.ledger,evaluate(spec)),sort_keys=True))

if __name__=="__main__":
    main()
