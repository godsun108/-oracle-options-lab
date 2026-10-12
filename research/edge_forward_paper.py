"""Append-only, hash-linked delayed forward paper observations. No broker fills."""
import argparse
import hashlib
import json
import math
from pathlib import Path

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def verify(state):
    if state is None:
        return []
    if state.get("schema")!="oracle-q-edge-forward-paper-v1" or state.get("orders_enabled") is not False:
        raise ValueError("invalid read-only forward paper ledger")
    events=state.get("events")
    if not isinstance(events,list) or state.get("events_recorded")!=len(events):
        raise ValueError("invalid forward event count")
    prior=None
    for e in events:
        body={k:v for k,v in e.items() if k!="event_sha256"}
        if e.get("previous_sha256")!=prior or e.get("event_sha256")!=digest(body):
            raise ValueError("forward event hash chain tampered")
        prior=e["event_sha256"]
    if state.get("head_sha256")!=prior:
        raise ValueError("forward ledger head mismatch")
    return list(events)

def advance(previous,current):
    if current.get("schema")!="oracle-q-edge-lab-v1" or current.get("orders_enabled") is not False or current.get("edge_proven") is not False:
        raise ValueError("untrusted research report")
    reports=current.get("reports")
    if not isinstance(reports,list) or not reports:
        raise ValueError("no market reports")
    events=verify(previous)
    registered={}
    settled=set()
    for event in events:
        key=(event["symbol"],event["strategy_id"],event["signal_date"])
        if event["type"]=="SIGNAL_REGISTERED":
            if key in registered:
                raise ValueError("duplicate registered forward signal")
            registered[key]=event
        elif event["type"]=="PAPER_OUTCOME_OBSERVED":
            if key in settled or key not in registered:
                raise ValueError("invalid paper settlement event")
            settled.add(key)
        else:
            raise ValueError("unrecognized forward event")
    head=events[-1]["event_sha256"] if events else None
    def add(body):
        nonlocal head
        body["previous_sha256"]=head
        body["event_sha256"]=digest(body)
        head=body["event_sha256"]
        events.append(body)
    source_sha=digest(current)
    for report in reports:
        if report.get("status")!="HISTORICAL_OPEN_PROXY_BACKTEST_ONLY" or report.get("price_field")!="open_only":
            raise ValueError("market report not validated for forward observation")
        symbol=report["symbol"]
        dates=report.get("recent_opens")
        if not isinstance(dates,list) or not dates:
            raise ValueError("missing recent open evidence")
        opens={}
        for row in dates:
            day=row["time"]
            price=row["open"]
            if day in opens or not isinstance(price,(float,int)) or not math.isfinite(price) or price<=0:
                raise ValueError("invalid recent open evidence")
            opens[day]=price
        if list(opens)!=sorted(opens) or report["last_completed_date"]!=dates[-1]["time"]:
            raise ValueError("recent open chronology mismatch")
        for strategy in report["strategies"]:
            sid=strategy["strategy_id"]
            wanted=strategy["next_session_paper_signal"]
            if wanted not in (0,1) or isinstance(wanted,bool):
                raise ValueError("invalid paper-only signal")
            key=(symbol,sid,report["last_completed_date"])
            if key not in registered:
                event={"type":"SIGNAL_REGISTERED","symbol":symbol,"strategy_id":sid,
                       "signal_date":key[2],"signal":wanted,"source_report_sha256":source_sha,
                       "orders_enabled":False,"fill_verified":False}
                add(event)
                registered[key]=event
        for key,original in list(registered.items()):
            if key[0]!=symbol or key in settled:
                continue
            later=[(day,price) for day,price in opens.items() if day>key[2]]
            if len(later)<2:
                continue
            entry_date,entry_open=later[0]
            exit_date,exit_open=later[1]
            direction=original["signal"]
            result=direction*(exit_open/entry_open-1)
            if direction:
                result-=0.002  # two 10bps hypothetical transitions
            benchmark=(exit_open/entry_open-1)-0.002
            add({"type":"PAPER_OUTCOME_OBSERVED","symbol":symbol,"strategy_id":key[1],
                 "signal_date":key[2],"entry_date":entry_date,"exit_date":exit_date,
                 "hypothetical_net_return_pct":round(result*100,6),
                 "hypothetical_buy_hold_return_pct":round(benchmark*100,6),
                 "hypothetical_excess_vs_buy_hold_pct":round((result-benchmark)*100,6),
                 "source_report_sha256":source_sha,
                 "orders_enabled":False,"fill_verified":False})
            settled.add(key)
    return {"schema":"oracle-q-edge-forward-paper-v1",
            "status":"FORWARD_PAPER_OBSERVATIONS_IN_PROGRESS",
            "orders_enabled":False,"fill_verified":False,"edge_proven":False,
            "events":events,"events_recorded":len(events),"head_sha256":head,
            "signals_registered":len(registered),"outcomes_observed":len(settled),
            "pending_signals":len(registered)-len(settled),
            "warning":"Signals are archived before later prices are observed; hypothetical open-to-open returns are NOT fills or validated strategy profitability."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--current",required=True)
    p.add_argument("--prior")
    p.add_argument("--output",required=True)
    a=p.parse_args()
    current=json.loads(Path(a.current).read_text())
    prior=json.loads(Path(a.prior).read_text()) if a.prior and Path(a.prior).exists() else None
    result=advance(prior,current)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Forward paper observations:",result["signals_registered"],"registered;",
          result["outcomes_observed"],"observed; pending:",result["pending_signals"])

if __name__=="__main__":
    main()
