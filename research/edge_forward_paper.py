"""Append-only, hash-linked delayed forward paper observations. No broker fills."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from research.edge_session_calendar import session_bounds, expected_entry_exit, validate_sequence, CALENDAR_SHA256

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

def parse_utc_timestamp(value):
    if not isinstance(value,str):
        raise ValueError("forward observation missing timestamp")
    try:
        stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("invalid forward observation timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("forward observation timestamp must include timezone")
    return stamp.astimezone(timezone.utc)

def session_open_utc(day):
    return session_bounds(day)[0]

def advance(previous,current, *, registered_at=None):
    if current.get("schema")!="oracle-q-edge-lab-v1" or current.get("orders_enabled") is not False or current.get("edge_proven") is not False:
        raise ValueError("untrusted research report")
    observed_at=parse_utc_timestamp(current.get("observed_at"))
    registration = parse_utc_timestamp(registered_at) if registered_at else observed_at
    if registration < observed_at:
        raise ValueError("registration precedes source observation")
    reports=current.get("reports")
    if not isinstance(reports,list) or not reports:
        raise ValueError("no market reports")
    events=verify(previous)
    registered={}
    settled=set()
    excluded=set()
    checkpoints={}
    for event in events:
        if event["type"]=="SOURCE_OPEN_CHECKPOINT":
            key=(event["symbol"],event["open_date"])
            if key in checkpoints:
                raise ValueError("duplicate open checkpoint")
            price=event.get("open_price")
            if not isinstance(price,(int,float)) or isinstance(price,bool) or not math.isfinite(price) or price<=0:
                raise ValueError("invalid historical open checkpoint")
            checkpoints[key]=price
            continue
        key=(event["symbol"],event["strategy_id"],event["signal_date"])
        if event["type"]=="SIGNAL_REGISTERED":
            if key in registered:
                raise ValueError("duplicate registered forward signal")
            registered[key]=event
        elif event["type"]=="PAPER_OUTCOME_OBSERVED":
            if key in settled or key in excluded or key not in registered:
                raise ValueError("invalid paper settlement event")
            settled.add(key)
        elif event["type"]=="SIGNAL_EXCLUDED_TIMING":
            if key not in registered or key in excluded or key in settled:
                raise ValueError("invalid excluded signal")
            excluded.add(key)
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
            if day in opens or not isinstance(price,(float,int)) or isinstance(price,bool) or not math.isfinite(price) or price<=0:
                raise ValueError("invalid recent open evidence")
            opens[day]=price
        if list(opens)!=sorted(opens) or report["last_completed_date"]!=dates[-1]["time"]:
            raise ValueError("recent open chronology mismatch")
        validate_sequence(list(opens), now=observed_at, require_fresh=True)
        validate_sequence(list(opens), now=registration, require_fresh=True)
        # Check every previously observed opening price before recording new evidence.
        # A vendor adjustment or correction must be investigated explicitly, not
        # silently allowed to rewrite forward paper outcome assumptions.
        for day,price in opens.items():
            key=(symbol,day)
            if key in checkpoints and checkpoints[key]!=price:
                raise ValueError("SOURCE_OPEN_REVISED: "+symbol+" "+day)
        for day,price in opens.items():
            key=(symbol,day)
            if key not in checkpoints:
                add({"type":"SOURCE_OPEN_CHECKPOINT","symbol":symbol,
                     "open_date":day,"open_price":price,
                     "source_observed_at":observed_at.isoformat(),
                     "calendar_sha256":CALENDAR_SHA256,
                     "source_report_sha256":source_sha,
                     "checkpoint_class":"SOURCE_PRICE_OBSERVATION_NOT_FORWARD_SIGNAL",
                     "orders_enabled":False,"fill_verified":False})
                checkpoints[key]=price
        for strategy in report["strategies"]:
            sid=strategy["strategy_id"]
            wanted=strategy["next_session_paper_signal"]
            if wanted not in (0,1) or isinstance(wanted,bool):
                raise ValueError("invalid paper-only signal")
            key=(symbol,sid,report["last_completed_date"])
            if key not in registered:
                event={"type":"SIGNAL_REGISTERED","symbol":symbol,"strategy_id":sid,
                       "signal_date":key[2],"signal":wanted,
                       "registered_at":registration.isoformat(),
                       "source_observed_at":observed_at.isoformat(),
                       "calendar_sha256":CALENDAR_SHA256,
                       "source_report_sha256":source_sha,
                       "orders_enabled":False,"fill_verified":False}
                add(event)
                registered[key]=event
        for key,original in list(registered.items()):
            if key[0]!=symbol or key in settled or key in excluded:
                continue
            # Older signals lacked immutable creation time. Never backfill a
            # potentially already elapsed market open as a forward fill.
            if "registered_at" not in original:
                add({"type":"SIGNAL_EXCLUDED_TIMING","symbol":symbol,
                     "strategy_id":key[1],"signal_date":key[2],
                     "reason":"LEGACY_SIGNAL_HAS_NO_REGISTRATION_TIMESTAMP",
                     "orders_enabled":False,"fill_verified":False})
                excluded.add(key)
                continue
            registered_at=parse_utc_timestamp(original["registered_at"])
            # Entry must be strictly AFTER signal registration; do not assume
            # a historical bar's open was tradeable when registration came later.
            entry_date,exit_date=expected_entry_exit(key[2],registered_at)
            if exit_date > report["last_completed_date"]:
                continue
            if entry_date not in opens or exit_date not in opens:
                raise ValueError("MISSING_REQUIRED_FORWARD_OPEN")
            entry_open,exit_open=opens[entry_date],opens[exit_date]
            direction=original["signal"]
            result=direction*(exit_open/entry_open-1)
            if direction:
                result-=0.002  # two 10bps hypothetical transitions
            benchmark=(exit_open/entry_open-1)-0.002
            add({"type":"PAPER_OUTCOME_OBSERVED","symbol":symbol,"strategy_id":key[1],
                 "signal_date":key[2],"entry_date":entry_date,"exit_date":exit_date,
                 "source_observed_at":observed_at.isoformat(),
                 "calendar_sha256":CALENDAR_SHA256,
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
            "open_checkpoints_recorded":len(checkpoints),
            "signals_excluded_timing":len(excluded),
            "pending_signals":len(registered)-len(settled)-len(excluded),
            "warning":"Signals are archived before later prices are observed; hypothetical open-to-open returns are NOT fills or validated strategy profitability."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--current",required=True)
    p.add_argument("--prior")
    p.add_argument("--output",required=True)
    a=p.parse_args()
    current=json.loads(Path(a.current).read_text())
    prior=json.loads(Path(a.prior).read_text()) if a.prior else None
    result=advance(prior,current,registered_at=datetime.now(timezone.utc).isoformat())
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Forward paper observations:",result["signals_registered"],"registered;",
          result["outcomes_observed"],"observed; pending:",result["pending_signals"])

if __name__=="__main__":
    main()
