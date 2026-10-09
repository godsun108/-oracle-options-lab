"""Conservative PACO option premium comparison between two collected snapshots."""
import argparse
import json
from pathlib import Path

def compare(earlier,later):
    if any(x.get("status")!="COLLECTED" or x.get("orders_enabled") is not False for x in (earlier,later)):
        raise ValueError("both collections must be read-only and COLLECTED")
    def index(collection):
        found={}
        for snap in collection.get("snapshots",[]):
            if snap.get("provider")!="tradier" or snap.get("orders_enabled") is not False:
                raise ValueError("invalid snapshot provenance")
            for c in snap.get("contracts",[]):
                symbol=c.get("occ_symbol")
                if not symbol or symbol in found:continue
                bid=c.get("bid");ask=c.get("ask")
                if not isinstance(bid,(int,float)) or not isinstance(ask,(int,float)) or bid<0 or ask<=0 or bid>ask:continue
                found[symbol]=c
        return found
    before=index(earlier);after=index(later)
    rows=[]
    for symbol in sorted(before.keys()&after.keys()):
        a=before[symbol];b=after[symbol]
        rows.append({"occ_symbol":symbol,"type":b.get("type"),
                     "expiration":b.get("expiration"),"strike":b.get("strike"),
                     "earlier_bid":a["bid"],"earlier_ask":a["ask"],
                     "later_bid":b["bid"],"later_ask":b["ask"],
                     "midpoint_change":round((b["bid"]+b["ask"]-a["bid"]-a["ask"])/2,4),
                     "hypothetical_buy_ask_sell_bid_change":round(b["bid"]-a["ask"],4),
                     "executable_fill_verified":False,"quote_freshness_verified":False})
    return {"schema":"paco-premium-comparison-v1","status":"COMPARABLE" if rows else "NO_MATCHING_CONTRACTS",
            "earlier_collection":earlier.get("collected_at"),"later_collection":later.get("collected_at"),
            "matched_contracts":len(rows),"contracts":rows,"orders_enabled":False,
            "warning":"Observational quotes only: timestamps do not verify quote freshness, execution, or returns."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--earlier",required=True)
    p.add_argument("--later",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=compare(json.loads(Path(a.earlier).read_text()),json.loads(Path(a.later).read_text()))
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PACO matched contracts:",result["matched_contracts"])
if __name__=="__main__":main()
