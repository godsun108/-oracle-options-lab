"""Independent semantic audit of hash-linked forward paper observations.

Rejects backdated entries, price revisions hidden in outcomes, unsupported fills,
unregistered signals and arithmetic inconsistencies. Never asserts alpha.
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from research.edge_forward_paper import verify, parse_utc_timestamp, session_open_utc

from research.edge_session_calendar import expected_entry_exit, eligible_cutoff

TOLERANCE_PCT = 0.000002

def _finite_positive(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value > 0

def audit(ledger):
    events = verify(ledger)
    opens = {}
    registered = {}
    outcomes = {}
    excluded = set()
    counts = defaultdict(int)
    for event in events:
        kind = event.get("type")
        counts[kind] += 1
        if event.get("orders_enabled") is not False or event.get("fill_verified") is not False:
            raise ValueError("paper event claims real order or fill")
        if "source_observed_at" in event:
            source_time = parse_utc_timestamp(event["source_observed_at"])
            cutoff = eligible_cutoff(source_time).isoformat()
            if kind == "SOURCE_OPEN_CHECKPOINT" and event["open_date"] > cutoff:
                raise ValueError("source timestamp precedes eligible price session")
            if kind == "SIGNAL_REGISTERED":
                if "registered_at" not in event:
                    raise ValueError("legacy untimed signal has incompatible source timestamp")
                if event["signal_date"] != cutoff or source_time > parse_utc_timestamp(event["registered_at"]):
                    raise ValueError("source timestamp incompatible with signal registration")
            if kind == "PAPER_OUTCOME_OBSERVED" and event["exit_date"] > cutoff:
                raise ValueError("source timestamp precedes eligible outcome session")
        if kind == "SOURCE_OPEN_CHECKPOINT":
            key = (event["symbol"], event["open_date"])
            price = event["open_price"]
            session_open_utc(key[1])
            if key in opens or not _finite_positive(price):
                raise ValueError("duplicate or invalid open checkpoint")
            opens[key] = price
        elif kind == "SIGNAL_REGISTERED":
            key = (event["symbol"], event["strategy_id"], event["signal_date"])
            if key in registered or event.get("signal") not in (0,1) or isinstance(event.get("signal"),bool):
                raise ValueError("duplicate or invalid paper signal")
            if "registered_at" in event:
                parse_utc_timestamp(event["registered_at"])
            registered[key] = event
        elif kind == "SIGNAL_EXCLUDED_TIMING":
            key = (event["symbol"], event["strategy_id"], event["signal_date"])
            if key not in registered or key in excluded or key in outcomes:
                raise ValueError("invalid timing exclusion")
            if event.get("reason") != "LEGACY_SIGNAL_HAS_NO_REGISTRATION_TIMESTAMP":
                raise ValueError("unrecognized timing exclusion")
            if "registered_at" in registered[key]:
                raise ValueError("timestamped signal cannot be excluded as legacy")
            excluded.add(key)
        elif kind == "PAPER_OUTCOME_OBSERVED":
            key = (event["symbol"], event["strategy_id"], event["signal_date"])
            if key not in registered or key in outcomes or key in excluded:
                raise ValueError("outcome lacks eligible unique signal")
            outcomes[key] = event
        else:
            raise ValueError("unrecognized paper event")
    for key, signal in registered.items():
        if "registered_at" not in signal and key not in excluded:
            raise ValueError("legacy untimed signal not quarantined")
    for key, outcome in outcomes.items():
        signal = registered[key]
        registered_at = parse_utc_timestamp(signal["registered_at"])
        entry_day = outcome["entry_date"]
        exit_day = outcome["exit_date"]
        if not (key[2] < entry_day < exit_day):
            raise ValueError("invalid entry/exit chronology")
        if session_open_utc(entry_day) <= registered_at:
            raise ValueError("retroactive opening price used as entry")
        if (entry_day, exit_day) != expected_entry_exit(key[2], registered_at):
            raise ValueError("outcome skips required exchange session")
        candidates = sorted(day for (symbol,day) in opens
                            if symbol == key[0] and day > key[2] and session_open_utc(day) > registered_at)
        if len(candidates) < 2 or candidates[:2] != [entry_day, exit_day]:
            raise ValueError("outcome is not first two eligible observed opens")
        entry = opens[(key[0], entry_day)]
        exit_price = opens[(key[0], exit_day)]
        underlying = exit_price/entry - 1
        expected = (underlying - 0.002) if signal["signal"] == 1 else 0.0
        buy_hold = underlying - 0.002
        fields = (
            ("hypothetical_net_return_pct", expected*100),
            ("hypothetical_buy_hold_return_pct", buy_hold*100),
            ("hypothetical_excess_vs_buy_hold_pct", (expected-buy_hold)*100),
        )
        for field, value in fields:
            actual = outcome.get(field)
            if not isinstance(actual,(int,float)) or isinstance(actual,bool) or not math.isfinite(actual):
                raise ValueError("missing or nonfinite outcome field: "+field)
            if abs(actual-value) > TOLERANCE_PCT:
                raise ValueError("paper outcome arithmetic mismatch: "+field)
    if ledger.get("signals_registered") != len(registered):
        raise ValueError("signal count mismatch")
    if ledger.get("outcomes_observed") != len(outcomes):
        raise ValueError("outcome count mismatch")
    if ledger.get("pending_signals") != len(registered)-len(outcomes)-len(excluded):
        raise ValueError("pending count mismatch")
    if ledger.get("signals_excluded_timing") != len(excluded):
        raise ValueError("timing exclusion count mismatch")
    if ledger.get("open_checkpoints_recorded") != len(opens):
        raise ValueError("source checkpoint count mismatch")
    return {
        "schema":"oracle-q-forward-integrity-audit-v1",
        "status":"FORWARD_LEDGER_SEMANTICS_VERIFIED",
        "hash_chain_verified":True,
        "chronological_entry_validation":True,
        "outcome_price_and_cost_math_verified":True,
        "registered_signals":len(registered),
        "excluded_legacy_signals":len(excluded),
        "forward_outcomes":len(outcomes),
        "pending_signals":len(registered)-len(outcomes)-len(excluded),
        "open_price_checkpoints":len(opens),
        "orders_enabled":False,"fill_verified":False,"edge_proven":False,
        "warning":"Ledger consistency is verified, not provider authenticity, executable fills, or profitability."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=audit(json.loads(Path(args.ledger).read_text()))
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Forward audit:",result["status"],"outcomes:",result["forward_outcomes"],
          "excluded:",result["excluded_legacy_signals"])

if __name__=="__main__":
    main()
