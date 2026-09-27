"""Oracle Q Dollar-EV Experiment 002. See frozen preregistration."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from oracle_q.regime_features import build_regime_features
BASE=["ret_5","ret_20","dist_ma20","dist_ma50","dist_ma200"]
CONTRACT=["dte","entry_delta","spread_pct","premium_pct_spot","moneyness","log_open_interest"]
ALPHA=30.;MIN_TRAIN=100

def macro():
    files=list(Path("seldon_artifact").rglob("seldon_macro_feature_12m.json")) or list(Path("seldon_artifact").rglob("*.json"))
    x=json.loads(files[0].read_text()); x=x.get("rows",x.get("features",[])) if isinstance(x,dict) else x
    q=pd.DataFrame(x); pc=next(c for c in q if c in ("probability","p_unrate_higher","seldon_p_unrate_higher_12m")); dc=next(c for c in q if c in ("macro_as_of","as_of"))
    return q[[dc,pc]].rename(columns={dc:"macro_as_of",pc:"seldon_p"}).assign(macro_as_of=lambda z:pd.to_datetime(z.macro_as_of))

def prep():
    tr=pd.read_csv("oracle/oracle_stage9_options_trades.csv");tr.signal_date=pd.to_datetime(tr.signal_date).dt.normalize()
    raw=pd.read_csv("https://raw.githubusercontent.com/OStochastic/Daily-SPY-data-from-2000-2025/main/spy_data.csv",skiprows=[1,2]);raw.columns=["date","close","high","low","open","volume"];raw.date=pd.to_datetime(raw.date)
    for c in ["close","volume"]:raw[c]=pd.to_numeric(raw[c])
    f=build_regime_features(raw[["date","close","volume"]]);f.date=pd.to_datetime(f.date).dt.normalize()
    tr["spread_pct"]=(pd.to_numeric(tr.entry_ask)-pd.to_numeric(tr.entry_bid))/pd.to_numeric(tr.entry_ask)
    tr["premium_pct_spot"]=pd.to_numeric(tr.entry_ask)/pd.to_numeric(tr.entry_spot_unadjusted);tr["moneyness"]=pd.to_numeric(tr.strike)/pd.to_numeric(tr.entry_spot_unadjusted)-1
    tr["log_open_interest"]=np.log1p(pd.to_numeric(tr.entry_open_interest))
    tr=tr.merge(f[["date"]+BASE],left_on="signal_date",right_on="date",how="left")
    m=macro();tr=pd.merge_asof(tr.sort_values("signal_date"),m.sort_values("macro_as_of"),left_on="signal_date",right_on="macro_as_of",direction="backward")
    if (tr.macro_as_of>tr.signal_date).fillna(False).any():raise AssertionError("future macro leakage")
    return tr

def walk(g,fs):
    g=g.sort_values("signal_date").reset_index(drop=True);o=[]
    for i in range(MIN_TRAIN,len(g)):
        a=g.iloc[:i];b=g.iloc[[i]];X=a[fs].astype(float);z=b[fs].astype(float)
        if X.isna().any().any() or z.isna().any().any():continue
        sc=StandardScaler().fit(X);model=Ridge(alpha=ALPHA).fit(sc.transform(X),a.one_contract_pnl.astype(float))
        o.append({"signal_date":b.signal_date.iloc[0],"pred_dollar_ev":float(model.predict(sc.transform(z))[0]),"one_contract_pnl":float(b.one_contract_pnl.iloc[0]),"option_return":float(b.option_return.iloc[0])})
    return pd.DataFrame(o)

def forecast(q):
    y=q.one_contract_pnl.to_numpy(float);p=q.pred_dollar_ev.to_numpy(float)
    return {"n":len(q),"mse_dollars":float(np.mean((y-p)**2)),"mae_dollars":float(np.mean(abs(y-p))),"corr":float(np.corrcoef(y,p)[0,1]) if len(q)>1 else None}

def econ(q):
    q=q[q.pred_dollar_ev>0].copy();d=q.one_contract_pnl.astype(float);r=q.option_return.astype(float)
    if q.empty:return {"trades":0}
    gp=float(d[d>0].sum());gl=float(-d[d<0].sum());eq=peak=1.;dd=0.
    for x in r:eq*=1+float(x);peak=max(peak,eq);dd=max(dd,(peak-eq)/peak)
    return {"trades":len(q),"mean_dollar_pnl":float(d.mean()),"total_dollar_pnl":float(d.sum()),"mean_option_return":float(r.mean()),"win_rate":float((d>0).mean()),"dollar_profit_factor":gp/gl if gl else None,"max_compounded_drawdown":dd}

def main():
    z=prep();specs={"D016":("O2_D40_2_3DTE",BASE+["seldon_p"]+CONTRACT),"D019":("O3_D25_2_3DTE",BASE)}
    out={"schema":"oracle.q.dollar_ev.002.v1","status":"BURNED_HISTORY_DISCOVERY_ONLY","candidates":{}}
    for name,(spec,fs) in specs.items():
        q=walk(z[(z.status=="ok")&(z.spec==spec)].copy(),fs);yr=pd.to_datetime(q.signal_date).dt.year
        periods={"2017-2021":q[(yr>=2017)&(yr<=2021)],"2022-2025":q[yr>=2022],"FULL":q}
        out["candidates"][name]={"structure":spec,"forecast":{k:forecast(v) for k,v in periods.items()},"economic_2022_2025":econ(periods["2022-2025"])}
    out["promotion_boundary"]="Historical discovery only. Any survivor requires frozen genuinely future paper-forward evidence."
    Path("out").mkdir(exist_ok=True);Path("out/oracle_q_dollar_ev_002.json").write_text(json.dumps(out,indent=2)+chr(10));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
