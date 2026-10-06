"""Classify when saved research observations have enough later sessions for evaluation."""
from __future__ import annotations
from datetime import date

def later_sessions(signal_date, completed_dates):
    s=date.fromisoformat(signal_date)
    return sorted(d for d in completed_dates if date.fromisoformat(d)>s)

def classify(record, completed_dates):
    sig=record["canonical_signal"]
    obs=record["prospective_options"]
    later=later_sessions(sig["signal_date"],completed_dates)
    if not sig["signal"]:
        return {"state":"NO_SIGNAL","ready":True,"evaluation_date":None}
    if obs["status"]!="OBSERVED" or not obs.get("selected_contract"):
        return {"state":"NO_OBSERVATION","ready":True,"evaluation_date":None}
    if len(later)<2:
        return {"state":"PENDING","ready":False,"evaluation_date":None}
    return {"state":"READY","ready":True,"evaluation_date":later[1]}
