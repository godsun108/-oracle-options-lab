"""Score frozen Oracle Q Batch 002. No post-selection tuning."""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.preprocessing import StandardScaler
from oracle_q.regime_features import build_regime_features
TREND=["ret_5","ret_20","dist_ma20","dist_ma50","dist_ma200"]
VOL=["rv10","rv20","rv60","vol_ratio_10_60"];VOLUME=["volume_ratio20"]
CONTRACT=["dte","entry_delta","spread_pct","premium_pct_spot","moneyness","log_open_interest"]
FAMILIES={"TREND":TREND,"VOL":VOL,"VOLUME":VOLUME,"MIXED":TREND+VOL+VOLUME,
"MACRO":TREND+["seldon_p"],"CONTRACT":TREND+CONTRACT,"FULL":TREND+VOL+VOLUME+["seldon_p"]+CONTRACT}
MIN_TRAIN=100;ALPHA=30.

def macro():
 fs=list(Path("seldon_artifact").rglob("seldon_macro_feature_12m.json")) or list(Path("seldon_artifact").rglob("*.json"))
 x=json.loads(fs[0].read_text());x=x.get("rows",x.get("features",[])) if isinstance(x,dict) else x;q=pd.DataFrame(x)
 pc=next(c for c in q if c in ("probability","p_unrate_higher","seldon_p_unrate_higher_12m"));dc=next(c for c in q if c in ("macro_as_of","as_of"))
 return q[[dc,pc]].rename(columns={dc:"macro_as_of",pc:"seldon_p"}).assign(macro_as_of=lambda z:pd.to_datetime(z.macro_as_of))

def prep():
 tr=pd.read_csv("oracle/oracle_stage9_options_trades.csv");tr.signal_date=pd.to_datetime(tr.signal_date).dt.normalize()
 raw=pd.read_csv("https://raw.githubusercontent.com/OStochastic/Daily-SPY-data-from-2000-2025/main/spy_data.csv",skiprows=[1,2]);raw.columns=["date","close","high","low","open","volume"];raw.date=pd.to_datetime(raw.date)
 for c in ["close","volume"]:raw[c]=pd.to_numeric(raw[c])
 f=build_regime_features(raw[["date","close","volume"]]);f.date=pd.to_datetime(f.date).dt.normalize()
 tr["spread_pct"]=(pd.to_numeric(tr.entry_ask)-pd.to_numeric(tr.entry_bid))/pd.to_numeric(tr.entry_ask)
 tr["premium_pct_spot"]=pd.to_numeric(tr.entry_ask)/pd.to_numeric(tr.entry_spot_unadjusted);tr["moneyness"]=pd.to_numeric(tr.strike)/pd.to_numeric(tr.entry_spot_unadjusted)-1
 tr["log_open_interest"]=np.log1p(pd.to_numeric(tr.entry_open_interest))
 tr=tr.merge(f[["date"]+TREND+VOL+VOLUME],left_on="signal_date",right_on="date",how="left")
 m=macro();tr=pd.merge_asof(tr.sort_values("signal_date"),m.sort_values("macro_as_of"),left_on="signal_date",right_on="macro_as_of",direction="backward")
 if (tr.macro_as_of>tr.signal_date).fillna(False).any():raise AssertionError("future macro leakage")
 return tr

def walk(g,fs,target):
 g=g.sort_values("signal_date").reset_index(drop=True);o=[]
 for i in range(MIN_TRAIN,len(g)):
  a=g.iloc[:i];b=g.iloc[[i]];X=a[fs].astype(float);z=b[fs].astype(float)
  if X.isna().any().any() or z.isna().any().any():continue
  sc=StandardScaler().fit(X);Xt=sc.transform(X);zt=sc.transform(z)
  if target=="win_probability":
   y=(a.option_return.astype(float)>0).astype(int)
   if y.nunique()<2:continue
   model=LogisticRegression(C=1/ALPHA,max_iter=2000).fit(Xt,y);pred=float(model.predict_proba(zt)[0,1])
  else:
   model=Ridge(alpha=ALPHA).fit(Xt,a.one_contract_pnl.astype(float));pred=float(model.predict(zt)[0])
  o.append({"signal_date":b.signal_date.iloc[0],"pred":pred,"pnl":float(b.one_contract_pnl.iloc[0]),"ret":float(b.option_return.iloc[0])})
 return pd.DataFrame(o)

def econ(q,target):
 sel=q.pred>.5 if target=="win_probability" else q.pred>0;q=q[sel].copy()
 if q.empty:return {"trades":0}
 d=q.pnl.astype(float);r=q.ret.astype(float);gp=float(d[d>0].sum());gl=float(-d[d<0].sum());eq=peak=1.;dd=0.
 for x in r:eq*=1+float(x);peak=max(peak,eq);dd=max(dd,(peak-eq)/peak)
 return {"trades":len(q),"mean_dollar_pnl":float(d.mean()),"total_dollar_pnl":float(d.sum()),"mean_option_return":float(r.mean()),"win_rate":float((d>0).mean()),"dollar_profit_factor":gp/gl if gl else None,"max_compounded_drawdown":dd}

def main():
 man=json.loads(Path("manifest/oracle_q_batch_002_manifest.json").read_text());z=prep();res=[]
 for c in man["selected"]:
  q=walk(z[(z.status=="ok")&(z.spec==c["option_structure"])].copy(),FAMILIES[c["regime"]],c["target"]);yr=pd.to_datetime(q.signal_date).dt.year;h=q[yr>=2022]
  if c["target"]=="win_probability":
   y=(h.ret>0).astype(float);forecast={"brier":float(np.mean((y-h.pred)**2)) if len(h) else None}
  else:forecast={"mse_dollars":float(np.mean((h.pnl-h.pred)**2)) if len(h) else None,"mae_dollars":float(np.mean(abs(h.pnl-h.pred))) if len(h) else None}
  res.append({"candidate":c,"n_predictions":len(q),"forecast_2022_2025":forecast,"economic_2022_2025":econ(h,c["target"])})
 out={"schema":"oracle.q.batch002.score.v1","status":"BURNED_HISTORY_DISCOVERY_ONLY","batch_id":man["batch_id"],"results":res,
 "multiplicity":{"batch_candidates_scored":len(res),"prior_batches_exist":True},"promotion_boundary":"No historical result establishes edge; future paper-forward evidence required."}
 Path("out").mkdir(exist_ok=True);Path("out/oracle_q_batch_002_scores.json").write_text(json.dumps(out,indent=2)+chr(10));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
