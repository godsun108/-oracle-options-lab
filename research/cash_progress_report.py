"""Audit checkpoint progression without claiming any trading strategy returns."""
import argparse
import json
from pathlib import Path
from research.cash_ledger_run_summary import summarize

def report(ledger):
    # Validate the complete hash chain and cash-only invariants before reporting.
    summarize(ledger)
    entries=ledger["entries"]
    days=[e["as_of"] for e in entries]
    if days!=sorted(set(days)):
        raise ValueError("nonmonotonic or duplicate checkpoint dates")
    return {
        "schema":"oracle-q-cash-progress-v1",
        "first_observation":days[0],
        "last_observation":days[-1],
        "distinct_trading_dates":len(days),
        "cash":ledger["initial_cash"],
        "trades":0,
        "orders_enabled":False,
        "strategy_performance_available":False,
        "multi_day_continuity_observed":len(days)>=2,
        "ledger_head_sha256":entries[-1]["entry_hash"],
        "interpretation":"Only a no-trade cash baseline; does not establish strategy performance."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    data=report(json.loads(Path(a.ledger).read_text()))
    Path(a.output).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps(data,sort_keys=True))
if __name__=="__main__":
    main()
