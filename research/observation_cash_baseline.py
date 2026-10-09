"""Auditable zero-trade cash benchmark from verified live observations.

This is NOT a trading strategy, persistent portfolio, or return claim.
"""
import argparse
import json
from pathlib import Path
from research.feed_evidence import assess
from research.multi_market_observer import SYMBOLS

def build_baseline(observation, now=None, starting_cash=2000.0):
    evidence=assess(observation,now=now)
    if evidence["status"]!="PASS":
        raise ValueError("feed evidence FAIL: "+",".join(evidence["problems"]))
    if not isinstance(starting_cash,(int,float)) or isinstance(starting_cash,bool) or not 0<starting_cash<1e12:
        raise ValueError("invalid starting cash")
    results=observation["results"]
    return {
        "schema":"oracle-q-cash-baseline-v1",
        "as_of":max(r["as_of"] for r in results),
        "symbols":list(SYMBOLS),
        "source":"VERIFIED_TRADIER_OBSERVATION",
        "source_sha256":observation["sha256"],
        "initial_cash":float(starting_cash),
        "ending_cash":float(starting_cash),
        "positions":[],
        "trades":0,
        "realized_pnl":0.0,
        "unrealized_pnl":0.0,
        "return_pct":0.0,
        "orders_enabled":False,
        "strategy_enabled":False,
        "status":"NO_TRADE_CASH_BASELINE",
        "disclaimer":"Single-observation cash reference, not strategy performance; no positions or orders."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--observation",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    observation=json.loads(Path(args.observation).read_text(encoding="utf-8"))
    result=build_baseline(observation)
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("Verified observation; zero-trade cash baseline recorded")
if __name__=="__main__":
    main()
