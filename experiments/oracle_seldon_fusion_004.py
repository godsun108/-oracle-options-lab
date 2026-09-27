"""Fusion 004: preregistered price-aware option expected-value research."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json, math
import numpy as np, pandas as pd
from experiments.oracle_seldon_fusion_001 import BASE_FEATURES, SPEC, L2, MIN_TRAIN, seldon_snapshots
from oracle_q.regime_features import build_regime_features

def ridge_walk(df,features):
    rows=[]
    for i in range(MIN_TRAIN,len(df)):
        train=df.iloc[:i].dropna(subset=features+["option_return"])
        test=df.iloc[[i]].dropna(subset=features)
        if len(train)<MIN_TRAIN or test.empty: continue
        X=train[features].to_numpy(float); y=train.option_return.to_numpy(float)
        mu=X.mean(0); sd=X.std(0); sd=np.where(sd==0,1,sd)
        Xs=(X-mu)/sd; xt=(test[features].to_numpy(float)-mu)/sd
        A=np.column_stack([np.ones(len(Xs)),Xs]); at=np.column_stack([np.ones(len(xt)),xt])
        pen=np.eye(A.shape[1])*L2; pen[0,0]=0
        beta=np.linalg.solve(A.T@A+pen,A.T@y)
        rows.append({"signal_date":test.signal_date.iloc[0],"pred_ev":float((at@beta)[0])})
    return pd.DataFrame(rows)

def err(g,col):
    y=g.option_return.to_numpy(float); p=g[col].to_numpy(float)
    return {"n":len(g),"mse":float(np.mean((p-y)**2)),"mae":float(np.mean(abs(p-y))),
            "correlation":float(np.corrcoef(p,y)[0,1]) if len(g)>1 else None}

def econ(g,col):
    q=g[g[col]>0].sort_values("signal_date"); r=q.option_return
    if q.empty:return {"trades":0}
    gp=float(r[r>0].sum()); gl=float(-r[r<0].sum()); eq=peak=1.; dd=0.
    for x in r: eq*=1+float(x); peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
    return {"trades":len(q),"mean_option_return":float(r.mean()),"mean_one_contract_pnl":float(q.one_contract_pnl.mean()),
            "total_one_contract_pnl":float(q.one_contract_pnl.sum()),"win_rate":float((r>0).mean()),
            "profit_factor":gp/gl if gl else None,"max_compounded_drawdown":dd}

CONTRACT_FEATURES=["dte","entry_delta","spread_pct","premium_pct_spot","moneyness","log_open_interest"]

def main():
    tr=pd.read_csv("oracle/oracle_stage9_options_trades.csv")
    raw=pd.read_csv("https://raw.githubusercontent.com/OStochastic/Daily-SPY-data-from-2000-2025/main/spy_data.csv",skiprows=[1,2])
    raw.columns=["date","close","high","low","open","volume"]; raw.date=pd.to_datetime(raw.date)
    for c in ["close","volume"]:raw[c]=pd.to_numeric(raw[c])
    feat=build_regime_features(raw[["date","close","volume"]]); feat.date=pd.to_datetime(feat.date).dt.normalize()
    z=tr[(tr.status=="ok")&(tr.spec==SPEC)].copy(); z.signal_date=pd.to_datetime(z.signal_date).dt.normalize()
    z["spread_pct"]=(pd.to_numeric(z.entry_ask)-pd.to_numeric(z.entry_bid))/pd.to_numeric(z.entry_ask)
    z["premium_pct_spot"]=pd.to_numeric(z.entry_ask)/pd.to_numeric(z.entry_spot_unadjusted)
    z["moneyness"]=pd.to_numeric(z.strike)/pd.to_numeric(z.entry_spot_unadjusted)-1
    z["log_open_interest"]=np.log1p(pd.to_numeric(z.entry_open_interest))
    z=z.merge(feat[["date"]+BASE_FEATURES],left_on="signal_date",right_on="date",how="left").sort_values("signal_date")
    macro=seldon_snapshots(); macro.macro_as_of=pd.to_datetime(macro.macro_as_of)
    z=pd.merge_asof(z.sort_values("signal_date"),macro.sort_values("macro_as_of"),left_on="signal_date",right_on="macro_as_of",direction="backward")
    if (z.macro_as_of>z.signal_date).fillna(False).any(): raise AssertionError("future macro leakage")
    base=ridge_walk(z,BASE_FEATURES).rename(columns={"pred_ev":"pred_ev_base"})
    fused=ridge_walk(z,BASE_FEATURES+["seldon_p_unrate_higher_12m"]).rename(columns={"pred_ev":"pred_ev_fused"})
    q=z[["signal_date","option_return","one_contract_pnl"]].merge(base,on="signal_date").merge(fused,on="signal_date")
    periods={"2017-2021":q[(q.signal_date.dt.year>=2017)&(q.signal_date.dt.year<=2021)],
             "2022-2025":q[q.signal_date.dt.year>=2022],"FULL":q}
    summary=[]
    for name,g in periods.items():
        row={"period":name,"n":len(g)}
        for model in ["base","macro","price","full"]:
            e=err(g,f"pred_ev_{model}"); row.update({f"mse_{model}":e["mse"],f"mae_{model}":e["mae"],f"corr_{model}":e["correlation"]})
        summary.append(row)
    h=periods["2022-2025"]
    result={"schema":"oracle.seldon.fusion.004.v1","status":"RESEARCH_ONLY_BURNED_HISTORY","contract_features":CONTRACT_FEATURES,
            "summary":summary,"economic_diagnostic_2022_2025":{m+"_pred_ev_gt_0":econ(h,f"pred_ev_{m}") for m in ["base","macro","price","full"]},
            "promotion_boundary":"Historical diagnostic only. Any candidate requires a frozen genuinely future paper-forward test."}
    Path("out").mkdir(exist_ok=True); Path("out/oracle_seldon_fusion_004.json").write_text(json.dumps(result,indent=2)+"
")
    pd.DataFrame(summary).to_csv("out/oracle_seldon_fusion_004_summary.csv",index=False); q.to_csv("out/oracle_seldon_fusion_004_predictions.csv",index=False)
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
