"""PACO quote-based hypothetical one-contract outcome audit; never executable fills."""
import argparse
import json
import math
from pathlib import Path

def evaluate(comparison, *, fee_per_side=0.65, multiplier=100):
    if comparison.get("schema")!="paco-premium-comparison-v1" or comparison.get("orders_enabled") is not False:
        raise ValueError("invalid read-only PACO comparison")
    if comparison.get("status") not in ("COMPARABLE","NO_MATCHING_CONTRACTS"):
        raise ValueError("invalid comparison status")
    if not isinstance(fee_per_side,(int,float)) or not math.isfinite(fee_per_side) or fee_per_side<0:
        raise ValueError("invalid fee")
    if multiplier!=100:raise ValueError("only standard 100-share options supported")
    rows=[];skipped=0
    for c in comparison.get("contracts",[]):
        a=c.get("earlier_ask");b=c.get("later_bid")
        if not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or not all(map(math.isfinite,(a,b))) or a<=0 or b<0:
            skipped+=1;continue
        gross=round((b-a)*multiplier,2)
        fees=round(2*fee_per_side,2)
        cost=round(a*multiplier+fee_per_side,2)
        pnl=round(gross-fees,2)
        rows.append({"occ_symbol":c.get("occ_symbol"),"hypothetical_entry_ask":a,
                     "hypothetical_exit_bid":b,"gross_quote_change_usd":gross,
                     "round_trip_fees_usd":fees,"hypothetical_net_usd":pnl,
                     "hypothetical_return_pct":round(100*pnl/cost,4),
                     "executable_fill_verified":False,"strategy_signal_verified":False})
    wins=sum(x["hypothetical_net_usd"]>0 for x in rows)
    return {"schema":"paco-quote-outcome-audit-v1","status":"OBSERVATIONAL_ONLY" if rows else "INSUFFICIENT_DATA",
            "matched_contracts":comparison.get("matched_contracts"),
            "audited_contracts":len(rows),"skipped_contracts":skipped,
            "positive_quote_outcomes":wins,"nonpositive_quote_outcomes":len(rows)-wins,
            "fee_per_side_usd":fee_per_side,"multiplier":multiplier,
            "hypothetical_outcomes":rows,"orders_enabled":False,
            "strategy_profitability_proven":False,"trade_fills_verified":False,
            "warning":"All-contract quote outcomes are NOT strategy-selected trades, realized P&L, independent quotes, or an executable backtest. Missing timing, liquidity, slippage and signal evidence."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--comparison",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=evaluate(json.loads(Path(a.comparison).read_text()))
    Path(a.output).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("PACO observational outcome audit:",result["status"],"contracts:",result["audited_contracts"])
if __name__=="__main__":main()
