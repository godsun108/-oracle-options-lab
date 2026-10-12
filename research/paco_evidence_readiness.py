"""Conservative PACO research-readiness summary; never infer executable returns."""
import argparse
import json
from pathlib import Path

def assess(continuity, comparison, signal):
    if continuity.get("schema") != "paco-snapshot-continuity-v1" or continuity.get("orders_enabled") is not False:
        raise ValueError("invalid read-only PACO continuity")
    if comparison.get("schema") != "paco-premium-comparison-v1" or comparison.get("orders_enabled") is not False:
        raise ValueError("invalid read-only PACO comparison")
    if signal.get("orders_enabled") is not False:
        raise ValueError("invalid signal permissions")
    runs=int(continuity.get("runs_recorded",0))
    entries=continuity.get("entries")
    if not isinstance(entries,list) or len(entries)!=runs or runs<1:
        raise ValueError("continuity run count mismatch")
    same_day=comparison.get("same_utc_day")
    cross_day=(same_day is False and comparison.get("status")=="COMPARABLE"
               and comparison.get("matched_contracts",0)>0)
    signal_verified=(signal.get("spx_record_close") is True
                     and signal.get("history_coverage_complete_verified") is True)
    return {"schema":"paco-evidence-readiness-v1","status":"RESEARCH_NOT_VALIDATED",
            "continuity_runs":runs,"matched_contracts":comparison.get("matched_contracts",0),
            "cross_day_quote_pair_observed":bool(cross_day),
            "independent_quote_freshness_verified":False,
            "spx_ath_signal_verified":bool(signal_verified),
            "trade_fills_verified":False,"strategy_profitability_proven":False,
            "orders_enabled":False,
            "warning":"Cross-day quote pairs are not executed trades or strategy returns. A full ATH history, signal timing, quote freshness, fees and slippage require independent validation."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--continuity",required=True)
    p.add_argument("--comparison",required=True)
    p.add_argument("--signal",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=assess(*(json.loads(Path(p).read_text()) for p in
                    (args.continuity,args.comparison,args.signal)))
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PACO research readiness:",result["status"],"continuity runs:",result["continuity_runs"])
if __name__=="__main__":
    main()
