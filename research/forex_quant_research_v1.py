"""Research-only FX quant signal evaluator. Never places trades or fabricates prices.

Bars are chronological observed mid-prices; signals are evaluated at the last
closed bar and are not executions. No lookahead, leverage or claimed profits.
"""
import math

PAIRS = ("EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD","NZDUSD")
STRATEGIES = ("trend_20_60","mean_reversion_20","momentum_20")

def evaluate(pair, bars, *, spread_bps, slippage_bps=1.0):
    if pair not in PAIRS: raise ValueError("unsupported pair")
    if not isinstance(bars,list) or len(bars)<61: raise ValueError("need 61 observed bars")
    if not isinstance(spread_bps,(int,float)) or isinstance(spread_bps,bool) or not math.isfinite(spread_bps) or spread_bps<0: raise ValueError("invalid spread")
    if not isinstance(slippage_bps,(int,float)) or isinstance(slippage_bps,bool) or not math.isfinite(slippage_bps) or slippage_bps<0: raise ValueError("invalid slippage")
    previous=None
    for bar in bars:
        if not isinstance(bar,dict) or not isinstance(bar.get("timestamp"),str) or not isinstance(bar.get("mid"),(int,float)) or isinstance(bar["mid"],bool) or not math.isfinite(bar["mid"]) or bar["mid"]<=0: raise ValueError("invalid bar")
        from datetime import datetime,timezone
        try: ts=datetime.fromisoformat(bar["timestamp"].replace("Z","+00:00"))
        except ValueError: raise ValueError("invalid timestamp") from None
        if ts.tzinfo is None or (previous is not None and ts<=previous): raise ValueError("nonchronological bars")
        previous=ts
    p=[float(b["mid"]) for b in bars]
    mean20=sum(p[-20:])/20
    mean60=sum(p[-60:])/60
    sigma20=(sum((x-mean20)**2 for x in p[-20:])/20)**0.5
    trend="LONG" if mean20>mean60 else ("SHORT" if mean20<mean60 else "FLAT")
    z=(p[-1]-mean20)/sigma20 if sigma20 else 0
    revert="SHORT" if z>2 else ("LONG" if z< -2 else "FLAT")
    momentum="LONG" if p[-1]>p[-21] else ("SHORT" if p[-1]<p[-21] else "FLAT")
    return {"schema":"oracle.fx-research-signals.v1","mode":"RESEARCH_ONLY","pair":pair,
        "asOf":bars[-1]["timestamp"],"barCount":len(bars),
        "strategies":dict(zip(STRATEGIES,(trend,revert,momentum))),
        "assumedRoundTripExecutionBps":spread_bps+2*slippage_bps,
        "ordersEnabled":False,"brokerFillsVerified":False,
        "realizedPnlAvailable":False,"edgeProven":False,
        "warning":"Signals only. Validate feed provenance, session, bid/ask, swap, financing and out-of-sample net PnL before any trading claim."}
