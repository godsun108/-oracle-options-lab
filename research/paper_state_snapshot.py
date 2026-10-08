"""State snapshot validation and integrity envelope for cross-run paper recovery.

No network operations; storage transport is deliberately separate. Refuse
corrupt, incompatible or mismatched strategy state. Not a broker interface.
"""
import hashlib
import json
import os
from pathlib import Path

SCHEMA=1

def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False)

def seal(plan,state):
    if state.get("mode")!="FORWARD_PAPER_ONLY" or state.get("orders_enabled") is not False:
        raise ValueError("unsafe paper state")
    payload={"schema":SCHEMA,"plan":plan,"state":state}
    return {"payload":payload,"sha256":hashlib.sha256(canonical(payload).encode()).hexdigest()}

def verify(envelope,expected_plan):
    payload=envelope["payload"]
    if payload["schema"]!=SCHEMA or payload["plan"]!=expected_plan:
        raise ValueError("schema or plan mismatch")
    digest=hashlib.sha256(canonical(payload).encode()).hexdigest()
    if digest!=envelope["sha256"]:
        raise ValueError("state integrity mismatch")
    state=payload["state"]
    if state.get("mode")!="FORWARD_PAPER_ONLY" or state.get("orders_enabled") is not False:
        raise ValueError("unsafe state")
    if state.get("cash",0)<0:
        raise ValueError("negative cash")
    return state

def write_snapshot(path,plan,state):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(seal(plan,state),indent=2,sort_keys=True)+"\n",encoding="utf-8")

def read_snapshot(path,plan):
    return verify(json.loads(Path(path).read_text(encoding="utf-8")),plan)
