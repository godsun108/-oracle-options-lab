"""ORACLE Proof-of-Edge Engine.

No strategy gets promoted because it looks good in-sample.
Input CSV requires: timestamp, signal, return
signal: -1, 0, +1 (or fractional exposure)
return: forward underlying/strategy return for that signal horizon.

This module evaluates chronological walk-forward folds after configurable
round-trip costs. It is intentionally model-agnostic so Oracle strategies
can be compared on the same evidence standard.
"""
from __future__ import annotations
import argparse, csv, json, math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

@dataclass
class Trade:
    timestamp: str
    pnl: float

def load(path: str, cost_bps: float) -> list[Trade]:
    out=[]
    with open(path,newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s=float(r["signal"]); ret=float(r["return"])
            if s == 0: continue
            gross=s*ret
            cost=abs(s)*cost_bps/10000.0
            out.append(Trade(r["timestamp"],gross-cost))
    return out

def metrics(ts: list[Trade]) -> dict:
    xs=[t.pnl for t in ts]
    if not xs:
        return {"trades":0,"expectancy":0,"win_rate":0,"profit_factor":0,
                "max_drawdown":0,"sharpe":0,"net_return":0}
    wins=sum(x>0 for x in xs)
    gp=sum(x for x in xs if x>0); gl=-sum(x for x in xs if x<0)
    equity=1.0; peak=1.0; mdd=0.0
    for x in xs:
        equity*=1+x; peak=max(peak,equity)
        mdd=max(mdd,(peak-equity)/peak)
    sd=pstdev(xs)
    return {
      "trades":len(xs),"expectancy":mean(xs),"win_rate":wins/len(xs),
      "profit_factor":gp/gl if gl else (float("inf") if gp else 0),
      "max_drawdown":mdd,"sharpe":mean(xs)/sd*math.sqrt(len(xs)) if sd else 0,
      "net_return":equity-1,
    }

def walk_forward(ts:list[Trade], folds:int=5, min_train:int=30)->dict:
    n=len(ts)
    if n < min_train+folds:
        return {"error":"insufficient_history","trades":n}
    step=max(1,(n-min_train)//folds)
    tests=[]
    for i in range(folds):
        start=min_train+i*step
        end=n if i==folds-1 else min(n,start+step)
        if start>=n: break
        tests.append(metrics(ts[start:end]))
    valid=[x for x in tests if x["trades"]]
    positive=sum(x["expectancy"]>0 for x in valid)
    aggregate=metrics(ts[min_train:])
    return {"folds":valid,"positive_folds":positive,
            "positive_fold_ratio":positive/len(valid) if valid else 0,
            "out_of_sample":aggregate}

def verdict(report:dict,min_trades=30,max_dd=.20,min_pf=1.10,min_positive=.60)->dict:
    m=report.get("out_of_sample",{})
    reasons=[]
    if m.get("trades",0)<min_trades: reasons.append("too_few_oos_trades")
    if m.get("expectancy",0)<=0: reasons.append("non_positive_expectancy")
    if m.get("profit_factor",0)<min_pf: reasons.append("profit_factor_below_gate")
    if m.get("max_drawdown",1)>max_dd: reasons.append("drawdown_above_gate")
    if report.get("positive_fold_ratio",0)<min_positive: reasons.append("unstable_across_folds")
    return {"decision":"TRADE_CANDIDATE" if not reasons else "NO_TRADE",
            "reasons":reasons,
            "note":"Candidate means eligible for paper-forward validation, not guaranteed profit."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv"); p.add_argument("--cost-bps",type=float,default=5)
    p.add_argument("--folds",type=int,default=5); p.add_argument("--min-train",type=int,default=30)
    a=p.parse_args()
    trades=load(a.csv,a.cost_bps)
    report=walk_forward(trades,a.folds,a.min_train)
    report["assumptions"]={"round_trip_cost_bps":a.cost_bps}
    report["gate"]=verdict(report)
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__": main()
