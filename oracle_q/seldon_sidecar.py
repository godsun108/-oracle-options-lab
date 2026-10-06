"""Validate a prospective Seldon research sidecar without altering Oracle."""
from __future__ import annotations
from datetime import date
import hashlib,json
REQUIRED=("as_of","source_experiment","target","horizon","probability","baseline_probability","evidence","vintage_safe","status")
def attach(payload,signal_date):
    for k in REQUIRED:
        if k not in payload: raise ValueError("missing Seldon field "+k)
    if payload["status"]!="RESEARCH_FEATURE_ONLY": raise ValueError("invalid Seldon status")
    if payload["vintage_safe"] is not True: raise ValueError("Seldon is not vintage safe")
    if date.fromisoformat(payload["as_of"])>date.fromisoformat(signal_date): raise ValueError("future Seldon leakage")
    for k in ("probability","baseline_probability"):
        if not 0<=float(payload[k])<=1: raise ValueError("invalid Seldon probability")
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return {"state":"ATTACHED","payload":payload,"payload_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "research_only":True,"can_modify_oracle_signal":False}
def unavailable():
    return {"state":"MISSING","payload":None,"payload_sha256":None,"research_only":True,"can_modify_oracle_signal":False}
