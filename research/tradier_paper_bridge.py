"""Read-only Tradier daily OHLC to persistent virtual-paper account bridge.

Requires an explicit research plan supplied by the caller. No order API calls.
"""
import argparse
import json
import os
from pathlib import Path
from research.multi_market_observer import request_history, eligible_cutoff
from research.tradier_daily_bars import validate_daily_bars
from research.persistent_forward_runner import run

def collect_paper_bars(symbol, token, now=None, fetch=request_history):
    if not token:
        raise ValueError("TRADIER_TOKEN required")
    if not isinstance(symbol,str) or not symbol.isupper() or not symbol.isalpha() or len(symbol)>8:
        raise ValueError("invalid symbol")
    cutoff=eligible_cutoff(now)
    start=(cutoff-__import__("datetime").timedelta(days=850)).isoformat()
    rows=fetch(symbol,token,start,cutoff.isoformat())
    return validate_daily_bars(rows,now)

def paper_from_tradier(plan,token,state_path,now=None,fetch=request_history):
    if not isinstance(plan,dict) or plan.get("validated") is not True:
        raise ValueError("explicit validated research plan required")
    symbol=plan.get("symbol")
    bars=collect_paper_bars(symbol,token,now,fetch)
    if not bars:
        raise ValueError("no completed Tradier daily bars")
    report=run(plan,bars,state_path)
    report.update({"source":"TRADIER_READ_ONLY_DAILY","symbol":symbol,
                   "feed_last_bar":bars[-1]["time"],"feed_bars":len(bars),
                   "orders_enabled":False})
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--plan",required=True)
    parser.add_argument("--state",required=True)
    parser.add_argument("--report",required=True)
    args=parser.parse_args()
    plan=json.loads(Path(args.plan).read_text(encoding="utf-8"))
    report=paper_from_tradier(plan,os.getenv("TRADIER_TOKEN",""),args.state)
    dest=Path(args.report)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
