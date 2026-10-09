"""Fail-closed PACO signal-gated quote audit. Signals must predate entry quotes."""
import argparse
import json
from datetime import date
from pathlib import Path
from research.paco_quote_outcome_audit import evaluate

def gate(comparison,signal_evidence):
    base=evaluate(comparison)
    result={"schema":"paco-signal-gated-audit-v1","orders_enabled":False,
            "strategy_profitability_proven":False,"trade_fills_verified":False,
            "status":"SIGNAL_NOT_VERIFIED","eligible_contracts":0,
            "hypothetical_outcomes":[],"rejected_contracts":base["audited_contracts"],
            "warning":"Signal evidence, execution, option freshness and historical coverage are not independently proven."}
    if signal_evidence.get("orders_enabled") is not False:
        return result
    if signal_evidence.get("status")!="CANDIDATES_REQUIRE_HISTORICAL_OPTION_QUOTES" or signal_evidence.get("spx_record_close") is not True:
        return result
    trigger=signal_evidence.get("trigger_date")
    earlier=comparison.get("earlier_collection")
    later=comparison.get("later_collection")
    try:
        if not isinstance(trigger,str) or not isinstance(earlier,str) or not isinstance(later,str):
            return result
        # Collection timestamps may include timezone offsets; compare date only.
        trigger_date=date.fromisoformat(trigger)
        earlier_date=date.fromisoformat(earlier[:10])
        later_date=date.fromisoformat(later[:10])
        if not (trigger_date<=earlier_date<=later_date):return result
        if signal_evidence.get("history_bars",0)<252:return result
    except (ValueError,TypeError):return result
    candidates={c.get("symbol") for c in signal_evidence.get("candidates",[]) if isinstance(c,dict)}
    if not candidates:return result
    selected=[r for r in base["hypothetical_outcomes"] if r.get("occ_symbol") in candidates]
    result.update({"status":"SIGNAL_GATED_OBSERVATIONAL_ONLY" if selected else "NO_MATCHING_SIGNAL_CANDIDATES",
                   "eligible_contracts":len(selected),"hypothetical_outcomes":selected,
                   "rejected_contracts":base["audited_contracts"]-len(selected),
                   "signal_trigger_date":trigger,"signal_history_bars":signal_evidence["history_bars"]})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--comparison",required=True)
    p.add_argument("--signal",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    r=gate(json.loads(Path(a.comparison).read_text()),json.loads(Path(a.signal).read_text()))
    Path(a.output).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("PACO signal-gated audit:",r["status"],"eligible:",r["eligible_contracts"])
if __name__=="__main__":main()
