"""Apply Oracle's evidence gate to realized historical option trades.

Consumes Stage-9 output produced by the frozen workflow. Prices already use
next-session EOD ask for entry and following-session EOD bid for exit, so the
observed spread is naturally included in realized option_return.
"""
from __future__ import annotations
import json, math
import pandas as pd

def _metrics(g: pd.DataFrame) -> dict:
    r=pd.to_numeric(g["option_return"],errors="coerce").dropna()
    if r.empty:return {"trades":0}
    gp=float(r[r>0].sum()); gl=float(-r[r<0].sum())
    eq=1.0; peak=1.0; dd=0.0
    for x in r:
        eq*=1+float(x); peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
    sd=float(r.std(ddof=0))
    return {"trades":int(len(r)),"expectancy":float(r.mean()),
      "win_rate":float((r>0).mean()),"profit_factor":gp/gl if gl else math.inf,
      "max_drawdown":dd,"sharpe_trade":float(r.mean()/sd*math.sqrt(len(r))) if sd else 0.0,
      "compounded_return":eq-1}

def evaluate(trades:pd.DataFrame,min_oos=20)->dict:
    x=trades.loc[trades["status"].eq("ok")].copy()
    x["entry_date"]=pd.to_datetime(x["entry_date"],errors="raise")
    x["option_return"]=pd.to_numeric(x["option_return"],errors="coerce")
    rows={}
    for spec,g in x.groupby("spec"):
        g=g.sort_values("entry_date")
        # Frozen historical period boundary: discovery through 2016;
        # everything afterward is treated as non-discovery evidence here.
        discovery=g[g.entry_date.dt.year<=2016]
        oos=g[g.entry_date.dt.year>=2017]
        m=_metrics(oos)
        reasons=[]
        if m.get("trades",0)<min_oos: reasons.append("too_few_oos_trades")
        if m.get("expectancy",0)<=0: reasons.append("non_positive_oos_expectancy")
        if m.get("profit_factor",0)<1.10: reasons.append("oos_profit_factor_below_1.10")
        if m.get("max_drawdown",1)>.50: reasons.append("oos_compounded_drawdown_above_50pct")
        # Require both validation and locked holdout expectancy to be positive.
        validation=_metrics(g[(g.entry_date.dt.year>=2017)&(g.entry_date.dt.year<=2021)])
        holdout=_metrics(g[g.entry_date.dt.year>=2022])
        if validation.get("expectancy",0)<=0: reasons.append("validation_expectancy_not_positive")
        if holdout.get("expectancy",0)<=0: reasons.append("holdout_expectancy_not_positive")
        rows[str(spec)]={"discovery":_metrics(discovery),"validation":validation,
          "holdout":holdout,"out_of_sample":m,
          "decision":"PAPER_FORWARD_CANDIDATE" if not reasons else "NO_TRADE",
          "reasons":reasons}
    return {"methodology":{
      "entry":"T+1 EOD ask","exit":"T+2 EOD bid",
      "spread":"embedded in realized quotes",
      "discovery":"2008-2016","validation":"2017-2021","holdout":"2022-2025",
      "warning":"Historical evidence does not guarantee future profit."
    },"specs":rows}

def main(path="out/oracle_stage9_options_trades.csv"):
    print(json.dumps(evaluate(pd.read_csv(path)),indent=2,allow_nan=False))

if __name__=="__main__": main()
