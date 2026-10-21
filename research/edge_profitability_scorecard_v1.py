"""Research-only proof-of-edge scorecard. Never infer trades from observations."""
import json
import math
from pathlib import Path

def score(trades, *, min_trades=30, max_drawdown_limit=0.20):
    if not isinstance(trades, list):
        raise ValueError("trades must be a list")
    seen=set(); net=[]; equity=1.0; peak=1.0; drawdown=0.0
    for t in trades:
        if not isinstance(t,dict) or not isinstance(t.get("id"),str) or not t["id"] or t["id"] in seen:
            raise ValueError("invalid or duplicate trade ID")
        seen.add(t["id"])
        if t.get("status")!="SETTLED_PAPER" or t.get("broker_fill_verified") is not False:
            raise ValueError("only settled simulated paper trades accepted")
        for k in ("gross_pnl","total_cost","starting_equity"):
            v=t.get(k)
            if not isinstance(v,(float,int)) or isinstance(v,bool) or not math.isfinite(v):
                raise ValueError("invalid "+k)
        if t["total_cost"]<0 or t["starting_equity"]<=0:
            raise ValueError("invalid costs or equity")
        value=t["gross_pnl"]-t["total_cost"]
        net.append(value)
        # Per-trade return assumes nonoverlapping, sequential trades and no deposits.
        if not math.isclose(t["starting_equity"],equity,rel_tol=1e-8,abs_tol=1e-8):
            raise ValueError("equity discontinuity or unsupported overlapping trades")
        equity+=value
        if equity<=0:
            raise ValueError("nonpositive equity")
        peak=max(peak,equity)
        drawdown=max(drawdown,(peak-equity)/peak)
    wins=sum(x for x in net if x>0)
    losses=-sum(x for x in net if x<0)
    profit_factor=wins/losses if losses>0 else (None if wins==0 else float("inf"))
    expectancy=sum(net)/len(net) if net else None
    eligible=len(net)>=min_trades and expectancy is not None and expectancy>0 and (profit_factor is not None and profit_factor>=1.10) and drawdown<=max_drawdown_limit
    return {"schema":"oracle-q-edge-scorecard-v1","mode":"RESEARCH_ONLY","orders_enabled":False,
            "sample_size":len(net),"net_pnl":sum(net),"net_expectancy_per_trade":expectancy,
            "profit_factor":profit_factor if profit_factor!=float("inf") else "INF",
            "max_drawdown":drawdown,"minimum_sample_met":len(net)>=min_trades,
            "preliminary_edge_gate_passed":eligible,
            "promotion_authorized":False,"broker_fills_verified":False,
            "warning":"Requires independently verified chronology, complete costs, and walk-forward folds before any claim of edge. Sequential nonoverlapping trades only."}

if __name__=="__main__":
    import sys
    if len(sys.argv)!=2: raise SystemExit("usage: python research/edge_profitability_scorecard_v1.py settled-paper-trades.json")
    payload=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(score(payload["trades"]),indent=2,allow_nan=False))
