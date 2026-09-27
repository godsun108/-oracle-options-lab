"""Oracle x Seldon Experiment 001 — preregistered macro-feature fusion.

Frozen design:
- Oracle population: frozen Stage-9 realized option trades.
- Oracle spec: O4_ATM_7_10DTE (Stage-11 frozen lead).
- Oracle base features: Stage-11 trend set.
- Seldon feature: 12m probability UNRATE is higher, using Experiment-004 model family.
- Seldon snapshots: quarterly, vintage-safe; carried forward to Oracle signal dates.
- Comparison: identical expanding walk-forward logistic model, L2=30, base vs base+Seldon.
- No trade authorization. Research only.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0,".")
from oracle_q.regime_features import build_regime_features
from oracle_q.walk_forward import walk_forward_predict, brier

BASE_FEATURES=["ret_5","ret_20","dist_ma20","dist_ma50","dist_ma200"]
SPEC="O4_ATM_7_10DTE"; L2=30.0; MIN_TRAIN=100
SELDON_REPO_RAW="https://raw.githubusercontent.com/godsun108/Seldon/main"

def seldon_snapshots():
    # Import the exact Seldon implementation by checking out Seldon beside Oracle in CI.
    sys.path.insert(0,"../Seldon")
    from experiments.fred_macro_004 import state,p_analogue
    cutoffs=[f"{y}-{m:02d}-{31 if m in (1,7,10) else 30:02d}" for y in range(2000,2026) for m in (1,4,7,10)]
    states=[]
    for c in cutoffs:
        try: states.append(state(c))
        except Exception as e:
            # Recent/future quarter ends may not yet be available.
            print(f"skip Seldon cutoff {c}: {type(e).__name__}",file=sys.stderr)
    key="outcome_12m"; steps=4
    for i in range(len(states)-steps):
        states[i][key]=int(states[i+steps]["unemployment"]>states[i]["unemployment"])
    rows=[]
    for i in range(12,len(states)):
        train=[r for r in states[:i] if key in r]
        if len(train)<7: continue
        cur=states[i]
        p=p_analogue(train,cur,key)
        rows.append({"macro_as_of":cur["cutoff"],"seldon_p_unrate_higher_12m":p,
                     "seldon_n_train":len(train),"seldon_vintage_safe":True})
    return pd.DataFrame(rows)

def score(ev):
    if ev.empty:return {"n":0}
    return {"n":int(len(ev)),"brier_model":brier(ev.target,ev.p_model),
            "brier_unconditional":brier(ev.target,ev.p_unconditional)}

def main():
    trades=pd.read_csv("out/oracle_stage9_options_trades.csv")
    raw=pd.read_csv("https://raw.githubusercontent.com/OStochastic/Daily-SPY-data-from-2000-2025/main/spy_data.csv",skiprows=[1,2])
    raw.columns=["date","close","high","low","open","volume"]
    raw["date"]=pd.to_datetime(raw.date)
    for c in ["close","volume"]:raw[c]=pd.to_numeric(raw[c])
    feat=build_regime_features(raw[["date","close","volume"]]); feat["date"]=pd.to_datetime(feat.date).dt.normalize()

    g=trades[(trades.status=="ok")&(trades.spec==SPEC)].copy()
    g["signal_date"]=pd.to_datetime(g.signal_date).dt.normalize()
    g["target"]=(pd.to_numeric(g.one_contract_pnl)>0).astype(int)
    z=g.merge(feat[["date"]+BASE_FEATURES],left_on="signal_date",right_on="date",how="left").sort_values("signal_date")

    macro=seldon_snapshots(); macro["macro_as_of"]=pd.to_datetime(macro.macro_as_of)
    z=pd.merge_asof(z.sort_values("signal_date"),macro.sort_values("macro_as_of"),
                    left_on="signal_date",right_on="macro_as_of",direction="backward")
    if (z.macro_as_of>z.signal_date).fillna(False).any():raise AssertionError("future macro leakage")

    base=walk_forward_predict(z,BASE_FEATURES,"target",date_col="signal_date",min_train=MIN_TRAIN,l2=L2)
    fused_features=BASE_FEATURES+["seldon_p_unrate_higher_12m"]
    fused=walk_forward_predict(z,fused_features,"target",date_col="signal_date",min_train=MIN_TRAIN,l2=L2)
    actual=z[["signal_date","target"]]
    be=actual.merge(base,on="signal_date",how="inner")
    fe=actual.merge(fused,on="signal_date",how="inner")
    common=be[["signal_date","target","p_model","p_unconditional"]].merge(
        fe[["signal_date","p_model"]],on="signal_date",suffixes=("_base","_fused"))
    common["period"]=np.select([common.signal_date.dt.year<=2016,common.signal_date.dt.year<=2021],
                               ["2008-2016","2017-2021"],default="2022-2025")
    rows=[]
    for period,q in list(common.groupby("period"))+[("FULL",common)]:
        bb=brier(q.target,q.p_model_base); fb=brier(q.target,q.p_model_fused); ub=brier(q.target,q.p_unconditional)
        rows.append({"period":period,"n":len(q),"brier_base":bb,"brier_fused":fb,
                     "delta_fused_minus_base":fb-bb,"brier_unconditional":ub,
                     "fused_improves":bool(fb<bb)})
    result={"schema":"oracle.seldon.fusion.001.v1","status":"RESEARCH_ONLY",
            "preregistered":{"oracle_spec":SPEC,"base_features":BASE_FEATURES,
              "seldon_feature":"12m probability UNRATE higher","l2":L2,"min_train":MIN_TRAIN,
              "macro_join":"latest vintage-safe quarterly snapshot on or before signal date"},
            "summary":rows}
    Path("out").mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv("out/oracle_seldon_fusion_001_summary.csv",index=False)
    common.to_csv("out/oracle_seldon_fusion_001_predictions.csv",index=False)
    Path("out/oracle_seldon_fusion_001.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
