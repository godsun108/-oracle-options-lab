"""Oracle Q Batch-001 scorer.

Scores only candidates frozen by Q-BATCH-001. Historical outcomes through 2025
are burned discovery evidence and cannot promote a candidate to live trading.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from oracle_q.regime_features import build_regime_features

BASE=["ret_5","ret_20","dist_ma20","dist_ma50","dist_ma200"]
CONTRACT=["dte","entry_delta","spread_pct","premium_pct_spot","moneyness","log_open_interest"]
MIN_TRAIN=100; L2=30.0

def macro_snapshots():
    files=list(Path("seldon_artifact").rglob("seldon_macro_feature_12m.json"))
    if not files: files=list(Path("seldon_artifact").rglob("*.json"))
    rows=json.loads(files[0].read_text())
    if isinstance(rows,dict):
        rows=rows.get("rows",rows.get("features",[]))
    q=pd.DataFrame(rows)
    # canonical producer uses probability field
    pcol=next(c for c in q.columns if c in ("probability","p_unrate_higher","seldon_p_unrate_higher_12m"))
    dcol=next(c for c in q.columns if c in ("macro_as_of","as_of"))
    return q[[dcol,pcol]].rename(columns={dcol:"macro_as_of",pcol:"seldon_p"}).assign(macro_as_of=lambda x:pd.to_datetime(x.macro_as_of))

def prepare():
    tr=pd.read_csv("oracle/oracle_stage9_options_trades.csv")
    raw=pd.read_csv("https://raw.githubusercontent.com/OStochastic/Daily-SPY-data-from-2000-2025/main/spy_data.csv",skiprows=[1,2])
    raw.columns=["date","close","high","low","open","volume"]; raw.date=pd.to_datetime(raw.date)
    for c in ["close","volume"]: raw[c]=pd.to_numeric(raw[c])
    f=build_regime_features(raw[["date","close","volume"]]); f.date=pd.to_datetime(f.date).dt.normalize()
    tr.signal_date=pd.to_datetime(tr.signal_date).dt.normalize()
    tr["spread_pct"]=(pd.to_numeric(tr.entry_ask)-pd.to_numeric(tr.entry_bid))/pd.to_numeric(tr.entry_ask)
    tr["premium_pct_spot"]=pd.to_numeric(tr.entry_ask)/pd.to_numeric(tr.entry_spot_unadjusted)
    tr["moneyness"]=pd.to_numeric(tr.strike)/pd.to_numeric(tr.entry_spot_unadjusted)-1
    tr["log_open_interest"]=np.log1p(pd.to_numeric(tr.entry_open_interest))
    tr=tr.merge(f[["date"]+BASE],left_on="signal_date",right_on="date",how="left")
    m=macro_snapshots()
    tr=pd.merge_asof(tr.sort_values("signal_date"),m.sort_values("macro_as_of"),left_on="signal_date",right_on="macro_as_of",direction="backward")
    if (tr.macro_as_of>tr.signal_date).fillna(False).any(): raise AssertionError("future macro leakage")
    return tr

def walk(g,features,target):
    g=g.sort_values("signal_date").reset_index(drop=True); out=[]
    for i in range(MIN_TRAIN,len(g)):
        train=g.iloc[:i]; row=g.iloc[[i]]
        X=train[features].astype(float); z=row[features].astype(float)
        if X.isna().any().any() or z.isna().any().any(): continue
        sc=StandardScaler().fit(X); Xt=sc.transform(X); zt=sc.transform(z)
        if target=="win_probability":
            y=(train.option_return.astype(float)>0).astype(int)
            if y.nunique()<2: continue
            model=LogisticRegression(C=1/L2,max_iter=2000).fit(Xt,y)
            pred=float(model.predict_proba(zt)[0,1])
        else:
            y=train.option_return.astype(float)
            model=Ridge(alpha=L2).fit(Xt,y); pred=float(model.predict(zt)[0])
        out.append({"signal_date":row.signal_date.iloc[0],"pred":pred,
                    "option_return":float(row.option_return.iloc[0]),"one_contract_pnl":float(row.one_contract_pnl.iloc[0])})
    return pd.DataFrame(out)

def econ(q,select):
    q=q.loc[select(q)].copy(); r=q.option_return.astype(float)
    if q.empty:return {"trades":0}
    gp=float(r[r>0].sum());gl=float(-r[r<0].sum());eq=peak=1.;dd=0.
    for x in r: eq*=1+float(x);peak=max(peak,eq);dd=max(dd,(peak-eq)/peak)
    return {"trades":len(q),"mean_return":float(r.mean()),"mean_pnl":float(q.one_contract_pnl.mean()),
      "total_pnl":float(q.one_contract_pnl.sum()),"win_rate":float((r>0).mean()),
      "profit_factor":gp/gl if gl else None,"max_drawdown":dd}

def main():
    manifest=json.loads(Path("manifest/oracle_q_batch_001_manifest.json").read_text())
    data=prepare(); results=[]
    for c in manifest["selected"]:
        g=data[(data.status=="ok")&(data.spec==c["option_structure"])].copy()
        features=list(BASE)
        if c["regime"]=="trend+seldon12m": features+=["seldon_p"]
        if c["contract_features"]: features+=CONTRACT
        q=walk(g,features,c["target"])
        h=q[pd.to_datetime(q.signal_date).dt.year>=2022]
        if c["target"]=="win_probability":
            # frozen natural decision boundary; no threshold search
            e=econ(h,lambda z:z.pred>.5)
            forecast={"brier":float(np.mean(((h.option_return>0).astype(float)-h.pred)**2)) if len(h) else None}
        else:
            e=econ(h,lambda z:z.pred>0)
            forecast={"mse":float(np.mean((h.option_return-h.pred)**2)) if len(h) else None}
        results.append({"candidate":c,"n_predictions":len(q),"historical_2022_2025":e,"forecast":forecast})
    out={"schema":"oracle.q.batch.001.score.v1","status":"BURNED_HISTORY_DISCOVERY_ONLY",
      "batch_id":manifest["batch_id"],"results":results,
      "promotion_boundary":"No historical result can establish an edge. Any survivor must be frozen before genuinely future paper-forward evidence."}
    Path("out").mkdir(exist_ok=True);Path("out/oracle_q_batch_001_scores.json").write_text(json.dumps(out,indent=2)+chr(10))
    print(json.dumps(out,indent=2))
if __name__=="__main__":main()
