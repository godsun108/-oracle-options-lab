"""Fail-closed cross-run continuity for read-only PACO option-chain snapshots."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def append(previous,current,run_id):
    if current.get("status")!="COLLECTED" or not current.get("snapshots"):
        raise ValueError("current PACO snapshot collection not verified")
    if current.get("orders_enabled") is not False:
        raise ValueError("orders must be disabled")
    if previous is None:
        entries=[]
    else:
        entries=previous.get("entries")
        if not isinstance(entries,list) or not entries:
            raise ValueError("invalid prior PACO continuity")
        prev_hash=None
        for entry in entries:
            body={k:v for k,v in entry.items() if k!="entry_sha256"}
            if entry.get("previous_sha256")!=prev_hash or entry.get("entry_sha256")!=digest(body):
                raise ValueError("prior PACO chain failed verification")
            prev_hash=entry["entry_sha256"]
        if previous.get("head_sha256")!=prev_hash or previous.get("runs_recorded")!=len(entries):
            raise ValueError("prior PACO head or count mismatch")
        if any(str(e["run_id"])==str(run_id) for e in entries):
            raise ValueError("duplicate run id")
    last=entries[-1]["entry_sha256"] if entries else None
    entry={"run_id":str(run_id),"collected_at":current.get("collected_at"),
           "snapshot_sha256":digest(current),"snapshot_count":len(current["snapshots"]),
           "previous_sha256":last}
    entry["entry_sha256"]=digest(entry)
    return {"schema":"paco-snapshot-continuity-v1","orders_enabled":False,
            "entries":entries+[entry],"head_sha256":entry["entry_sha256"],
            "runs_recorded":len(entries)+1}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",required=True)
    p.add_argument("--prior")
    p.add_argument("--output",required=True)
    p.add_argument("--run-id",required=True)
    args=p.parse_args()
    current=json.loads(Path(args.snapshot).read_text())
    previous=json.loads(Path(args.prior).read_text()) if args.prior and Path(args.prior).exists() else None
    result=append(previous,current,args.run_id)
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PACO continuity: VERIFIED runs:",result["runs_recorded"],"head:",result["head_sha256"])
if __name__=="__main__":
    main()
